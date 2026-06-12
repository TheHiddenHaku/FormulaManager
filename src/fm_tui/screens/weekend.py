"""Schermata weekend: il flusso del Gran Premio sessione per sessione (FOR-21).

E' il guscio TUI della macchina a stati del motore (fm_engine.weekend):
mostra le sessioni del Formato weekend Standard con il loro stato e
lancia la prossima da giocare. Ogni sessione vive nella sua schermata
(PracticeScreen, QualifyingScreen, RaceScreen) e alla chiusura
restituisce l'esito: questa schermata avanza la macchina a stati e
scrive il Checkpoint transazionale (fine sessione e pre-gara, ADR 0001
e CONTEXT.md). Gli effetti dei Programmi delle libere viaggiano nello
stato weekend e vengono passati a Qualifiche e Gara.

Edge case del Checkpoint: se la scrittura fallisce, lo stato appena
giocato resta in memoria, l'errore e' mostrato e il salvataggio e'
ritentabile (tasto s); il Checkpoint successivo salva comunque l'intera
Carriera, quindi un retry riuscito riassorbe ogni arretrato. Il
Checkpoint pre-gara e' bloccante: senza salvataggio la Gara non parte.
"""

from dataclasses import replace

import psycopg
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

from fm_engine.career import Career
from fm_engine.circuits import circuit_by_code
from fm_engine.events import ClassifiedResult
from fm_engine.practice import PracticeSessionResult
from fm_engine.qualifying import QualifyingResult
from fm_engine.race import start_race
from fm_engine.weekend import (
    WeekendPhase,
    WeekendState,
    advance_after_practice,
    advance_after_qualifying,
    advance_after_race,
)
from fm_persistence import connect, save_career
from fm_tui.screens.practice import PracticeScreen
from fm_tui.screens.qualifying import QualifyingScreen
from fm_tui.screens.race import RaceScreen, commentary_context, race_entries
from fm_tui.screens.race_result import RaceResultScreen

# Italian labels of the weekend phases, in playing order.
_PHASE_LABELS: dict[WeekendPhase, str] = {
    WeekendPhase.FP1: "FP1 (prove libere)",
    WeekendPhase.FP2: "FP2 (prove libere)",
    WeekendPhase.FP3: "FP3 (prove libere)",
    WeekendPhase.QUALIFYING: "Qualifiche (Q1/Q2/Q3)",
    WeekendPhase.RACE: "Gara",
}

_DONE_MARKER = "[conclusa]"
_NEXT_MARKER = "[da giocare] <-- prossima"
_PENDING_MARKER = "[in attesa]"

_SAVED_LABEL = "Checkpoint salvato."
_SAVE_FAILED_LABEL = "CHECKPOINT FALLITO: {error} (premi s per riprovare)"
_NEVER_SAVED_LABEL = "Nessun Checkpoint del weekend ancora scritto."


class WeekendScreen(Screen[Career]):
    """Il weekend del GP: stato delle sessioni, lancio e Checkpoint."""

    NAME = "weekend"

    DEFAULT_CSS = """
    WeekendScreen #weekend-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    WeekendScreen #weekend-sessions {
        margin: 1;
        padding: 0 1;
        border: solid $primary;
    }

    WeekendScreen #save-status {
        padding: 0 2;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("g", "play_next", "Gioca la prossima sessione"),
        Binding("s", "retry_save", "Riprova il Checkpoint"),
        Binding("escape", "back", "Torna alla griglia"),
    ]

    def __init__(self, career: Career) -> None:
        if career.weekend is None:
            raise ValueError("WeekendScreen needs a Career with a weekend in progress")
        super().__init__(name=self.NAME)
        self._career = career
        self._circuit = circuit_by_code(career.weekend.circuit_code)
        self._save_failed = False
        self._last_save_error = ""
        world = career.world
        self._driver_names = {driver.id: driver.name for driver in world.drivers}
        self._commentary_context = commentary_context(world)

    # ------------------------------------------------------------------
    # Read-only state, for the header and the Pilot tests
    # ------------------------------------------------------------------

    @property
    def career(self) -> Career:
        """La Carriera con lo stato weekend piu' recente in memoria."""
        return self._career

    @property
    def weekend(self) -> WeekendState:
        """Lo stato corrente della macchina a stati del weekend."""
        weekend = self._career.weekend
        assert weekend is not None  # guaranteed by the constructor
        return weekend

    @property
    def save_failed(self) -> bool:
        """True se l'ultimo Checkpoint e' fallito ed e' in attesa di retry."""
        return self._save_failed

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="weekend-header")
        yield Static(self._sessions_text(), id="weekend-sessions")
        yield Static(_NEVER_SAVED_LABEL, id="save-status")
        yield Footer()

    # ------------------------------------------------------------------
    # Session dispatch
    # ------------------------------------------------------------------

    def action_play_next(self) -> None:
        """Lancia la prossima sessione del weekend, o il risultato a fine GP."""
        phase = self.weekend.phase
        if phase in (WeekendPhase.FP1, WeekendPhase.FP2, WeekendPhase.FP3):
            self._open_practice()
        elif phase is WeekendPhase.QUALIFYING:
            self._open_qualifying()
        elif phase is WeekendPhase.RACE:
            self._open_race()
        else:
            self._open_result()

    def action_retry_save(self) -> None:
        """Ritenta il Checkpoint fallito: lo stato in memoria e' intatto."""
        if not self._save_failed:
            self.notify("Nessun Checkpoint in sospeso.")
            return
        self._checkpoint()

    def action_back(self) -> None:
        """Torna alla griglia portando con se' la Carriera aggiornata."""
        self.dismiss(self._career)

    def _open_practice(self) -> None:
        session = self.weekend.next_practice_session
        assert session is not None  # phase checked by the caller
        screen = PracticeScreen(
            world=self._career.world,
            circuit=self._circuit,
            seed=self.weekend.seed,
            session=session,
            effects=self.weekend.effects,
        )

        def on_close(result: PracticeSessionResult | None) -> None:
            if result is None:
                return
            self._advance(advance_after_practice(self.weekend, result))

        self.app.push_screen(screen, on_close)

    def _open_qualifying(self) -> None:
        screen = QualifyingScreen(
            entries=race_entries(self._career.world),
            driver_names=self._driver_names,
            circuit=self._circuit,
            seed=self.weekend.seed,
            effects=self.weekend.effects,
        )

        def on_close(result: QualifyingResult | None) -> None:
            if result is None:
                return
            self._advance(advance_after_qualifying(self.weekend, result))

        self.app.push_screen(screen, on_close)

    def _open_race(self) -> None:
        """Checkpoint pre-gara, poi la Gara interattiva sulla griglia salvata."""
        if not self._checkpoint():
            return
        weekend = self.weekend
        assert weekend.grid_driver_ids is not None  # set by advance_after_qualifying
        entries_by_id = {entry.driver.id: entry for entry in race_entries(self._career.world)}
        grid = tuple(entries_by_id[driver_id] for driver_id in weekend.grid_driver_ids)
        state, events = start_race(grid, self._circuit, seed=weekend.seed, effects=weekend.effects)
        screen = RaceScreen(state=state, initial_events=events, context=self._commentary_context)

        def on_close(classification: tuple[ClassifiedResult, ...] | None) -> None:
            if classification is None:
                return
            self._advance(advance_after_race(self.weekend, classification))
            self._open_result()

        self.app.push_screen(screen, on_close)

    def _open_result(self) -> None:
        classification = self.weekend.race_classification
        if classification is None:
            return
        team_names = dict(self._commentary_context.team_names)
        self.app.push_screen(
            RaceResultScreen(
                circuit_name=self._circuit.name,
                classification=classification,
                driver_names=self._driver_names,
                team_names=team_names,
            )
        )

    # ------------------------------------------------------------------
    # State machine advance and transactional Checkpoint
    # ------------------------------------------------------------------

    def _advance(self, weekend: WeekendState) -> None:
        """Registra la sessione conclusa in memoria e scrive il Checkpoint."""
        self._career = replace(self._career, weekend=weekend)
        self._checkpoint()
        self._refresh()

    def _checkpoint(self) -> bool:
        """Salva l'intera Carriera; in caso di errore lo stato resta in memoria.

        Ritorna True a salvataggio riuscito. Al fallimento mostra
        l'errore e arma il retry (tasto s): la sessione appena giocata
        non va mai persa.
        """
        try:
            with connect() as connection:
                self._career = save_career(connection, self._career)
        except (RuntimeError, psycopg.Error) as error:
            self._save_failed = True
            self._last_save_error = str(error)
            self.notify(
                f"Checkpoint fallito: {error}. Premi s per riprovare.",
                severity="error",
                timeout=10,
            )
            self._refresh()
            return False
        self._save_failed = False
        self._last_save_error = ""
        self._refresh()
        return True

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        self.query_one("#weekend-header", Static).update(self._header_text())
        self.query_one("#weekend-sessions", Static).update(self._sessions_text())
        self.query_one("#save-status", Static).update(self._save_status_text())

    def _header_text(self) -> str:
        weekend = self.weekend
        if weekend.finished:
            status = "Weekend concluso: g per rivedere il risultato"
        else:
            status = f"Prossima sessione: {_PHASE_LABELS[weekend.phase]}"
        return f"Weekend di gara: {self._circuit.name}  |  {status}"

    def _sessions_text(self) -> str:
        weekend = self.weekend
        phases = tuple(_PHASE_LABELS)
        current_index = len(phases) if weekend.finished else phases.index(weekend.phase)
        lines = ["Formato weekend: Standard", ""]
        for index, phase in enumerate(phases):
            if index < current_index:
                marker = _DONE_MARKER
            elif index == current_index:
                marker = _NEXT_MARKER
            else:
                marker = _PENDING_MARKER
            lines.append(f"  {_PHASE_LABELS[phase]:28} {marker}")
        if weekend.grid_driver_ids is not None:
            pole_name = self._driver_names[weekend.grid_driver_ids[0]]
            lines.append("")
            lines.append(f"Griglia decisa: pole di {pole_name}")
        if weekend.race_classification is not None:
            winner = self._driver_names[weekend.race_classification[0].driver_id]
            lines.append(f"Vincitore del GP: {winner}")
        return "\n".join(lines)

    def _save_status_text(self) -> str:
        if self._save_failed:
            return _SAVE_FAILED_LABEL.format(error=self._last_save_error)
        if self._career.last_checkpoint_at is None:
            return _NEVER_SAVED_LABEL
        return _SAVED_LABEL
