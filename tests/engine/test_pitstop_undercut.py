"""Pit stop, eventi box e undercut emergente dai distacchi (FOR-10)."""

from random import Random

import pytest
from test_race_base import _entry

from fm_engine.circuits import circuit_by_code
from fm_engine.events import PitEntry, PitExit, TyreChange
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.pitstop import (
    PIT_STOP_BASE_SECONDS,
    PIT_STOP_MINIMUM_SECONDS,
    pit_stop_seconds,
)
from fm_engine.race import start_race, step
from fm_engine.state import DriverOrders, Orders, PitOrder
from fm_engine.tyres import Compound, CompoundSlot, nominated_compounds

NO_MISFORTUNE = MisfortuneConfig.disabled()


def test_pit_stop_seconds_distribution():
    rng = Random(123)
    draws = [pit_stop_seconds(rng) for _ in range(1000)]
    assert all(draw >= PIT_STOP_MINIMUM_SECONDS for draw in draws)
    average = sum(draws) / len(draws)
    assert abs(average - PIT_STOP_BASE_SECONDS) < 0.1


def test_pit_order_changes_tyres_and_emits_events():
    circuit = circuit_by_code("sakhir")
    entries = (_entry(1, team_id=1, strength=70), _entry(2, team_id=2, strength=70))
    state, _ = start_race(entries, circuit, seed=9, misfortune=NO_MISFORTUNE)
    soft = nominated_compounds(circuit)[CompoundSlot.SOFT]
    medium = nominated_compounds(circuit)[CompoundSlot.MEDIUM]
    for _ in range(5):
        state, _ = step(state)
    aged = state.car_of(1).tyres
    assert aged.age_laps == 5 and aged.degradation_seconds > 0
    orders = Orders(drivers={1: DriverOrders(pit=PitOrder(compound=soft))})
    state, events = step(state, orders)
    pit_events = [e for e in events if isinstance(e, PitEntry | TyreChange | PitExit)]
    assert [type(e) for e in pit_events] == [PitEntry, TyreChange, PitExit]
    change = pit_events[1]
    assert change.old_compound == medium.value and change.new_compound == soft.value
    exit_event = pit_events[2]
    assert exit_event.time_lost_seconds >= PIT_STOP_MINIMUM_SECONDS
    fresh = state.car_of(1).tyres
    assert fresh.compound is soft and fresh.age_laps == 0 and fresh.degradation_seconds == 0.0
    assert state.car_of(1).compounds_used == (medium, soft)
    assert state.car_of(1).last_lap_seconds > state.car_of(2).last_lap_seconds + 10


def test_pit_rejoin_is_not_a_duel():
    """Chi rientra dai box cede la posizione senza che serva un sorpasso."""
    circuit = circuit_by_code("sakhir")
    entries = (_entry(1, team_id=1, strength=70), _entry(2, team_id=2, strength=70))
    state, _ = start_race(entries, circuit, seed=9, misfortune=NO_MISFORTUNE)
    soft = nominated_compounds(circuit)[CompoundSlot.SOFT]
    orders = Orders(drivers={1: DriverOrders(pit=PitOrder(compound=soft))})
    state, events = step(state, orders)
    assert state.cars[0].entry.driver.id == 2
    from fm_engine.events import Overtake

    assert not [e for e in events if isinstance(e, Overtake)]


def test_wet_compounds_are_inactive_until_weather():
    circuit = circuit_by_code("sakhir")
    entries = (_entry(1, team_id=1, strength=70), _entry(2, team_id=2, strength=70))
    state, _ = start_race(entries, circuit, seed=9, misfortune=NO_MISFORTUNE)
    orders = Orders(drivers={1: DriverOrders(pit=PitOrder(compound=Compound.WET))})
    with pytest.raises(ValueError):
        step(state, orders)


def test_only_nominated_compounds_are_available():
    circuit = circuit_by_code("sakhir")  # nomina C1/C2/C3
    entries = (_entry(1, team_id=1, strength=70), _entry(2, team_id=2, strength=70))
    state, _ = start_race(entries, circuit, seed=9, misfortune=NO_MISFORTUNE)
    orders = Orders(drivers={1: DriverOrders(pit=PitOrder(compound=Compound.C5))})
    with pytest.raises(ValueError):
        step(state, orders)
    with pytest.raises(ValueError):
        start_race(entries, circuit, seed=9, starting_compounds={1: Compound.C5})


def _undercut_gain(seed: int) -> float:
    """Gara a 2 alla pari: il pilota 2 anticipa la sosta di 6 giri.

    Misura il guadagno dell'undercut sui distacchi nella finestra di
    sosta: differenza tra il distacco del pilota 2 dal pilota 1 prima
    della propria sosta e dopo la sosta del rivale (giro 21, entrambi
    fermati una volta). Positivo se anticipare ha pagato.
    """
    circuit = circuit_by_code("sakhir")
    entries = (_entry(1, team_id=1, strength=70), _entry(2, team_id=2, strength=70))
    state, _ = start_race(entries, circuit, seed=seed, misfortune=NO_MISFORTUNE)
    hard = nominated_compounds(circuit)[CompoundSlot.HARD]
    pit_for = {
        14: Orders(drivers={2: DriverOrders(pit=PitOrder(compound=hard))}),
        20: Orders(drivers={1: DriverOrders(pit=PitOrder(compound=hard))}),
    }

    def deficit_of_2(current) -> float:
        return current.car_of(2).total_time_seconds - current.car_of(1).total_time_seconds

    deficit_before = None
    while state.lap < 21:
        if state.lap == 13:
            deficit_before = deficit_of_2(state)
        state, _ = step(state, pit_for.get(state.lap + 1))
    assert deficit_before is not None
    return deficit_before - deficit_of_2(state)


def test_undercut_gains_show_in_the_gaps():
    """Chi anticipa la sosta guadagna sul rivale rimasto fuori su gomme vecchie."""
    gains = [_undercut_gain(seed) for seed in (1, 2, 3, 4, 5)]
    assert len([gain for gain in gains if gain > 0]) >= 4, gains
    assert sum(gains) / len(gains) > 1.5, gains
