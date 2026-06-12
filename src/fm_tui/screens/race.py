"""Schermata gara: Telecronaca, monitor tempi e Auto-pausa (FOR-17, FOR-18).

La finestra principale del giocatore sulla simulazione: un RichLog
riceve la Telecronaca (fm_engine.commentary) riga per riga in ordine di
Tick, mentre una DataTable mostra la Classifica tempi live (posizione,
pilota, distacco, Mescola, eta' gomme) aggiornata cella per cella con
throttling del refresh: mai un ridisegno completo a ogni Tick.

Un worker asyncio avanza il motore Tick dopo Tick senza mai bloccare
l'event loop di Textual: velocita' 1x/2x/4x, pausa/riprendi e
skip-to-event (corsa a vuoto fino al prossimo Evento chiave o alla
bandiera a scacchi).

Auto-pausa (FOR-18): ogni Evento chiave del motore, piu' il Guasto
proprio di una vettura del giocatore, congela la simulazione una sola
volta e apre il pannello di decisione contestuale (PitOrderPanel). Da
li', o in pausa manuale con il tasto box, il manager impartisce
l'Ordine di pit con scelta della Mescola: il motore lo applica al Tick
successivo e la gara riprende fluida. Nessuna scrittura su database
durante la gara (ADR 0001).
"""

import asyncio
import time
from dataclasses import dataclass
from random import Random

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Label,
    RadioButton,
    RadioSet,
    RichLog,
    Static,
)

from fm_engine.circuits import CALENDAR_2026
from fm_engine.commentary import CommentaryContext, narrate
from fm_engine.events import (
    CarFailure,
    ChequeredFlag,
    ClassifiedResult,
    Crossover,
    RaceEvent,
    RainStarted,
    RainStopped,
    SafetyCarDeployed,
    SafetyCarEnding,
    VscDeployed,
    VscEnding,
    is_key_event,
)
from fm_engine.race import step
from fm_engine.state import (
    CarAttributes,
    CarRaceState,
    DriverOrders,
    Orders,
    PitOrder,
    RaceEntry,
    RaceState,
)
from fm_engine.tyres import Compound, CompoundSlot, nominated_compounds
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
_STATUS_AUTO_PAUSED = "Auto-pausa"
_STATUS_SKIPPING = "Skip all'evento"
_STATUS_FINISHED = "Bandiera a scacchi"

# Italian labels for the nominated compound slots offered by the panel.
_SLOT_LABELS: dict[CompoundSlot, str] = {
    CompoundSlot.SOFT: "Morbida",
    CompoundSlot.MEDIUM: "Media",
    CompoundSlot.HARD: "Dura",
}

# Italian labels for the Crossover tyre categories.
_TYRE_CATEGORY_LABELS: dict[str, str] = {
    "slick": "le slick",
    "intermediate": "le intermedie",
    "wet": "le gomme da bagnato",
}

_MANUAL_PANEL_DESCRIPTION = "Pausa ai box: ordinare un pit stop?"


@dataclass(frozen=True)
class PitDecision:
    """La decisione presa dal pannello: quale pilota e quale Mescola."""

    driver_id: int
    compound: Compound


class PitOrderPanel(ModalScreen[PitDecision | None]):
    """Pannello di decisione contestuale dell'Ordine di pit (FOR-18).

    Descrive l'Evento chiave (o la pausa manuale) e offre la scelta di
    pilota e Mescola. dismiss(PitDecision) = pit ordinato;
    dismiss(None) = nessun Ordine.
    """

    NAME = "pit_order_panel"

    DEFAULT_CSS = """
    PitOrderPanel {
        align: center middle;
    }

    PitOrderPanel #pit-window {
        width: 70;
        height: auto;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    PitOrderPanel #pit-description {
        margin-bottom: 1;
    }

    PitOrderPanel RadioSet {
        height: auto;
        margin-bottom: 1;
    }

    PitOrderPanel #pit-buttons {
        height: auto;
        align-horizontal: center;
    }

    PitOrderPanel #pit-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Riprendi senza ordini"),
    ]

    def __init__(
        self,
        description: str,
        drivers: tuple[tuple[int, str], ...],
        compounds: tuple[tuple[Compound, str], ...],
        preselected: Compound,
    ) -> None:
        super().__init__(name=self.NAME)
        self._description = description
        self._drivers = drivers
        self._compounds = compounds
        self._preselected = preselected

    @property
    def description(self) -> str:
        """Il testo contestuale mostrato in testa al pannello."""
        return self._description

    def compose(self) -> ComposeResult:
        with Vertical(id="pit-window"):
            yield Label(self._description, id="pit-description")
            yield Label("Pilota da richiamare ai box:")
            with RadioSet(id="pit-drivers"):
                for index, (driver_id, name) in enumerate(self._drivers):
                    yield RadioButton(name, value=index == 0, id=f"pit-driver-{driver_id}")
            yield Label("Mescola da montare:")
            with RadioSet(id="pit-compounds"):
                for compound, label in self._compounds:
                    yield RadioButton(
                        label,
                        value=compound is self._preselected,
                        id=f"pit-compound-{compound.value}",
                    )
            with Horizontal(id="pit-buttons"):
                yield Button("Ordina il pit", variant="primary", id="confirm-pit")
                yield Button("Riprendi senza ordini", id="dismiss-panel")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-pit":
            self.dismiss(self._decision())
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _decision(self) -> PitDecision | None:
        """La coppia (pilota, Mescola) selezionata, o None se incompleta."""
        driver_button = self.query_one("#pit-drivers", RadioSet).pressed_button
        compound_button = self.query_one("#pit-compounds", RadioSet).pressed_button
        if driver_button is None or compound_button is None or driver_button.id is None:
            return None
        if compound_button.id is None:
            return None
        driver_id = int(driver_button.id.removeprefix("pit-driver-"))
        compound = Compound(compound_button.id.removeprefix("pit-compound-"))
        return PitDecision(driver_id=driver_id, compound=compound)


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
        Binding("b", "pit_order", "Ordine di pit"),
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
        # Auto-pause bookkeeping (FOR-18): the player's drivers, the pit
        # orders queued for the next Tick and the key events already
        # handled (each one pauses exactly once).
        self._player_driver_ids = tuple(
            car.entry.driver.id for car in state.cars if car.entry.team_id == PLAYER_TEAM_ID
        )
        self._pending_pits: dict[int, Compound] = {}
        self._handled_key_events: set[RaceEvent] = set()
        self._auto_paused = False
        self._panel_open = False
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

    @property
    def is_auto_paused(self) -> bool:
        """True se la pausa corrente e' un'Auto-pausa da Evento chiave."""
        return self._auto_paused and not self._resume.is_set()

    @property
    def race_state(self) -> RaceState:
        """Lo stato di gara dopo l'ultimo Tick simulato."""
        return self._state

    @property
    def pending_pit_orders(self) -> dict[int, Compound]:
        """Gli Ordini di pit in coda per il prossimo Tick (copia)."""
        return dict(self._pending_pits)

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

        Ogni iterazione attende l'eventuale pausa, consuma gli Ordini
        di pit in coda, simula un giro, scrive la cronaca e aggiorna il
        monitor, poi cede il controllo all'event loop: in skip con uno
        sleep(0), altrimenti con il ritardo della velocita' scelta. Gli
        Eventi chiave nuovi del Tick scatenano l'Auto-pausa (FOR-18).
        """
        while not self._state.finished:
            await self._resume.wait()
            self._state, events = step(self._state, self._take_orders())
            self._write_commentary(events)
            for event in events:
                if isinstance(event, ChequeredFlag):
                    self._classification = event.classification
            triggers = self._new_triggers(events)
            if self._state.finished:
                self._skipping = False
            elif triggers:
                # Auto-pause: freeze on the spot, then ask the manager.
                self._skipping = False
                self._auto_pause(triggers)
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
        if self._state.finished or self._panel_open:
            return
        if self._resume.is_set():
            self._resume.clear()
            self._skipping = False
            self._update_header()
        else:
            self._resume_simulation()

    def action_speed(self, multiplier: str) -> None:
        """Imposta la velocita' di simulazione a 1x, 2x o 4x."""
        if self._state.finished:
            return
        self._speed = int(multiplier)
        self._skipping = False
        self._update_header()

    def action_skip_to_event(self) -> None:
        """Corre a vuoto fino al prossimo Evento chiave o alla bandiera."""
        if self._state.finished or self._panel_open:
            return
        self._skipping = True
        self._resume_simulation()

    def action_pit_order(self) -> None:
        """Apre il pannello dell'Ordine di pit, mettendo in pausa se serve."""
        if self._state.finished or self._panel_open:
            return
        was_running = self._resume.is_set()
        self._resume.clear()
        self._skipping = False
        self._update_header()
        self._open_pit_panel(_MANUAL_PANEL_DESCRIPTION, resume_on_dismiss=was_running)

    def action_back(self) -> None:
        """Lascia la schermata gara e torna alla griglia."""
        self.app.pop_screen()

    # ------------------------------------------------------------------
    # Auto-pause and the pit order panel (FOR-18)
    # ------------------------------------------------------------------

    def _take_orders(self) -> Orders | None:
        """Gli Ordini in coda per il prossimo Tick; la coda si svuota."""
        if not self._pending_pits:
            return None
        drivers = {
            driver_id: DriverOrders(pit=PitOrder(compound=compound))
            for driver_id, compound in self._pending_pits.items()
        }
        self._pending_pits.clear()
        return Orders(drivers=drivers)

    def _new_triggers(self, events: tuple[RaceEvent, ...]) -> tuple[RaceEvent, ...]:
        """Gli inneschi di Auto-pausa non ancora gestiti tra gli eventi.

        Eventi chiave del motore (is_key_event) piu' il Guasto proprio;
        ogni evento entra nel registro dei gestiti alla prima vista,
        cosi' lo stesso Evento chiave non scatena mai due Auto-pause.
        """
        triggers: list[RaceEvent] = []
        for event in events:
            if not (is_key_event(event) or self._is_own_failure(event)):
                continue
            if event in self._handled_key_events:
                continue
            self._handled_key_events.add(event)
            triggers.append(event)
        return tuple(triggers)

    def _is_own_failure(self, event: RaceEvent) -> bool:
        """True per il Guasto di una vettura del giocatore."""
        return isinstance(event, CarFailure) and event.driver_id in self._player_driver_ids

    def _auto_pause(self, triggers: tuple[RaceEvent, ...]) -> None:
        """Congela la simulazione e apre il pannello di decisione."""
        self._resume.clear()
        self._auto_paused = True
        description = "\n".join(self._trigger_description(event) for event in triggers)
        self._open_pit_panel(description, resume_on_dismiss=True)

    def _open_pit_panel(self, description: str, resume_on_dismiss: bool) -> None:
        """Mostra il PitOrderPanel per i piloti del giocatore in gara.

        Se nessuna vettura del giocatore e' in pista non c'e' niente da
        decidere: la pausa resta, il pannello no. Alla chiusura: con
        una decisione il pit va in coda e la gara riprende; senza
        decisione riprende solo se resume_on_dismiss e' True.
        """
        drivers = tuple(
            (car.entry.driver.id, self._commentary_context.driver_name(car.entry.driver.id))
            for car in self._state.cars
            if car.entry.driver.id in self._player_driver_ids
        )
        if not drivers:
            return
        nominated = nominated_compounds(self._state.circuit)
        compounds = tuple(
            (nominated[slot], f"{_SLOT_LABELS[slot]} ({nominated[slot].value.upper()})")
            for slot in (CompoundSlot.SOFT, CompoundSlot.MEDIUM, CompoundSlot.HARD)
        ) + ((Compound.INTERMEDIATE, "Intermedia"), (Compound.WET, "Bagnato"))
        self._panel_open = True

        def on_close(decision: PitDecision | None) -> None:
            self._panel_open = False
            if decision is not None:
                self._pending_pits[decision.driver_id] = decision.compound
                self._resume_simulation()
            elif resume_on_dismiss:
                self._resume_simulation()
            else:
                self._update_header()

        panel = PitOrderPanel(
            description=description,
            drivers=drivers,
            compounds=compounds,
            preselected=nominated[CompoundSlot.MEDIUM],
        )
        self.app.push_screen(panel, on_close)

    def _resume_simulation(self) -> None:
        """Riprende la simulazione esattamente da dove si era fermata."""
        self._auto_paused = False
        self._resume.set()
        self._update_header()

    def _trigger_description(self, event: RaceEvent) -> str:
        """La descrizione contestuale di un innesco di Auto-pausa."""
        if isinstance(event, SafetyCarDeployed):
            return "Safety car in pista: box ora a costo ridotto? Quale Mescola?"
        if isinstance(event, SafetyCarEnding):
            return "La Safety car rientra: ultima occasione di sosta scontata prima del verde."
        if isinstance(event, VscDeployed):
            return "VSC attivo: pit stop scontato finche' dura. Box ora?"
        if isinstance(event, VscEnding):
            return "Il VSC sta per finire: ultima chance di sosta scontata."
        if isinstance(event, RainStarted):
            return "Pioggia in arrivo: passare a gomme da bagnato?"
        if isinstance(event, RainStopped):
            return "La pioggia e' cessata: la pista si asciuga, valutare il rientro in slick."
        if isinstance(event, Crossover):
            label = _TYRE_CATEGORY_LABELS.get(event.to_category, event.to_category)
            return f"Crossover gomme: ora convengono {label}. Box per il cambio?"
        if isinstance(event, CarFailure):
            name = self._commentary_context.driver_name(event.driver_id)
            return f"Guasto per {name}: la sua vettura si ferma."
        return "Evento chiave in pista: decidere ora."

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
        elif self.is_auto_paused:
            status = _STATUS_AUTO_PAUSED
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
