"""Gara base: classifica, punti, duelli e Ordini (FOR-8)."""

import pytest

from fm_engine.circuits import CALENDAR_2026, circuit_by_code
from fm_engine.events import ChequeredFlag, FastestLap, Overtake, RaceStarted, TeamOrderSwap
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.points import points_for_position
from fm_engine.race import start_race, step
from fm_engine.state import (
    Aggression,
    CarAttributes,
    DriverOrders,
    DuelInstruction,
    Orders,
    RaceEntry,
    TeamOrder,
)
from fm_engine.world.models import Driver

# Sfiga spenta per le gare curate: i test sugli Ordini vogliono solo fisica.
NO_MISFORTUNE = MisfortuneConfig.disabled()


def _entry(driver_id: int, team_id: int, strength: int) -> RaceEntry:
    """Una iscritta con tutti gli attributi al livello dato: duelli mirati."""
    driver = Driver(
        id=driver_id,
        name=f"Driver {driver_id}",
        nationality="it",
        age=28,
        one_lap_pace=strength,
        race_pace=strength,
        duels=strength,
        tyre_management=strength,
        wet_weather=strength,
        consistency=strength,
        potential=50,
        salary_demand_usd=5_000_000,
    )
    car = CarAttributes(
        engine_power=strength,
        downforce=strength,
        aero_efficiency=strength,
        mechanical_grip=strength,
        tyre_management=strength,
        reliability=strength,
    )
    return RaceEntry(driver=driver, team_id=team_id, car=car)


def test_start_race_keeps_grid_order(entry_factory):
    entries = entry_factory()
    state, events = start_race(entries, circuit_by_code("albert_park"), seed=3)
    assert [car.entry.driver.id for car in state.cars] == [e.driver.id for e in entries]
    assert [car.position for car in state.cars] == list(range(1, 23))
    assert state.lap == 0 and not state.finished
    assert events == (RaceStarted(lap=0, circuit_code="albert_park", total_laps=58),)


def test_start_race_rejects_bad_grids(entry_factory):
    circuit = circuit_by_code("albert_park")
    with pytest.raises(ValueError):
        start_race(entry_factory(count=1), circuit, seed=1)
    twice = entry_factory(count=2) + entry_factory(count=2)
    with pytest.raises(ValueError):
        start_race(twice, circuit, seed=1)


def test_full_race_classification(entry_factory, run_race):
    entries = entry_factory()
    state, events = run_race(entries, circuit_by_code("albert_park"), seed=99)
    assert state.finished and state.lap == state.total_laps == 58
    runners = len(state.cars)
    assert runners + len(state.dnfs) == 22
    assert [car.position for car in state.cars] == list(range(1, runners + 1))
    gaps = [car.gap_to_leader_seconds for car in state.cars]
    assert gaps[0] == 0.0
    assert gaps == sorted(gaps)
    flags = [event for event in events if isinstance(event, ChequeredFlag)]
    assert len(flags) == 1
    classification = flags[0].classification
    assert len(classification) == runners
    assert [row.driver_id for row in classification] == [car.entry.driver.id for car in state.cars]
    for row in classification:
        assert row.points == points_for_position(row.position)


def test_step_after_finish_raises(entry_factory, run_race):
    entries = entry_factory()
    state, _ = run_race(entries, circuit_by_code("spa"), seed=5)
    with pytest.raises(ValueError):
        step(state)


def test_overtakes_happen_and_are_typed(entry_factory, run_race):
    entries = entry_factory()
    _, events = run_race(entries, circuit_by_code("albert_park"), seed=11)
    overtakes = [event for event in events if isinstance(event, Overtake)]
    assert overtakes, "una gara a 22 vetture senza sorpassi non e' plausibile"
    for overtake in overtakes:
        assert overtake.driver_id != overtake.overtaken_driver_id
        assert overtake.position >= 1


def test_fastest_lap_is_tracked(entry_factory, run_race):
    entries = entry_factory()
    state, events = run_race(entries, circuit_by_code("spa"), seed=21)
    fastest_events = [event for event in events if isinstance(event, FastestLap)]
    assert fastest_events
    assert state.fastest_lap_seconds == fastest_events[-1].time_seconds
    assert state.fastest_lap_driver_id == fastest_events[-1].driver_id
    assert state.fastest_lap_seconds > 0


def test_hold_positions_freezes_teammates(run_race):
    entries = (_entry(1, team_id=1, strength=50), _entry(2, team_id=1, strength=90))
    orders = Orders(teams={1: TeamOrder.HOLD_POSITIONS})
    state, events = run_race(
        entries, circuit_by_code("spa"), seed=8, orders=orders, misfortune=NO_MISFORTUNE
    )
    assert state.cars[0].entry.driver.id == 1
    assert not [event for event in events if isinstance(event, Overtake)]


def test_without_orders_faster_teammate_overtakes(run_race):
    entries = (_entry(1, team_id=1, strength=50), _entry(2, team_id=1, strength=90))
    state, events = run_race(entries, circuit_by_code("spa"), seed=8, misfortune=NO_MISFORTUNE)
    assert state.cars[0].entry.driver.id == 2
    assert [event for event in events if isinstance(event, Overtake)]


def test_swap_positions_promotes_faster_teammate(entry_factory):
    entries = (_entry(1, team_id=1, strength=50), _entry(2, team_id=1, strength=90))
    state, _ = start_race(entries, circuit_by_code("spa"), seed=8, misfortune=NO_MISFORTUNE)
    orders = Orders(teams={1: TeamOrder.SWAP_POSITIONS})
    state, events = step(state, orders)
    swaps = [event for event in events if isinstance(event, TeamOrderSwap)]
    assert len(swaps) == 1
    assert swaps[0].promoted_driver_id == 2 and swaps[0].demoted_driver_id == 1
    assert state.cars[0].entry.driver.id == 2
    assert not [event for event in events if isinstance(event, Overtake)]


def test_no_risk_instruction_blocks_attacks(run_race):
    entries = (_entry(1, team_id=1, strength=50), _entry(2, team_id=2, strength=90))
    orders = Orders(drivers={2: DriverOrders(duel_instruction=DuelInstruction.NO_RISK)})
    state, events = run_race(
        entries, circuit_by_code("spa"), seed=8, orders=orders, misfortune=NO_MISFORTUNE
    )
    assert state.cars[0].entry.driver.id == 1
    assert not [event for event in events if isinstance(event, Overtake)]


def test_push_is_faster_than_conserve_on_raw_pace():
    """Il Push paga sul passo puro; il conto del Degrado e' un'altra voce."""
    from random import Random

    from fm_engine.laptime import lap_time_seconds

    entry = _entry(1, team_id=1, strength=70)
    circuit = circuit_by_code("spa")

    def average_lap(aggression: Aggression) -> float:
        rng = Random(33)
        return sum(lap_time_seconds(entry, circuit, aggression, rng) for _ in range(200)) / 200

    assert average_lap(Aggression.PUSH) < average_lap(Aggression.NORMAL)
    assert average_lap(Aggression.NORMAL) < average_lap(Aggression.CONSERVE)


def test_push_wears_tyres_faster_than_conserve():
    entries = (_entry(1, team_id=1, strength=70), _entry(2, team_id=2, strength=70))
    push = Orders(drivers={1: DriverOrders(aggression=Aggression.PUSH)})
    conserve = Orders(drivers={1: DriverOrders(aggression=Aggression.CONSERVE)})
    pushed, _ = start_race(entries, circuit_by_code("spa"), seed=33, misfortune=NO_MISFORTUNE)
    conserved = pushed
    for _ in range(10):
        pushed, _ = step(pushed, push)
        conserved, _ = step(conserved, conserve)
    assert (
        pushed.car_of(1).tyres.degradation_seconds > conserved.car_of(1).tyres.degradation_seconds
    )


def test_smoke_1000_races(entry_factory):
    """Smoke: 1000 gare complete senza errori, su tutto il Calendario."""
    entries = entry_factory()
    for seed in range(1000):
        circuit = CALENDAR_2026[seed % len(CALENDAR_2026)]
        state, _ = start_race(entries, circuit, seed=seed)
        while not state.finished:
            state, _ = step(state)
        assert state.lap == circuit.race_laps
        assert [car.position for car in state.cars] == list(range(1, len(state.cars) + 1))
        assert len(state.cars) + len(state.dnfs) == 22
