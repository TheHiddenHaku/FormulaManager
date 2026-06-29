"""Schermata risultato post-gara: ordine d'arrivo e punti (FOR-21).

Mostra la classifica finale della Gara (posizione, pilota, squadra,
distacco dal vincitore, eventuale penalita' bi-mescola e punti 2026) e
la tabella dei punti costruttori del GP (somma dei punti dei piloti per
squadra). Schermata di sola presentazione: riceve la classifica gia'
decisa dal motore e non tocca mai il database (ADR 0001).
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from fm_engine.career import Career
from fm_engine.events import ClassifiedResult
from fm_engine.points import constructor_points
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_tui.screens.standings import StandingsScreen
from fm_tui.widgets.team_colors import (
    driver_team_colors,
    highlighted_row,
    player_highlight_style,
    row_with_team_colors,
)

_LEADER_GAP = "-"
_NO_POINTS = "0"


class RaceResultScreen(Screen[None]):
    """Il risultato del Gran Premio: ordine d'arrivo e punti assegnati."""

    NAME = "race_result"

    DEFAULT_CSS = """
    RaceResultScreen #result-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    RaceResultScreen .table-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    RaceResultScreen DataTable {
        height: auto;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("l", "open_standings", "Classifiche"),
        Binding("escape", "back", "Chiudi il risultato"),
    ]

    def __init__(
        self,
        circuit_name: str,
        classification: tuple[ClassifiedResult, ...],
        driver_names: dict[int, str],
        team_names: dict[int, str],
        career: Career | None = None,
    ) -> None:
        super().__init__(name=self.NAME)
        self._circuit_name = circuit_name
        self._classification = classification
        self._driver_names = driver_names
        self._team_names = team_names
        self._career = career
        # Player livery highlight (B03): the player's drivers and constructor
        # row are evidenced with the team colour. Without a Career (and so
        # without the player slot) the helper falls back to a readable bold.
        color = career.world.player_slot.primary_color if career is not None else None
        self._player_style = player_highlight_style(color)
        # Team colour squares next to every driver: needs the world (the Career).
        self._team_colors = driver_team_colors(career.world) if career is not None else {}

    def compose(self) -> ComposeResult:
        winner = self._driver_names[self._classification[0].driver_id]
        yield Static(
            f"Risultato del GP: {self._circuit_name}  |  Vince {winner}",
            id="result-header",
        )
        with VerticalScroll():
            yield Static("Ordine d'arrivo", classes="table-title")
            yield DataTable(id="classification-table", cursor_type="row", zebra_stripes=True)
            yield Static("Punti costruttori del GP", classes="table-title")
            yield DataTable(id="constructors-table", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self._populate_classification()
        self._populate_constructors()

    def action_back(self) -> None:
        """Chiude il risultato e torna al flusso weekend."""
        self.dismiss(None)

    def action_open_standings(self) -> None:
        """Apre le classifiche aggiornate col GP appena concluso (T5.1.1)."""
        if self._career is None:
            return
        self.app.push_screen(StandingsScreen(self._career))

    def _populate_classification(self) -> None:
        table = self.query_one("#classification-table", DataTable)
        table.add_columns("Pos", "Pilota", "Squadra", "Distacco", "Penalita'", "Punti")
        for result in self._classification:
            gap = _LEADER_GAP if result.position == 1 else f"+{result.gap_to_winner_seconds:.3f}"
            penalty = f"+{result.penalty_seconds:.0f}s" if result.penalty_seconds else ""
            cells = [
                str(result.position),
                self._driver_names[result.driver_id],
                self._team_names.get(result.team_id, str(result.team_id)),
                gap,
                penalty,
                str(result.points) if result.points else _NO_POINTS,
            ]
            primary, secondary = self._team_colors.get(result.driver_id, (None, None))
            highlight = self._player_style if result.team_id == PLAYER_TEAM_ID else None
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
        table = self.query_one("#constructors-table", DataTable)
        table.add_columns("Squadra", "Punti")
        totals = constructor_points(self._classification)
        for team_id, points in sorted(totals.items(), key=lambda item: -item[1]):
            cells = (self._team_names.get(team_id, str(team_id)), str(points))
            if team_id == PLAYER_TEAM_ID:
                table.add_row(*highlighted_row(cells, self._player_style))
            else:
                table.add_row(*cells)
