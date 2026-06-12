"""Test dei Danni: riparazioni su Cassa e Cap, Sforamento (FOR-23).

Gli eventi CarDamage del motore di gara diventano addebiti forzosi:
la vettura corre sempre, anche oltre il Cap residuo, e il Cap negativo
e' lo Sforamento.
"""

from datetime import date

from fm_engine.economy import (
    SEASON_CAP_USD,
    TeamLedger,
    Transaction,
    TransactionKind,
    charge_damage_repairs,
    repair_cost_usd,
)
from fm_engine.events import CarDamage

GAME_DATE = date(2026, 3, 8)


def _funded(amount_usd: int) -> TeamLedger:
    return TeamLedger().record(
        Transaction(
            kind=TransactionKind.OTHER,
            amount_usd=amount_usd,
            game_date=GAME_DATE,
            description="Dotazione di prova",
        )
    )


def _damage(driver_id: int, amount_usd: int, lap: int = 10) -> CarDamage:
    return CarDamage(lap=lap, driver_id=driver_id, amount_usd=amount_usd)


def test_repair_cost_is_proportional_to_the_damage_entity():
    assert repair_cost_usd(_damage(1, 500_000)) == 500_000
    assert repair_cost_usd(_damage(1, 3_000_000)) == 3_000_000


def test_charge_repairs_only_for_the_player_cars():
    ledger = _funded(10_000_000)
    damages = (_damage(1, 500_000, lap=7), _damage(99, 2_000_000, lap=8))
    charged = charge_damage_repairs(
        ledger,
        damages,
        player_driver_ids=(1, 2),
        game_date=GAME_DATE,
        driver_names={1: "Rossi"},
    )
    assert len(charged.entries) == 2  # dotazione + una riparazione
    entry = charged.entries[-1]
    assert entry.kind is TransactionKind.DAMAGE
    assert entry.amount_usd == -500_000
    assert entry.counts_against_cap is True
    assert "Rossi" in entry.description
    assert "giro 7" in entry.description
    assert charged.cash_usd == 9_500_000
    assert charged.cap_remaining_usd == SEASON_CAP_USD - 500_000


def test_repair_beyond_the_cap_is_forced_and_tracked_as_overspend():
    """Mai vetture ferme per Cap: l'addebito passa e il Cap va negativo."""
    ledger = _funded(300_000_000).spend(
        TransactionKind.OTHER, SEASON_CAP_USD - 1_000_000, GAME_DATE
    )
    assert ledger.cap_remaining_usd == 1_000_000
    charged = charge_damage_repairs(
        ledger,
        (_damage(1, 3_000_000),),
        player_driver_ids=(1,),
        game_date=GAME_DATE,
    )
    assert charged.cap_remaining_usd == -2_000_000
    assert charged.overspend_usd == 2_000_000
    assert charged.cash_usd == ledger.cash_usd - 3_000_000
    # Il nome di ripiego quando il pilota non e' noto.
    assert "vettura 1" in charged.entries[-1].description


def test_no_player_damages_leave_the_ledger_intact():
    ledger = _funded(10_000_000)
    charged = charge_damage_repairs(
        ledger,
        (_damage(99, 1_000_000),),
        player_driver_ids=(1, 2),
        game_date=GAME_DATE,
    )
    assert charged == ledger
    assert ledger.overspend_usd == 0
