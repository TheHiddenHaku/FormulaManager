"""Schermata classifiche piloti e costruttori (T5.1.1).

Mostra le due classifiche della stagione corrente, ricostruite dai
risultati dei GP disputati (fm_engine.season): tutti i 22 piloti e le 11
squadre compaiono sempre, anche a zero punti prima del primo GP, in un
ordine stabile. Schermata di sola presentazione: riceve la Carriera gia'
in memoria e non tocca il database (ADR 0001).
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from fm_engine.career import Career
from fm_engine.season import constructor_standings, driver_standings
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_tui.widgets.date_bar import DateBar
from fm_tui.widgets.team_colors import (
    driver_team_colors,
    highlighted_row,
    player_highlight_style,
    row_with_team_colors,
)

_NO_CONTRACT_LABEL = "senza Contratto"
_PLAYER_TEAM_FALLBACK = "(la tua squadra)"


class StandingsScreen(Screen[None]):
    """Le classifiche piloti e costruttori della stagione in corso."""

    NAME = "standings"

    DEFAULT_CSS = """
    StandingsScreen #standings-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    StandingsScreen .table-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    StandingsScreen DataTable {
        height: auto;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Chiudi le classifiche"),
    ]

    def __init__(self, career: Career) -> None:
        super().__init__(name=self.NAME)
        self._career = career
        # Player livery highlight (B03): the player's drivers and the player's
        # constructor row are evidenced with the team colour.
        self._player_style = player_highlight_style(career.world.player_slot.primary_color)

    def compose(self) -> ComposeResult:
        yield DateBar(self._career.season)
        yield Static(self._header(), id="standings-header")
        with VerticalScroll():
            yield Static("Classifica piloti", classes="table-title")
            yield DataTable(id="drivers-standings", cursor_type="row", zebra_stripes=True)
            yield Static("Classifica costruttori", classes="table-title")
            yield DataTable(id="constructors-standings", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self._populate_drivers()
        self._populate_constructors()

    def action_back(self) -> None:
        """Chiude le classifiche e torna alla schermata precedente."""
        self.dismiss(None)

    def _header(self) -> str:
        season = self._career.season
        return f"Classifiche {season.year}  |  GP disputati: {len(season.results)}"

    def _team_names(self) -> dict[int, str]:
        world = self._career.world
        names = {team.id: team.name for team in world.ai_teams}
        names[PLAYER_TEAM_ID] = world.player_slot.name or _PLAYER_TEAM_FALLBACK
        return names

    def _populate_drivers(self) -> None:
        world = self._career.world
        table = self.query_one("#drivers-standings", DataTable)
        table.add_columns("Pos", "Pilota", "Squadra", "Punti", "Vittorie")
        driver_names = {driver.id: driver.name for driver in world.drivers}
        team_names = self._team_names()
        driver_team = {contract.driver_id: contract.team_id for contract in world.contracts}
        team_colors = driver_team_colors(world)
        driver_ids = [driver.id for driver in world.drivers]
        for standing in driver_standings(self._career.season.results, driver_ids):
            team_id = driver_team.get(standing.driver_id)
            team = _NO_CONTRACT_LABEL
            if team_id is not None:
                team = team_names.get(team_id, _NO_CONTRACT_LABEL)
            cells = [
                str(standing.position),
                driver_names.get(standing.driver_id, str(standing.driver_id)),
                team,
                str(standing.points),
                str(standing.wins),
            ]
            primary, secondary = team_colors.get(standing.driver_id, (None, None))
            highlight = self._player_style if team_id == PLAYER_TEAM_ID else None
            table.add_row(
                *row_with_team_colors(
                    cells,
                    name_index=1,
                    primary_color=primary,
                    secondary_color=secondary,
                    highlight_style=highlight,
                )
            )

    def _populate_constructors(self) -> None:
        world = self._career.world
        table = self.query_one("#constructors-standings", DataTable)
        table.add_columns("Pos", "Squadra", "Punti", "Vittorie")
        team_names = self._team_names()
        team_ids = [PLAYER_TEAM_ID, *(team.id for team in world.ai_teams)]
        for standing in constructor_standings(self._career.season.results, team_ids):
            cells = (
                str(standing.position),
                team_names.get(standing.team_id, str(standing.team_id)),
                str(standing.points),
                str(standing.wins),
            )
            if standing.team_id == PLAYER_TEAM_ID:
                table.add_row(*highlighted_row(cells, self._player_style))
            else:
                table.add_row(*cells)
