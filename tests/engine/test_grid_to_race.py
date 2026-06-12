"""Integrazione qualifiche -> gara: la griglia alimenta start_race (FOR-9)."""

from fm_engine.circuits import circuit_by_code
from fm_engine.qualifying import simulate_qualifying
from fm_engine.race import start_race, step


def test_qualifying_grid_feeds_the_race(entry_factory):
    entries = entry_factory()
    circuit = circuit_by_code("albert_park")
    result, _ = simulate_qualifying(entries, circuit, seed=77)
    state, _ = start_race(result.grid, circuit, seed=77)
    assert [car.entry.driver.id for car in state.cars] == [entry.driver.id for entry in result.grid]
    assert state.cars[0].entry.driver.id == result.pole_driver_id


def test_full_weekend_qualifying_then_race(entry_factory):
    entries = entry_factory()
    circuit = circuit_by_code("spa")
    result, _ = simulate_qualifying(entries, circuit, seed=5)
    state, _ = start_race(result.grid, circuit, seed=5)
    while not state.finished:
        state, _ = step(state)
    assert state.lap == circuit.race_laps
    assert sorted(car.entry.driver.id for car in state.cars + state.dnfs) == sorted(
        entry.driver.id for entry in entries
    )
