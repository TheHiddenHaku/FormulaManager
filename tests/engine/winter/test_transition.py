"""La transizione di stagione completa: Carry-over, scelte, rollover (FOR-32).

advance_winter mette in fila i cinque pezzi e produce lo stato della
stagione nuova (World + ledger). Test end-to-end e casi limite del
rollover economico (Sforamento zero e Sforamento pesante).
"""

from dataclasses import replace
from datetime import date

import pytest

from fm_engine.economy import (
    MINIMUM_CAP_USD,
    SEASON_CAP_USD,
    TeamLedger,
    Transaction,
    TransactionKind,
    annual_sponsor_usd,
)
from fm_engine.economy.income import DEFAULT_PLAYER_PRESTIGE
from fm_engine.winter import (
    RenegotiationChoices,
    WinterBudgetExceeded,
    WinterConfig,
    WinterDecisions,
    WinterProject,
    advance_winter,
)
from fm_engine.winter.carryover import grid_attribute_means, regress_attribute
from fm_engine.winter.projects import WinterProjectConfig
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_engine.world.models import CAR_ATTRIBUTES

SEED = 42
CONCLUDED_YEAR = 2026


def _set_up_world(philosophy: str = "balanced", engine_supplier_id=None):
    world = generate(SEED)
    world = replace(world, player_slot=PlayerSlot(name="Scuderia X", primary_color="#ff2800"))
    free = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free[0].id, free[1].id),
        engine_supplier_id=engine_supplier_id,
        chassis_philosophy=philosophy,
    )
    return apply_team_setup(world, choices)


def _funded(amount_usd: int, year: int = CONCLUDED_YEAR) -> TeamLedger:
    ledger = TeamLedger(season_year=year)
    return ledger.record(
        Transaction(
            kind=TransactionKind.OTHER,
            amount_usd=amount_usd,
            game_date=date(year, 1, 1),
            description="Dotazione di prova",
        )
    )


# --------------------------------------------------------------------------
# Carry-over conseguente
# --------------------------------------------------------------------------


def test_default_decisions_apply_only_carryover_to_the_car():
    world = _set_up_world()
    before = world.player_slot.car_attributes
    means = grid_attribute_means(world)

    out = advance_winter(world, _funded(0), CONCLUDED_YEAR)

    after = out.world.player_slot.car_attributes
    for name in CAR_ATTRIBUTES:
        assert after[name] == regress_attribute(before[name], means[name], 0.7)
    assert out.winter_spend_usd == 0
    # La vettura 2027 e' diversa dalla 2026 (effetto conseguente).
    assert after != before


def test_renegotiation_and_projects_change_the_new_season_car():
    world = _set_up_world(philosophy="balanced", engine_supplier_id=None)
    supplier = world.engine_suppliers[0]
    decisions = WinterDecisions(
        renegotiation=RenegotiationChoices(
            engine_supplier_id=supplier.id, chassis_philosophy="fast"
        ),
        winter_projects=(WinterProject(attribute="reliability", points=4),),
    )
    config = WinterConfig(
        projects=WinterProjectConfig(budget_usd=40_000_000, cost_per_point_usd=4_000_000)
    )

    out = advance_winter(world, _funded(0), CONCLUDED_YEAR, decisions, config)

    slot = out.world.player_slot
    # Rinegoziazione conseguente: motore del fornitore, Filosofia veloce.
    assert slot.engine_supplier_id == supplier.id
    assert slot.chassis_philosophy == "fast"
    assert slot.engine_power == supplier.engine_power
    # Progetto invernale conseguente: spesa dal budget dedicato.
    assert out.winter_spend_usd == 4 * 4_000_000


def test_budget_overflow_raises_before_touching_state():
    world = _set_up_world()
    decisions = WinterDecisions(
        winter_projects=(
            WinterProject(attribute="downforce", points=6),
            WinterProject(attribute="mechanical_grip", points=6),
        )
    )
    config = WinterConfig(
        projects=WinterProjectConfig(budget_usd=40_000_000, cost_per_point_usd=4_000_000)
    )
    with pytest.raises(WinterBudgetExceeded):
        advance_winter(world, _funded(0), CONCLUDED_YEAR, decisions, config)


# --------------------------------------------------------------------------
# Rollover economico: casi limite Sforamento
# --------------------------------------------------------------------------


def test_rollover_without_overspend_keeps_full_cap_and_credits_sponsor():
    world = _set_up_world()
    ledger = _funded(30_000_000)

    out = advance_winter(world, ledger, CONCLUDED_YEAR)

    assert out.ledger.season_year == CONCLUDED_YEAR + 1
    assert out.ledger.cap_usd == SEASON_CAP_USD
    assert out.ledger.overspend_usd == 0
    # Cassa = saldo riportato 30M + Sponsor annuale dal Prestigio.
    sponsor = annual_sponsor_usd(DEFAULT_PLAYER_PRESTIGE)
    assert out.ledger.cash_usd == 30_000_000 + sponsor


def test_rollover_with_heavy_overspend_drops_to_the_cap_floor():
    world = _set_up_world()
    # Danno forzoso enorme oltre il Cap: Sforamento pesante.
    ledger = _funded(500_000_000).record(
        Transaction(
            kind=TransactionKind.DAMAGE,
            amount_usd=-(SEASON_CAP_USD + 300_000_000),
            game_date=date(CONCLUDED_YEAR, 12, 1),
            description="Danno catastrofico",
            counts_against_cap=True,
        )
    )
    assert ledger.overspend_usd == 300_000_000

    out = advance_winter(world, ledger, CONCLUDED_YEAR)

    # La penalita' porta il Cap al pavimento (non sotto).
    assert out.ledger.cap_usd == MINIMUM_CAP_USD
    assert out.ledger.overspend_usd == 0


def test_rollover_with_light_overspend_reduces_cap_proportionally():
    world = _set_up_world()
    ledger = _funded(400_000_000).record(
        Transaction(
            kind=TransactionKind.DAMAGE,
            amount_usd=-(SEASON_CAP_USD + 5_000_000),
            game_date=date(CONCLUDED_YEAR, 12, 1),
            description="Danno",
            counts_against_cap=True,
        )
    )
    assert ledger.overspend_usd == 5_000_000

    out = advance_winter(world, ledger, CONCLUDED_YEAR)

    assert out.ledger.cap_usd == SEASON_CAP_USD - 5_000_000


def test_sponsor_scales_with_prestige_config():
    world = _set_up_world()
    high = advance_winter(
        world, _funded(0), CONCLUDED_YEAR, config=WinterConfig(player_prestige=90)
    )
    low = advance_winter(world, _funded(0), CONCLUDED_YEAR, config=WinterConfig(player_prestige=10))
    assert high.ledger.cash_usd > low.ledger.cash_usd


# --------------------------------------------------------------------------
# Immutabilita' e default
# --------------------------------------------------------------------------


def test_transition_does_not_mutate_inputs():
    world = _set_up_world()
    before_car = world.player_slot.car_attributes
    ledger = _funded(10_000_000)
    advance_winter(world, ledger, CONCLUDED_YEAR)
    assert world.player_slot.car_attributes == before_car
    assert ledger.season_year == CONCLUDED_YEAR


def test_transition_does_not_touch_contracts():
    world = _set_up_world()
    before = world.contracts
    out = advance_winter(world, _funded(0), CONCLUDED_YEAR)
    assert out.world.contracts == before
