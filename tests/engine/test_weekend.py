"""Macchina a stati del weekend Standard e cablaggio dei Programmi (FOR-21).

Headless, solo motore: il weekend concatena FP1 -> FP2 -> FP3 ->
Qualifiche -> Gara -> concluso senza salti ne' stati irraggiungibili;
il Formato weekend e' letto dal flag del circuito e i formati non
giocabili vengono rifiutati. Gli effetti dei Programmi delle libere
sono cablati su Qualifiche (qualifying_adjustment_seconds) e gara
(race_adjustment_seconds via RaceState.pace_adjustments).
"""

from dataclasses import replace

import pytest

from fm_engine.circuits import circuit_by_code
from fm_engine.events import ChequeredFlag
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.points import constructor_points, sprint_points_for_position, with_sprint_points
from fm_engine.practice import (
    DriverPracticeEffects,
    PracticeEffects,
    PracticeProgramme,
    PracticeSession,
    simulate_practice_session,
)
from fm_engine.qualifying import simulate_qualifying
from fm_engine.race import start_race, step
from fm_engine.weekend import (
    PHASE_PRACTICE_SESSIONS,
    SPRINT_PHASES,
    STANDARD_PHASES,
    WeekendFormat,
    WeekendPhase,
    WeekendState,
    advance_after_practice,
    advance_after_qualifying,
    advance_after_race,
    advance_after_sprint_qualifying,
    advance_after_sprint_race,
    sprint_race_laps,
    start_weekend,
)

SEED = 42


def player_ids(entries):
    """I 2 piloti dello slot giocatore (team_id 0) della griglia sintetica."""
    return tuple(entry.driver.id for entry in entries if entry.team_id == 0)


@pytest.fixture
def player_grid(entry_factory):
    """Griglia sintetica con i primi 2 piloti nello slot del giocatore."""
    entries = entry_factory()
    return tuple(
        replace(entry, team_id=0) if index < 2 else entry for index, entry in enumerate(entries)
    )


# ---------------------------------------------------------------------------
# Weekend format flag
# ---------------------------------------------------------------------------


def test_start_weekend_reads_the_standard_format_flag():
    circuit = circuit_by_code("albert_park")
    assert circuit.weekend_format_2026 == "standard"
    state = start_weekend(circuit, seed=SEED)
    assert state.phase is WeekendPhase.FP1
    assert state.weekend_format is WeekendFormat.STANDARD
    assert state.circuit_code == "albert_park"
    assert state.seed == SEED


def test_start_weekend_reads_the_sprint_format_flag():
    sprint_circuit = next(
        circuit
        for circuit in (circuit_by_code("shanghai"), circuit_by_code("miami"))
        if circuit.weekend_format_2026 == "sprint"
    )
    state = start_weekend(sprint_circuit, seed=SEED)
    assert state.phase is WeekendPhase.FP1
    assert state.weekend_format is WeekendFormat.SPRINT
    assert state.is_sprint


def test_start_weekend_rejects_unknown_formats():
    circuit = replace(circuit_by_code("albert_park"), weekend_format_2026="endurance")
    with pytest.raises(ValueError, match="unknown weekend format"):
        start_weekend(circuit, seed=SEED)


# ---------------------------------------------------------------------------
# The full state machine, end to end and with no skips
# ---------------------------------------------------------------------------


def test_standard_weekend_phases_in_order():
    assert STANDARD_PHASES == (
        WeekendPhase.FP1,
        WeekendPhase.FP2,
        WeekendPhase.FP3,
        WeekendPhase.QUALIFYING,
        WeekendPhase.RACE,
        WeekendPhase.FINISHED,
    )


def test_full_weekend_end_to_end(player_grid):
    circuit = circuit_by_code("albert_park")
    weekend = start_weekend(circuit, seed=SEED)
    first, second = player_ids(player_grid)

    # FP1 -> FP3: the programme effects accumulate in the weekend state.
    programmes = {
        PracticeSession.FP1: PracticeProgramme.SETUP,
        PracticeSession.FP2: PracticeProgramme.QUALIFYING_FOCUS,
        PracticeSession.FP3: PracticeProgramme.RACE_PACE,
    }
    for session in PracticeSession:
        assert weekend.next_practice_session is session
        result = simulate_practice_session(
            player_grid,
            circuit,
            session,
            {first: programmes[session], second: programmes[session]},
            seed=SEED,
            effects=weekend.effects,
        )
        weekend = advance_after_practice(weekend, result)
    assert weekend.phase is WeekendPhase.QUALIFYING
    assert weekend.effects.for_driver(first).qualifying_bonus_seconds > 0.0
    assert weekend.effects.for_driver(first).race_pace_bonus_seconds > 0.0

    # Qualifying decides the starting grid, pole first.
    qualifying, _ = simulate_qualifying(player_grid, circuit, seed=SEED, effects=weekend.effects)
    weekend = advance_after_qualifying(weekend, qualifying)
    assert weekend.phase is WeekendPhase.RACE
    assert weekend.grid_driver_ids == tuple(entry.driver.id for entry in qualifying.grid)
    assert weekend.grid_driver_ids[0] == qualifying.pole_driver_id

    # The race runs headless on the saved grid with the practice effects.
    entries_by_id = {entry.driver.id: entry for entry in player_grid}
    grid = tuple(entries_by_id[driver_id] for driver_id in weekend.grid_driver_ids)
    state, _ = start_race(grid, circuit, seed=SEED, effects=weekend.effects)
    while not state.finished:
        state, events = step(state)
    classification = next(
        event.classification for event in events if isinstance(event, ChequeredFlag)
    )
    weekend = advance_after_race(weekend, classification)
    assert weekend.finished
    assert weekend.race_classification == classification

    # 2026 points awarded: 25 to the winner, constructors as driver sums.
    assert weekend.race_classification[0].points == 25
    teams = constructor_points(weekend.race_classification)
    assert sum(teams.values()) == sum(result.points for result in classification)


# ---------------------------------------------------------------------------
# Sprint weekend (Weekend sprint)
# ---------------------------------------------------------------------------


def test_sprint_weekend_phases_in_order():
    assert SPRINT_PHASES == (
        WeekendPhase.FP1,
        WeekendPhase.SPRINT_QUALIFYING,
        WeekendPhase.SPRINT_RACE,
        WeekendPhase.QUALIFYING,
        WeekendPhase.RACE,
        WeekendPhase.FINISHED,
    )


def test_full_sprint_weekend_end_to_end(player_grid):
    circuit = replace(circuit_by_code("albert_park"), weekend_format_2026="sprint")
    weekend = start_weekend(circuit, seed=SEED)
    assert weekend.is_sprint

    # A single free practice, then the sprint qualifying.
    assert weekend.next_practice_session is PracticeSession.FP1
    fp1 = simulate_practice_session(
        player_grid, circuit, PracticeSession.FP1, {}, seed=SEED, effects=weekend.effects
    )
    weekend = advance_after_practice(weekend, fp1)
    assert weekend.phase is WeekendPhase.SPRINT_QUALIFYING
    # No FP2/FP3 in a sprint weekend.
    assert weekend.next_practice_session is None

    # Sprint qualifying sets the sprint grid.
    sprint_qualifying, _ = simulate_qualifying(
        player_grid, circuit, seed=SEED, effects=weekend.effects
    )
    weekend = advance_after_sprint_qualifying(weekend, sprint_qualifying)
    assert weekend.phase is WeekendPhase.SPRINT_RACE
    assert weekend.sprint_grid_driver_ids == tuple(
        entry.driver.id for entry in sprint_qualifying.grid
    )

    # Sprint race over a reduced distance, scored with the sprint table (8-1).
    sprint_circuit = replace(circuit, race_laps=sprint_race_laps(circuit))
    assert 1 <= sprint_circuit.race_laps < circuit.race_laps
    entries_by_id = {entry.driver.id: entry for entry in player_grid}
    grid = tuple(entries_by_id[driver_id] for driver_id in weekend.sprint_grid_driver_ids)
    state, _ = start_race(grid, sprint_circuit, seed=SEED, effects=weekend.effects)
    while not state.finished:
        state, events = step(state)
    sprint_result = with_sprint_points(
        next(event.classification for event in events if isinstance(event, ChequeredFlag))
    )
    weekend = advance_after_sprint_race(weekend, sprint_result)
    assert weekend.phase is WeekendPhase.QUALIFYING
    assert weekend.sprint_classification[0].points == 8
    assert all(
        result.points == sprint_points_for_position(result.position)
        for result in weekend.sprint_classification
    )

    # The normal qualifying and Grand Prix close the sprint weekend.
    qualifying, _ = simulate_qualifying(player_grid, circuit, seed=SEED, effects=weekend.effects)
    weekend = advance_after_qualifying(weekend, qualifying)
    assert weekend.phase is WeekendPhase.RACE
    grid = tuple(entries_by_id[driver_id] for driver_id in weekend.grid_driver_ids)
    state, _ = start_race(grid, circuit, seed=SEED, effects=weekend.effects)
    while not state.finished:
        state, events = step(state)
    race_classification = next(
        event.classification for event in events if isinstance(event, ChequeredFlag)
    )
    weekend = advance_after_race(weekend, race_classification)
    assert weekend.finished
    # The Grand Prix keeps the full race points (25 to the winner).
    assert weekend.race_classification[0].points == 25


def test_sprint_advance_functions_reject_wrong_phase(player_grid):
    circuit = replace(circuit_by_code("albert_park"), weekend_format_2026="sprint")
    weekend = start_weekend(circuit, seed=SEED)
    qualifying, _ = simulate_qualifying(player_grid, circuit, seed=SEED)

    # At FP1 the sprint sessions cannot be recorded yet.
    with pytest.raises(ValueError, match="does not accept a sprint qualifying result"):
        advance_after_sprint_qualifying(weekend, qualifying)
    with pytest.raises(ValueError, match="does not accept a sprint race classification"):
        advance_after_sprint_race(weekend, (object(),))

    # The sprint race rejects an empty classification.
    at_sprint_race = replace(weekend, phase=WeekendPhase.SPRINT_RACE)
    with pytest.raises(ValueError, match="cannot be empty"):
        advance_after_sprint_race(at_sprint_race, ())


def test_no_phase_skips_or_unreachable_states(player_grid):
    circuit = circuit_by_code("albert_park")
    weekend = start_weekend(circuit, seed=SEED)
    first, second = player_ids(player_grid)
    fp2_result = simulate_practice_session(
        player_grid, circuit, PracticeSession.FP2, {first: None, second: None}, seed=SEED
    )
    qualifying, _ = simulate_qualifying(player_grid, circuit, seed=SEED)

    # FP1 phase: no FP2 result, no qualifying, no race classification.
    with pytest.raises(ValueError, match="expected a fp1 result"):
        advance_after_practice(weekend, fp2_result)
    with pytest.raises(ValueError, match="does not accept a qualifying result"):
        advance_after_qualifying(weekend, qualifying)
    with pytest.raises(ValueError, match="does not accept a race classification"):
        advance_after_race(weekend, (object(),))

    # Qualifying phase: practice is over, the race has not happened yet.
    at_qualifying = replace(weekend, phase=WeekendPhase.QUALIFYING)
    with pytest.raises(ValueError, match="does not accept a practice result"):
        advance_after_practice(at_qualifying, fp2_result)
    with pytest.raises(ValueError, match="does not accept a race classification"):
        advance_after_race(at_qualifying, (object(),))

    # Race phase rejects an empty classification.
    at_race = replace(weekend, phase=WeekendPhase.RACE)
    with pytest.raises(ValueError, match="cannot be empty"):
        advance_after_race(at_race, ())

    # Finished weekend: nothing else can advance.
    done = replace(weekend, phase=WeekendPhase.FINISHED)
    with pytest.raises(ValueError):
        advance_after_practice(done, fp2_result)
    with pytest.raises(ValueError):
        advance_after_qualifying(done, qualifying)
    with pytest.raises(ValueError):
        advance_after_race(done, (object(),))


def test_phase_practice_sessions_cover_only_the_free_practices():
    assert set(PHASE_PRACTICE_SESSIONS) == {
        WeekendPhase.FP1,
        WeekendPhase.FP2,
        WeekendPhase.FP3,
    }
    state = WeekendState(circuit_code="albert_park", seed=SEED, phase=WeekendPhase.QUALIFYING)
    assert state.next_practice_session is None


# ---------------------------------------------------------------------------
# Practice effects wired into qualifying and race
# ---------------------------------------------------------------------------


def test_qualifying_applies_the_practice_adjustment_to_covered_drivers(entry_factory):
    entries = entry_factory()
    circuit = circuit_by_code("albert_park")
    target = entries[0].driver.id
    # Full setup and max qualifying bonus: strictly faster than baseline.
    effects = PracticeEffects(
        drivers={
            target: DriverPracticeEffects(setup_percentage=100.0, qualifying_bonus_seconds=0.20)
        }
    )
    baseline, _ = simulate_qualifying(entries, circuit, seed=SEED)
    boosted, _ = simulate_qualifying(entries, circuit, seed=SEED, effects=effects)

    def best_q1_time(result, driver_id):
        rows = result.segments[0].rows
        return next(row.time_seconds for row in rows if row.driver_id == driver_id)

    assert best_q1_time(boosted, target) == pytest.approx(best_q1_time(baseline, target) - 0.20)
    # Drivers not covered by the effects are untouched: same draws, same times.
    other = entries[5].driver.id
    assert best_q1_time(boosted, other) == best_q1_time(baseline, other)


def test_race_applies_the_practice_pace_adjustment(entry_factory):
    entries = entry_factory(count=4)
    circuit = replace(circuit_by_code("monza"), race_laps=5)
    target = entries[0].driver.id
    effects = PracticeEffects(
        drivers={
            target: DriverPracticeEffects(setup_percentage=100.0, race_pace_bonus_seconds=0.12)
        }
    )
    quiet = MisfortuneConfig.disabled()

    baseline, _ = start_race(entries, circuit, seed=SEED, misfortune=quiet)
    boosted, _ = start_race(entries, circuit, seed=SEED, misfortune=quiet, effects=effects)
    assert boosted.pace_adjustments == {target: pytest.approx(-0.12)}
    assert baseline.pace_adjustments == {}

    while not baseline.finished:
        baseline, _ = step(baseline)
    while not boosted.finished:
        boosted, _ = step(boosted)
    # The adjustment survives every Tick and shaves cumulative time.
    assert boosted.pace_adjustments == {target: pytest.approx(-0.12)}
    baseline_total = baseline.car_of(target).total_time_seconds
    boosted_total = boosted.car_of(target).total_time_seconds
    assert boosted_total < baseline_total


def test_setup_deficit_alone_costs_lap_time_in_qualifying(entry_factory):
    """Chi non lavora sul setup paga: deficit positivo, tempo peggiore."""
    entries = entry_factory()
    circuit = circuit_by_code("albert_park")
    target = entries[0].driver.id
    # Baseline setup (30%), no bonus: the adjustment is a pure penalty.
    effects = PracticeEffects(drivers={target: DriverPracticeEffects()})
    baseline, _ = simulate_qualifying(entries, circuit, seed=SEED)
    lazy, _ = simulate_qualifying(entries, circuit, seed=SEED, effects=effects)
    baseline_time = next(
        row.time_seconds for row in baseline.segments[0].rows if row.driver_id == target
    )
    lazy_time = next(row.time_seconds for row in lazy.segments[0].rows if row.driver_id == target)
    assert lazy_time > baseline_time
