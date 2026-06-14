"""Fase Test pre-season: Programmi, Classifica tempi, Stime (T5.1.2).

I Programmi di Conoscenza stringono le Stime sugli attributi propri
(margine post < margine pre); 0 giorni di Conoscenza lasciano le Stime
larghe e il report lo segnala. La Classifica tempi del giorno e' esatta
per tutte le vetture in pista.
"""

from dataclasses import replace

import pytest

from fm_engine.info import INITIAL_MARGIN, car_subject, driver_subject, margin_for_level
from fm_engine.info.estimates import KnowledgeState
from fm_engine.preseason import (
    PRESEASON_DAYS,
    PreseasonProgramme,
    PreseasonState,
    preseason_report,
    run_test_day,
)
from fm_engine.state import CarAttributes, RaceEntry
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_engine.world.models import PLAYER_TEAM_ID

SEED = 11


def _set_up_world():
    world = replace(generate(SEED), player_slot=PlayerSlot(name="Scuderia X", primary_color="#fff"))
    free = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free[0].id, free[1].id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    return apply_team_setup(world, choices)


def _entries(world) -> tuple[RaceEntry, ...]:
    drivers_by_id = {driver.id: driver for driver in world.drivers}
    entries: list[RaceEntry] = []
    player_car = CarAttributes.from_player_slot(world.player_slot)
    for contract in world.contracts_of(PLAYER_TEAM_ID):
        entries.append(
            RaceEntry(
                driver=drivers_by_id[contract.driver_id], team_id=PLAYER_TEAM_ID, car=player_car
            )
        )
    for team in world.ai_teams:
        car = CarAttributes.from_team(team)
        for contract in world.contracts_of(team.id):
            entries.append(
                RaceEntry(driver=drivers_by_id[contract.driver_id], team_id=team.id, car=car)
            )
    return tuple(entries)


def _player_ids(world) -> tuple[int, ...]:
    return tuple(contract.driver_id for contract in world.contracts_of(PLAYER_TEAM_ID))


def test_knowledge_programme_tightens_own_estimates():
    world = _set_up_world()
    entries = _entries(world)
    first, second = _player_ids(world)
    knowledge = KnowledgeState()
    before = knowledge.estimate_for(driver_subject(first), 70.0).margin
    outcome = run_test_day(
        PreseasonState(),
        knowledge,
        entries,
        {first: PreseasonProgramme.KNOWLEDGE, second: PreseasonProgramme.DEVELOPMENT},
        seed=1,
    )
    after = outcome.knowledge.estimate_for(driver_subject(first), 70.0).margin
    assert after < before
    # The car is learned too by the Knowledge programme.
    assert outcome.knowledge.level_for(car_subject(PLAYER_TEAM_ID)) == 1
    # The driver on Development did not tighten his driver estimate.
    assert outcome.knowledge.level_for(driver_subject(second)) == 0


def test_timesheet_lists_every_car_with_exact_times():
    world = _set_up_world()
    entries = _entries(world)
    first, second = _player_ids(world)
    outcome = run_test_day(
        PreseasonState(),
        KnowledgeState(),
        entries,
        {first: PreseasonProgramme.KNOWLEDGE, second: PreseasonProgramme.KNOWLEDGE},
        seed=3,
    )
    classification = outcome.result.classification
    assert len(classification) == len(entries)
    assert [row.position for row in classification] == list(range(1, len(entries) + 1))
    # Times are sorted and strictly meaningful (a real lap time, seconds).
    assert classification[0].time_seconds < classification[-1].time_seconds


def test_full_phase_completes_and_report_counts_knowledge_days():
    world = _set_up_world()
    entries = _entries(world)
    first, second = _player_ids(world)
    preseason = PreseasonState()
    knowledge = KnowledgeState()
    for day in range(PRESEASON_DAYS):
        programme = PreseasonProgramme.KNOWLEDGE if day < 2 else PreseasonProgramme.DEVELOPMENT
        outcome = run_test_day(
            preseason, knowledge, entries, {first: programme, second: programme}, seed=day
        )
        preseason, knowledge = outcome.preseason, outcome.knowledge
    assert preseason.completed
    report = preseason_report(preseason, knowledge, (first, second))
    assert report.knowledge_days == 2
    assert not report.zero_knowledge
    assert report.drivers[0].margin < INITIAL_MARGIN


def test_zero_knowledge_days_leave_wide_estimates_flagged():
    world = _set_up_world()
    entries = _entries(world)
    first, second = _player_ids(world)
    preseason = PreseasonState()
    knowledge = KnowledgeState()
    for day in range(PRESEASON_DAYS):
        outcome = run_test_day(
            preseason,
            knowledge,
            entries,
            {first: PreseasonProgramme.DEVELOPMENT, second: PreseasonProgramme.RELIABILITY},
            seed=day,
        )
        preseason, knowledge = outcome.preseason, outcome.knowledge
    report = preseason_report(preseason, knowledge, (first, second))
    assert report.knowledge_days == 0
    assert report.zero_knowledge
    assert report.drivers[0].margin == margin_for_level(0)


def test_running_past_the_end_is_rejected():
    world = _set_up_world()
    entries = _entries(world)
    first, second = _player_ids(world)
    preseason = PreseasonState()
    knowledge = KnowledgeState()
    for day in range(PRESEASON_DAYS):
        outcome = run_test_day(
            preseason,
            knowledge,
            entries,
            {first: PreseasonProgramme.DEVELOPMENT, second: PreseasonProgramme.DEVELOPMENT},
            seed=day,
        )
        preseason, knowledge = outcome.preseason, outcome.knowledge
    with pytest.raises(ValueError, match="already completed"):
        run_test_day(
            preseason,
            knowledge,
            entries,
            {first: PreseasonProgramme.DEVELOPMENT, second: PreseasonProgramme.DEVELOPMENT},
            seed=99,
        )
