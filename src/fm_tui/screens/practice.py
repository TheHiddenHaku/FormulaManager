"""Schermata prove libere: Programmi per pilota e report di sessione (FOR-20).

In alto la scheda circuito: caratteristiche della pista, le 3 Mescole
nominate del GP e la previsione meteo del weekend. Per ogni pilota del
manager uno slot con la scelta del Programma (Setup, Gomme, Focus
qualifica, Passo gara, Strategia); il lancio della sessione e' sincrono
(la simulazione di una sessione di libere e' istantanea) e produce il
report con gli effetti ottenuti e la Classifica tempi esatta delle 22
vetture.

La schermata gioca UNA sessione di libere del weekend (FOR-21): riceve
la sessione da giocare e gli effetti cumulati finora, e alla chiusura
restituisce il PracticeSessionResult al flusso weekend (dismiss), che
avanza la macchina a stati e scrive il Checkpoint. Chiudere senza aver
lanciato restituisce None: la sessione resta da giocare.

Se il manager lancia senza un Programma per qualche pilota, una modale
chiede conferma e il motore applica il default, segnalato nel report.
Niente scritture su database (ADR 0001): la schermata consuma soltanto
simulate_practice_session.
"""

from collections.abc import Mapping

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Footer, Label, Select, Static

from fm_engine.circuits import Circuit
from fm_engine.practice import (
    DEFAULT_PROGRAMME,
    PRACTICE_SESSIONS,
    PracticeEffects,
    PracticeProgramme,
    PracticeSession,
    PracticeSessionResult,
    revealed_degradation_rates,
    simulate_practice_session,
)
from fm_engine.tyres import CompoundSlot, nominated_compounds
from fm_engine.weather import session_forecast
from fm_engine.world.models import PLAYER_TEAM_ID, World
from fm_tui.screens.race import race_entries
from fm_tui.widgets.team_colors import highlighted_row, player_highlight_style

# Italian labels of the 5 practice programmes.
PROGRAMME_LABELS: dict[PracticeProgramme, str] = {
    PracticeProgramme.SETUP: "Setup",
    PracticeProgramme.TYRES: "Gomme",
    PracticeProgramme.QUALIFYING_FOCUS: "Focus qualifica",
    PracticeProgramme.RACE_PACE: "Passo gara",
    PracticeProgramme.STRATEGY: "Strategia",
}

# Italian labels of the compounds, same rendering as the race monitor.
_COMPOUND_LABELS: dict[str, str] = {
    "c1": "C1",
    "c2": "C2",
    "c3": "C3",
    "c4": "C4",
    "c5": "C5",
    "intermediate": "Inter",
    "wet": "Bagnato",
}

# Italian labels of the circuit weather profiles.
_WEATHER_PROFILE_LABELS: dict[str, str] = {
    "dry": "asciutto",
    "variable": "variabile",
    "wet": "piovoso",
}

_SESSION_LABELS = {session: session.value.upper() for session in PRACTICE_SESSIONS}
_SESSION_OVER_LABEL = "Sessione conclusa: esc per continuare il weekend"


def _format_lap_time(seconds: float) -> str:
    """Il tempo sul giro in formato m:ss.mmm."""
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes)}:{remainder:06.3f}"


class DefaultProgrammeConfirmation(ModalScreen[bool]):
    """Conferma del lancio con Programmi mancanti: dismiss True = lancia."""

    NAME = "default_programme_confirmation"

    DEFAULT_CSS = """
    DefaultProgrammeConfirmation {
        align: center middle;
    }

    DefaultProgrammeConfirmation #confirm-window {
        width: 64;
        height: auto;
        padding: 1 2;
        border: thick $warning;
        background: $surface;
    }

    DefaultProgrammeConfirmation #confirm-question {
        margin-bottom: 1;
    }

    DefaultProgrammeConfirmation #confirm-buttons {
        height: auto;
        align-horizontal: center;
    }

    DefaultProgrammeConfirmation #confirm-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("s", "confirm", "Si', lancia"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Annulla", show=False),
    ]

    def __init__(self, driver_names: tuple[str, ...]) -> None:
        super().__init__(name=self.NAME)
        self._driver_names = driver_names

    def compose(self) -> ComposeResult:
        names = ", ".join(self._driver_names)
        default_label = PROGRAMME_LABELS[DEFAULT_PROGRAMME]
        with Vertical(id="confirm-window"):
            yield Label(
                f"Nessun Programma assegnato a: {names}.\n"
                f"Lanciare la sessione col Programma di default ({default_label})?",
                id="confirm-question",
            )
            with Horizontal(id="confirm-buttons"):
                yield Button("Si', lancia", variant="warning", id="confirm")
                yield Button("Annulla", id="cancel")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class PracticeScreen(Screen[PracticeSessionResult | None]):
    """Una sessione di libere del GP: Programmi, scheda circuito e report."""

    NAME = "practice"

    DEFAULT_CSS = """
    PracticeScreen #practice-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    PracticeScreen #circuit-card {
        margin: 0 1;
        padding: 0 1;
        border: solid $primary;
    }

    PracticeScreen .section-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    PracticeScreen .programme-row {
        height: auto;
        margin: 0 1;
    }

    PracticeScreen .programme-row Label {
        width: 28;
        padding: 1 1 0 0;
    }

    PracticeScreen .programme-row Select {
        width: 32;
    }

    PracticeScreen #launch-session {
        margin: 1 1;
    }

    PracticeScreen #session-report {
        margin: 0 1;
        padding: 0 1;
        border: solid $secondary;
    }

    PracticeScreen #timesheet {
        height: auto;
        margin: 0 1 1 1;
    }
    """

    BINDINGS = [
        Binding("l", "launch_session", "Lancia la sessione"),
        Binding("escape", "back", "Continua il weekend"),
    ]

    def __init__(
        self,
        world: World,
        circuit: Circuit,
        seed: int,
        session: PracticeSession = PracticeSession.FP1,
        effects: PracticeEffects | None = None,
    ) -> None:
        super().__init__(name=self.NAME)
        self._world = world
        self._circuit = circuit
        self._seed = seed
        self._session = session
        self._entries = race_entries(world)
        self._driver_names = {driver.id: driver.name for driver in world.drivers}
        self._player_driver_ids = tuple(
            contract.driver_id for contract in world.contracts_of(PLAYER_TEAM_ID)
        )
        # Player drivers are highlighted in the timesheet, like the standings
        # and the race, with the team livery colour.
        self._player_style = player_highlight_style(world.player_slot.primary_color)
        self._effects = effects if effects is not None else PracticeEffects()
        self._result: PracticeSessionResult | None = None

    # ------------------------------------------------------------------
    # Read-only state, for the header and the Pilot tests
    # ------------------------------------------------------------------

    @property
    def effects(self) -> PracticeEffects:
        """Gli effetti del weekend cumulati, sessione corrente inclusa."""
        return self._effects

    @property
    def result(self) -> PracticeSessionResult | None:
        """L'esito della sessione, se gia' lanciata."""
        return self._result

    @property
    def session_played(self) -> bool:
        """True dopo il lancio della sessione: una sola per schermata."""
        return self._result is not None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="practice-header")
        with VerticalScroll():
            yield Static(self._circuit_card_text(), id="circuit-card")
            yield Static("Programmi della sessione", classes="section-title")
            options = [(label, programme.value) for programme, label in PROGRAMME_LABELS.items()]
            for driver_id in self._player_driver_ids:
                with Horizontal(classes="programme-row"):
                    yield Label(self._driver_names[driver_id])
                    yield Select(
                        options,
                        prompt="Nessun Programma",
                        id=f"programme-{driver_id}",
                    )
            yield Button("Lancia la sessione", variant="primary", id="launch-session")
            yield Static("", id="session-report")
            yield Static("Classifica tempi", classes="section-title")
            yield DataTable(id="timesheet", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#timesheet", DataTable)
        table.add_columns("Pos", "Pilota", "Tempo", "Distacco")

    # ------------------------------------------------------------------
    # Session launch
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch-session":
            self.action_launch_session()

    def action_launch_session(self) -> None:
        """Lancia la sessione di libere coi Programmi scelti.

        Senza un Programma per qualche pilota chiede conferma: il motore
        applica il default e il report lo segnala (edge case FOR-20).
        """
        if self.session_played:
            self.notify("La sessione e' gia' stata giocata.", severity="warning")
            return
        assignments = self._current_assignments()
        missing = tuple(
            self._driver_names[driver_id]
            for driver_id, programme in assignments.items()
            if programme is None
        )
        if not missing:
            self._run_session(assignments)
            return

        def on_confirmation(confirmed: bool | None) -> None:
            if confirmed:
                self._run_session(assignments)

        self.app.push_screen(DefaultProgrammeConfirmation(missing), on_confirmation)

    def action_back(self) -> None:
        """Chiude la sessione e restituisce l'esito al flusso weekend.

        None se la sessione non e' stata lanciata: resta da giocare.
        """
        self.dismiss(self._result)

    def _current_assignments(self) -> dict[int, PracticeProgramme | None]:
        assignments: dict[int, PracticeProgramme | None] = {}
        for driver_id in self._player_driver_ids:
            select = self.query_one(f"#programme-{driver_id}", Select)
            assignments[driver_id] = None if select.is_blank() else PracticeProgramme(select.value)
        return assignments

    def _run_session(self, assignments: Mapping[int, PracticeProgramme | None]) -> None:
        result = simulate_practice_session(
            self._entries,
            self._circuit,
            self._session,
            assignments,
            seed=self._seed,
            effects=self._effects,
        )
        self._effects = result.effects
        self._result = result
        self.query_one("#session-report", Static).update(self._report_text(result))
        self._populate_timesheet(result)
        self.query_one("#practice-header", Static).update(self._header_text())
        self.query_one("#launch-session", Button).disabled = True

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _header_text(self) -> str:
        if self.session_played:
            status = _SESSION_OVER_LABEL
        else:
            status = f"Da giocare: {_SESSION_LABELS[self._session]}"
        return f"Prove libere {_SESSION_LABELS[self._session]}: {self._circuit.name}  |  {status}"

    def _circuit_card_text(self) -> str:
        circuit = self._circuit
        nominated = nominated_compounds(circuit)
        compounds = "  ".join(
            f"{slot_label}: {_COMPOUND_LABELS[nominated[slot].value]}"
            for slot, slot_label in (
                (CompoundSlot.SOFT, "Soft"),
                (CompoundSlot.MEDIUM, "Medium"),
                (CompoundSlot.HARD, "Hard"),
            )
        )
        # The forecast is deterministic for (circuit, seed): the card can
        # show the weekend numbers before the first session is launched.
        rain_chance = session_forecast(circuit, self._seed).rain_chance
        profile = _WEATHER_PROFILE_LABELS.get(circuit.weather_profile, circuit.weather_profile)
        return (
            f"{circuit.name} ({circuit.locality}, {circuit.country})\n"
            f"Lunghezza: {circuit.length_metres} m  |  Giri gara: {circuit.race_laps}  |  "
            f"Severita' gomme: {circuit.tyre_severity}/5  |  "
            f"Difficolta' di sorpasso: {circuit.overtaking_difficulty}/5\n"
            f"Mescole nominate  {compounds}\n"
            f"Previsione weekend: profilo {profile}, "
            f"probabilita' di pioggia {rain_chance:.0%}"
        )

    def _report_text(self, result: PracticeSessionResult) -> str:
        lines = [f"Report {_SESSION_LABELS[result.session]}"]
        for report in result.reports:
            name = self._driver_names[report.driver_id]
            programme = PROGRAMME_LABELS[report.programme]
            suffix = " (default)" if report.defaulted else ""
            lines.append(f"{name}: Programma {programme}{suffix}")
            if report.programme is PracticeProgramme.SETUP:
                lines.append(
                    f"  Setup al {report.setup_percentage:.0f}% "
                    f"(+{report.setup_gain:.0f} in sessione)"
                )
            elif report.programme is PracticeProgramme.TYRES:
                revealed = ", ".join(
                    _COMPOUND_LABELS[compound.value] for compound in report.newly_revealed
                )
                lines.append(f"  Curve di Degrado rivelate: {revealed or 'nessuna nuova'}")
            elif report.programme is PracticeProgramme.QUALIFYING_FOCUS:
                lines.append(
                    f"  Bonus qualifica del weekend: -{report.qualifying_bonus_seconds:.2f} s/giro"
                )
            elif report.programme is PracticeProgramme.RACE_PACE:
                lines.append(
                    f"  Bonus passo gara del weekend: -{report.race_pace_bonus_seconds:.2f} s/giro"
                )
            elif report.programme is PracticeProgramme.STRATEGY:
                lines.append(f"  Lettura strategica: livello {report.strategy_insight}")
        lines.append("")
        lines.append("Effetti validi per il weekend:")
        for driver_id in self._player_driver_ids:
            driver = result.effects.for_driver(driver_id)
            lines.append(
                f"  {self._driver_names[driver_id]}: setup {driver.setup_percentage:.0f}%"
                f", qualifica -{driver.qualifying_bonus_seconds:.2f} s"
                f", gara -{driver.race_pace_bonus_seconds:.2f} s"
            )
        rates = revealed_degradation_rates(result.effects, self._circuit)
        if rates:
            revealed = ", ".join(
                f"{_COMPOUND_LABELS[compound.value]} {rate:.3f} s/giro"
                for compound, rate in rates.items()
            )
            lines.append(f"  Degrado rivelato: {revealed}")
        if result.effects.strategy_insight > 0:
            suggested = next(
                (
                    report.suggested_stops
                    for report in result.reports
                    if report.suggested_stops is not None
                ),
                None,
            )
            if suggested is not None:
                lines.append(f"  Strategia consigliata: {suggested} soste")
        return "\n".join(lines)

    def _populate_timesheet(self, result: PracticeSessionResult) -> None:
        table = self.query_one("#timesheet", DataTable)
        table.clear()
        best = result.classification[0].time_seconds
        for row in result.classification:
            gap = "-" if row.position == 1 else f"+{row.time_seconds - best:.3f}"
            cells = [
                str(row.position),
                self._driver_names[row.driver_id],
                _format_lap_time(row.time_seconds),
                gap,
            ]
            if row.driver_id in self._player_driver_ids:
                table.add_row(*highlighted_row(cells, self._player_style))
            else:
                table.add_row(*cells)
