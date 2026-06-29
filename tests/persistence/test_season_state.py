"""Round-trip dello stato di stagione nel Checkpoint (T5.1.1).

Sul Postgres effimero Docker (mai matilde): lo stato di partenza torna a
NULL e ricarica al default; una stagione con GP disputati conserva anno,
data di gioco e classifiche; il Checkpoint successivo sostituisce lo stato.
"""

from dataclasses import replace
from datetime import date

from fm_engine.career import Career
from fm_engine.circuits import circuit_by_code
from fm_engine.events import ClassifiedResult
from fm_engine.season import SeasonState, record_race
from fm_engine.world import generate
from fm_persistence import load_career, save_career

SEED = 7


def _classification() -> tuple[ClassifiedResult, ...]:
    return tuple(
        ClassifiedResult(
            position=position,
            driver_id=position,
            team_id=(position - 1) // 2,
            total_time_seconds=5400.0 + position,
            gap_to_winner_seconds=float(position - 1),
            points=(25, 18, 15)[position - 1] if position <= 3 else 0,
        )
        for position in range(1, 23)
    )


def test_starting_season_round_trips_to_default(conn):
    career = Career(name="Stagione iniziale", world=generate(SEED))
    saved = save_career(conn, career)
    loaded = load_career(conn, saved.id)
    assert loaded.season == SeasonState()
    assert loaded.season.year == 2026
    assert loaded.season.results == ()


def test_played_rounds_persist_with_classification(conn):
    season = record_race(SeasonState(), circuit_by_code("albert_park"), _classification())
    season = record_race(season, circuit_by_code("suzuka"), _classification())
    career = Career(name="Stagione in corso", world=generate(SEED), season=season)
    saved = save_career(conn, career)
    loaded = load_career(conn, saved.id)
    assert loaded.season == season
    assert loaded.season.completed_rounds == frozenset({1, 3})
    assert loaded.season.game_date == date(2026, 3, 29)
    assert loaded.season.results[0].classification[0].points == 25


def test_sprint_round_persists_the_sprint_classification(conn):
    """Un GP con Weekend sprint conserva la classifica sprint coi punti sprint."""
    sprint = tuple(
        ClassifiedResult(
            position=position,
            driver_id=position,
            team_id=(position - 1) // 2,
            total_time_seconds=1800.0 + position,
            gap_to_winner_seconds=float(position - 1),
            points=(8, 7, 6)[position - 1] if position <= 3 else 0,
        )
        for position in range(1, 23)
    )
    # Round 2 (Shanghai) is a sprint weekend in the 2026 calendar.
    season = record_race(SeasonState(), circuit_by_code("shanghai"), _classification(), sprint)
    career = Career(name="Stagione sprint", world=generate(SEED), season=season)
    saved = save_career(conn, career)
    loaded = load_career(conn, saved.id)
    assert loaded.season == season
    assert loaded.season.results[0].sprint_classification[0].points == 8


def test_next_checkpoint_overwrites_the_season_state(conn):
    season = record_race(SeasonState(), circuit_by_code("albert_park"), _classification())
    career = Career(name="Avanzamento stagione", world=generate(SEED), season=season)
    saved = save_career(conn, career)
    advanced = record_race(season, circuit_by_code("suzuka"), _classification())
    saved = save_career(conn, replace(saved, season=advanced))
    loaded = load_career(conn, saved.id)
    assert loaded.season.completed_rounds == frozenset({1, 3})
    # Stato riportato al default: la colonna torna NULL.
    saved = save_career(conn, replace(saved, season=SeasonState()))
    assert load_career(conn, saved.id).season == SeasonState()
