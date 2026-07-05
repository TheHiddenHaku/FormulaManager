"""Round-trip dei Checkpoint su Postgres effimero Docker (FOR-5).

save_career seguito da load_career deve ricostruire la Carriera per
intero. Il termine di confronto e' l'equivalenza canonica documentata in
fm_persistence.mapping: i campi del Mondo senza colonna nello schema
(seed, config, ingaggio richiesto, personalita' di spesa) sono
normalizzati ai valori canonici da persistable_projection; tutto cio'
che ha una colonna (incluse nazionalita' dei piloti e colori dello slot
giocatore, FOR-6) deve essere strutturalmente identico.
"""

import sqlite3
import uuid
from dataclasses import replace

import pytest

from fm_engine.career import Career
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_persistence import (
    CareerNotFoundError,
    delete_career,
    list_careers,
    load_career,
    save_career,
)
from fm_persistence.mapping import (
    UNPERSISTED_PERSONALITY,
    UNPERSISTED_SALARY_DEMAND,
    persistable_projection,
)

SEED = 42

_STATE_TABLES = ("engine_suppliers", "teams", "drivers", "contracts")


@pytest.fixture
def world():
    return generate(SEED)


def _count(conn, table: str, career_id: uuid.UUID) -> int:
    row = conn.execute(  # noqa: S608 - table names from test constant
        f"select count(*) from {table} where career_id = ?", (career_id,)
    ).fetchone()
    return row[0]


def test_migration_and_seed_applied(conn):
    """Sanity del fixture: schema baseline e dati statici presenti."""
    assert conn.execute("select count(*) from circuits").fetchone()[0] == 24
    points = conn.execute(
        "select sum(points) from points_tables where code = 'race_2026'"
    ).fetchone()[0]
    assert points == 101


def test_round_trip_structurally_identical(conn, world):
    """Criterio FOR-5: stato salvato == stato ricaricato (Carriera intera)."""
    saved = save_career(conn, Career(name="Prova round-trip", world=world))
    assert saved.id is not None
    assert saved.created_at is not None
    assert saved.last_checkpoint_at is not None
    assert saved.world == world  # il Mondo in memoria resta intatto

    reloaded = load_career(conn, saved.id)
    assert reloaded == replace(saved, world=persistable_projection(world))


def test_round_trip_field_by_field(conn, world):
    """Le entita' con colonne complete sono identiche; le lacune sono canoniche."""
    saved = save_career(conn, Career(name="Prova entita'", world=world))
    reloaded = load_career(conn, saved.id).world

    # Fully persisted: identical to the original World.
    assert reloaded.engine_suppliers == world.engine_suppliers
    assert reloaded.contracts == world.contracts
    assert reloaded.player_slot == world.player_slot

    # Teams: everything identical except the personality (schema gap).
    assert reloaded.ai_teams == tuple(
        replace(team, personality=UNPERSISTED_PERSONALITY) for team in world.ai_teams
    )

    # Drivers: everything identical (Potential and nationality included)
    # except the salary demand (schema gap).
    assert reloaded.drivers == tuple(
        replace(driver, salary_demand_usd=UNPERSISTED_SALARY_DEMAND) for driver in world.drivers
    )
    assert all(driver.nationality for driver in reloaded.drivers)


def test_round_trip_preserves_retired_flag(conn, world):
    """Il flag ritirato (FOR-31) sopravvive al round-trip: un ritirato resta tale."""
    retired_id = world.drivers[0].id
    with_retired = replace(
        world,
        drivers=(replace(world.drivers[0], retired=True), *world.drivers[1:]),
    )
    saved = save_career(conn, Career(name="Con ritirato", world=with_retired))
    reloaded = load_career(conn, saved.id).world

    by_id = {driver.id: driver for driver in reloaded.drivers}
    assert by_id[retired_id].retired
    assert all(not driver.retired for driver in reloaded.drivers if driver.id != retired_id)


def test_round_trip_player_slot_with_name(conn, world):
    """Il nome scelto per la squadra del giocatore sopravvive al round-trip."""
    with_name = replace(world, player_slot=PlayerSlot(name="Scuderia Alessio"))
    saved = save_career(conn, Career(name="Con squadra giocatore", world=with_name))
    reloaded = load_career(conn, saved.id)
    assert reloaded.world.player_slot == PlayerSlot(name="Scuderia Alessio")


def test_round_trip_player_slot_with_colors(conn, world):
    """I colori della livrea scelti alla creazione sopravvivono al round-trip."""
    slot = PlayerSlot(name="Scuderia X", primary_color="#ff2800", secondary_color="bianco")
    with_colors = replace(world, player_slot=slot)
    saved = save_career(conn, Career(name="Con colori", world=with_colors))
    reloaded = load_career(conn, saved.id)
    assert reloaded.world.player_slot == slot


def test_round_trip_after_team_setup(conn, world):
    """Il Setup squadra (FOR-7) sopravvive al round-trip: vettura e Contratti.

    Lo stipendio dei Contratti ha colonna e resta esatto anche se
    l'ingaggio richiesto dei piloti e' una lacuna di schema.
    """
    named = replace(world, player_slot=PlayerSlot(name="Scuderia X"))
    choices = TeamSetupChoices(
        driver_ids=(world.contracts[0].driver_id, world.contracts[1].driver_id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="fast",
    )
    set_up = apply_team_setup(named, choices)

    saved = save_career(conn, Career(name="Con Setup squadra", world=set_up))
    reloaded = load_career(conn, saved.id)

    assert reloaded.world.player_slot == set_up.player_slot
    assert reloaded.world.player_slot.is_set_up
    assert reloaded.world.contracts == set_up.contracts
    assert reloaded.world == persistable_projection(set_up)


def test_next_checkpoint_overwrites_state(conn, world):
    """Due save consecutivi: load ritorna l'ultimo stato, senza duplicati."""
    first = save_career(conn, Career(name="Prima del GP", world=world))

    world_after = replace(
        world,
        ai_teams=tuple(
            replace(team, cash_usd=team.cash_usd + 1_000_000) for team in world.ai_teams
        ),
    )
    second = save_career(conn, replace(first, name="Dopo il GP", world=world_after))

    assert second.id == first.id
    assert second.created_at == first.created_at
    assert second.last_checkpoint_at > first.last_checkpoint_at

    reloaded = load_career(conn, first.id)
    assert reloaded.name == "Dopo il GP"
    assert reloaded.world == persistable_projection(world_after)
    assert reloaded.last_checkpoint_at == second.last_checkpoint_at

    # Delete and reinsert: no duplicated rows after the second checkpoint.
    assert _count(conn, "drivers", first.id) == len(world.drivers)
    assert _count(conn, "teams", first.id) == len(world.ai_teams)
    assert _count(conn, "contracts", first.id) == len(world.contracts)
    assert _count(conn, "engine_suppliers", first.id) == len(world.engine_suppliers)


def test_failed_save_leaves_no_new_career(conn, world):
    """Atomicita': se un insert viola un CHECK, non resta nulla sul database."""
    broken = replace(world, drivers=(replace(world.drivers[0], age=10), *world.drivers[1:]))
    with pytest.raises(sqlite3.IntegrityError):
        save_career(conn, Career(name="Mai nata", world=broken))
    assert conn.execute("select count(*) from careers").fetchone()[0] == 0


def test_failed_save_preserves_previous_checkpoint(conn, world):
    """Atomicita' sul Checkpoint successivo: rollback totale, stato intatto."""
    saved = save_career(conn, Career(name="Checkpoint buono", world=world))

    broken = replace(world, drivers=(replace(world.drivers[0], age=10), *world.drivers[1:]))
    with pytest.raises(sqlite3.IntegrityError):
        save_career(conn, replace(saved, name="Checkpoint rotto", world=broken))

    reloaded = load_career(conn, saved.id)
    assert reloaded == replace(saved, world=persistable_projection(world))


def test_save_on_missing_id_raises(conn, world):
    career = Career(name="Fantasma", world=world, id=uuid.uuid4())
    with pytest.raises(CareerNotFoundError):
        save_career(conn, career)


def test_load_on_missing_id_raises(conn):
    with pytest.raises(CareerNotFoundError):
        load_career(conn, uuid.uuid4())


def test_list_careers_with_metadata(conn, world):
    """Le Carriere salvate compaiono con nome e data ultimo Checkpoint."""
    assert list_careers(conn) == []
    first = save_career(conn, Career(name="Prima carriera", world=world))
    second = save_career(conn, Career(name="Seconda carriera", world=world))

    careers = list_careers(conn)
    assert [summary.name for summary in careers] == ["Seconda carriera", "Prima carriera"]
    assert careers[0].id == second.id
    assert careers[0].last_checkpoint_at == second.last_checkpoint_at
    assert careers[1].id == first.id
    assert careers[1].created_at == first.created_at


def test_delete_career_cascades(conn, world):
    """La cancellazione propaga alle tabelle di stato e non tocca le altre Carriere."""
    doomed = save_career(conn, Career(name="Da eliminare", world=world))
    survivor = save_career(conn, Career(name="Superstite", world=world))

    assert delete_career(conn, doomed.id) is True
    assert delete_career(conn, doomed.id) is False

    with pytest.raises(CareerNotFoundError):
        load_career(conn, doomed.id)
    for table in _STATE_TABLES:
        assert _count(conn, table, doomed.id) == 0

    reloaded = load_career(conn, survivor.id)
    assert reloaded.world == persistable_projection(world)
