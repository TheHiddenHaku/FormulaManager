"""Test della Misura d'emergenza: prestito e sponsor-tampone (FOR-24).

Una sola Misura per stagione, nelle due varianti, con tutti gli effetti
registrati nel registro con causale.
"""

from datetime import date

import pytest

from fm_engine.economy import (
    EMERGENCY_HEADROOM_USD,
    LOAN_INTEREST_RATE,
    LOAN_REPAYMENT_RACES,
    STOPGAP_PRESTIGE_MALUS,
    SolvencyState,
    TeamLedger,
    TransactionKind,
    loan_offer,
    stopgap_offer,
    take_loan,
    take_stopgap_sponsor,
)

GAME_DATE = date(2026, 3, 8)
SHORTFALL = 650_000


def test_loan_offer_terms():
    offer = loan_offer(SHORTFALL)
    assert offer.principal_usd == SHORTFALL + EMERGENCY_HEADROOM_USD
    assert offer.repayment_races == LOAN_REPAYMENT_RACES
    assert offer.principal_instalment_usd == offer.principal_usd // LOAN_REPAYMENT_RACES
    expected_interest = int(offer.principal_usd * LOAN_INTEREST_RATE) // LOAN_REPAYMENT_RACES
    assert offer.interest_instalment_usd == expected_interest
    # Il prestito costa piu' del capitale: gli interessi sono reali.
    assert offer.total_repayment_usd > offer.principal_usd - LOAN_REPAYMENT_RACES


def test_offers_reject_non_positive_shortfalls():
    with pytest.raises(ValueError):
        loan_offer(0)
    with pytest.raises(ValueError):
        stopgap_offer(-1)


def test_take_loan_credits_the_principal_and_arms_the_plan():
    ledger, solvency = take_loan(TeamLedger(), SolvencyState(), SHORTFALL, GAME_DATE)
    offer = loan_offer(SHORTFALL)
    entry = ledger.entries[-1]
    assert entry.kind is TransactionKind.LOAN
    assert entry.amount_usd == offer.principal_usd
    assert "Prestito d'emergenza" in entry.description
    assert ledger.cash_usd == offer.principal_usd
    # Il prestito non tocca il Cap.
    assert ledger.cap_remaining_usd == ledger.cap_usd
    assert solvency.emergency_used
    assert not solvency.emergency_pending
    assert solvency.loan_instalments_left == offer.repayment_races
    assert solvency.loan_instalment_usd == offer.instalment_usd


def test_take_stopgap_credits_the_cash_and_applies_the_malus():
    ledger, solvency = take_stopgap_sponsor(TeamLedger(), SolvencyState(), SHORTFALL, GAME_DATE)
    offer = stopgap_offer(SHORTFALL)
    entry = ledger.entries[-1]
    assert entry.kind is TransactionKind.STOPGAP_SPONSOR
    assert entry.amount_usd == offer.amount_usd
    assert str(STOPGAP_PRESTIGE_MALUS) in entry.description
    assert solvency.emergency_used
    assert solvency.prestige_malus == STOPGAP_PRESTIGE_MALUS
    assert not solvency.loan_active


def test_one_measure_per_season_no_exceptions():
    _, used = take_loan(TeamLedger(), SolvencyState(), SHORTFALL, GAME_DATE)
    with pytest.raises(ValueError):
        take_loan(TeamLedger(), used, SHORTFALL, GAME_DATE)
    with pytest.raises(ValueError):
        take_stopgap_sponsor(TeamLedger(), used, SHORTFALL, GAME_DATE)
