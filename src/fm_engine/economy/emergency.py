"""La Misura d'emergenza: prestito o sponsor-tampone (FOR-24).

L'unico salvagente economico della stagione, quando la Cassa non copre
la scadenza stipendi (CONTEXT.md). Due varianti, a scelta del giocatore:

- Prestito con interessi: capitale subito, rientro a rate (quota
  capitale piu' interessi) sulle gare successive, addebitate da
  settle_post_race.
- Sponsor-tampone: denaro subito in cambio di un malus al Prestigio,
  che sconta gli Sponsor annuali futuri.

Entrambe coprono lo scoperto piu' un margine di respiro. Una sola
Misura per stagione: il secondo tentativo e' un errore di programma
(il regolamento non la richiede piu' a emergency_used True).
"""

from dataclasses import dataclass, replace
from datetime import date

from fm_engine.economy.ledger import TeamLedger, Transaction, TransactionKind
from fm_engine.economy.solvency import SolvencyState

# Headroom credited beyond the shortfall, for both variants. Tunable.
EMERGENCY_HEADROOM_USD = 5_000_000

# Loan terms: total interest rate over the whole plan, repayment races.
LOAN_INTEREST_RATE = 0.20
LOAN_REPAYMENT_RACES = 6

# Prestige malus of the stopgap sponsor. Tunable.
STOPGAP_PRESTIGE_MALUS = 10


@dataclass(frozen=True)
class LoanOffer:
    """Il piano del prestito: capitale, rate e interessi per gara."""

    principal_usd: int
    repayment_races: int
    principal_instalment_usd: int
    interest_instalment_usd: int

    @property
    def instalment_usd(self) -> int:
        """La rata complessiva per gara."""
        return self.principal_instalment_usd + self.interest_instalment_usd

    @property
    def total_repayment_usd(self) -> int:
        """Quanto costa il prestito sull'intero piano di rientro."""
        return self.instalment_usd * self.repayment_races


@dataclass(frozen=True)
class StopgapOffer:
    """Lo sponsor-tampone: denaro subito, malus Prestigio."""

    amount_usd: int
    prestige_malus: int


def loan_offer(shortfall_usd: int) -> LoanOffer:
    """Il prestito offerto per lo scoperto dato: capitale e piano rate."""
    if shortfall_usd <= 0:
        raise ValueError(f"shortfall must be positive, got {shortfall_usd}")
    principal = shortfall_usd + EMERGENCY_HEADROOM_USD
    interest_total = int(principal * LOAN_INTEREST_RATE)
    return LoanOffer(
        principal_usd=principal,
        repayment_races=LOAN_REPAYMENT_RACES,
        principal_instalment_usd=principal // LOAN_REPAYMENT_RACES,
        interest_instalment_usd=interest_total // LOAN_REPAYMENT_RACES,
    )


def stopgap_offer(shortfall_usd: int) -> StopgapOffer:
    """Lo sponsor-tampone offerto per lo scoperto dato."""
    if shortfall_usd <= 0:
        raise ValueError(f"shortfall must be positive, got {shortfall_usd}")
    return StopgapOffer(
        amount_usd=shortfall_usd + EMERGENCY_HEADROOM_USD,
        prestige_malus=STOPGAP_PRESTIGE_MALUS,
    )


def _require_available(solvency: SolvencyState) -> None:
    if solvency.emergency_used:
        raise ValueError("emergency measure already used this season")


def take_loan(
    ledger: TeamLedger,
    solvency: SolvencyState,
    shortfall_usd: int,
    game_date: date,
) -> tuple[TeamLedger, SolvencyState]:
    """Attiva il prestito: capitale in Cassa, piano di rientro armato."""
    _require_available(solvency)
    offer = loan_offer(shortfall_usd)
    ledger = ledger.record(
        Transaction(
            kind=TransactionKind.LOAN,
            amount_usd=offer.principal_usd,
            game_date=game_date,
            description=(f"Prestito d'emergenza (rientro in {offer.repayment_races} gare)"),
        )
    )
    solvency = replace(
        solvency,
        emergency_used=True,
        emergency_pending=False,
        loan_instalments_left=offer.repayment_races,
        loan_principal_instalment_usd=offer.principal_instalment_usd,
        loan_interest_instalment_usd=offer.interest_instalment_usd,
    )
    return ledger, solvency


def take_stopgap_sponsor(
    ledger: TeamLedger,
    solvency: SolvencyState,
    shortfall_usd: int,
    game_date: date,
) -> tuple[TeamLedger, SolvencyState]:
    """Attiva lo sponsor-tampone: denaro subito, malus Prestigio."""
    _require_available(solvency)
    offer = stopgap_offer(shortfall_usd)
    ledger = ledger.record(
        Transaction(
            kind=TransactionKind.STOPGAP_SPONSOR,
            amount_usd=offer.amount_usd,
            game_date=game_date,
            description=f"Sponsor-tampone (malus Prestigio -{offer.prestige_malus})",
        )
    )
    solvency = replace(
        solvency,
        emergency_used=True,
        emergency_pending=False,
        prestige_malus=solvency.prestige_malus + offer.prestige_malus,
    )
    return ledger, solvency
