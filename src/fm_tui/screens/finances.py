"""Schermata finanze: Cassa, Cap residuo e storico movimenti (FOR-15).

Presenta il registro economico della squadra del giocatore: i due saldi
nella barra persistente e lo storico dei movimenti dal piu' recente,
ognuno con data di gioco, causale, importo e peso sul Cap. Nessuna query
qui (ADR 0001): la schermata riceve la Carriera gia' in memoria.

Edge case: a inizio Carriera, senza movimenti, lo storico mostra
l'empty state ("Nessun movimento registrato").
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from fm_engine.career import Career
from fm_engine.economy import TransactionKind
from fm_tui.widgets.balance_bar import BalanceBar, format_usd

# Italian labels of the transaction kinds (causali).
KIND_LABELS: dict[TransactionKind, str] = {
    TransactionKind.RACE_PRIZE: "Premio gara",
    TransactionKind.ANNUAL_SPONSOR: "Sponsor annuale",
    TransactionKind.CONSTRUCTORS_POOL: "Montepremi costruttori",
    TransactionKind.ONE_OFF_SPONSOR: "Sponsor una tantum",
    TransactionKind.STOPGAP_SPONSOR: "Sponsor-tampone",
    TransactionKind.LOAN: "Prestito",
    TransactionKind.INTEREST: "Interessi",
    TransactionKind.SALARY: "Stipendi piloti",
    TransactionKind.ENGINE_FEE: "Canone motore",
    TransactionKind.DEVELOPMENT_PROJECT: "Progetto di sviluppo",
    TransactionKind.DAMAGE: "Danni",
    TransactionKind.OVERSPEND: "Sforamento",
    TransactionKind.OTHER: "Altro",
}

EMPTY_STATE_LABEL = "Nessun movimento registrato"

# Marker for movements that consume the cap besides moving cash.
_CAP_MARKER = "si"


class FinancesScreen(Screen):
    """Le finanze della squadra: saldi e storico del registro."""

    NAME = "finances"

    DEFAULT_CSS = """
    FinancesScreen #finances-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    FinancesScreen .table-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    FinancesScreen DataTable {
        height: auto;
        margin: 0 1;
    }

    FinancesScreen #finances-empty {
        padding: 1 2;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Indietro"),
    ]

    def __init__(self, career: Career) -> None:
        super().__init__(name=self.NAME)
        self._career = career

    def compose(self) -> ComposeResult:
        ledger = self._career.ledger
        team_name = self._career.world.player_slot.name or "(slot vuoto)"
        yield Static(
            f"Finanze: {team_name}  |  Stagione {ledger.season_year}",
            id="finances-header",
        )
        yield BalanceBar(ledger)
        with VerticalScroll():
            yield Static("Storico movimenti", classes="table-title")
            if ledger.entries:
                yield DataTable(id="transactions-table", cursor_type="row", zebra_stripes=True)
            else:
                yield Static(EMPTY_STATE_LABEL, id="finances-empty")
        yield Footer()

    def on_mount(self) -> None:
        if not self._career.ledger.entries:
            return
        table = self.query_one("#transactions-table", DataTable)
        table.add_columns("Data", "Causale", "Importo", "Cap", "Descrizione")
        # Newest first: the latest movement opens the history. The
        # explicit + makes income tell apart from charges at a glance.
        for entry in reversed(self._career.ledger.entries):
            amount = format_usd(entry.amount_usd)
            if entry.amount_usd > 0:
                amount = f"+{amount}"
            table.add_row(
                entry.game_date.strftime("%d/%m/%Y"),
                KIND_LABELS[entry.kind],
                amount,
                _CAP_MARKER if entry.counts_against_cap else "",
                entry.description or "",
            )
        table.focus()

    def action_back(self) -> None:
        """Torna alla schermata principale della Carriera."""
        self.app.pop_screen()
