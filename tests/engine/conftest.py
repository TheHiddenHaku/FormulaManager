"""Fixture comuni dei test del motore di gara (FOR-8).

Griglie sintetiche riproducibili: niente dipendenza dalla generazione
del Mondo, i test del motore controllano direttamente gli attributi.
"""

from collections.abc import Callable
from random import Random

import pytest

from fm_engine.circuits import Circuit
from fm_engine.events import RaceEvent
from fm_engine.race import start_race, step
from fm_engine.state import CarAttributes, Orders, RaceEntry, RaceState
from fm_engine.world.models import Driver

EntryFactory = Callable[..., tuple[RaceEntry, ...]]


@pytest.fixture
def entry_factory() -> EntryFactory:
    """Costruisce una griglia sintetica di RaceEntry, riproducibile dal seed."""

    def make(count: int = 22, seed: int = 1234) -> tuple[RaceEntry, ...]:
        rng = Random(seed)
        entries = []
        for index in range(count):
            driver = Driver(
                id=index + 1,
                name=f"Driver {index + 1}",
                nationality="it",
                age=rng.randint(20, 38),
                one_lap_pace=rng.randint(40, 92),
                race_pace=rng.randint(40, 92),
                duels=rng.randint(40, 92),
                tyre_management=rng.randint(40, 92),
                wet_weather=rng.randint(40, 92),
                consistency=rng.randint(40, 92),
                potential=rng.randint(20, 95),
                salary_demand_usd=5_000_000,
            )
            car = CarAttributes(
                engine_power=rng.randint(40, 85),
                downforce=rng.randint(40, 85),
                aero_efficiency=rng.randint(40, 85),
                mechanical_grip=rng.randint(40, 85),
                tyre_management=rng.randint(40, 85),
                reliability=rng.randint(40, 85),
            )
            entries.append(RaceEntry(driver=driver, team_id=index // 2 + 1, car=car))
        return tuple(entries)

    return make


@pytest.fixture
def run_race() -> Callable[..., tuple[RaceState, list[RaceEvent]]]:
    """Simula una gara completa e raccoglie tutti gli eventi emessi."""

    def run(
        entries: tuple[RaceEntry, ...],
        circuit: Circuit,
        seed: int,
        orders: Orders | None = None,
    ) -> tuple[RaceState, list[RaceEvent]]:
        state, events = start_race(entries, circuit, seed)
        collected = list(events)
        while not state.finished:
            state, events = step(state, orders)
            collected.extend(events)
        return state, collected

    return run
