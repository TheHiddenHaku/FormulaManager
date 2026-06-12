"""Punti 2026: tabella e attribuzione per posizione (FOR-8)."""

import pytest

from fm_engine.points import RACE_POINTS_2026, points_for_position


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
