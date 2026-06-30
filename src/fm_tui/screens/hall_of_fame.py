"""Schermata Albo d'oro: Titoli anno per anno e statistiche cumulative (T5.3.2).

Mostra tre viste in una sola schermata di sola lettura: l'Albo d'oro (i
Titoli piloti e costruttori di ogni stagione conclusa), le statistiche
cumulative dei piloti (vittorie, podi, pole, Titoli) e quelle delle
squadre. I dati vengono dall'archivio della Carriera (Career.archive),
calcolati da fm_engine.history: sono i dati archiviati veri, mai
placeholder.

Empty state esplicito quando nessuna stagione e' ancora conclusa: i
Titoli si assegnano solo a fine stagione, quindi a meta' della prima
stagione l'Albo d'oro e' ancora vuoto. La schermata legge l'archivio in
memoria e non tocca il database (ADR 0001).
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from fm_engine.career import Career
from fm_engine.history import driver_stats, hall_of_fame, team_stats
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_tui.widgets.date_bar import DateBar

_PLAYER_TEAM_FALLBACK = "(la tua squadra)"
_EMPTY_TITLE = "Albo d'oro vuoto"
_EMPTY_BODY = (
    "Nessuna stagione conclusa: i Titoli piloti e costruttori si assegnano "
    "a fine stagione. Concludi la stagione in corso per iscrivere il primo "
    "campione nell'Albo d'oro."
)
_NO_CHAMPION = "-"


class HallOfFameScreen(Screen[None]):
    """L'Albo d'oro coi Titoli anno per anno e le statistiche cumulative."""

    NAME = "hall_of_fame"

    DEFAULT_CSS = """
    HallOfFameScreen #hall-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    HallOfFameScreen .table-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    HallOfFameScreen #hall-empty {
        margin: 1;
        padding: 1;
        border: solid $primary;
    }

    HallOfFameScreen DataTable {
        height: auto;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Chiudi l'Albo d'oro"),
    ]

    def __init__(self, career: Career) -> None:
        super().__init__(name=self.NAME)
        self._career = career
        self._archive = career.archive
        self._driver_names = {driver.id: driver.name for driver in career.world.drivers}
        self._team_names = self._build_team_names()

    def compose(self) -> ComposeResult:
        yield DateBar(self._career.season)
        yield Static(self._header(), id="hall-header")
        with VerticalScroll():
            if not self._archive.concluded_seasons:
                yield Static(f"{_EMPTY_TITLE}\n\n{_EMPTY_BODY}", id="hall-empty")
            else:
                yield Static("Albo d'oro: Titoli anno per anno", classes="table-title")
                yield DataTable(id="hall-of-fame", cursor_type="row", zebra_stripes=True)
                yield Static("Statistiche cumulative piloti", classes="table-title")
                yield DataTable(id="driver-stats", cursor_type="row", zebra_stripes=True)
                yield Static("Statistiche cumulative squadre", classes="table-title")
                yield DataTable(id="team-stats", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        if not self._archive.concluded_seasons:
            return
        self._populate_hall_of_fame()
        self._populate_driver_stats()
        self._populate_team_stats()

    def action_back(self) -> None:
        """Chiude l'Albo d'oro e torna alla schermata precedente."""
        self.dismiss(None)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _populate_hall_of_fame(self) -> None:
        table = self.query_one("#hall-of-fame", DataTable)
        table.add_columns("Stagione", "Campione piloti", "Campione costruttori")
        for entry in hall_of_fame(self._archive):
            table.add_row(
                str(entry.year),
                self._driver_label(entry.driver_champion_id),
                self._team_label(entry.constructor_champion_id),
            )

    def _populate_driver_stats(self) -> None:
        table = self.query_one("#driver-stats", DataTable)
        table.add_columns("Pilota", "Vittorie", "Podi", "Pole", "Titoli")
        stats = sorted(
            driver_stats(self._archive),
            key=lambda item: (-item.titles, -item.wins, -item.podiums, -item.poles, item.driver_id),
        )
        for entry in stats:
            table.add_row(
                self._driver_label(entry.driver_id),
                str(entry.wins),
                str(entry.podiums),
                str(entry.poles),
                str(entry.titles),
            )

    def _populate_team_stats(self) -> None:
        table = self.query_one("#team-stats", DataTable)
        table.add_columns("Squadra", "Vittorie", "Podi", "Pole", "Titoli")
        stats = sorted(
            team_stats(self._archive),
            key=lambda item: (-item.titles, -item.wins, -item.podiums, -item.poles, item.team_id),
        )
        for entry in stats:
            table.add_row(
                self._team_label(entry.team_id),
                str(entry.wins),
                str(entry.podiums),
                str(entry.poles),
                str(entry.titles),
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _header(self) -> str:
        concluded = len(self._archive.concluded_seasons)
        return f"Albo d'oro  |  Stagioni concluse: {concluded}"

    def _build_team_names(self) -> dict[int, str]:
        world = self._career.world
        names = {team.id: team.name for team in world.ai_teams}
        names[PLAYER_TEAM_ID] = world.player_slot.name or _PLAYER_TEAM_FALLBACK
        return names

    def _driver_label(self, driver_id: int | None) -> str:
        if driver_id is None:
            return _NO_CHAMPION
        return self._driver_names.get(driver_id, f"Pilota {driver_id}")

    def _team_label(self, team_id: int | None) -> str:
        if team_id is None:
            return _NO_CHAMPION
        return self._team_names.get(team_id, f"Squadra {team_id}")
