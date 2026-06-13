"""Stati economici e regolamento post-gara degli obblighi (FOR-24).

La squadra del giocatore ha uno stato economico esplicito e derivabile:
sana (HEALTHY), bloccata (BLOCKED: Cassa negativa o insolvenza in corso,
spese facoltative rifiutate e Progetti sospesi), emergenza (EMERGENCY:
scadenza stipendi scoperta, Misura d'emergenza in attesa di scelta),
fallita (BANKRUPT: insolvenza protratta per N gare consecutive, fine
della Carriera).

settle_post_race regola gli obblighi della scadenza di gara: rata
stipendi (T4.1.2) ed eventuale rata del prestito d'emergenza. Se la
Cassa non copre il dovuto e la Misura non e' ancora stata usata, il
regolamento si ferma e chiede la Misura (EMERGENCY_REQUIRED); a Misura
gia' bruciata gli addebiti passano comunque (la Cassa va in negativo) e
parte il conto alla rovescia del fallimento.

Motore puro (ADR 0002): la persistenza dello stato vive in
fm_persistence (colonna careers.solvency_state).
"""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date
from enum import Enum

from fm_engine.economy.ledger import TeamLedger, Transaction, TransactionKind
from fm_engine.economy.salaries import (
    RACES_PER_SEASON,
    charge_salary_instalments,
    salary_instalment_usd,
)
from fm_engine.world.models import Contract

# Consecutive insolvent races before bankruptcy. Configurable per call.
BANKRUPTCY_RACES = 3


class EconomicStatus(Enum):
    """Lo stato economico della squadra (CONTEXT.md, Misura d'emergenza)."""

    HEALTHY = "healthy"
    BLOCKED = "blocked"
    EMERGENCY = "emergency"
    BANKRUPT = "bankrupt"


@dataclass(frozen=True)
class SolvencyState:
    """La storia di solvibilita' della squadra, persistita a Checkpoint.

    emergency_used vale per la stagione corrente (una sola Misura);
    insolvent_races e' il conto alla rovescia del fallimento; le rate
    del prestito attivo viaggiano qui (quota capitale e interessi).
    prestige_malus accumula i malus degli sponsor-tampone e sconta lo
    Sponsor annuale futuro.
    """

    emergency_used: bool = False
    emergency_pending: bool = False
    insolvent_races: int = 0
    loan_instalments_left: int = 0
    loan_principal_instalment_usd: int = 0
    loan_interest_instalment_usd: int = 0
    prestige_malus: int = 0

    @property
    def loan_active(self) -> bool:
        """True finche' restano rate del prestito d'emergenza da pagare."""
        return self.loan_instalments_left > 0

    @property
    def loan_instalment_usd(self) -> int:
        """La rata complessiva del prestito: quota capitale piu' interessi."""
        return self.loan_principal_instalment_usd + self.loan_interest_instalment_usd


class SettlementOutcome(Enum):
    """L'esito del regolamento post-gara degli obblighi."""

    PAID = "paid"
    EMERGENCY_REQUIRED = "emergency_required"
    INSOLVENT = "insolvent"
    BANKRUPT = "bankrupt"


@dataclass(frozen=True)
class Settlement:
    """Il risultato di settle_post_race: nuovo registro, stato e esito."""

    ledger: TeamLedger
    solvency: SolvencyState
    outcome: SettlementOutcome
    shortfall_usd: int = 0


def economic_status(
    ledger: TeamLedger,
    solvency: SolvencyState,
    bankruptcy_races: int = BANKRUPTCY_RACES,
) -> EconomicStatus:
    """Lo stato economico corrente, derivato da registro e solvibilita'."""
    if solvency.insolvent_races >= bankruptcy_races:
        return EconomicStatus.BANKRUPT
    if solvency.emergency_pending:
        return EconomicStatus.EMERGENCY
    if ledger.cash_usd < 0 or solvency.insolvent_races > 0:
        return EconomicStatus.BLOCKED
    return EconomicStatus.HEALTHY


def optional_spending_blocked(ledger: TeamLedger, solvency: SolvencyState) -> bool:
    """True quando le spese facoltative sono bloccate (Progetti sospesi).

    Vale per ogni stato diverso da sana: il doppio vincolo di spesa
    (TeamLedger.spend) rifiuta comunque tutto con la Cassa a zero o
    negativa, questo predicato rende il blocco esplicito e interrogabile.
    """
    return economic_status(ledger, solvency) is not EconomicStatus.HEALTHY


def settle_post_race(
    ledger: TeamLedger,
    solvency: SolvencyState,
    contracts: Iterable[Contract],
    game_date: date,
    race_count: int = RACES_PER_SEASON,
    bankruptcy_races: int = BANKRUPTCY_RACES,
    charge_loan: bool = True,
) -> Settlement:
    """Regola gli obblighi della scadenza di gara: stipendi e rata prestito.

    Cassa sufficiente: addebita tutto e azzera il conto dell'insolvenza.
    Cassa insufficiente con Misura disponibile: nessun addebito, esito
    EMERGENCY_REQUIRED con lo scoperto; il chiamante applica la Misura
    (fm_engine.economy.emergency) e richiama il regolamento con
    charge_loan False, perche' il rientro del prestito appena acceso
    parte dalle gare successive. Cassa insufficiente a Misura bruciata:
    addebiti forzosi, conto alla rovescia del fallimento (BANKRUPT a
    insolvent_races >= N).
    """
    contracts = tuple(contracts)
    salary_due = sum(salary_instalment_usd(c.salary_usd, race_count) for c in contracts)
    loan_due = solvency.loan_instalment_usd if (charge_loan and solvency.loan_active) else 0
    due = salary_due + loan_due
    cash = ledger.cash_usd

    if cash < due and not solvency.emergency_used:
        return Settlement(
            ledger=ledger,
            solvency=replace(solvency, emergency_pending=True),
            outcome=SettlementOutcome.EMERGENCY_REQUIRED,
            shortfall_usd=due - cash,
        )

    ledger = charge_salary_instalments(ledger, contracts, game_date, race_count)
    if loan_due:
        left = solvency.loan_instalments_left
        ledger = ledger.record(
            Transaction(
                kind=TransactionKind.LOAN,
                amount_usd=-solvency.loan_principal_instalment_usd,
                game_date=game_date,
                description=f"Rata prestito ({left} rimanenti)",
            )
        )
        ledger = ledger.record(
            Transaction(
                kind=TransactionKind.INTEREST,
                amount_usd=-solvency.loan_interest_instalment_usd,
                game_date=game_date,
                description="Interessi sul prestito d'emergenza",
            )
        )
        solvency = replace(solvency, loan_instalments_left=left - 1)

    if cash < due:
        insolvent_races = solvency.insolvent_races + 1
        solvency = replace(solvency, insolvent_races=insolvent_races, emergency_pending=False)
        outcome = (
            SettlementOutcome.BANKRUPT
            if insolvent_races >= bankruptcy_races
            else SettlementOutcome.INSOLVENT
        )
        return Settlement(ledger, solvency, outcome, shortfall_usd=due - cash)

    solvency = replace(solvency, insolvent_races=0, emergency_pending=False)
    return Settlement(ledger, solvency, SettlementOutcome.PAID)
