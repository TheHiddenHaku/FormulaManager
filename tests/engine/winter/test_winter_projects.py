"""Progetti invernali con budget dedicato (FOR-32).

I Progetti invernali comprano punti attributo da un budget dedicato e li
applicano davvero alla vettura della stagione nuova. Vincoli: budget,
range punti, motore Cliente (niente sviluppo Potenza motore).
"""

import pytest

from fm_engine.winter.projects import (
    CustomerEngineLocked,
    WinterBudgetExceeded,
    WinterProject,
    WinterProjectConfig,
    apply_winter_projects,
    validate_selection,
)
from fm_engine.world.models import CAR_ATTRIBUTES

_CONFIG = WinterProjectConfig(
    budget_usd=40_000_000, cost_per_point_usd=4_000_000, max_points_per_project=6
)


def _baseline() -> dict[str, int]:
    return dict.fromkeys(CAR_ATTRIBUTES, 60)


def test_winter_project_cost_is_points_times_unit_cost():
    project = WinterProject(attribute="downforce", points=5)
    assert project.cost_usd(_CONFIG) == 5 * 4_000_000


def test_apply_winter_projects_adds_points_to_the_car():
    selection = (
        WinterProject(attribute="downforce", points=4),
        WinterProject(attribute="reliability", points=2),
    )
    out = apply_winter_projects(_baseline(), selection, is_engine_customer=False, config=_CONFIG)
    assert out["downforce"] == 64
    assert out["reliability"] == 62
    # Gli altri attributi non cambiano.
    assert out["aero_efficiency"] == 60


def test_apply_winter_projects_clamps_to_scale():
    out = apply_winter_projects(
        {**_baseline(), "reliability": 98},
        (WinterProject(attribute="reliability", points=6),),
        is_engine_customer=False,
        config=_CONFIG,
    )
    assert out["reliability"] == 100


def test_selection_over_budget_is_rejected():
    # Budget 40M, costo unitario 4M: 11 punti = 44M > budget.
    selection = (
        WinterProject(attribute="downforce", points=6),
        WinterProject(attribute="mechanical_grip", points=5),
    )
    with pytest.raises(WinterBudgetExceeded):
        validate_selection(selection, is_engine_customer=False, config=_CONFIG)


def test_selection_within_budget_is_accepted():
    selection = (
        WinterProject(attribute="downforce", points=6),
        WinterProject(attribute="mechanical_grip", points=4),
    )
    spend = validate_selection(selection, is_engine_customer=False, config=_CONFIG)
    assert spend == 10 * 4_000_000


def test_customer_team_cannot_develop_engine_power():
    with pytest.raises(CustomerEngineLocked):
        apply_winter_projects(
            _baseline(),
            (WinterProject(attribute="engine_power", points=3),),
            is_engine_customer=True,
            config=_CONFIG,
        )


def test_own_engine_team_can_develop_engine_power():
    out = apply_winter_projects(
        _baseline(),
        (WinterProject(attribute="engine_power", points=3),),
        is_engine_customer=False,
        config=_CONFIG,
    )
    assert out["engine_power"] == 63


def test_unknown_attribute_is_rejected():
    with pytest.raises(ValueError):
        validate_selection(
            (WinterProject(attribute="cornering", points=1),),
            is_engine_customer=False,
            config=_CONFIG,
        )


def test_points_out_of_range_is_rejected():
    with pytest.raises(ValueError):
        validate_selection(
            (WinterProject(attribute="downforce", points=0),),
            is_engine_customer=False,
            config=_CONFIG,
        )
    with pytest.raises(ValueError):
        validate_selection(
            (WinterProject(attribute="downforce", points=7),),
            is_engine_customer=False,
            config=_CONFIG,
        )


def test_empty_selection_costs_nothing_and_changes_nothing():
    spend = validate_selection((), is_engine_customer=False, config=_CONFIG)
    assert spend == 0
    out = apply_winter_projects(_baseline(), (), is_engine_customer=False, config=_CONFIG)
    assert out == _baseline()


def test_config_rejects_invalid_values():
    with pytest.raises(ValueError):
        WinterProjectConfig(cost_per_point_usd=0)
    with pytest.raises(ValueError):
        WinterProjectConfig(budget_usd=-1)
    with pytest.raises(ValueError):
        WinterProjectConfig(max_points_per_project=0)
