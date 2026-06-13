"""Test del registro Cassa e Cap (FOR-15).

Il doppio vincolo e' il cuore: la spesa consentita e' min(Cassa, Cap
residuo $215M) e il rifiuto dichiara quale vincolo ha bloccato. Tutto
headless: il registro e' motore puro (ADR 0002).
"""

from datetime import date

import pytest

from fm_engine.economy import (
    SEASON_CAP_USD,
    SpendingBlocked,
    TeamLedger,
    Transaction,
    TransactionKind,
)

GAME_DATE = date(2026, 3, 8)


def _funded(amount_usd: int) -> TeamLedger:
    """Un registro con la sola dotazione iniziale richiesta dal test."""
    return TeamLedger().record(
        Transaction(
            kind=TransactionKind.OTHER,
            amount_usd=amount_usd,
            game_date=GAME_DATE,
            description="Dotazione di prova",
        )
    )


def test_empty_ledger_balances():
    ledger = TeamLedger()
    assert ledger.cash_usd == 0
    assert ledger.cap_usd == SEASON_CAP_USD == 215_000_000
    assert ledger.cap_remaining_usd == SEASON_CAP_USD
    assert ledger.allowed_spending_usd == 0
    assert ledger.entries == ()


def test_record_income_moves_cash_not_cap():
    ledger = _funded(30_000_000)
    assert ledger.cash_usd == 30_000_000
    assert ledger.cap_remaining_usd == SEASON_CAP_USD
    assert len(ledger.entries) == 1


def test_record_non_cap_expense_leaves_cap_intact():
    """Un addebito fuori Cap (stile stipendi) pesa solo sulla Cassa."""
    ledger = _funded(30_000_000).record(
        Transaction(
            kind=TransactionKind.SALARY,
            amount_usd=-5_000_000,
            game_date=GAME_DATE,
            description="Stipendi piloti",
            counts_against_cap=False,
        )
    )
    assert ledger.cash_usd == 25_000_000
    assert ledger.cap_remaining_usd == SEASON_CAP_USD


def test_spend_moves_cash_and_cap():
    ledger = _funded(30_000_000).spend(
        TransactionKind.OTHER, 10_000_000, GAME_DATE, description="Spesa di prova"
    )
    assert ledger.cash_usd == 20_000_000
    assert ledger.cap_remaining_usd == SEASON_CAP_USD - 10_000_000
    assert ledger.entries[-1].amount_usd == -10_000_000
    assert ledger.entries[-1].counts_against_cap is True


def test_spend_blocked_by_cash_when_cash_is_the_tight_side():
    """Cassa < Cap residuo: il rifiuto dichiara la Cassa."""
    ledger = _funded(1_000_000)
    with pytest.raises(SpendingBlocked) as blocked:
        ledger.spend(TransactionKind.OTHER, 2_000_000, GAME_DATE)
    assert blocked.value.constraint == "cash"
    assert blocked.value.allowed_usd == 1_000_000
    # Immutabile: il registro originale resta intatto.
    assert ledger.cash_usd == 1_000_000
    assert len(ledger.entries) == 1


def test_spend_blocked_by_cap_when_cap_is_the_tight_side():
    """Cassa > Cap residuo: il rifiuto dichiara il Cap."""
    ledger = _funded(300_000_000)
    with pytest.raises(SpendingBlocked) as blocked:
        ledger.spend(TransactionKind.OTHER, 220_000_000, GAME_DATE)
    assert blocked.value.constraint == "cap"
    assert blocked.value.allowed_usd == SEASON_CAP_USD


def test_spend_exactly_at_the_cash_limit_is_allowed():
    ledger = _funded(1_000_000).spend(TransactionKind.OTHER, 1_000_000, GAME_DATE)
    assert ledger.cash_usd == 0
    assert ledger.allowed_spending_usd == 0


def test_spend_exactly_at_the_cap_limit_is_allowed():
    ledger = _funded(300_000_000).spend(TransactionKind.OTHER, SEASON_CAP_USD, GAME_DATE)
    assert ledger.cap_remaining_usd == 0
    assert ledger.cash_usd == 300_000_000 - SEASON_CAP_USD
    # Cap esaurito: qualunque altra spesa a Cap e' bloccata dal Cap.
    with pytest.raises(SpendingBlocked) as blocked:
        ledger.spend(TransactionKind.OTHER, 1, GAME_DATE)
    assert blocked.value.constraint == "cap"


def test_spend_outside_the_cap_is_limited_by_cash_only():
    """Una spesa fuori Cap ignora il Cap residuo: conta solo la Cassa."""
    ledger = _funded(300_000_000).spend(TransactionKind.OTHER, SEASON_CAP_USD, GAME_DATE)
    after = ledger.spend(TransactionKind.OTHER, 50_000_000, GAME_DATE, counts_against_cap=False)
    assert after.cash_usd == 35_000_000
    assert after.cap_remaining_usd == 0


def test_spend_rejects_non_positive_amounts():
    ledger = _funded(10_000_000)
    with pytest.raises(ValueError):
        ledger.spend(TransactionKind.OTHER, 0, GAME_DATE)
    with pytest.raises(ValueError):
        ledger.spend(TransactionKind.OTHER, -5, GAME_DATE)


def test_history_keeps_registration_order():
    ledger = _funded(30_000_000)
    ledger = ledger.spend(TransactionKind.OTHER, 1_000_000, GAME_DATE, description="prima")
    ledger = ledger.spend(TransactionKind.OTHER, 2_000_000, GAME_DATE, description="seconda")
    assert [entry.description for entry in ledger.entries] == [
        "Dotazione di prova",
        "prima",
        "seconda",
    ]
