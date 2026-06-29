"""Schermata di strategia pre-gara: la gomma di partenza dei piloti (Strategia Pit Stop).

Prima della Gara il manager sceglie la Mescola di partenza per ciascuno dei
suoi piloti, potendo differenziarla tra i due. Le opzioni sono le tre Mescole
da asciutto nominate per il GP (Soft, Medium, Hard); il default e' la Medium.
Alla conferma la schermata restituisce la mappa pilota -> Mescola al flusso
weekend, che la passa a start_race; senza conferma (esc) la Gara non parte e si
torna alla hub. Solo scelta: nessuna logica di gara qui (ADR 0002).
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Label, RadioButton, RadioSet

from fm_engine.tyres import Compound


class RaceStrategyScreen(Screen[dict[int, Compound] | None]):
    """Scelta della Mescola di partenza per i piloti del giocatore, pre-gara."""

    NAME = "race_strategy"

    DEFAULT_CSS = """
    RaceStrategyScreen #strategy-window {
        margin: 1 2;
        padding: 1 2;
        border: solid $primary;
        height: auto;
    }

    RaceStrategyScreen #strategy-title {
        text-style: bold;
        margin-bottom: 1;
    }

    RaceStrategyScreen RadioSet {
        height: auto;
        margin-bottom: 1;
    }

    RaceStrategyScreen #strategy-buttons {
        height: auto;
        align-horizontal: center;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Annulla"),
    ]

    def __init__(
        self,
        drivers: tuple[tuple[int, str], ...],
        compounds: tuple[tuple[Compound, str], ...],
        default: Compound,
    ) -> None:
        super().__init__(name=self.NAME)
        self._drivers = drivers
        self._compounds = compounds
        self._default = default

    def compose(self) -> ComposeResult:
        with VerticalScroll(), Vertical(id="strategy-window"):
            yield Label(
                "Strategia: scegli la gomma di partenza per ogni pilota",
                id="strategy-title",
            )
            for driver_id, name in self._drivers:
                yield Label(name)
                with RadioSet(id=f"strategy-{driver_id}"):
                    for compound, label in self._compounds:
                        yield RadioButton(
                            label,
                            value=compound is self._default,
                            id=f"strategy-{driver_id}-{compound.value}",
                        )
            with Horizontal(id="strategy-buttons"):
                yield Button("Conferma e parti", variant="primary", id="confirm-strategy")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-strategy":
            self.dismiss(self._choices())

    def action_cancel(self) -> None:
        """Annulla la scelta: la Gara non parte, si torna alla hub."""
        self.dismiss(None)

    def _choices(self) -> dict[int, Compound]:
        """La Mescola di partenza scelta per ciascun pilota (default se vuoto)."""
        choices: dict[int, Compound] = {}
        for driver_id, _ in self._drivers:
            pressed = self.query_one(f"#strategy-{driver_id}", RadioSet).pressed_button
            if pressed is None or pressed.id is None:
                choices[driver_id] = self._default
                continue
            value = pressed.id.removeprefix(f"strategy-{driver_id}-")
            choices[driver_id] = Compound(value)
        return choices
