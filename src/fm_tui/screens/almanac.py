"""Schermata Almanacco: l'archivio consultabile dei GP della Carriera (T5.3.2).

Navigazione da tastiera a tre livelli con back (escape): elenco delle
stagioni archiviate -> elenco dei GP della stagione -> dettaglio del GP
(griglia di partenza, ordine d'arrivo completo ed eventi principali). Il
dettaglio NON mostra la Telecronaca integrale (ADR 0003): solo griglia,
arrivo ed eventi principali (Safety car, Abbandoni).

Empty state esplicito quando nessun GP e' stato ancora archiviato. La
schermata legge l'archivio gia' in memoria nella Carriera (Career.archive)
e non tocca il database (ADR 0001).
"""

from enum import Enum, auto

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from fm_engine.career import Career
from fm_engine.circuits import circuit_by_code
from fm_engine.history import ArchivedGrandPrix, PrincipalEventKind, SeasonArchive
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_tui.widgets.date_bar import DateBar

_NO_CONTRACT_LABEL = "senza Contratto"
_PLAYER_TEAM_FALLBACK = "(la tua squadra)"
_EMPTY_TITLE = "Almanacco vuoto"
_EMPTY_BODY = (
    "Nessun Gran Premio archiviato: disputa almeno un GP per popolare "
    "l'Almanacco. La stagione in corso compare appena conclusa la prima gara."
)
_DNF_LABEL = "Abbandono"


class _View(Enum):
    """Il livello di navigazione corrente dell'Almanacco."""

    SEASONS = auto()
    GRANDS_PRIX = auto()
    DETAIL = auto()


class AlmanacScreen(Screen[None]):
    """L'Almanacco: stagioni, GP e dettaglio di ogni gara archiviata."""

    NAME = "almanac"

    DEFAULT_CSS = """
    AlmanacScreen #almanac-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    AlmanacScreen .table-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    AlmanacScreen #almanac-empty {
        margin: 1;
        padding: 1;
        border: solid $primary;
    }

    AlmanacScreen DataTable {
        height: auto;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Indietro"),
    ]

    def __init__(self, career: Career) -> None:
        super().__init__(name=self.NAME)
        self._career = career
        self._archive = career.archive
        self._view = _View.SEASONS
        self._selected_year: int | None = None
        self._driver_names = {driver.id: driver.name for driver in career.world.drivers}
        self._team_names = self._build_team_names()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield DateBar(self._career.season)
        yield Static("", id="almanac-header")
        with VerticalScroll(id="almanac-body"):
            if self._archive.is_empty:
                yield Static("", id="almanac-empty")
            else:
                yield Static("", id="almanac-title", classes="table-title")
                yield DataTable(id="almanac-table", cursor_type="row", zebra_stripes=True)
                # The GP detail uses three stacked sections, hidden until needed.
                yield Static("", id="almanac-grid-title", classes="table-title")
                yield DataTable(id="almanac-grid", cursor_type="row", zebra_stripes=True)
                yield Static("", id="almanac-result-title", classes="table-title")
                yield DataTable(id="almanac-result", cursor_type="row", zebra_stripes=True)
                yield Static("", id="almanac-events-title", classes="table-title")
                yield DataTable(id="almanac-events", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        if self._archive.is_empty:
            self._render_empty()
            return
        self._render_seasons()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Invio su una riga scende di un livello: stagione -> GP -> dettaglio.

        La selezione di riga della DataTable (Invio col cursore sulla
        riga) e' il gesto di navigazione: la riga selezionata decide
        quale stagione o GP aprire.
        """
        if self._archive.is_empty:
            return
        if self._view is _View.SEASONS:
            self._open_season_at(event.cursor_row)
        elif self._view is _View.GRANDS_PRIX:
            self._open_grand_prix_at(event.cursor_row)

    def action_back(self) -> None:
        """Risale di un livello, o chiude l'Almanacco dal livello stagioni."""
        if self._view is _View.DETAIL:
            self._view = _View.GRANDS_PRIX
            self._render_grands_prix()
        elif self._view is _View.GRANDS_PRIX:
            self._view = _View.SEASONS
            self._render_seasons()
        else:
            self.dismiss(None)

    def _open_season_at(self, row: int) -> None:
        if not 0 <= row < len(self._archive.seasons):
            return
        self._selected_year = self._archive.seasons[row].year
        self._view = _View.GRANDS_PRIX
        self._render_grands_prix()

    def _open_grand_prix_at(self, row: int) -> None:
        season = self._selected_season()
        if season is None or not 0 <= row < len(season.grands_prix):
            return
        grand_prix = season.grands_prix[row]
        self._view = _View.DETAIL
        self._render_detail(grand_prix)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_empty(self) -> None:
        self.query_one("#almanac-header", Static).update("Almanacco")
        empty = self.query_one("#almanac-empty", Static)
        empty.update(f"{_EMPTY_TITLE}\n\n{_EMPTY_BODY}")

    def _render_seasons(self) -> None:
        self._set_detail_visible(False)
        self.query_one("#almanac-header", Static).update(
            "Almanacco  |  Invio per aprire una stagione, Esc per chiudere"
        )
        self.query_one("#almanac-title", Static).update("Stagioni archiviate")
        table = self.query_one("#almanac-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Stagione", "GP archiviati", "Stato")
        for season in self._archive.seasons:
            status = "Conclusa" if season.is_concluded else "In corso"
            table.add_row(str(season.year), str(len(season.grands_prix)), status)
        table.focus()

    def _render_grands_prix(self) -> None:
        self._set_detail_visible(False)
        season = self._selected_season()
        if season is None:
            self._view = _View.SEASONS
            self._render_seasons()
            return
        self.query_one("#almanac-header", Static).update(
            f"Almanacco {season.year}  |  Invio per il dettaglio, Esc per le stagioni"
        )
        self.query_one("#almanac-title", Static).update(f"Gran Premi {season.year}")
        table = self.query_one("#almanac-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Round", "Circuito", "Vincitore", "Pole")
        for grand_prix in season.grands_prix:
            table.add_row(
                str(grand_prix.round),
                self._circuit_name(grand_prix.circuit_code),
                self._winner_name(grand_prix),
                self._driver_label(grand_prix.pole_driver_id),
            )
        table.focus()

    def _render_detail(self, grand_prix: ArchivedGrandPrix) -> None:
        season = self._selected_season()
        year = season.year if season is not None else ""
        self.query_one("#almanac-header", Static).update(
            f"Almanacco {year}  |  {self._circuit_name(grand_prix.circuit_code)} "
            f"(round {grand_prix.round})  |  Esc per i GP"
        )
        self.query_one("#almanac-title", Static).update("")
        self.query_one("#almanac-table", DataTable).clear(columns=True)
        self._set_detail_visible(True)

        grid_title = self.query_one("#almanac-grid-title", Static)
        grid_title.update("Griglia di partenza")
        grid_table = self.query_one("#almanac-grid", DataTable)
        grid_table.clear(columns=True)
        grid_table.add_columns("Pos", "Pilota")
        for position, driver_id in enumerate(grand_prix.starting_grid, start=1):
            grid_table.add_row(str(position), self._driver_label(driver_id))

        result_title = self.query_one("#almanac-result-title", Static)
        result_title.update("Ordine d'arrivo")
        result_table = self.query_one("#almanac-result", DataTable)
        result_table.clear(columns=True)
        result_table.add_columns("Pos", "Pilota", "Squadra", "Punti")
        for result in grand_prix.classification:
            result_table.add_row(
                str(result.position),
                self._driver_label(result.driver_id),
                self._team_label(result.team_id),
                str(result.points),
            )

        events_title = self.query_one("#almanac-events-title", Static)
        events_table = self.query_one("#almanac-events", DataTable)
        events_table.clear(columns=True)
        if grand_prix.principal_events:
            events_title.update("Eventi principali")
            events_table.add_columns("Giro", "Evento", "Dettaglio")
            for event in grand_prix.principal_events:
                events_table.add_row(
                    str(event.lap),
                    self._event_label(event.kind),
                    self._event_detail(event),
                )
        else:
            events_title.update("Eventi principali: nessuno")

    def _set_detail_visible(self, visible: bool) -> None:
        for widget_id in (
            "#almanac-grid-title",
            "#almanac-grid",
            "#almanac-result-title",
            "#almanac-result",
            "#almanac-events-title",
            "#almanac-events",
        ):
            self.query_one(widget_id).display = visible
        for widget_id in ("#almanac-title", "#almanac-table"):
            self.query_one(widget_id).display = not visible

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _selected_season(self) -> SeasonArchive | None:
        if self._selected_year is None:
            return None
        return self._archive.season_for(self._selected_year)

    def _build_team_names(self) -> dict[int, str]:
        world = self._career.world
        names = {team.id: team.name for team in world.ai_teams}
        names[PLAYER_TEAM_ID] = world.player_slot.name or _PLAYER_TEAM_FALLBACK
        return names

    def _circuit_name(self, code: str) -> str:
        try:
            return circuit_by_code(code).name
        except (KeyError, ValueError):
            return code

    def _driver_label(self, driver_id: int | None) -> str:
        if driver_id is None:
            return "-"
        return self._driver_names.get(driver_id, f"Pilota {driver_id}")

    def _team_label(self, team_id: int) -> str:
        return self._team_names.get(team_id, f"Squadra {team_id}")

    def _winner_name(self, grand_prix: ArchivedGrandPrix) -> str:
        for result in grand_prix.classification:
            if result.position == 1:
                return self._driver_label(result.driver_id)
        return "-"

    def _event_label(self, kind: PrincipalEventKind) -> str:
        if kind is PrincipalEventKind.SAFETY_CAR:
            return "Safety car"
        return _DNF_LABEL

    def _event_detail(self, event) -> str:
        if event.driver_id is None:
            return event.detail
        return f"{self._driver_label(event.driver_id)}: {event.detail}"
