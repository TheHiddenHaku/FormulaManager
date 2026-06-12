"""Schermata elenco Carriere: il punto d'ingresso del gioco (FOR-6).

Mostra le Carriere salvate (Checkpoint piu' recente in alto) con le
azioni crea/apri/elimina visibili nel Footer. Al primo avvio, senza
Carriere, compare un empty state esplicito che invita a crearne una:
mai un elenco vuoto silenzioso.

L'elenco si ricarica dal database a ogni ritorno su questa schermata
(evento ScreenResume): creazioni ed eliminazioni si riflettono senza
riavvio, e i nomi editati via Studio appaiono al load successivo perche'
elenco e apertura leggono sempre dal database.

Accesso al database: una connessione per operazione (elenco, load,
delete), aperta e chiusa nell'azione; nessuna connessione resta aperta
durante la navigazione (ADR 0001).
"""

import uuid

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Label, OptionList, Static
from textual.widgets.option_list import Option

from fm_persistence import (
    CareerSummary,
    connect,
    delete_career,
    list_careers,
    load_career,
)
from fm_tui.screens.grid import Grid
from fm_tui.screens.new_career import NewCareer


class DeleteConfirmation(ModalScreen[bool]):
    """Conferma di eliminazione di una Carriera: dismiss True = elimina."""

    NAME = "delete_confirmation"

    DEFAULT_CSS = """
    DeleteConfirmation {
        align: center middle;
    }

    DeleteConfirmation #confirm-window {
        width: 64;
        height: auto;
        padding: 1 2;
        border: thick $error;
        background: $surface;
    }

    DeleteConfirmation #confirm-question {
        margin-bottom: 1;
    }

    DeleteConfirmation #confirm-buttons {
        height: auto;
        align-horizontal: center;
    }

    DeleteConfirmation #confirm-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("s", "confirm", "Si', elimina"),
        Binding("n", "cancel", "No"),
        Binding("escape", "cancel", "Annulla", show=False),
    ]

    def __init__(self, career_name: str) -> None:
        super().__init__(name=self.NAME)
        self._career_name = career_name

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-window"):
            yield Label(
                f"Eliminare la Carriera '{self._career_name}'?\n"
                "L'operazione cancella a cascata tutto il suo stato.",
                id="confirm-question",
            )
            with Horizontal(id="confirm-buttons"):
                yield Button("Si', elimina", variant="error", id="confirm")
                yield Button("Annulla", id="cancel")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class CareerList(Screen):
    """Elenco delle Carriere salvate, con crea/apri/elimina."""

    NAME = "career_list"

    DEFAULT_CSS = """
    CareerList #title {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    CareerList #empty-state {
        padding: 2;
        color: $text-muted;
    }

    CareerList #career-list {
        margin: 1;
    }
    """

    BINDINGS = [
        Binding("n", "new", "Nuova Carriera"),
        Binding("enter", "open", "Apri"),
        Binding("e", "delete", "Elimina"),
    ]

    def __init__(self) -> None:
        super().__init__(name=self.NAME)
        self._summaries: list[CareerSummary] = []

    def compose(self) -> ComposeResult:
        yield Static("Formula Manager: le tue Carriere", id="title")
        yield Static(
            "Nessuna Carriera salvata.\nPremi n per creare la tua prima Carriera.",
            id="empty-state",
        )
        yield OptionList(id="career-list")
        yield Footer()

    def on_screen_resume(self) -> None:
        """Ricarica l'elenco ogni volta che la schermata torna attiva."""
        self._reload()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Invio o click su una voce: apre quella Carriera."""
        if event.option_id is not None:
            self._open(uuid.UUID(event.option_id))

    def action_new(self) -> None:
        self.app.push_screen(NewCareer())

    def action_open(self) -> None:
        summary = self._highlighted_summary()
        if summary is not None:
            self._open(summary.id)

    def action_delete(self) -> None:
        summary = self._highlighted_summary()
        if summary is None:
            return

        def _execute(confirmed: bool | None) -> None:
            if confirmed:
                with connect() as connection:
                    delete_career(connection, summary.id)
                self._reload()

        self.app.push_screen(DeleteConfirmation(summary.name), _execute)

    def _reload(self) -> None:
        """Rilegge le Carriere dal database e aggiorna elenco ed empty state."""
        with connect() as connection:
            self._summaries = list_careers(connection)
        option_list = self.query_one("#career-list", OptionList)
        option_list.clear_options()
        option_list.add_options(
            Option(self._label(summary), id=str(summary.id)) for summary in self._summaries
        )
        empty = not self._summaries
        self.query_one("#empty-state", Static).display = empty
        option_list.display = not empty
        if not empty:
            option_list.highlighted = 0
            option_list.focus()

    def _highlighted_summary(self) -> CareerSummary | None:
        option_list = self.query_one("#career-list", OptionList)
        if not self._summaries or option_list.highlighted is None:
            return None
        return self._summaries[option_list.highlighted]

    def _open(self, career_id: uuid.UUID) -> None:
        """Carica la Carriera dal database e apre la griglia."""
        with connect() as connection:
            career = load_career(connection, career_id)
        self.app.push_screen(Grid(career))

    @staticmethod
    def _label(summary: CareerSummary) -> str:
        if summary.last_checkpoint_at is None:
            checkpoint = "mai salvata"
        else:
            checkpoint = summary.last_checkpoint_at.strftime("%d/%m/%Y %H:%M")
        return f"{summary.name}  (ultimo Checkpoint: {checkpoint})"
