"""Qualifiche 2026: eliminazioni, Classifica tempi, determinismo (FOR-9)."""

from random import Random

import pytest

from fm_engine.circuits import circuit_by_code
from fm_engine.events import (
    PolePosition,
    QualifyingElimination,
    QualifyingSegment,
    QualifyingTimeSet,
)
from fm_engine.qualifying import simulate_qualifying
from fm_engine.state import CarAttributes, RaceEntry
from fm_engine.world.models import Driver


def _uniform_car() -> CarAttributes:
    return CarAttributes(
        engine_power=70,
        downforce=70,
        aero_efficiency=70,
        mechanical_grip=70,
        tyre_management=70,
        reliability=70,
    )


def _qualifier(driver_id: int, one_lap_pace: int) -> RaceEntry:
    """Vetture identiche: conta solo il Giro secco del pilota."""
    driver = Driver(
        id=driver_id,
        name=f"Driver {driver_id}",
        nationality="it",
        age=28,
        one_lap_pace=one_lap_pace,
        race_pace=101 - one_lap_pace if one_lap_pace < 100 else 40,
        duels=60,
        tyre_management=60,
        wet_weather=60,
        consistency=90,
        potential=50,
        salary_demand_usd=5_000_000,
    )
    return RaceEntry(driver=driver, team_id=(driver_id - 1) // 2 + 1, car=_uniform_car())


def _one_lap_graded_entries() -> tuple[RaceEntry, ...]:
    """22 iscritte con Giro secco crescente con l'id: 30, 33, ..., 93."""
    return tuple(_qualifier(driver_id, 30 + (driver_id - 1) * 3) for driver_id in range(1, 23))


def test_segments_sizes_and_eliminations(entry_factory):
    entries = entry_factory()
    result, events = simulate_qualifying(entries, circuit_by_code("monza"), seed=4)
    q1, q2, q3 = result.segments
    assert (q1.segment, q2.segment, q3.segment) == (
        QualifyingSegment.Q1,
        QualifyingSegment.Q2,
        QualifyingSegment.Q3,
    )
    assert (len(q1.rows), len(q2.rows), len(q3.rows)) == (22, 16, 10)
    eliminations = [event for event in events if isinstance(event, QualifyingElimination)]
    q1_out = [e for e in eliminations if e.segment is QualifyingSegment.Q1]
    q2_out = [e for e in eliminations if e.segment is QualifyingSegment.Q2]
    assert len(q1_out) == 6 and len(q2_out) == 6
    assert sorted(e.position for e in q1_out) == list(range(17, 23))
    assert sorted(e.position for e in q2_out) == list(range(11, 17))


def test_timesheets_are_sorted_and_complete(entry_factory):
    entries = entry_factory()
    result, events = simulate_qualifying(entries, circuit_by_code("monza"), seed=4)
    times_set = [event for event in events if isinstance(event, QualifyingTimeSet)]
    assert len(times_set) == 22 + 16 + 10
    for classification in result.segments:
        times = [row.time_seconds for row in classification.rows]
        assert times == sorted(times)
        assert [row.position for row in classification.rows] == list(
            range(1, len(classification.rows) + 1)
        )


def test_grid_order_follows_segment_rankings(entry_factory):
    entries = entry_factory()
    result, _ = simulate_qualifying(entries, circuit_by_code("monza"), seed=4)
    q1, q2, q3 = result.segments
    grid_ids = [entry.driver.id for entry in result.grid]
    assert len(result.grid) == 22
    assert grid_ids[:10] == [row.driver_id for row in q3.rows]
    assert grid_ids[10:16] == [row.driver_id for row in q2.rows[10:]]
    assert grid_ids[16:] == [row.driver_id for row in q1.rows[16:]]
    assert result.pole_driver_id == grid_ids[0]


def test_pole_event_matches_q3_winner(entry_factory):
    entries = entry_factory()
    result, events = simulate_qualifying(entries, circuit_by_code("monza"), seed=4)
    poles = [event for event in events if isinstance(event, PolePosition)]
    assert len(poles) == 1
    q3 = result.segments[-1]
    assert poles[0].driver_id == q3.rows[0].driver_id
    assert poles[0].time_seconds == q3.rows[0].time_seconds


def test_determinism(entry_factory):
    entries = entry_factory()
    circuit = circuit_by_code("monza")
    first_result, first_events = simulate_qualifying(entries, circuit, seed=12)
    second_result, second_events = simulate_qualifying(entries, circuit, seed=12)
    assert first_result == second_result
    assert first_events == second_events
    other_result, _ = simulate_qualifying(entries, circuit, seed=13)
    assert other_result.segments != first_result.segments


def test_one_lap_pace_drives_the_grid():
    """A parita' di vettura il Giro secco decide la griglia, non il Passo gara."""
    entries = _one_lap_graded_entries()
    circuit = circuit_by_code("monza")
    rng = Random(0)
    top_positions: list[float] = []
    bottom_positions: list[float] = []
    top_ids = {entry.driver.id for entry in entries[-5:]}
    bottom_ids = {entry.driver.id for entry in entries[:5]}
    for _ in range(10):
        result, _ = simulate_qualifying(entries, circuit, seed=rng.randint(0, 10**9))
        grid_position = {entry.driver.id: index + 1 for index, entry in enumerate(result.grid)}
        top_positions.extend(grid_position[driver_id] for driver_id in top_ids)
        bottom_positions.extend(grid_position[driver_id] for driver_id in bottom_ids)
    average_top = sum(top_positions) / len(top_positions)
    average_bottom = sum(bottom_positions) / len(bottom_positions)
    assert average_top < average_bottom - 5


def test_rejects_wrong_grid_size(entry_factory):
    with pytest.raises(ValueError):
        simulate_qualifying(entry_factory(count=20), circuit_by_code("monza"), seed=1)
