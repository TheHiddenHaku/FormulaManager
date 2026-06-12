"""Schermata gara: Telecronaca in streaming e monitor tempi live (FOR-17).

La finestra principale del giocatore sulla simulazione: un RichLog
riceve la Telecronaca (fm_engine.commentary) riga per riga in ordine di
Tick, mentre una DataTable mostra la Classifica tempi live (posizione,
pilota, distacco, Mescola, eta' gomme) aggiornata cella per cella con
throttling del refresh: mai un ridisegno completo a ogni Tick.

Un worker asyncio avanza il motore Tick dopo Tick senza mai bloccare
l'event loop di Textual: velocita' 1x/2x/4x, pausa/riprendi e
skip-to-event (corsa a vuoto fino al prossimo Evento chiave o alla
bandiera a scacchi; sull'Evento chiave la simulazione si ferma in pausa
cosi' il manager puo' leggere, l'Auto-pausa vera arriva con FOR-18).

Niente Ordini e niente scritture su database durante la gara (ADR
0001): la schermata consuma soltanto step() e narrate().
"""

import asyncio
import time
from random import Random

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, RichLog, Static

from fm_engine.circuits import CALENDAR_2026
from fm_engine.commentary import CommentaryContext, narrate
from fm_engine.events import ChequeredFlag, ClassifiedResult, RaceEvent, is_key_event
from fm_engine.race import step
from fm_engine.state import CarAttributes, CarRaceState, RaceEntry, RaceState
from fm_engine.world.models import PLAYER_TEAM_ID, World

# Seconds of real time between two Ticks, per simulation speed.
TICK_DELAY_SECONDS: dict[int, float] = {1: 1.2, 2: 0.6, 4: 0.3}

# Minimum seconds between two monitor refreshes: during skip-to-event
# the Ticks run much faster than this, and the table is not redrawn for
# every one of them.
MONITOR_REFRESH_INTERVAL_SECONDS = 0.1

# Italian labels for the fitted compound shown in the live monitor.
_COMPOUND_LABELS: dict[str, str] = {
    "c1": "C1",
    "c2": "C2",
    "c3": "C3",
    "c4": "C4",
    "c5": "C5",
    "intermediate": "Inter",
    "wet": "Bagnato",
}

_LEADER_GAP = "-"
_DNF_LABEL = "Abbandono"
_EMPTY_CELL = "-"

# UI labels for the simulation status shown in the header.
_STATUS_RUNNING = "In corsa"
_STATUS_PAUSED = "In pausa"
_STATUS_SKIPPING = "Skip all'evento"
_STATUS_FINISHED = "Bandiera a scacchi"


def race_entries(world: World) -> tuple[RaceEntry, ...]:
    """Le 22 iscritte alla gara dal Mondo della Carriera.

    I 2 piloti del giocatore corrono sulla sua vettura iniziale, quindi
    il Setup squadra deve essere completato; le squadre AI schierano i
    loro contrattualizzati. L'ordine e' giocatore prima, poi le AI:
    sara' la Qualifica a decidere la griglia.
    """
    if not world.player_slot.is_set_up:
        raise ValueError("player slot not set up yet: no car to race with")
    drivers_by_id = {driver.id: driver for driver in world.drivers}
    entries: list[RaceEntry] = []
    player_car = CarAttributes.from_player_slot(world.player_slot)
    for contract in world.contracts_of(PLAYER_TEAM_ID):
        entries.append(
            RaceEntry(
                driver=drivers_by_id[contract.driver_id],
                team_id=PLAYER_TEAM_ID,
                car=player_car,
            )
        )
    for team in world.ai_teams:
        car = CarAttributes.from_team(team)
        for contract in world.contracts_of(team.id):
            entries.append(
                RaceEntry(driver=drivers_by_id[contract.driver_id], team_id=team.id, car=car)
            )
    return tuple(entries)


def commentary_context(world: World) -> CommentaryContext:
    """Il contesto della Telecronaca: nomi al posto degli id del motore."""
    team_names = {team.id: team.name for team in world.ai_teams}
    if world.player_slot.name:
        team_names[PLAYER_TEAM_ID] = world.player_slot.name
    return CommentaryContext(
        driver_names={driver.id: driver.name for driver in world.drivers},
        team_names=team_names,
        circuit_names={circuit.code: circuit.name for circuit in CALENDAR_2026},
    )


class RaceScreen(Screen):
    """La Gara interattiva: cronaca in streaming e monitor tempi live."""

    NAME = "race"

    DEFAULT_CSS = """
    RaceScreen #race-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    RaceScreen #race-body {
        height: 1fr;
    }

    RaceScreen #commentary {
        width: 1fr;
        margin: 0 1;
        border: solid $primary;
    }

    RaceScreen #monitor {
        width: auto;
        margin-right: 1;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_pause", "Pausa/Riprendi"),
        Binding("1", "speed('1')", "1x"),
        Binding("2", "speed('2')", "2x"),
        Binding("4", "speed('4')", "4x"),
        Binding("s", "skip_to_event", "Salta all'evento"),
        Binding("escape", "back", "Lascia la gara"),
    ]

    def __init__(
        self,
        state: RaceState,
        initial_events: tuple[RaceEvent, ...],
        context: CommentaryContext,
    ) -> None:
        super().__init__(name=self.NAME)
        self._state = state
        self._initial_events = initial_events
        self._commentary_context = context
        # Commentary RNG stream, separate from the engine's (seed, lap)
        # streams: deterministic text for a given race seed.
        self._commentary_rng = Random(state.seed)
        self._speed = 1
        self._skipping = False
        self._resume = asyncio.Event()
        self._resume.set()
        self._classification: tuple[ClassifiedResult, ...] | None = None
        # Cell cache for per-cell updates: (row index, column index) -> value.
        self._cells: dict[tuple[int, int], str] = {}
        self._row_keys: list[object] = []
        self._column_keys: list[object] = []
        self._last_monitor_refresh = 0.0

    # ------------------------------------------------------------------
    # Read-only state, for the header and the Pilot tests
    # ------------------------------------------------------------------

    @property
    def race_finished(self) -> bool:
        """True dopo la bandiera a scacchi."""
        return self._state.finished

    @property
    def current_lap(self) -> int:
        """L'ultimo giro completato."""
        return self._state.lap

    @property
    def is_paused(self) -> bool:
        """True se la simulazione e' congelata in attesa di riprendere."""
        return not self._resume.is_set()

    @property
    def speed_multiplier(self) -> int:
        """La velocita' di simulazione corrente (1, 2 o 4)."""
        return self._speed

    @property
    def is_skipping(self) -> bool:
        """True durante la corsa a vuoto verso il prossimo Evento chiave."""
        return self._skipping

    # ------------------------------------------------------------------
    # Layout and start-up
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="race-header")
        with Horizontal(id="race-body"):
            yield RichLog(id="commentary", wrap=True, markup=False, highlight=False)
            yield DataTable(id="monitor", cursor_type="none", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#monitor", DataTable)
        self._column_keys = list(
            table.add_columns("Pos", "Pilota", "Distacco", "Mescola", "Eta' gomme")
        )
        for index, row in enumerate(self._monitor_rows()):
            self._row_keys.append(table.add_row(*row, key=f"slot-{index}"))
            for column_index, value in enumerate(row):
                self._cells[(index, column_index)] = value
        self._write_commentary(self._initial_events)
        self.run_worker(self._run_race(), exclusive=True)

    # ------------------------------------------------------------------
    # The asyncio worker: one Tick at a time, never blocking the loop
    # ------------------------------------------------------------------

    async def _run_race(self) -> None:
        """Avanza il motore Tick dopo Tick fino alla bandiera a scacchi.

        Ogni iterazione attende l'eventuale pausa, simula un giro,
        scrive la cronaca e aggiorna il monitor, poi cede il controllo
        all'event loop: in skip con uno sleep(0), altrimenti con il
        ritardo della velocita' scelta.
        """
        while not self._state.finished:
            await self._resume.wait()
            self._state, events = step(self._state)
            self._write_commentary(events)
            for event in events:
                if isinstance(event, ChequeredFlag):
                    self._classification = event.classification
            if self._skipping and (
                self._state.finished or any(is_key_event(event) for event in events)
            ):
                # The skip found its event: freeze so the manager can read.
                self._skipping = False
                if not self._state.finished:
                    self._resume.clear()
            self._refresh_monitor(force=self._state.finished or self.is_paused)
            self._update_header()
            if self._state.finished:
                break
            if self._skipping:
                await asyncio.sleep(0)
            else:
                await asyncio.sleep(TICK_DELAY_SECONDS[self._speed])
        self._refresh_monitor(force=True)
        self._update_header()

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def action_toggle_pause(self) -> None:
        """Congela o riprende la simulazione; la tabella resta consultabile."""
        if self._state.finished:
            return
        if self._resume.is_set():
            self._resume.clear()
            self._skipping = False
        else:
            self._resume.set()
        self._update_header()

    def action_speed(self, multiplier: str) -> None:
        """Imposta la velocita' di simulazione a 1x, 2x o 4x."""
        if self._state.finished:
            return
        self._speed = int(multiplier)
        self._skipping = False
        self._update_header()

    def action_skip_to_event(self) -> None:
        """Corre a vuoto fino al prossimo Evento chiave o alla bandiera."""
        if self._state.finished:
            return
        self._skipping = True
        self._resume.set()
        self._update_header()

    def action_back(self) -> None:
        """Lascia la schermata gara e torna alla griglia."""
        self.app.pop_screen()

    # ------------------------------------------------------------------
    # Commentary and live monitor
    # ------------------------------------------------------------------

    def _write_commentary(self, events: tuple[RaceEvent, ...]) -> None:
        """Le righe di Telecronaca degli eventi del Tick, in ordine."""
        log = self.query_one("#commentary", RichLog)
        for line in narrate(events, self._commentary_context, self._commentary_rng):
            log.write(line)

    def _monitor_rows(self) -> list[tuple[str, str, str, str, str]]:
        """Le righe correnti del monitor: in gara prima, Abbandoni in coda.

        A bandiera a scacchi esposta usa la classifica finale (penalita'
        bi-mescola incluse), con il distacco dal vincitore.
        """
        state = self._state
        rows: list[tuple[str, str, str, str, str]] = []
        if self._classification is not None:
            cars_by_id = {car.entry.driver.id: car for car in state.cars}
            for result in self._classification:
                car = cars_by_id[result.driver_id]
                gap = (
                    _LEADER_GAP if result.position == 1 else f"+{result.gap_to_winner_seconds:.3f}"
                )
                rows.append(self._car_row(str(result.position), car, gap))
        else:
            for car in state.cars:
                gap = _LEADER_GAP if car.position == 1 else f"+{car.gap_to_leader_seconds:.3f}"
                rows.append(self._car_row(str(car.position), car, gap))
        # Retired cars at the bottom, most recent retirement first.
        for car in reversed(state.dnfs):
            rows.append(self._car_row(_EMPTY_CELL, car, _DNF_LABEL))
        return rows

    @staticmethod
    def _car_row(position: str, car: CarRaceState, gap: str) -> tuple[str, str, str, str, str]:
        compound = car.tyres.compound.value
        return (
            position,
            car.entry.driver.name,
            gap,
            _COMPOUND_LABELS.get(compound, compound),
            f"{car.tyres.age_laps} giri",
        )

    def _refresh_monitor(self, force: bool = False) -> None:
        """Aggiorna il monitor cella per cella, con throttling temporale.

        Solo le celle cambiate vengono toccate; sotto l'intervallo
        minimo il refresh viene saltato del tutto (skip-to-event macina
        Tick molto piu' in fretta del limite).
        """
        now = time.monotonic()
        if not force and now - self._last_monitor_refresh < MONITOR_REFRESH_INTERVAL_SECONDS:
            return
        self._last_monitor_refresh = now
        table = self.query_one("#monitor", DataTable)
        for row_index, row in enumerate(self._monitor_rows()):
            for column_index, value in enumerate(row):
                if self._cells.get((row_index, column_index)) == value:
                    continue
                table.update_cell(
                    self._row_keys[row_index],
                    self._column_keys[column_index],
                    value,
                    update_width=True,
                )
                self._cells[(row_index, column_index)] = value

    def _header_text(self) -> str:
        state = self._state
        if state.finished:
            status = _STATUS_FINISHED
        elif self.is_paused:
            status = _STATUS_PAUSED
        elif self._skipping:
            status = _STATUS_SKIPPING
        else:
            status = f"{_STATUS_RUNNING} {self._speed}x"
        return (
            f"Gara: {self._commentary_context.circuit_name(state.circuit.code)}  |  "
            f"Giro {state.lap}/{state.total_laps}  |  {status}"
        )

    def _update_header(self) -> None:
        self.query_one("#race-header", Static).update(self._header_text())
