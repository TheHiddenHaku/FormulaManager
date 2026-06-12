"""Bagnato: specialisti visibili nei risultati, Errori amplificati (FOR-13)."""

from dataclasses import replace
from random import Random

from fm_engine.circuits import circuit_by_code
from fm_engine.events import Accident, DriverError
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.race import start_race, step
from fm_engine.state import CarAttributes, RaceEntry
from fm_engine.tyres import Compound
from fm_engine.weather import wet_error_multiplier
from fm_engine.world.models import Driver

NO_MISFORTUNE = MisfortuneConfig.disabled()


def _wet_graded_entries() -> tuple[RaceEntry, ...]:
    """22 iscritte identiche tranne l'attributo Bagnato, crescente con l'id."""
    car = CarAttributes(
        engine_power=70,
        downforce=70,
        aero_efficiency=70,
        mechanical_grip=70,
        tyre_management=70,
        reliability=70,
    )
    entries = []
    for driver_id in range(1, 23):
        driver = Driver(
            id=driver_id,
            name=f"Driver {driver_id}",
            nationality="it",
            age=28,
            one_lap_pace=70,
            race_pace=70,
            duels=60,
            tyre_management=60,
            wet_weather=30 + (driver_id - 1) * 3,
            consistency=90,
            potential=50,
            salary_demand_usd=5_000_000,
        )
        entries.append(RaceEntry(driver=driver, team_id=(driver_id - 1) // 2 + 1, car=car))
    return tuple(entries)


def test_wet_specialists_show_up_in_wet_results():
    """Su N gare bagnate gli specialisti del Bagnato emergono in classifica."""
    entries = _wet_graded_entries()
    circuit = circuit_by_code("spa")
    rng = Random(0)
    specialist_ids = {entry.driver.id for entry in entries[-5:]}
    struggler_ids = {entry.driver.id for entry in entries[:5]}
    specialist_positions: list[int] = []
    struggler_positions: list[int] = []
    for _ in range(8):
        # Griglia mescolata a ogni gara: niente bias di posizione di partenza.
        grid = list(entries)
        rng.shuffle(grid)
        state, _ = start_race(
            tuple(grid), circuit, seed=rng.randint(0, 10**9), misfortune=NO_MISFORTUNE
        )
        # Diluvio fisso per tutta la gara: pista satura.
        state = replace(state, rain_intensity=1.0, track_wetness=1.0)
        for _ in range(30):
            state, _ = step(state)
            state = replace(state, rain_intensity=1.0, track_wetness=1.0)
        positions = {car.entry.driver.id: car.position for car in state.cars}
        specialist_positions.extend(positions[i] for i in specialist_ids)
        struggler_positions.extend(positions[i] for i in struggler_ids)
    average_specialist = sum(specialist_positions) / len(specialist_positions)
    average_struggler = sum(struggler_positions) / len(struggler_positions)
    assert average_specialist < average_struggler - 5, (average_specialist, average_struggler)


def test_wet_error_multiplier_grows_with_wetness_and_wrong_tyre():
    dry = wet_error_multiplier(Compound.C3, 0.0)
    wet_right_tyre = wet_error_multiplier(Compound.INTERMEDIATE, 0.6)
    wet_wrong_tyre = wet_error_multiplier(Compound.C3, 0.6)
    assert dry == 1.0
    assert wet_right_tyre > dry
    assert wet_wrong_tyre > wet_right_tyre


def test_errors_are_amplified_on_a_wet_track_comparatively(entry_factory):
    """A parita' di seed, pista bagnata e slick producono piu' Sfiga."""
    entries = entry_factory()
    circuit = circuit_by_code("spa")
    base_state, _ = start_race(entries, circuit, seed=5, misfortune=NO_MISFORTUNE)
    for _ in range(5):
        base_state, _ = step(base_state)
    loud_config = MisfortuneConfig().scaled(8.0)
    wet_count = 0
    dry_count = 0
    for seed in range(200):
        for wetness, bucket in ((0.7, "wet"), (0.0, "dry")):
            probe = replace(
                base_state,
                seed=seed + 50_000,
                misfortune=loud_config,
                rain_intensity=0.0,
                track_wetness=wetness,
            )
            _, events = step(probe)
            count = sum(1 for e in events if isinstance(e, DriverError | Accident))
            if bucket == "wet":
                wet_count += count
            else:
                dry_count += count
    assert wet_count > dry_count * 1.5, (wet_count, dry_count)
