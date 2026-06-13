"""Test degli stipendi piloti (FOR-22).

L'addebito periodico pesa SOLO sulla Cassa: l'invarianza del Cap residuo
e' asserita esplicitamente, come da regole F1 2026 (stipendi fuori Cap).
"""

from datetime import date

import pytest

from fm_engine.economy import (
    RACES_PER_SEASON,
    SEASON_CAP_USD,
    TeamLedger,
    TransactionKind,
    charge_salary_instalments,
    salary_instalment_usd,
)
from fm_engine.world.models import PLAYER_TEAM_ID, Contract

GAME_DATE = date(2026, 3, 8)


def _contract(driver_id: int, salary_usd: int) -> Contract:
    return Contract(
        driver_id=driver_id,
        team_id=PLAYER_TEAM_ID,
        start_season=2026,
        duration_seasons=2,
        salary_usd=salary_usd,
    )


def test_races_per_season_follows_the_calendar():
    assert RACES_PER_SEASON == 24


def test_salary_instalment_is_the_per_race_share():
    assert salary_instalment_usd(12_000_000) == 500_000
    assert salary_instalment_usd(6_000_000) == 250_000
    assert salary_instalment_usd(12_000_000, race_count=4) == 3_000_000


def test_salary_instalment_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        salary_instalment_usd(12_000_000, race_count=0)
    with pytest.raises(ValueError):
        salary_instalment_usd(-1)


def test_charge_aggregates_the_player_contracts_cash_only():
    contracts = (_contract(1, 12_000_000), _contract(2, 6_000_000))
    ledger = charge_salary_instalments(TeamLedger(), contracts, GAME_DATE)
    assert len(ledger.entries) == 1
    entry = ledger.entries[0]
    assert entry.kind is TransactionKind.SALARY
    assert entry.amount_usd == -750_000
    assert entry.counts_against_cap is False
    assert "2 Contratti" in entry.description
    assert ledger.cash_usd == -750_000
    # Asserzione esplicita: gli stipendi non consumano Cap.
    assert ledger.cap_remaining_usd == SEASON_CAP_USD


def test_charge_without_contracts_leaves_the_ledger_intact():
    ledger = TeamLedger()
    assert charge_salary_instalments(ledger, (), GAME_DATE) == ledger
