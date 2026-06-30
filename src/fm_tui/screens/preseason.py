"""Schermata Test pre-season: Programmi per giorno e Classifica tempi (T5.1.2).

Per ognuno dei giorni di Test il manager assegna un Programma a ciascun
suo pilota (Sviluppo, Conoscenza, Affidabilita') e svolge il giorno: la
Classifica tempi e' esatta per tutte le 22 vetture, ma il contesto delle
AI (carburante, Programma) resta ignoto, Tempi sporchi. I Programmi di
Conoscenza stringono le Stime sulla propria vettura e sui propri piloti.

Ogni giorno svolto scrive il Checkpoint (ADR 0001). A fine fase si apre il
report pre-stagione, poi si torna alla griglia con la Carriera aggiornata.
La schermata riceve la Carriera in memoria e la restituisce alla chiusura.
"""

from dataclasses import replace

import psycopg
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Label, Select, Static

from fm_engine.career import Career
from fm_engine.preseason import (
    PreseasonProgramme,
    preseason_report,
    run_test_day,
)
from fm_engine.season import INITIAL_SEASON_YEAR
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_persistence import connect, save_career
from fm_tui.screens.preseason_report import PreseasonReportScreen
from fm_tui.screens.race import race_entries
from fm_tui.widgets.date_bar import DateBar

# Italian labels of the 3 pre-season programmes.
PROGRAMME_LABELS: dict[PreseasonProgramme, str] = {
    PreseasonProgramme.DEVELOPMENT: "Sviluppo",
    PreseasonProgramme.KNOWLEDGE: "Conoscenza",
    PreseasonProgramme.RELIABILITY: "Affidabilita'",
}

_DIRTY_NOTE = "I tempi delle AI sono sporchi: carburante e Programma ignoti, da interpretare."


def _format_lap_time(seconds: float) -> str:
    """Il tempo sul giro in formato m:ss.mmm."""
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes)}:{remainder:06.3f}"


class PreseasonScreen(Screen[Career]):
    """La fase Test pre-season: assegna Programmi, svolgi i giorni, leggi i tempi."""

    NAME = "preseason"

    DEFAULT_CSS = """
    PreseasonScreen #preseason-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    PreseasonScreen .section-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    PreseasonScreen .programme-row {
        height: auto;
        margin: 0 1;
    }

    PreseasonScreen .programme-row Label {
        width: 28;
        padding: 1 1 0 0;
    }

    PreseasonScreen .programme-row Select {
        width: 32;
    }

    PreseasonScreen #run-day {
        margin: 1 1;
    }

    PreseasonScreen #dirty-note {
        padding: 0 1;
        color: $text-muted;
    }

    PreseasonScreen #timesheet {
        height: auto;
        margin: 0 1 1 1;
    }
    """

    BINDINGS = [
        Binding("g", "run_day", "Svolgi il giorno"),
        Binding("escape", "back", "Torna alla griglia"),
    ]

    def __init__(self, career: Career) -> None:
        if not career.world.player_slot.is_set_up:
            raise ValueError("PreseasonScreen needs a Career with the team set up")
        super().__init__(name=self.NAME)
        self._career = career
        self._entries = race_entries(career.world)
        self._driver_names = {driver.id: driver.name for driver in career.world.drivers}
        self._player_driver_ids = tuple(
            contract.driver_id for contract in career.world.contracts_of(PLAYER_TEAM_ID)
        )
        self._save_failed = False

    # ------------------------------------------------------------------
    # Read-only state, for the Pilot tests
    # ------------------------------------------------------------------

    @property
    def career(self) -> Career:
        """La Carriera con lo stato di fase piu' recente in memoria."""
        return self._career

    @property
    def completed(self) -> bool:
        """True quando tutti i giorni di Test sono stati svolti."""
        return self._career.preseason.completed

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield DateBar(self._career.season)
        yield Static(self._header_text(), id="preseason-header")
        with VerticalScroll():
            yield Static("Programmi del giorno", classes="section-title")
            options = [(label, programme.value) for programme, label in PROGRAMME_LABELS.items()]
            for driver_id in self._player_driver_ids:
                with Horizontal(classes="programme-row"):
                    yield Label(self._driver_names[driver_id])
                    yield Select(
                        options,
                        value=PreseasonProgramme.KNOWLEDGE.value,
                        allow_blank=False,
                        id=f"programme-{driver_id}",
                    )
            yield Button("Svolgi il giorno", variant="primary", id="run-day")
            yield Static(_DIRTY_NOTE, id="dirty-note")
            yield Static("Classifica tempi", classes="section-title")
            yield DataTable(id="timesheet", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#timesheet", DataTable)
        table.add_columns("Pos", "Pilota", "Tempo", "Distacco")

    # ------------------------------------------------------------------
    # Run a test day
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-day":
            self.action_run_day()

    def action_run_day(self) -> None:
        """Svolge il prossimo giorno di Test coi Programmi scelti."""
        if self.completed:
            self.notify("Test pre-season conclusi.", severity="warning")
            return
        programmes = {
            driver_id: PreseasonProgramme(self.query_one(f"#programme-{driver_id}", Select).value)
            for driver_id in self._player_driver_ids
        }
        day = self._career.preseason.current_day
        # Include the season year so each season's test runs differently (T5.1.2).
        year_offset = (self._career.season.year - INITIAL_SEASON_YEAR) * 100_000
        seed = self._career.world.seed * 1_000 + year_offset + 900 + day
        outcome = run_test_day(
            self._career.preseason,
            self._career.knowledge,
            self._entries,
            programmes,
            seed=seed,
        )
        self._career = replace(
            self._career,
            preseason=outcome.preseason,
            knowledge=outcome.knowledge,
        )
        self._checkpoint()
        self._populate_timesheet(outcome.result)
        self.query_one("#preseason-header", Static).update(self._header_text())
        if self.completed:
            self._open_report()

    def action_back(self) -> None:
        """Torna alla griglia portando con se' la Carriera aggiornata."""
        self.dismiss(self._career)

    def _open_report(self) -> None:
        report = preseason_report(
            self._career.preseason, self._career.knowledge, self._player_driver_ids
        )
        self.query_one("#run-day", Button).disabled = True
        self.app.push_screen(
            PreseasonReportScreen(report, dict(self._driver_names)),
            # Rimanda la chiusura di questa schermata sulla App: chiudere la
            # PreseasonScreen dentro la callback di dismiss del report la
            # eseguirebbe mentre questa schermata e' ancora il message pump
            # attivo, e Textual solleverebbe ScreenError (deadlock guard).
            lambda _: self.app.call_later(self.dismiss, self._career),
        )

    def _checkpoint(self) -> None:
        """Salva l'intera Carriera; in caso di errore lo stato resta in memoria."""
        try:
            with connect() as connection:
                self._career = save_career(connection, self._career)
            self._save_failed = False
        except (RuntimeError, psycopg.Error) as error:
            self._save_failed = True
            self.notify(
                f"Checkpoint fallito: {error}. Riprova svolgendo di nuovo o riapri la fase.",
                severity="error",
                timeout=10,
            )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _header_text(self) -> str:
        preseason = self._career.preseason
        if preseason.completed:
            status = "Fase conclusa: esc per andare al primo GP"
        else:
            status = f"Giorno {preseason.current_day} di {preseason.total_days}"
        return f"Test pre-season  |  {status}"

    def _populate_timesheet(self, result) -> None:
        table = self.query_one("#timesheet", DataTable)
        table.clear()
        best = result.classification[0].time_seconds
        for row in result.classification:
            gap = "-" if row.position == 1 else f"+{row.time_seconds - best:.3f}"
            table.add_row(
                str(row.position),
                self._driver_names[row.driver_id],
                _format_lap_time(row.time_seconds),
                gap,
            )
