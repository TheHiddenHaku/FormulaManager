"""Schermata calendario di stagione (T5.1.1).

Mostra i 24 GP della stagione corrente con le date reali dell'anno, il
Formato weekend e lo stato di ciascuno (disputato, prossimo, in
programma, Sprint post-MVP). L'intestazione evidenzia il prossimo GP e il
conto dei giorni mancanti: durante la pausa estiva il conto e' grande e
lo stacco lungo si vede a colpo d'occhio. Schermata di sola
presentazione: legge la Carriera in memoria, non tocca il database
(ADR 0001).
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from fm_engine.career import Career
from fm_engine.season import (
    days_until_next_grand_prix,
    next_grand_prix,
    season_calendar,
)
from fm_tui.widgets.date_bar import DateBar

_FORMAT_LABELS = {"standard": "Standard", "sprint": "Sprint"}

_STATUS_DONE = "Disputato"
_STATUS_NEXT = "Prossimo <--"
_STATUS_SCHEDULED = "In programma"


class CalendarScreen(Screen[None]):
    """Il Calendario della stagione: 24 GP con date, formato e stato."""

    NAME = "calendar"

    DEFAULT_CSS = """
    CalendarScreen #calendar-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    CalendarScreen DataTable {
        height: auto;
        margin: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Chiudi il calendario"),
    ]

    def __init__(self, career: Career) -> None:
        super().__init__(name=self.NAME)
        self._career = career

    def compose(self) -> ComposeResult:
        yield DateBar(self._career.season)
        yield Static(self._header(), id="calendar-header")
        with VerticalScroll():
            yield DataTable(id="calendar-table", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self._populate()

    def action_back(self) -> None:
        """Chiude il calendario e torna alla schermata precedente."""
        self.dismiss(None)

    def _header(self) -> str:
        season = self._career.season
        upcoming = next_grand_prix(season)
        if upcoming is None:
            return f"Calendario {season.year}  |  Stagione conclusa"
        days = days_until_next_grand_prix(season)
        race_date = upcoming.race_date.strftime("%d/%m/%Y")
        return (
            f"Calendario {season.year}  |  Prossimo GP: {upcoming.circuit.name} "
            f"({race_date}) tra {days} giorni"
        )

    def _populate(self) -> None:
        season = self._career.season
        table = self.query_one("#calendar-table", DataTable)
        table.add_columns("Round", "Gran Premio", "Paese", "Data", "Formato", "Stato")
        completed = season.completed_rounds
        upcoming = next_grand_prix(season)
        next_round = None if upcoming is None else upcoming.round
        for entry in season_calendar(season.year):
            weekend_format = entry.circuit.weekend_format_2026
            table.add_row(
                str(entry.round),
                entry.circuit.name,
                entry.circuit.country,
                entry.race_date.strftime("%d/%m/%Y"),
                _FORMAT_LABELS.get(weekend_format, weekend_format),
                self._status(entry.round, completed, next_round),
            )

    @staticmethod
    def _status(round_: int, completed: frozenset[int], next_round: int | None) -> str:
        if round_ in completed:
            return _STATUS_DONE
        if next_round is not None and round_ == next_round:
            return _STATUS_NEXT
        return _STATUS_SCHEDULED
