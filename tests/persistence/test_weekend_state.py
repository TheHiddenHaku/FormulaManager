"""Round-trip dello stato weekend nel Checkpoint (FOR-21).

Sul Postgres effimero Docker (mai matilde): una Carriera salvata a
meta' weekend riapre dalla sessione giusta, con griglia ed effetti dei
Programmi intatti; il weekend concluso conserva la classifica coi
punti; le Carriere senza weekend in corso restano com'erano (NULL).
"""

from dataclasses import replace

from fm_engine.career import Career
from fm_engine.events import ClassifiedResult
from fm_engine.practice import DriverPracticeEffects, PracticeEffects
from fm_engine.tyres import Compound
from fm_engine.weekend import WeekendPhase, WeekendState
from fm_engine.world import generate
from fm_persistence import load_career, save_career

SEED = 7
WEEKEND_SEED = 7_001

MID_WEEKEND = WeekendState(
    circuit_code="albert_park",
    seed=WEEKEND_SEED,
    phase=WeekendPhase.RACE,
    effects=PracticeEffects(
        drivers={
            3: DriverPracticeEffects(
                setup_percentage=84.5,
                qualifying_bonus_seconds=0.10,
                race_pace_bonus_seconds=0.06,
            ),
            7: DriverPracticeEffects(setup_percentage=61.25),
        },
        revealed_compounds=frozenset({Compound.C4, Compound.C5}),
        strategy_insight=1,
    ),
    grid_driver_ids=tuple(range(1, 23)),
)


def test_mid_weekend_checkpoint_resumes_from_the_right_session(conn):
    """Chiusura dopo le Qualifiche: al load la fase e' la Gara, griglia salvata."""
    career = Career(name="Weekend a meta'", world=generate(SEED), weekend=MID_WEEKEND)
    saved = save_career(conn, career)
    loaded = load_career(conn, saved.id)
    assert loaded.weekend == MID_WEEKEND
    assert loaded.weekend.phase is WeekendPhase.RACE
    assert loaded.weekend.grid_driver_ids == tuple(range(1, 23))
    assert loaded.weekend.effects.for_driver(3).qualifying_bonus_seconds == 0.10


def test_finished_weekend_persists_the_classification_with_points(conn):
    classification = tuple(
        ClassifiedResult(
            position=position,
            driver_id=position,
            team_id=(position - 1) // 2,
            total_time_seconds=5400.0 + position,
            gap_to_winner_seconds=float(position - 1),
            points=(25, 18, 15)[position - 1] if position <= 3 else 0,
            penalty_seconds=30.0 if position == 3 else 0.0,
        )
        for position in range(1, 4)
    )
    weekend = replace(MID_WEEKEND, phase=WeekendPhase.FINISHED, race_classification=classification)
    career = Career(name="Weekend finito", world=generate(SEED), weekend=weekend)
    saved = save_career(conn, career)
    loaded = load_career(conn, saved.id)
    assert loaded.weekend == weekend
    assert loaded.weekend.race_classification[0].points == 25
    assert loaded.weekend.race_classification[2].penalty_seconds == 30.0


def test_career_without_weekend_round_trips_to_none(conn):
    career = Career(name="Fuori dal weekend", world=generate(SEED))
    saved = save_career(conn, career)
    loaded = load_career(conn, saved.id)
    assert loaded.weekend is None


def test_next_checkpoint_overwrites_the_weekend_state(conn):
    """Il Checkpoint successivo sostituisce lo stato: avanti FP1 -> FP2."""
    at_fp1 = WeekendState(circuit_code="albert_park", seed=WEEKEND_SEED)
    career = Career(name="Avanzamento", world=generate(SEED), weekend=at_fp1)
    saved = save_career(conn, career)
    at_fp2 = replace(at_fp1, phase=WeekendPhase.FP2)
    saved = save_career(conn, replace(saved, weekend=at_fp2))
    loaded = load_career(conn, saved.id)
    assert loaded.weekend == at_fp2
    # Weekend over and cleared: the column goes back to NULL.
    saved = save_career(conn, replace(saved, weekend=None))
    assert load_career(conn, saved.id).weekend is None
