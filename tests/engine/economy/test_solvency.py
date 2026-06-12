"""Test degli stati economici e del regolamento post-gara (FOR-24).

Transizioni deterministiche: sana, bloccata (spese facoltative
rifiutate), emergenza (Misura in attesa di scelta), fallita (insolvenza
protratta per N gare consecutive, N configurabile).
"""

from datetime import date

import pytest

from fm_engine.economy import (
    BANKRUPTCY_RACES,
    EconomicStatus,
    SettlementOutcome,
    SolvencyState,
    SpendingBlocked,
    TeamLedger,
    Transaction,
    TransactionKind,
    economic_status,
    optional_spending_blocked,
    settle_post_race,
    take_loan,
)
from fm_engine.world.models import PLAYER_TEAM_ID, Contract

GAME_DATE = date(2026, 3, 8)
RACE_COUNT = 24

# Two contracts: 12M + 6M a year, 750K per race in instalments.
CONTRACTS = (
    Contract(
        driver_id=1,
        team_id=PLAYER_TEAM_ID,
        start_season=2026,
        duration_seasons=2,
        salary_usd=12_000_000,
    ),
    Contract(
        driver_id=2,
        team_id=PLAYER_TEAM_ID,
        start_season=2026,
        duration_seasons=2,
        salary_usd=6_000_000,
    ),
)
SALARY_DUE = 750_000


def _funded(amount_usd: int) -> TeamLedger:
    return TeamLedger().record(
        Transaction(
            kind=TransactionKind.OTHER,
            amount_usd=amount_usd,
            game_date=GAME_DATE,
            description="Dotazione di prova",
        )
    )


# ---------------------------------------------------------------------------
# Economic states
# ---------------------------------------------------------------------------


def test_fresh_team_is_healthy():
    assert economic_status(_funded(10_000_000), SolvencyState()) is EconomicStatus.HEALTHY
    assert not optional_spending_blocked(_funded(10_000_000), SolvencyState())


def test_negative_cash_blocks_optional_spending():
    in_debt = _funded(-1_000_000)
    solvency = SolvencyState(emergency_used=True)
    assert economic_status(in_debt, solvency) is EconomicStatus.BLOCKED
    assert optional_spending_blocked(in_debt, solvency)
    # Il doppio vincolo di spesa rifiuta gia' tutto da solo.
    with pytest.raises(SpendingBlocked):
        in_debt.spend(TransactionKind.OTHER, 1, GAME_DATE)


def test_pending_emergency_state():
    solvency = SolvencyState(emergency_pending=True)
    assert economic_status(_funded(0), solvency) is EconomicStatus.EMERGENCY


def test_bankrupt_state_with_configurable_races():
    solvency = SolvencyState(emergency_used=True, insolvent_races=2)
    assert economic_status(_funded(0), solvency) is EconomicStatus.BLOCKED
    assert economic_status(_funded(0), solvency, bankruptcy_races=2) is EconomicStatus.BANKRUPT


# ---------------------------------------------------------------------------
# Post-race settlement
# ---------------------------------------------------------------------------


def test_settlement_paid_resets_the_insolvency_count():
    ledger = _funded(10_000_000)
    solvency = SolvencyState(emergency_used=True, insolvent_races=1)
    settlement = settle_post_race(ledger, solvency, CONTRACTS, GAME_DATE, RACE_COUNT)
    assert settlement.outcome is SettlementOutcome.PAID
    assert settlement.ledger.cash_usd == 10_000_000 - SALARY_DUE
    assert settlement.solvency.insolvent_races == 0
    assert economic_status(settlement.ledger, settlement.solvency) is EconomicStatus.HEALTHY


def test_uncovered_salaries_require_the_emergency_measure():
    ledger = _funded(100_000)
    settlement = settle_post_race(ledger, SolvencyState(), CONTRACTS, GAME_DATE, RACE_COUNT)
    assert settlement.outcome is SettlementOutcome.EMERGENCY_REQUIRED
    assert settlement.shortfall_usd == SALARY_DUE - 100_000
    # Nessun addebito finche' la Misura non e' scelta.
    assert settlement.ledger == ledger
    assert settlement.solvency.emergency_pending
    assert economic_status(settlement.ledger, settlement.solvency) is EconomicStatus.EMERGENCY


def test_emergency_then_loan_then_paid_and_instalments_run():
    """Insolvenza, Misura, rientro: il piano del prestito gira a ogni gara."""
    ledger = _funded(100_000)
    first = settle_post_race(ledger, SolvencyState(), CONTRACTS, GAME_DATE, RACE_COUNT)
    assert first.outcome is SettlementOutcome.EMERGENCY_REQUIRED

    ledger, solvency = take_loan(first.ledger, first.solvency, first.shortfall_usd, GAME_DATE)
    # Il rientro parte dalle gare successive: il regolamento della stessa
    # gara non addebita la rata del prestito appena acceso.
    settled = settle_post_race(
        ledger, solvency, CONTRACTS, GAME_DATE, RACE_COUNT, charge_loan=False
    )
    assert settled.outcome is SettlementOutcome.PAID
    assert settled.solvency.loan_instalments_left == solvency.loan_instalments_left

    # Dalla gara successiva la rata del prestito viene addebitata.
    after_next = settle_post_race(
        settled.ledger, settled.solvency, CONTRACTS, date(2026, 3, 22), RACE_COUNT
    )
    assert after_next.outcome is SettlementOutcome.PAID
    assert after_next.solvency.loan_instalments_left == solvency.loan_instalments_left - 1
    kinds = [entry.kind for entry in after_next.ledger.entries[-2:]]
    assert kinds == [TransactionKind.LOAN, TransactionKind.INTEREST]


def test_second_insolvency_starts_the_bankruptcy_countdown():
    """Misura bruciata: gli addebiti passano, la Cassa va in negativo."""
    ledger = _funded(100_000)
    solvency = SolvencyState(emergency_used=True)
    settlement = settle_post_race(ledger, solvency, CONTRACTS, GAME_DATE, RACE_COUNT)
    assert settlement.outcome is SettlementOutcome.INSOLVENT
    assert settlement.solvency.insolvent_races == 1
    assert settlement.ledger.cash_usd == 100_000 - SALARY_DUE
    assert economic_status(settlement.ledger, settlement.solvency) is EconomicStatus.BLOCKED
    assert optional_spending_blocked(settlement.ledger, settlement.solvency)


def test_protracted_insolvency_ends_in_bankruptcy():
    """Sequenza completa: N gare consecutive di insolvenza = fallimento."""
    ledger = _funded(0)
    solvency = SolvencyState(emergency_used=True)
    outcomes = []
    for _ in range(BANKRUPTCY_RACES):
        settlement = settle_post_race(ledger, solvency, CONTRACTS, GAME_DATE, RACE_COUNT)
        outcomes.append(settlement.outcome)
        ledger, solvency = settlement.ledger, settlement.solvency
    assert outcomes[:-1] == [SettlementOutcome.INSOLVENT] * (BANKRUPTCY_RACES - 1)
    assert outcomes[-1] is SettlementOutcome.BANKRUPT
    assert solvency.insolvent_races == BANKRUPTCY_RACES
    assert economic_status(ledger, solvency) is EconomicStatus.BANKRUPT


def test_a_paid_race_interrupts_the_countdown():
    ledger = _funded(0)
    solvency = SolvencyState(emergency_used=True, insolvent_races=2)
    rich = ledger.record(
        Transaction(
            kind=TransactionKind.ONE_OFF_SPONSOR,
            amount_usd=20_000_000,
            game_date=GAME_DATE,
            description="Sponsor salvifico",
        )
    )
    settlement = settle_post_race(rich, solvency, CONTRACTS, GAME_DATE, RACE_COUNT)
    assert settlement.outcome is SettlementOutcome.PAID
    assert settlement.solvency.insolvent_races == 0


def test_settlement_without_contracts_and_healthy_cash_is_a_no_op():
    ledger = _funded(1_000_000)
    settlement = settle_post_race(ledger, SolvencyState(), (), GAME_DATE, RACE_COUNT)
    assert settlement.outcome is SettlementOutcome.PAID
    assert settlement.ledger == ledger
