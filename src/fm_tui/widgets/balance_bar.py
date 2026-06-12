"""Barra dei saldi: Cassa, Cap residuo e stato economico (FOR-15, FOR-24).

Il widget persistente delle schermate gestionali: mostra i due saldi del
registro economico (fm_engine.economy) e, quando riceve anche lo stato
di solvibilita', lo stato economico della squadra col conto alla
rovescia del fallimento. Si aggiorna via update_ledger quando un
movimento cambia lo stato in memoria. Solo resa: nessuna logica
economica qui (ADR 0002).
"""

from textual.widgets import Static

from fm_engine.economy import (
    BANKRUPTCY_RACES,
    EconomicStatus,
    SolvencyState,
    TeamLedger,
    economic_status,
)

# Italian labels of the economic states (CONTEXT.md).
STATUS_LABELS: dict[EconomicStatus, str] = {
    EconomicStatus.HEALTHY: "sana",
    EconomicStatus.BLOCKED: "bloccata",
    EconomicStatus.EMERGENCY: "in emergenza",
    EconomicStatus.BANKRUPT: "FALLITA",
}


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

    def __init__(self, ledger: TeamLedger, solvency: SolvencyState | None = None) -> None:
        super().__init__()
        self._ledger = ledger
        self._solvency = solvency

    def on_mount(self) -> None:
        self.update(self._text())

    def update_ledger(self, ledger: TeamLedger, solvency: SolvencyState | None = None) -> None:
        """Aggiorna i saldi mostrati con l'ultimo stato del registro."""
        self._ledger = ledger
        if solvency is not None:
            self._solvency = solvency
        self.update(self._text())

    def _text(self) -> str:
        ledger = self._ledger
        text = (
            f"Cassa: {format_usd(ledger.cash_usd)}"
            f"  |  Cap residuo: {format_usd(ledger.cap_remaining_usd)}"
            f" su {format_usd(ledger.cap_usd)}"
        )
        if ledger.overspend_usd > 0:
            text += f"  |  SFORAMENTO: {format_usd(ledger.overspend_usd)}"
        if self._solvency is not None:
            status = economic_status(ledger, self._solvency)
            if status is not EconomicStatus.HEALTHY:
                text += f"  |  Squadra {STATUS_LABELS[status]}"
            if status is not EconomicStatus.BANKRUPT and self._solvency.insolvent_races > 0:
                left = BANKRUPTCY_RACES - self._solvency.insolvent_races
                text += f" (fallimento tra {left} gare)"
        return text
