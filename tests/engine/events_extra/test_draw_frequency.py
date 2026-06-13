"""Estrazione degli Eventi extra-gara: frequenza ed effetti (FOR-27).

Al massimo un evento per intervallo, frequenza bassa configurabile (la
maggioranza degli intervalli resta in silenzio su una stagione
simulata), effetti meccanici secchi applicati davvero: entrata in Cassa
con causale, consegna anticipata o posticipata, attributo del rivale in
calo.
"""

from datetime import date, timedelta
from random import Random

from fm_engine.development import DevelopmentProject
from fm_engine.economy import TeamLedger, TransactionKind
from fm_engine.events_extra import (
    EXTRA_EVENT_PROBABILITY,
    ExtraEventKind,
    draw_extra_event,
)
from fm_engine.world import generate

GAME_DATE = date(2026, 4, 5)
INTERVALS_PER_SEASON = 23


def _world():
    return generate(31)


def _project() -> DevelopmentProject:
    return DevelopmentProject(attribute="downforce", cost_usd=8_000_000, start_date=GAME_DATE)


def test_most_intervals_stay_silent_over_simulated_seasons():
    """Frequenza bassa: il silenzio e' la norma su piu' stagioni."""
    world = _world()
    rng = Random(2026)
    drawn = 0
    intervals = INTERVALS_PER_SEASON * 10
    for _ in range(intervals):
        outcome = draw_extra_event(world, TeamLedger(), (), GAME_DATE, rng)
        if outcome is not None:
            drawn += 1
    assert drawn / intervals < 0.5, "la maggioranza degli intervalli deve restare in silenzio"
    assert abs(drawn / intervals - EXTRA_EVENT_PROBABILITY) < 0.1
    assert drawn > 0, "con dieci stagioni qualche evento deve uscire"


def test_frequency_is_configurable():
    world = _world()
    silent = [
        draw_extra_event(world, TeamLedger(), (), GAME_DATE, Random(i), probability=0.0)
        for i in range(50)
    ]
    assert silent == [None] * 50
    always = [
        draw_extra_event(world, TeamLedger(), (), GAME_DATE, Random(i), probability=1.0)
        for i in range(50)
    ]
    assert all(outcome is not None for outcome in always)


def test_sponsor_event_moves_the_cash_with_a_cause():
    world = _world()
    outcome = None
    for seed in range(200):
        candidate = draw_extra_event(
            world, TeamLedger(), (), GAME_DATE, Random(seed), probability=1.0
        )
        if candidate.event.kind is ExtraEventKind.ONE_OFF_SPONSOR:
            outcome = candidate
            break
    assert outcome is not None
    entry = outcome.ledger.entries[-1]
    assert entry.kind is TransactionKind.ONE_OFF_SPONSOR
    assert entry.amount_usd == outcome.event.amount_usd
    assert entry.description == outcome.news
    # Entrata in Cassa, Cap intatto.
    assert outcome.ledger.cash_usd == outcome.event.amount_usd
    assert outcome.ledger.cap_remaining_usd == outcome.ledger.cap_usd


def test_project_events_shift_the_delivery_both_ways():
    world = _world()
    project = _project()
    delayed = accelerated = None
    for seed in range(400):
        candidate = draw_extra_event(
            world, TeamLedger(), (project,), GAME_DATE, Random(seed), probability=1.0
        )
        if candidate.event.kind is ExtraEventKind.PROJECT_DELAYED and delayed is None:
            delayed = candidate
        if candidate.event.kind is ExtraEventKind.PROJECT_ACCELERATED and accelerated is None:
            accelerated = candidate
        if delayed and accelerated:
            break
    assert delayed is not None and accelerated is not None
    assert delayed.projects[0].delivery_date == project.delivery_date + timedelta(
        days=delayed.event.shift_days
    )
    assert accelerated.projects[0].delivery_date == project.delivery_date - timedelta(
        days=accelerated.event.shift_days
    )
    assert "giorni" in delayed.news


def test_project_events_require_an_active_project():
    """Senza Progetti in corso escono solo sponsor e guai dei rivali."""
    world = _world()
    for seed in range(100):
        outcome = draw_extra_event(
            world, TeamLedger(), (), GAME_DATE, Random(seed), probability=1.0
        )
        assert outcome.event.kind in (
            ExtraEventKind.ONE_OFF_SPONSOR,
            ExtraEventKind.RIVAL_SETBACK,
        )


def test_rival_setback_drops_one_attribute_of_one_rival():
    world = _world()
    outcome = None
    for seed in range(200):
        candidate = draw_extra_event(
            world, TeamLedger(), (), GAME_DATE, Random(seed), probability=1.0
        )
        if candidate.event.kind is ExtraEventKind.RIVAL_SETBACK:
            outcome = candidate
            break
    assert outcome is not None
    changed = [
        (before, after)
        for before, after in zip(world.ai_teams, outcome.world.ai_teams, strict=True)
        if before != after
    ]
    assert len(changed) == 1
    before, after = changed[0]
    assert before.name in outcome.news
    deltas = [
        getattr(before, name) - getattr(after, name)
        for name in (
            "engine_power",
            "downforce",
            "aero_efficiency",
            "mechanical_grip",
            "tyre_management",
            "reliability",
        )
    ]
    assert sorted(deltas) == [0, 0, 0, 0, 0, 1]
