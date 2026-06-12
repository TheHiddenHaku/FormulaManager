"""Determinismo del motore di gara (FOR-8).

Stesso seed e stessi Ordini: stati ed eventi identici, run dopo run.
Seed diversi: gare diverse.
"""

from fm_engine.circuits import circuit_by_code
from fm_engine.state import Aggression, DriverOrders, Orders


def test_same_seed_same_race(entry_factory, run_race):
    entries = entry_factory()
    circuit = circuit_by_code("spa")
    first_state, first_events = run_race(entries, circuit, seed=42)
    second_state, second_events = run_race(entries, circuit, seed=42)
    assert first_state == second_state
    assert first_events == second_events


def test_same_seed_same_race_with_orders(entry_factory, run_race):
    entries = entry_factory()
    circuit = circuit_by_code("spa")
    orders = Orders(drivers={1: DriverOrders(aggression=Aggression.PUSH)})
    first_state, first_events = run_race(entries, circuit, seed=7, orders=orders)
    second_state, second_events = run_race(entries, circuit, seed=7, orders=orders)
    assert first_state == second_state
    assert first_events == second_events


def test_different_seeds_differ(entry_factory, run_race):
    entries = entry_factory()
    circuit = circuit_by_code("spa")
    first_state, _ = run_race(entries, circuit, seed=1)
    second_state, _ = run_race(entries, circuit, seed=2)
    assert first_state.cars != second_state.cars
