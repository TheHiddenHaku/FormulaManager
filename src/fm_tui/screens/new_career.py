"""Flusso di nuova Carriera: nome, identita' squadra, colori (FOR-6).

Il giocatore sceglie il nome della Carriera, il nome della sua squadra e
i colori della livrea (opzionali). Alla conferma la schermata genera il
Mondo con fm_engine.world.generate (seed casuale), valorizza lo slot del
giocatore con l'identita' scelta, salva il Checkpoint di creazione con
fm_persistence.save_career e avvia il wizard di Setup squadra (FOR-7,
fm_tui.screens.team_setup) con cui il giocatore compone piloti, motore e
Filosofia telaio. La schermata corrente viene sostituita: tornare
indietro dal wizard porta all'elenco, non al modulo.

Accesso al database: una connessione per il solo Checkpoint di
creazione, aperta e chiusa nell'azione di conferma (ADR 0001).
"""

import random
from dataclasses import replace

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, Static

from fm_engine.career import Career
from fm_engine.world import PlayerSlot, generate
from fm_persistence import connect, save_career
from fm_tui.screens.team_setup import TeamSetup

# Seed space of the generation: a non-negative 63-bit integer.
_MAX_SEED = 2**63


class NewCareer(Screen):
    """Modulo di creazione di una nuova Carriera."""

    NAME = "new_career"

    DEFAULT_CSS = """
    NewCareer #new-career-form {
        padding: 1 2;
        width: 70;
    }

    NewCareer #form-title {
        text-style: bold;
        margin-bottom: 1;
    }

    NewCareer Label {
        margin-top: 1;
    }

    NewCareer #error {
        color: $error;
        margin-top: 1;
    }

    NewCareer #form-buttons {
        height: auto;
        margin-top: 1;
    }

    NewCareer #form-buttons Button {
        margin-right: 2;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "create", "Crea la Carriera"),
        Binding("escape", "cancel", "Annulla"),
    ]

    def __init__(self) -> None:
        super().__init__(name=self.NAME)

    def compose(self) -> ComposeResult:
        with Vertical(id="new-career-form"):
            yield Static("Nuova Carriera", id="form-title")
            yield Label("Nome della Carriera")
            yield Input(placeholder="es. Scuderia X", id="career-name-input")
            yield Label("Nome della squadra")
            yield Input(placeholder="es. Scuderia X Racing", id="team-name-input")
            yield Label("Colore primario della livrea (#rrggbb o nome, opzionale)")
            yield Input(placeholder="es. #ff2800", id="primary-color-input")
            yield Label("Colore secondario della livrea (#rrggbb o nome, opzionale)")
            yield Input(placeholder="es. bianco", id="secondary-color-input")
            yield Static("", id="error")
            with Horizontal(id="form-buttons"):
                yield Button("Crea", variant="primary", id="create")
                yield Button("Annulla", id="cancel")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#career-name-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Invio in un campo equivale alla conferma del modulo."""
        self.action_create()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            self.action_create()
        elif event.button.id == "cancel":
            self.action_cancel()

    def action_cancel(self) -> None:
        """Torna all'elenco delle Carriere senza creare nulla."""
        self.app.pop_screen()

    def action_create(self) -> None:
        """Genera il Mondo, salva il Checkpoint di creazione, avvia il wizard."""
        career_name = self.query_one("#career-name-input", Input).value.strip()
        team_name = self.query_one("#team-name-input", Input).value.strip()
        if not career_name or not team_name:
            self.query_one("#error", Static).update(
                "Servono il nome della Carriera e il nome della squadra."
            )
            return

        player_slot = PlayerSlot(
            name=team_name,
            primary_color=self._color("#primary-color-input"),
            secondary_color=self._color("#secondary-color-input"),
        )
        world = replace(generate(random.randrange(_MAX_SEED)), player_slot=player_slot)
        with connect() as connection:
            saved = save_career(connection, Career(name=career_name, world=world))
        self.app.switch_screen(TeamSetup(saved))

    def _color(self, input_id: str) -> str | None:
        """Il colore dal campo indicato, None se lasciato vuoto."""
        value = self.query_one(input_id, Input).value.strip()
        return value or None
