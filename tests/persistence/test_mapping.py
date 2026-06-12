"""Test unitari della mappatura id interni <-> uuid (senza database)."""

import uuid

import pytest

from fm_engine.world import generate
from fm_persistence.mapping import id_from_uuid, persistable_projection, row_uuid

CAREER_A = uuid.uuid4()
CAREER_B = uuid.uuid4()


def test_internal_id_encoded_and_decoded():
    for internal_id in (0, 1, 22, 10_000):
        assert id_from_uuid(row_uuid(CAREER_A, "driver", internal_id)) == internal_id


def test_uuid_deterministic_per_career_and_kind():
    assert row_uuid(CAREER_A, "driver", 3) == row_uuid(CAREER_A, "driver", 3)


def test_uuid_distinct_across_careers_kinds_and_ids():
    distinct = {
        row_uuid(CAREER_A, "driver", 1),
        row_uuid(CAREER_A, "driver", 2),
        row_uuid(CAREER_A, "team", 1),
        row_uuid(CAREER_B, "driver", 1),
    }
    assert len(distinct) == 4


def test_internal_id_out_of_range_raises():
    with pytest.raises(ValueError):
        row_uuid(CAREER_A, "driver", -1)
    with pytest.raises(ValueError):
        row_uuid(CAREER_A, "driver", 1 << 64)


def test_persistable_projection_idempotent():
    world = generate(7)
    projected = persistable_projection(world)
    assert persistable_projection(projected) == projected


def test_projection_leaves_persisted_fields_intact():
    world = generate(7)
    projected = persistable_projection(world)
    assert projected.engine_suppliers == world.engine_suppliers
    assert projected.contracts == world.contracts
    assert projected.player_slot == world.player_slot
    assert [team.cash_usd for team in projected.ai_teams] == [
        team.cash_usd for team in world.ai_teams
    ]
    assert [driver.potential for driver in projected.drivers] == [
        driver.potential for driver in world.drivers
    ]
    # Nazionalita' persistita: la proiezione non la normalizza.
    assert [driver.nationality for driver in projected.drivers] == [
        driver.nationality for driver in world.drivers
    ]
