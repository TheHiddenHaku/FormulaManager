"""Test delle entrate automatiche della stagione (FOR-22).

Premio gara per piazzamento (mirror del seed SQL), Sponsor annuale
monotono nel Prestigio, Montepremi costruttori per classifica finale.
Tutte le entrate muovono solo la Cassa: il Cap residuo resta intatto.
"""

from datetime import date

import pytest

from fm_engine.economy import (
    DEFAULT_PLAYER_PRESTIGE,
    SEASON_CAP_USD,
    TeamLedger,
    TransactionKind,
    annual_sponsor_usd,
    constructors_pool_usd,
    credit_annual_sponsor,
    credit_constructors_pool,
    credit_race_prizes,
    race_prize_usd,
)
from fm_engine.events import ClassifiedResult
from fm_engine.world.models import PLAYER_TEAM_ID

GAME_DATE = date(2026, 3, 8)


def _result(position: int, driver_id: int, team_id: int) -> ClassifiedResult:
    return ClassifiedResult(
        position=position,
        driver_id=driver_id,
        team_id=team_id,
        total_time_seconds=5400.0 + position,
        gap_to_winner_seconds=float(position - 1),
        points=0,
        penalty_seconds=0.0,
    )


# ---------------------------------------------------------------------------
# Race prize: mirror of the seed table
# ---------------------------------------------------------------------------


def test_race_prize_mirrors_the_seed_table():
    assert race_prize_usd(1) == 3_000_000
    assert race_prize_usd(2) == 2_500_000
    assert race_prize_usd(10) == 650_000
    assert race_prize_usd(22) == 120_000


def test_race_prize_outside_the_table():
    assert race_prize_usd(23) == 0
    with pytest.raises(ValueError):
        race_prize_usd(0)


def test_credit_race_prizes_only_for_the_player_team():
    classification = (
        _result(1, driver_id=10, team_id=3),
        _result(3, driver_id=1, team_id=PLAYER_TEAM_ID),
        _result(11, driver_id=2, team_id=PLAYER_TEAM_ID),
    )
    ledger = credit_race_prizes(TeamLedger(), classification, GAME_DATE, "Albert Park")
    assert len(ledger.entries) == 2
    assert all(entry.kind is TransactionKind.RACE_PRIZE for entry in ledger.entries)
    assert ledger.entries[0].amount_usd == race_prize_usd(3)
    assert ledger.entries[0].description == "Albert Park: P3"
    assert ledger.entries[1].amount_usd == race_prize_usd(11)
    assert ledger.cash_usd == race_prize_usd(3) + race_prize_usd(11)
    assert ledger.cap_remaining_usd == SEASON_CAP_USD


# ---------------------------------------------------------------------------
# Annual sponsor: monotone in prestige
# ---------------------------------------------------------------------------


def test_annual_sponsor_grows_with_prestige():
    amounts = [annual_sponsor_usd(prestige) for prestige in (10, 30, 50, 70, 90)]
    assert amounts == sorted(amounts)
    assert len(set(amounts)) == len(amounts)


def test_annual_sponsor_rejects_out_of_scale_prestige():
    with pytest.raises(ValueError):
        annual_sponsor_usd(-1)
    with pytest.raises(ValueError):
        annual_sponsor_usd(101)


def test_credit_annual_sponsor_movement():
    ledger = credit_annual_sponsor(TeamLedger(), DEFAULT_PLAYER_PRESTIGE, date(2026, 1, 1))
    assert len(ledger.entries) == 1
    entry = ledger.entries[0]
    assert entry.kind is TransactionKind.ANNUAL_SPONSOR
    assert entry.amount_usd == annual_sponsor_usd(DEFAULT_PLAYER_PRESTIGE)
    assert str(DEFAULT_PLAYER_PRESTIGE) in entry.description
    assert ledger.cap_remaining_usd == SEASON_CAP_USD


# ---------------------------------------------------------------------------
# Constructors pool: end of season by final standing
# ---------------------------------------------------------------------------


def test_constructors_pool_decreases_with_the_standing():
    amounts = [constructors_pool_usd(position) for position in range(1, 12)]
    assert amounts == sorted(amounts, reverse=True)
    assert amounts[0] == 60_000_000
    assert amounts[-1] == 10_000_000


def test_constructors_pool_rejects_positions_outside_the_grid():
    with pytest.raises(ValueError):
        constructors_pool_usd(0)
    with pytest.raises(ValueError):
        constructors_pool_usd(12)


def test_credit_constructors_pool_movement():
    ledger = credit_constructors_pool(TeamLedger(), 4, date(2026, 12, 15))
    entry = ledger.entries[0]
    assert entry.kind is TransactionKind.CONSTRUCTORS_POOL
    assert entry.amount_usd == constructors_pool_usd(4)
    assert "P4" in entry.description
    assert ledger.cap_remaining_usd == SEASON_CAP_USD
