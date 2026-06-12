"""Schermata Misura d'emergenza: prestito o sponsor-tampone (FOR-24).

Si apre da sola quando la Cassa non copre la scadenza stipendi e la
Misura della stagione e' ancora disponibile. La scelta e' obbligata
(nessun escape): prestito con interessi e piano di rientro a rate,
oppure sponsor-tampone con malus Prestigio. Le due offerte arrivano dal
motore (fm_engine.economy.emergency) con importi reali, mai placeholder.

La schermata restituisce la variante scelta ("loan" o "stopgap"); il
chiamante (WeekendScreen) applica la Misura nel motore e completa il
regolamento della scadenza.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, OptionList, Static
from textual.widgets.option_list import Option

from fm_engine.economy import loan_offer, stopgap_offer
from fm_tui.widgets.balance_bar import format_usd

LOAN_CHOICE = "loan"
STOPGAP_CHOICE = "stopgap"


class EmergencyMeasureScreen(Screen[str]):
    """La scelta obbligata del salvagente economico della stagione."""

    NAME = "emergency_measure"

    DEFAULT_CSS = """
    EmergencyMeasureScreen #emergency-header {
        padding: 0 1;
        text-style: bold;
        background: $error;
        color: $text;
    }

    EmergencyMeasureScreen #emergency-intro {
        padding: 1 2;
    }

    EmergencyMeasureScreen OptionList {
        margin: 0 2;
        height: auto;
    }
    """

    BINDINGS = [
        Binding("enter", "select", "Conferma la Misura", show=False),
    ]

    def __init__(self, shortfall_usd: int) -> None:
        super().__init__(name=self.NAME)
        self._shortfall_usd = shortfall_usd
        self._loan = loan_offer(shortfall_usd)
        self._stopgap = stopgap_offer(shortfall_usd)

    def compose(self) -> ComposeResult:
        yield Static("MISURA D'EMERGENZA", id="emergency-header")
        yield Static(
            "La Cassa non copre la scadenza stipendi: scoperto di "
            f"{format_usd(self._shortfall_usd)}.\n"
            "Hai UNA sola Misura d'emergenza per stagione: scegli.",
            id="emergency-intro",
        )
        loan_label = (
            f"Prestito di {format_usd(self._loan.principal_usd)}: rientro in "
            f"{self._loan.repayment_races} gare, rata "
            f"{format_usd(self._loan.instalment_usd)} "
            f"(di cui interessi {format_usd(self._loan.interest_instalment_usd)}), "
            f"costo totale {format_usd(self._loan.total_repayment_usd)}"
        )
        stopgap_label = (
            f"Sponsor-tampone di {format_usd(self._stopgap.amount_usd)}: denaro "
            f"subito, malus Prestigio -{self._stopgap.prestige_malus}"
        )
        yield OptionList(
            Option(loan_label, id=LOAN_CHOICE),
            Option(stopgap_label, id=STOPGAP_CHOICE),
            id="emergency-options",
        )
        yield Footer()

    def on_mount(self) -> None:
        options = self.query_one("#emergency-options", OptionList)
        options.highlighted = 0
        options.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)
