"""Mescole, nomina per GP e curve di Degrado (FOR-10)."""

from test_race_base import _entry

from fm_engine.circuits import CALENDAR_2026, circuit_by_code
from fm_engine.pitstop import PIT_STOP_BASE_SECONDS
from fm_engine.state import Aggression
from fm_engine.tyres import (
    COMPOUND_DEGRADATION_RATE_SECONDS_PER_LAP,
    COMPOUND_PACE_OFFSET_SECONDS,
    Compound,
    CompoundSlot,
    after_lap,
    degradation_step_seconds,
    fresh_set,
    nominated_compounds,
    tyre_lap_loss_seconds,
)

DRY_ORDER = (Compound.C1, Compound.C2, Compound.C3, Compound.C4, Compound.C5)


def test_every_gp_nominates_3_dry_compounds_hard_to_soft():
    for circuit in CALENDAR_2026:
        nominated = nominated_compounds(circuit)
        assert set(nominated) == {CompoundSlot.HARD, CompoundSlot.MEDIUM, CompoundSlot.SOFT}
        hard, medium, soft = (
            nominated[CompoundSlot.HARD],
            nominated[CompoundSlot.MEDIUM],
            nominated[CompoundSlot.SOFT],
        )
        assert all(compound.is_dry for compound in (hard, medium, soft))
        assert DRY_ORDER.index(hard) < DRY_ORDER.index(medium) < DRY_ORDER.index(soft)


def test_softer_is_faster_but_more_fragile():
    offsets = [COMPOUND_PACE_OFFSET_SECONDS[compound] for compound in DRY_ORDER]
    rates = [COMPOUND_DEGRADATION_RATE_SECONDS_PER_LAP[compound] for compound in DRY_ORDER]
    assert offsets == sorted(offsets, reverse=True), "Soft piu' veloce della Hard"
    assert rates == sorted(rates), "Soft piu' fragile della Hard"


def test_wet_weather_compounds_exist_in_the_model():
    assert not Compound.INTERMEDIATE.is_dry
    assert not Compound.WET.is_dry
    assert Compound.INTERMEDIATE in COMPOUND_PACE_OFFSET_SECONDS
    assert Compound.WET in COMPOUND_DEGRADATION_RATE_SECONDS_PER_LAP


def test_degradation_is_monotonic_with_age():
    entry = _entry(1, team_id=1, strength=70)
    circuit = circuit_by_code("sakhir")
    tyres = fresh_set(Compound.C3)
    previous_loss = tyre_lap_loss_seconds(tyres)
    for expected_age in range(1, 31):
        tyres = after_lap(tyres, entry, circuit, Aggression.NORMAL)
        assert tyres.age_laps == expected_age
        loss = tyre_lap_loss_seconds(tyres)
        assert loss > previous_loss
        previous_loss = loss


def test_tyre_management_slows_degradation():
    careful = _entry(1, team_id=1, strength=90)
    careless = _entry(2, team_id=2, strength=40)
    circuit = circuit_by_code("sakhir")
    tyres = fresh_set(Compound.C3)
    careful_step = degradation_step_seconds(tyres, careful, circuit, Aggression.NORMAL)
    careless_step = degradation_step_seconds(tyres, careless, circuit, Aggression.NORMAL)
    assert careful_step < careless_step


def test_aggression_modulates_degradation():
    entry = _entry(1, team_id=1, strength=70)
    circuit = circuit_by_code("sakhir")
    tyres = fresh_set(Compound.C3)
    push = degradation_step_seconds(tyres, entry, circuit, Aggression.PUSH)
    normal = degradation_step_seconds(tyres, entry, circuit, Aggression.NORMAL)
    conserve = degradation_step_seconds(tyres, entry, circuit, Aggression.CONSERVE)
    assert push > normal > conserve


def test_circuit_severity_accelerates_degradation():
    entry = _entry(1, team_id=1, strength=70)
    tyres = fresh_set(Compound.C3)
    gentle = degradation_step_seconds(tyres, entry, circuit_by_code("monaco"), Aggression.NORMAL)
    severe = degradation_step_seconds(
        tyres, entry, circuit_by_code("silverstone"), Aggression.NORMAL
    )
    assert severe > gentle


def _optimal_stop_count(circuit) -> int:
    """Le soste ottime dalla sola curva di Degrado della Medium del GP."""
    entry = _entry(1, team_id=1, strength=60)
    medium = nominated_compounds(circuit)[CompoundSlot.MEDIUM]
    step = degradation_step_seconds(fresh_set(medium), entry, circuit, Aggression.NORMAL)
    laps = circuit.race_laps

    def race_cost(stops: int) -> float:
        stint = laps / (stops + 1)
        return (stops + 1) * step * stint * stint / 2 + stops * PIT_STOP_BASE_SECONDS

    return min(range(5), key=race_cost)


def test_one_or_two_stop_strategies_emerge_from_the_curves():
    """Su tutto il Calendario l'ottimo sta a 1-2 soste, mai 0 e mai 3+."""
    optimal_by_circuit = {circuit.code: _optimal_stop_count(circuit) for circuit in CALENDAR_2026}
    assert all(stops in (1, 2) for stops in optimal_by_circuit.values()), optimal_by_circuit
