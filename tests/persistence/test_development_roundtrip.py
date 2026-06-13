"""Round-trip dei Progetti di sviluppo ai Checkpoint (FOR-25).

I Progetti del giocatore viaggiano su development_projects: save e load
devono ricostruirli identici, nell'ordine di avvio, inclusi stato ed
esito dei consegnati.
"""

from dataclasses import replace
from datetime import date

import pytest

from fm_engine.career import Career
from fm_engine.development import DevelopmentProject, ProjectStatus
from fm_engine.world import PlayerSlot, generate
from fm_persistence import load_career, save_career

SEED = 9
START_DATE = date(2026, 3, 8)


@pytest.fixture
def world():
    return replace(generate(SEED), player_slot=PlayerSlot(name="Scuderia Sviluppo"))


def _projects() -> tuple[DevelopmentProject, ...]:
    return (
        DevelopmentProject(
            attribute="downforce",
            cost_usd=8_000_000,
            start_date=START_DATE,
            duration_days=42,
        ),
        DevelopmentProject(
            attribute="reliability",
            cost_usd=4_000_000,
            start_date=date(2026, 2, 1),
            duration_days=30,
            status=ProjectStatus.COMPLETED,
            outcome=2,
        ),
    )


def test_projects_round_trip_identical(conn, world):
    projects = _projects()
    saved = save_career(conn, Career(name="Con Progetti", world=world, projects=projects))
    reloaded = load_career(conn, saved.id)
    assert reloaded.projects == projects


def test_career_without_projects_round_trips_empty(conn, world):
    saved = save_career(conn, Career(name="Senza Progetti", world=world))
    assert load_career(conn, saved.id).projects == ()


def test_next_checkpoint_overwrites_projects(conn, world):
    first = save_career(conn, Career(name="Primo", world=world, projects=_projects()))
    only_one = (_projects()[0],)
    second = save_career(conn, replace(first, projects=only_one))
    reloaded = load_career(conn, second.id)
    assert reloaded.projects == only_one
    count = conn.execute(
        "select count(*) from development_projects where career_id = %s",
        (second.id,),
    ).fetchone()[0]
    assert count == 1
