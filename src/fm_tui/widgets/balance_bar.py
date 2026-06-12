"""Barra dei saldi: Cassa e Cap residuo sempre visibili (FOR-15).

Il widget persistente delle schermate gestionali: mostra i due saldi del
registro economico (fm_engine.economy) e si aggiorna via update_ledger
quando un movimento cambia lo stato in memoria. Solo resa: nessuna
logica economica qui (ADR 0002).
"""

from textual.widgets import Static

from fm_engine.economy import TeamLedger


def format_usd(amount_usd: int) -> str:
    """Importo USD compatto in stile $12.3M, col segno per le uscite."""
    sign = "-" if amount_usd < 0 else ""
    value = abs(amount_usd)
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.1f}K"
    return f"{sign}${value}"


class BalanceBar(Static):
    """I due saldi del doppio vincolo: Cassa e Cap residuo."""

    DEFAULT_CSS = """
    BalanceBar {
        padding: 0 1;
        background: $panel;
        color: $text;
        text-style: bold;
    }
    """

    def __init__(self, ledger: TeamLedger) -> None:
        super().__init__()
        self._ledger = ledger

    def on_mount(self) -> None:
        self.update(self._text())

    def update_ledger(self, ledger: TeamLedger) -> None:
        """Aggiorna i saldi mostrati con l'ultimo stato del registro."""
        self._ledger = ledger
        self.update(self._text())

    def _text(self) -> str:
        ledger = self._ledger
        return (
            f"Cassa: {format_usd(ledger.cash_usd)}"
            f"  |  Cap residuo: {format_usd(ledger.cap_remaining_usd)}"
            f" su {format_usd(ledger.cap_usd)}"
        )
