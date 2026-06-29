"""Punti 2026: tabella e attribuzione per posizione (FOR-8, Weekend sprint)."""

from dataclasses import replace

import pytest

from fm_engine.events import ClassifiedResult
from fm_engine.points import (
    RACE_POINTS_2026,
    SPRINT_POINTS_2026,
    points_for_position,
    sprint_points_for_position,
    with_sprint_points,
)


def test_2026_points_table():
    assert RACE_POINTS_2026 == (25, 18, 15, 12, 10, 8, 6, 4, 2, 1)


def test_points_for_scoring_positions():
    expected = dict(enumerate(RACE_POINTS_2026, start=1))
    for position, points in expected.items():
        assert points_for_position(position) == points


def test_no_points_below_tenth_place():
    for position in range(11, 23):
        assert points_for_position(position) == 0


def test_position_must_be_one_based():
    with pytest.raises(ValueError):
        points_for_position(0)
    with pytest.raises(ValueError):
        points_for_position(-3)


# ---------------------------------------------------------------------------
# Sprint points (Weekend sprint)
# ---------------------------------------------------------------------------


def test_2026_sprint_points_table():
    assert SPRINT_POINTS_2026 == (8, 7, 6, 5, 4, 3, 2, 1)


def test_sprint_points_for_scoring_positions():
    expected = dict(enumerate(SPRINT_POINTS_2026, start=1))
    for position, points in expected.items():
        assert sprint_points_for_position(position) == points


def test_no_sprint_points_below_eighth_place():
    for position in range(9, 23):
        assert sprint_points_for_position(position) == 0


def test_sprint_position_must_be_one_based():
    with pytest.raises(ValueError):
        sprint_points_for_position(0)


def _result(position: int) -> ClassifiedResult:
    return ClassifiedResult(
        position=position,
        driver_id=position,
        team_id=position,
        total_time_seconds=100.0 + position,
        gap_to_winner_seconds=float(position - 1),
        points=points_for_position(position),
        penalty_seconds=0.0,
    )


def test_with_sprint_points_relabels_points_only():
    classification = tuple(_result(position) for position in range(1, 11))
    relabelled = with_sprint_points(classification)
    # Points follow the sprint table; everything else is untouched.
    for original, sprint in zip(classification, relabelled, strict=True):
        assert sprint.points == sprint_points_for_position(sprint.position)
        assert sprint == replace(original, points=sprint_points_for_position(original.position))
    assert relabelled[0].points == 8
    assert relabelled[8].points == 0
