"""Test del rollover di stagione con penalita' da Sforamento (FOR-23).

Il nuovo anno parte col Cap pieno meno la penalita' proporzionale allo
Sforamento (nessuna penalita' senza Sforamento), il Cap non scende mai
sotto il pavimento e la Cassa finale viene riportata come saldo.
"""

from datetime import date

import pytest

from fm_engine.economy import (
    MINIMUM_CAP_USD,
    SEASON_CAP_USD,
    TeamLedger,
    Transaction,
    TransactionKind,
    overspend_penalty_usd,
    start_next_season,
)

GAME_DATE = date(2026, 12, 31)


def _funded(amount_usd: int) -> TeamLedger:
    return TeamLedger().record(
        Transaction(
            kind=TransactionKind.OTHER,
            amount_usd=amount_usd,
            game_date=date(2026, 1, 1),
            description="Dotazione di prova",
        )
    )


def _overspent(ledger: TeamLedger, damage_usd: int) -> TeamLedger:
    """Un registro in Sforamento: danno forzoso oltre il Cap residuo."""
    return ledger.record(
        Transaction(
            kind=TransactionKind.DAMAGE,
            amount_usd=-damage_usd,
            game_date=GAME_DATE,
            description="Riparazione di prova",
            counts_against_cap=True,
        )
    )


def test_rollover_without_overspend_keeps_the_full_cap():
    ledger = _funded(30_000_000)
    next_season = start_next_season(ledger, GAME_DATE)
    assert next_season.season_year == 2027
    assert next_season.cap_usd == SEASON_CAP_USD
    assert next_season.overspend_usd == 0
    # La Cassa viaggia nel nuovo registro come saldo riportato.
    assert next_season.cash_usd == 30_000_000
    assert len(next_season.entries) == 1
    assert "2026" in next_season.entries[0].description
    # Il saldo riportato non tocca il Cap.
    assert next_season.cap_remaining_usd == SEASON_CAP_USD


def test_rollover_with_overspend_reduces_the_next_cap():
    ledger = _overspent(_funded(300_000_000), SEASON_CAP_USD + 2_000_000)
    assert ledger.overspend_usd == 2_000_000
    next_season = start_next_season(ledger, GAME_DATE)
    assert next_season.cap_usd == SEASON_CAP_USD - 2_000_000
    assert next_season.overspend_usd == 0


def test_rollover_penalty_never_goes_below_the_cap_floor():
    ledger = _overspent(_funded(500_000_000), SEASON_CAP_USD + 200_000_000)
    assert ledger.overspend_usd == 200_000_000
    next_season = start_next_season(ledger, GAME_DATE)
    assert next_season.cap_usd == MINIMUM_CAP_USD


def test_rollover_with_zero_cash_has_no_carryover_entry():
    next_season = start_next_season(TeamLedger(), GAME_DATE)
    assert next_season.entries == ()
    assert next_season.cash_usd == 0


def test_overspend_penalty_rejects_negative_values():
    with pytest.raises(ValueError):
        overspend_penalty_usd(-1)
