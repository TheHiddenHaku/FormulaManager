"""Unit test del Setup squadra puro (FOR-7, fm_engine.world.team_setup).

Coprono l'applicazione delle scelte del wizard: vincolo dei 2 piloti,
rimpiazzi automatici nelle squadre AI, motore interno vs Cliente,
Filosofia telaio sugli attributi vettura iniziali, invarianti post-setup
e validazioni con errori chiari. Il Mondo e' frozen: si verifica anche
che l'input non venga toccato.
"""

from collections import Counter
from dataclasses import replace

import pytest

from fm_engine.world import (
    PLAYER_TEAM_ID,
    PlayerSlot,
    TeamSetupChoices,
    TeamSetupConfig,
    WorldConfig,
    apply_team_setup,
    generate,
)
from fm_engine.world.models import CAR_ATTRIBUTES
from fm_engine.world.team_setup import baseline_car_attribute, initial_car_attributes

SEED = 42

CONFIG = TeamSetupConfig()


@pytest.fixture
def world():
    """Mondo generato con lo slot del giocatore gia' nominato (T1.3.1)."""
    generated = generate(SEED)
    return replace(generated, player_slot=PlayerSlot(name="Scuderia X Racing"))


def _contracted_ids(world, count=2):
    """Gli id dei primi piloti contrattualizzati nelle squadre AI."""
    return tuple(contract.driver_id for contract in world.contracts[:count])


def _free_agent_ids(world):
    return tuple(driver.id for driver in world.drivers_without_contract)


def _choices(world, driver_ids, engine_supplier_id=None, philosophy="fast"):
    return TeamSetupChoices(
        driver_ids=driver_ids,
        engine_supplier_id=engine_supplier_id,
        chassis_philosophy=philosophy,
    )


# ---------------------------------------------------------------------------
# Player contracts
# ---------------------------------------------------------------------------


def test_player_gets_two_contracts_with_demand_salary_and_default_duration(world):
    picked = _contracted_ids(world)
    after = apply_team_setup(world, _choices(world, picked))

    player_contracts = after.contracts_of(PLAYER_TEAM_ID)
    assert tuple(c.driver_id for c in player_contracts) == picked
    demands = {driver.id: driver.salary_demand_usd for driver in world.drivers}
    for contract in player_contracts:
        assert contract.salary_usd == demands[contract.driver_id]
        assert contract.duration_seasons == CONFIG.player_contract_duration_seasons
        assert contract.start_season == world.config.initial_season


def test_player_contract_duration_is_tunable(world):
    config = TeamSetupConfig(player_contract_duration_seasons=3)
    after = apply_team_setup(world, _choices(world, _contracted_ids(world)), config)
    assert all(c.duration_seasons == 3 for c in after.contracts_of(PLAYER_TEAM_ID))


# ---------------------------------------------------------------------------
# Automatic refills of the AI teams
# ---------------------------------------------------------------------------


def test_ai_team_losing_a_driver_receives_a_free_agent(world):
    replaced = world.contracts[0]
    free_agents = _free_agent_ids(world)
    picked = (replaced.driver_id, _free_agent_ids(world)[0])
    after = apply_team_setup(world, _choices(world, picked))

    team_contracts = after.contracts_of(replaced.team_id)
    new_driver_ids = {c.driver_id for c in team_contracts} - {
        c.driver_id for c in world.contracts_of(replaced.team_id)
    }
    # The refill is the other free agent (the first one went to the player).
    assert new_driver_ids == {free_agents[1]}
    refill = next(c for c in team_contracts if c.driver_id in new_driver_ids)
    substitute = next(d for d in world.drivers if d.id == free_agents[1])
    # Same duration as the replaced contract, substitute's salary demand.
    assert refill.duration_seasons == replaced.duration_seasons
    assert refill.salary_usd == substitute.salary_demand_usd
    assert refill.start_season == replaced.start_season


def test_two_contracted_picks_consume_both_free_agents(world):
    picked = _contracted_ids(world)
    after = apply_team_setup(world, _choices(world, picked))
    assert after.drivers_without_contract == ()


def test_both_picks_from_the_same_ai_team(world):
    team_id = world.contracts[0].team_id
    picked = tuple(c.driver_id for c in world.contracts_of(team_id))
    after = apply_team_setup(world, _choices(world, picked))

    refilled = after.contracts_of(team_id)
    assert len(refilled) == 2
    assert {c.driver_id for c in refilled} == set(_free_agent_ids(world))


def test_picking_both_free_agents_changes_no_ai_contract(world):
    after = apply_team_setup(world, _choices(world, _free_agent_ids(world)))
    for team in world.ai_teams:
        assert after.contracts_of(team.id) == world.contracts_of(team.id)


# ---------------------------------------------------------------------------
# Post-setup invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pick_kind", ["contracted", "free", "mixed"])
def test_invariants_after_setup(world, pick_kind):
    if pick_kind == "contracted":
        picked = _contracted_ids(world)
    elif pick_kind == "free":
        picked = _free_agent_ids(world)
    else:
        picked = (_contracted_ids(world)[0], _free_agent_ids(world)[0])
    after = apply_team_setup(world, _choices(world, picked))

    # 22 total drivers, every team (player included) exactly 2 drivers,
    # no driver with two contracts.
    assert len(after.drivers) == 22
    per_team = Counter(contract.team_id for contract in after.contracts)
    assert per_team[PLAYER_TEAM_ID] == 2
    assert all(per_team[team.id] == 2 for team in after.ai_teams)
    driver_ids = [contract.driver_id for contract in after.contracts]
    assert len(driver_ids) == len(set(driver_ids))


def test_input_world_is_not_mutated(world):
    before_contracts = world.contracts
    before_slot = world.player_slot
    apply_team_setup(world, _choices(world, _contracted_ids(world)))
    assert world.contracts == before_contracts
    assert world.player_slot == before_slot
    assert not world.player_slot.is_set_up


# ---------------------------------------------------------------------------
# Engine choice
# ---------------------------------------------------------------------------


def test_in_house_engine_power_is_the_neutral_baseline(world):
    after = apply_team_setup(world, _choices(world, _contracted_ids(world)))
    assert after.player_slot.engine_supplier_id is None
    assert after.player_slot.engine_power == baseline_car_attribute(world.config)


def test_customer_engine_power_is_shared_with_the_supplier(world):
    supplier = world.engine_suppliers[0]
    after = apply_team_setup(
        world, _choices(world, _contracted_ids(world), engine_supplier_id=supplier.id)
    )
    assert after.player_slot.engine_supplier_id == supplier.id
    assert after.player_slot.engine_power == supplier.engine_power


# ---------------------------------------------------------------------------
# Chassis philosophy
# ---------------------------------------------------------------------------


def test_fast_philosophy_boosts_aero_efficiency(world):
    baseline = baseline_car_attribute(world.config)
    after = apply_team_setup(world, _choices(world, _contracted_ids(world), philosophy="fast"))
    slot = after.player_slot
    assert slot.chassis_philosophy == "fast"
    assert slot.aero_efficiency == baseline + CONFIG.chassis_bonus
    assert slot.downforce == baseline - CONFIG.chassis_malus
    assert slot.mechanical_grip == baseline - CONFIG.chassis_malus
    assert slot.tyre_management == baseline
    assert slot.reliability == baseline


def test_technical_philosophy_is_the_exact_inverse(world):
    baseline = baseline_car_attribute(world.config)
    after = apply_team_setup(world, _choices(world, _contracted_ids(world), philosophy="technical"))
    slot = after.player_slot
    assert slot.aero_efficiency == baseline - CONFIG.chassis_bonus
    assert slot.downforce == baseline + CONFIG.chassis_malus
    assert slot.mechanical_grip == baseline + CONFIG.chassis_malus


def test_chassis_deltas_are_tunable(world):
    config = TeamSetupConfig(chassis_bonus=20, chassis_malus=10)
    baseline = baseline_car_attribute(world.config)
    attributes = initial_car_attributes(world, None, "fast", config)
    assert attributes["aero_efficiency"] == baseline + 20
    assert attributes["downforce"] == baseline - 10


def test_attributes_stay_on_the_0_100_scale():
    # Extreme tunables: the deltas must clamp to the scale.
    high_world = generate(SEED, WorldConfig(car_attribute_range=(95, 100)))
    attributes = initial_car_attributes(
        high_world, None, "fast", TeamSetupConfig(chassis_bonus=50, chassis_malus=50)
    )
    assert all(0 <= value <= 100 for value in attributes.values())


def test_balanced_philosophy_keeps_the_neutral_baseline(world):
    baseline = baseline_car_attribute(world.config)
    attributes = initial_car_attributes(world, None, "balanced")
    assert attributes == dict.fromkeys(CAR_ATTRIBUTES, baseline)


# ---------------------------------------------------------------------------
# Validations
# ---------------------------------------------------------------------------


def test_rejects_duplicate_driver_ids(world):
    driver_id = _contracted_ids(world)[0]
    with pytest.raises(ValueError, match="2 distinct drivers"):
        apply_team_setup(world, _choices(world, (driver_id, driver_id)))


def test_rejects_unknown_driver_ids(world):
    with pytest.raises(ValueError, match="unknown driver ids"):
        apply_team_setup(world, _choices(world, (999, 1000)))


def test_rejects_unknown_engine_supplier(world):
    with pytest.raises(ValueError, match="unknown engine supplier"):
        apply_team_setup(world, _choices(world, _contracted_ids(world), engine_supplier_id=999))


def test_rejects_unknown_chassis_philosophy(world):
    with pytest.raises(ValueError, match="chassis philosophy"):
        apply_team_setup(world, _choices(world, _contracted_ids(world), philosophy="hybrid"))


def test_rejects_player_slot_without_identity():
    nameless = generate(SEED)
    with pytest.raises(ValueError, match="no identity"):
        apply_team_setup(nameless, _choices(nameless, _contracted_ids(nameless)))


def test_rejects_a_second_setup(world):
    once = apply_team_setup(world, _choices(world, _contracted_ids(world)))
    with pytest.raises(ValueError, match="already applied"):
        apply_team_setup(once, _choices(once, _free_agent_ids(world)))


def test_rejects_setup_without_enough_free_agents():
    config = WorldConfig(free_agents=0)
    world = replace(generate(SEED, config), player_slot=PlayerSlot(name="Scuderia X"))
    with pytest.raises(ValueError, match="not enough free agents"):
        apply_team_setup(world, _choices(world, _contracted_ids(world)))


def test_config_rejects_bad_values():
    with pytest.raises(ValueError):
        TeamSetupConfig(player_contract_duration_seasons=0)
    with pytest.raises(ValueError):
        TeamSetupConfig(in_house_engine_cost_usd=-1)
    with pytest.raises(ValueError):
        TeamSetupConfig(chassis_bonus=-1)
