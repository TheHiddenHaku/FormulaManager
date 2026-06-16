"""Carry-over della vettura tra due stagioni (FOR-32).

La vettura nuova eredita una quota degli Attributi con regressione verso
la media di griglia: chi e' sopra la media perde, chi e' sotto guadagna.
Valori noti verificati a mano, piu' gli aggangi alla scala 0-100.
"""

from dataclasses import replace

import pytest

from fm_engine.winter.carryover import (
    CarryoverConfig,
    apply_carryover,
    carried_over_attributes,
    grid_attribute_means,
    regress_attribute,
)
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_engine.world.models import CAR_ATTRIBUTES, PLAYER_TEAM_ID

SEED = 42


def _set_up_world(philosophy: str = "balanced"):
    world = generate(SEED)
    world = replace(world, player_slot=PlayerSlot(name="Scuderia X", primary_color="#ff2800"))
    free = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free[0].id, free[1].id),
        engine_supplier_id=None,
        chassis_philosophy=philosophy,
    )
    return apply_team_setup(world, choices)


def test_regress_attribute_moves_toward_the_mean():
    # Valore 80, media 60, keep_ratio 0.7: 0.7*80 + 0.3*60 = 56 + 18 = 74.
    assert regress_attribute(80, 60.0, 0.7) == 74
    # Sotto la media risale: 40 verso 60 -> 0.7*40 + 0.3*60 = 28 + 18 = 46.
    assert regress_attribute(40, 60.0, 0.7) == 46
    # Sulla media resta fermo.
    assert regress_attribute(60, 60.0, 0.7) == 60


def test_regress_attribute_clamps_to_scale():
    assert regress_attribute(100, 100.0, 0.0) == 100
    # keep_ratio 0 appiattisce sulla media (arrotondata).
    assert regress_attribute(0, 50.4, 0.0) == 50


def test_keep_ratio_one_changes_nothing():
    attributes = dict.fromkeys(CAR_ATTRIBUTES, 70)
    means = dict.fromkeys(CAR_ATTRIBUTES, 50.0)
    out = carried_over_attributes(attributes, means, CarryoverConfig(keep_ratio=1.0))
    assert out == attributes


def test_keep_ratio_zero_collapses_onto_the_mean():
    attributes = dict.fromkeys(CAR_ATTRIBUTES, 90)
    means = {name: 55.0 for name in CAR_ATTRIBUTES}
    out = carried_over_attributes(attributes, means, CarryoverConfig(keep_ratio=0.0))
    assert all(value == 55 for value in out.values())


def test_grid_means_include_the_player_when_set_up():
    world = _set_up_world()
    means = grid_attribute_means(world)
    cars = [{name: getattr(team, name) for name in CAR_ATTRIBUTES} for team in world.ai_teams]
    cars.append(world.player_slot.car_attributes)
    for name in CAR_ATTRIBUTES:
        expected = sum(car[name] for car in cars) / len(cars)
        assert means[name] == pytest.approx(expected)


def test_apply_carryover_regresses_the_player_car_with_known_values():
    world = _set_up_world()
    before = world.player_slot.car_attributes
    means = grid_attribute_means(world)
    config = CarryoverConfig(keep_ratio=0.7)

    after = apply_carryover(world, config).player_slot.car_attributes

    for name in CAR_ATTRIBUTES:
        expected = regress_attribute(before[name], means[name], 0.7)
        assert after[name] == expected
    # La vettura del 2027 e' diversa da quella del 2026 (effetto conseguente).
    assert after != before


def test_apply_carryover_regresses_every_ai_team_toward_the_mean():
    world = _set_up_world()
    means = grid_attribute_means(world)
    after = apply_carryover(world)
    for old_team, new_team in zip(world.ai_teams, after.ai_teams, strict=True):
        for name in CAR_ATTRIBUTES:
            old = getattr(old_team, name)
            new = getattr(new_team, name)
            mean = means[name]
            if old > mean:
                assert new <= old, f"{name}: chi e' sopra la media non sale"
                assert new >= round(mean), f"{name}: non scende sotto la media"
            elif old < mean:
                assert new >= old, f"{name}: chi e' sotto la media non scende"


def test_apply_carryover_skips_the_player_before_team_setup():
    # Slot non configurato: niente attributi, la media e' quella delle AI.
    world = generate(SEED)
    world = replace(world, player_slot=PlayerSlot(name="X"))
    out = apply_carryover(world)
    assert not out.player_slot.is_set_up
    # Le squadre AI sono comunque regredite.
    assert out.ai_teams != world.ai_teams


def test_carryover_config_rejects_ratio_out_of_range():
    with pytest.raises(ValueError):
        CarryoverConfig(keep_ratio=1.5)
    with pytest.raises(ValueError):
        CarryoverConfig(keep_ratio=-0.1)


def test_apply_carryover_leaves_the_input_world_untouched():
    world = _set_up_world()
    before = world.player_slot.car_attributes
    apply_carryover(world)
    assert world.player_slot.car_attributes == before
    assert PLAYER_TEAM_ID == 0
