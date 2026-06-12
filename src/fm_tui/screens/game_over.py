"""Schermata di fine Carriera per fallimento (FOR-24).

Appare quando l'insolvenza si protrae per N gare consecutive: la
Carriera termina e non e' piu' giocabile. Mostra il riepilogo (squadra,
stagione, Cassa finale, gare di insolvenza) e l'unica uscita e' il
ritorno all'elenco delle Carriere.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

from fm_engine.career import Career
from fm_tui.widgets.balance_bar import format_usd


class GameOverScreen(Screen):
    """Il fallimento: riepilogo finale e ritorno all'elenco Carriere."""

    NAME = "game_over"

    DEFAULT_CSS = """
    GameOverScreen #game-over-header {
        padding: 0 1;
        text-style: bold;
        background: $error;
        color: $text;
    }

    GameOverScreen #game-over-summary {
        margin: 1;
        padding: 1 2;
        border: solid $error;
    }
    """

    BINDINGS = [
        Binding("enter", "back_to_careers", "Torna all'elenco Carriere"),
        Binding("escape", "back_to_careers", "Torna all'elenco Carriere", show=False),
    ]

    def __init__(self, career: Career) -> None:
        super().__init__(name=self.NAME)
        self._career = career

    def compose(self) -> ComposeResult:
        ledger = self._career.ledger
        team_name = self._career.world.player_slot.name or "(slot vuoto)"
        lines = [
            f"La squadra {team_name} e' fallita.",
            "",
            f"Carriera: {self._career.name}",
            f"Stagione: {ledger.season_year}",
            f"Cassa finale: {format_usd(ledger.cash_usd)}",
            f"Gare consecutive in insolvenza: {self._career.solvency.insolvent_races}",
            "",
            "La Carriera e' terminata e non e' piu' giocabile.",
        ]
        yield Static("FALLIMENTO", id="game-over-header")
        yield Static("\n".join(lines), id="game-over-summary")
        yield Footer()

    def action_back_to_careers(self) -> None:
        """Risale lo stack fino all'elenco delle Carriere."""
        from fm_tui.screens.career_list import CareerList

        while len(self.app.screen_stack) > 1 and not isinstance(self.app.screen, CareerList):
            self.app.pop_screen()
