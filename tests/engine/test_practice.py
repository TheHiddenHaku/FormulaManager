"""Prove libere con Programmi: effetti misurabili nel weekend (FOR-20).

Test sul motore a seed fisso: Programma di default segnalato, setup a
rendimenti decrescenti che incide sui tempi, curve di Degrado rivelate
cumulativamente, bonus di qualifica e passo gara con tetto, lettura
strategica con soste consigliate, Classifica tempi esatta di sessione
e determinismo completo.
"""

from dataclasses import replace

import pytest

from fm_engine.circuits import CALENDAR_2026
from fm_engine.practice import (
    DEFAULT_PROGRAMME,
    INITIAL_SETUP_PERCENTAGE,
    QUALIFYING_BONUS_CAP_SECONDS,
    RACE_PACE_BONUS_CAP_SECONDS,
    PracticeEffects,
    PracticeProgramme,
    PracticeSession,
    qualifying_adjustment_seconds,
    race_adjustment_seconds,
    revealed_degradation_rates,
    setup_deficit_seconds,
    simulate_practice_session,
    suggested_stop_count,
)
from fm_engine.tyres import CompoundSlot, nominated_compounds

CIRCUIT = CALENDAR_2026[0]
SEED = 4242


def _player_ids(entries):
    """I 2 piloti 'del manager' delle griglie sintetiche: la prima squadra."""
    return tuple(entry.driver.id for entry in entries if entry.team_id == 1)


# ---------------------------------------------------------------------------
# Default programme and reports
# ---------------------------------------------------------------------------


def test_missing_programme_gets_the_default_and_is_flagged(entry_factory):
    entries = entry_factory()
    first, second = _player_ids(entries)
    result = simulate_practice_session(
        entries,
        CIRCUIT,
        PracticeSession.FP1,
        {first: None, second: PracticeProgramme.TYRES},
        seed=SEED,
    )
    by_driver = {report.driver_id: report for report in result.reports}
    assert by_driver[first].programme is DEFAULT_PROGRAMME
    assert by_driver[first].defaulted is True
    assert by_driver[second].programme is PracticeProgramme.TYRES
    assert by_driver[second].defaulted is False


def test_assignments_for_unknown_drivers_are_rejected(entry_factory):
    entries = entry_factory()
    with pytest.raises(ValueError):
        simulate_practice_session(
            entries,
            CIRCUIT,
            PracticeSession.FP1,
            {9999: PracticeProgramme.SETUP},
            seed=SEED,
        )


# ---------------------------------------------------------------------------
# Setup: diminishing returns, capped, and it shows on the stopwatch
# ---------------------------------------------------------------------------


def test_setup_percentage_grows_with_diminishing_returns(entry_factory):
    entries = entry_factory()
    driver_id = _player_ids(entries)[0]
    effects = None
    percentages = [INITIAL_SETUP_PERCENTAGE]
    for session in (PracticeSession.FP1, PracticeSession.FP2, PracticeSession.FP3):
        result = simulate_practice_session(
            entries,
            CIRCUIT,
            session,
            {driver_id: PracticeProgramme.SETUP},
            seed=SEED,
            effects=effects,
        )
        effects = result.effects
        percentages.append(effects.for_driver(driver_id).setup_percentage)
    gains = [after - before for before, after in zip(percentages, percentages[1:], strict=False)]
    assert all(gain > 0 for gain in gains)
    # Diminishing returns: each session closes a share of a smaller gap.
    assert gains[0] > gains[2]
    assert percentages[-1] <= 100.0
    assert setup_deficit_seconds(effects, driver_id) < setup_deficit_seconds(
        PracticeEffects(), driver_id
    )


def test_setup_earned_in_fp1_makes_fp2_lap_times_faster(entry_factory):
    entries = entry_factory()
    driver_id = _player_ids(entries)[0]
    fp1 = simulate_practice_session(
        entries,
        CIRCUIT,
        PracticeSession.FP1,
        {driver_id: PracticeProgramme.SETUP},
        seed=SEED,
    )
    # Same FP2 session, same seed and programme: with the FP1 setup work
    # in the bank vs from scratch. Only the setup deficit differs.
    assignments = {driver_id: PracticeProgramme.QUALIFYING_FOCUS}
    fp2_with_setup = simulate_practice_session(
        entries, CIRCUIT, PracticeSession.FP2, assignments, seed=SEED, effects=fp1.effects
    )
    fp2_without = simulate_practice_session(
        entries, CIRCUIT, PracticeSession.FP2, assignments, seed=SEED
    )

    def time_of(result, wanted):
        return next(row.time_seconds for row in result.classification if row.driver_id == wanted)

    assert time_of(fp2_with_setup, driver_id) < time_of(fp2_without, driver_id)


# ---------------------------------------------------------------------------
# Tyres: degradation curves revealed cumulatively, softest first
# ---------------------------------------------------------------------------


def test_tyre_programme_reveals_curves_cumulatively(entry_factory):
    entries = entry_factory()
    driver_id = _player_ids(entries)[0]
    nominated = nominated_compounds(CIRCUIT)
    fp1 = simulate_practice_session(
        entries,
        CIRCUIT,
        PracticeSession.FP1,
        {driver_id: PracticeProgramme.TYRES},
        seed=SEED,
    )
    # FP1 reveals the 2 softest nominated compounds.
    assert fp1.reports[0].newly_revealed == (
        nominated[CompoundSlot.SOFT],
        nominated[CompoundSlot.MEDIUM],
    )
    fp2 = simulate_practice_session(
        entries,
        CIRCUIT,
        PracticeSession.FP2,
        {driver_id: PracticeProgramme.TYRES},
        seed=SEED,
        effects=fp1.effects,
    )
    # FP2 completes the set: the effects accumulate across sessions.
    assert fp2.reports[0].newly_revealed == (nominated[CompoundSlot.HARD],)
    assert fp2.effects.revealed_compounds == frozenset(nominated.values())
    rates = revealed_degradation_rates(fp2.effects, CIRCUIT)
    assert set(rates) == set(nominated.values())
    assert all(rate > 0 for rate in rates.values())


# ---------------------------------------------------------------------------
# Weekend bonuses: applied, stacking, capped
# ---------------------------------------------------------------------------


def test_qualifying_focus_bonus_stacks_up_to_the_cap(entry_factory):
    entries = entry_factory()
    driver_id = _player_ids(entries)[0]
    effects = None
    for session in (PracticeSession.FP1, PracticeSession.FP2, PracticeSession.FP3):
        result = simulate_practice_session(
            entries,
            CIRCUIT,
            session,
            {driver_id: PracticeProgramme.QUALIFYING_FOCUS},
            seed=SEED,
            effects=effects,
        )
        effects = result.effects
    bonus = effects.for_driver(driver_id).qualifying_bonus_seconds
    assert bonus == pytest.approx(QUALIFYING_BONUS_CAP_SECONDS)
    # The bonus beats the untouched setup deficit reduction: the
    # adjustment is smaller than for a driver who did nothing.
    assert qualifying_adjustment_seconds(effects, driver_id) < qualifying_adjustment_seconds(
        PracticeEffects(), driver_id
    )


def test_race_pace_bonus_stacks_up_to_the_cap_and_adjusts_the_race(entry_factory):
    entries = entry_factory()
    driver_id = _player_ids(entries)[0]
    effects = None
    for session in (PracticeSession.FP1, PracticeSession.FP2, PracticeSession.FP3):
        result = simulate_practice_session(
            entries,
            CIRCUIT,
            session,
            {driver_id: PracticeProgramme.RACE_PACE},
            seed=SEED,
            effects=effects,
        )
        effects = result.effects
    assert effects.for_driver(driver_id).race_pace_bonus_seconds == pytest.approx(
        RACE_PACE_BONUS_CAP_SECONDS
    )
    assert race_adjustment_seconds(effects, driver_id) < race_adjustment_seconds(
        PracticeEffects(), driver_id
    )


# ---------------------------------------------------------------------------
# Strategy: insight levels and suggested stops
# ---------------------------------------------------------------------------


def test_strategy_programme_unlocks_the_suggested_stops(entry_factory):
    entries = entry_factory()
    driver_id = _player_ids(entries)[0]
    fp1 = simulate_practice_session(
        entries,
        CIRCUIT,
        PracticeSession.FP1,
        {driver_id: PracticeProgramme.STRATEGY},
        seed=SEED,
    )
    assert fp1.effects.strategy_insight == 1
    assert fp1.reports[0].suggested_stops == suggested_stop_count(CIRCUIT)
    assert fp1.reports[0].suggested_stops >= 1


def test_suggested_stops_track_tyre_severity():
    # All calendar circuits suggest a plausible dry strategy.
    for circuit in CALENDAR_2026:
        assert 1 <= suggested_stop_count(circuit) <= 3
    # Same circuit, harsher asphalt: never fewer stops suggested.
    gentle = replace(CIRCUIT, tyre_severity=1)
    severe = replace(CIRCUIT, tyre_severity=5)
    assert suggested_stop_count(gentle) <= suggested_stop_count(severe)


# ---------------------------------------------------------------------------
# Timesheet and determinism
# ---------------------------------------------------------------------------


def test_classification_covers_all_cars_with_exact_sorted_times(entry_factory):
    entries = entry_factory()
    first, second = _player_ids(entries)
    result = simulate_practice_session(
        entries,
        CIRCUIT,
        PracticeSession.FP1,
        {first: PracticeProgramme.SETUP, second: PracticeProgramme.TYRES},
        seed=SEED,
    )
    rows = result.classification
    assert len(rows) == len(entries)
    assert [row.position for row in rows] == list(range(1, len(entries) + 1))
    times = [row.time_seconds for row in rows]
    assert times == sorted(times)
    assert result.forecast.circuit_code == CIRCUIT.code
    assert 0.0 <= result.forecast.rain_chance <= 1.0


def test_practice_session_is_deterministic(entry_factory):
    entries = entry_factory()
    first, second = _player_ids(entries)
    assignments = {first: PracticeProgramme.SETUP, second: None}
    one = simulate_practice_session(entries, CIRCUIT, PracticeSession.FP1, assignments, seed=SEED)
    two = simulate_practice_session(entries, CIRCUIT, PracticeSession.FP1, assignments, seed=SEED)
    assert one == two
    other_seed = simulate_practice_session(
        entries, CIRCUIT, PracticeSession.FP1, assignments, seed=SEED + 1
    )
    assert one.classification != other_seed.classification
