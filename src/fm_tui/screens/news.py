"""Schermata Notizie: la rassegna stampa dell'intervallo tra due GP (FOR-27).

Compare solo quando l'intervallo ha prodotto qualcosa da raccontare
(consegne di Progetti, Eventi extra-gara): negli intervalli silenziosi
non si apre nessuna schermata, il silenzio e' normale. Le Notizie sono
scorribili da tastiera; si prosegue verso il weekend con escape o invio.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, OptionList, Static
from textual.widgets.option_list import Option


class NewsScreen(Screen):
    """La rassegna stampa dell'intervallo, da scorrere e chiudere."""

    NAME = "news"

    DEFAULT_CSS = """
    NewsScreen #news-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    NewsScreen #news-list {
        margin: 1;
        height: auto;
    }
    """

    BINDINGS = [
        Binding("escape", "proceed", "Prosegui"),
        Binding("enter", "proceed", "Prosegui", show=False),
    ]

    def __init__(self, news: tuple[str, ...]) -> None:
        if not news:
            raise ValueError("NewsScreen needs at least one news item")
        super().__init__(name=self.NAME)
        self._news = news

    def compose(self) -> ComposeResult:
        yield Static("Rassegna stampa", id="news-header")
        yield OptionList(*(Option(item) for item in self._news), id="news-list")
        yield Footer()

    def on_mount(self) -> None:
        news_list = self.query_one("#news-list", OptionList)
        news_list.highlighted = 0
        news_list.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.action_proceed()

    def action_proceed(self) -> None:
        """Chiude la rassegna e prosegue verso il weekend."""
        self.dismiss(None)
