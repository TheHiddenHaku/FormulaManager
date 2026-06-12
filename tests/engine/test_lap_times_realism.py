"""Tempi sul giro fisicamente plausibili per circuito (FOR-37).

Il tempo di pole simulato con una griglia forte deve cadere in una
finestra plausibile attorno al riferimento del circuito: la base e'
additiva, quindi la pole sta poco sopra il tempo base.
"""

from fm_engine.circuits import CALENDAR_2026
from fm_engine.qualifying import simulate_qualifying
from fm_engine.state import CarAttributes, RaceEntry
from fm_engine.world.models import Driver

# Plausibility window around the circuit reference, in seconds.
POLE_WINDOW_BELOW_SECONDS = 2.0
POLE_WINDOW_ABOVE_SECONDS = 6.0


def _strong_grid(count: int = 22) -> tuple[RaceEntry, ...]:
    """Una griglia di vetture e piloti forti: la pole sfiora il riferimento."""
    entries = []
    for index in range(count):
        driver = Driver(
            id=index + 1,
            name=f"Driver {index + 1}",
            nationality="it",
            age=28,
            one_lap_pace=88 + index % 5,
            race_pace=88 + index % 5,
            duels=80,
            tyre_management=80,
            wet_weather=80,
            consistency=88,
            potential=90,
            salary_demand_usd=5_000_000,
        )
        car = CarAttributes(
            engine_power=88,
            downforce=88,
            aero_efficiency=88,
            mechanical_grip=88,
            tyre_management=88,
            reliability=88,
        )
        entries.append(RaceEntry(driver=driver, team_id=index // 2 + 1, car=car))
    return tuple(entries)


def test_pole_times_fall_in_the_plausibility_window():
    """Per ogni circuito la pole simulata sta attorno al riferimento."""
    entries = _strong_grid()
    for circuit in CALENDAR_2026:
        for seed in (1, 2):
            result, _ = simulate_qualifying(entries, circuit, seed=seed)
            pole_seconds = result.segments[-1].rows[0].time_seconds
            assert (
                circuit.base_lap_seconds - POLE_WINDOW_BELOW_SECONDS
                <= pole_seconds
                <= circuit.base_lap_seconds + POLE_WINDOW_ABOVE_SECONDS
            ), (circuit.code, pole_seconds, circuit.base_lap_seconds)


def test_monaco_pole_never_below_seventy_seconds():
    """Il collaudo che ha originato la issue: 59.5s a Monaco e' impossibile."""
    entries = _strong_grid()
    monaco = next(circuit for circuit in CALENDAR_2026 if circuit.code == "monaco")
    for seed in range(1, 11):
        result, _ = simulate_qualifying(entries, monaco, seed=seed)
        pole_seconds = result.segments[-1].rows[0].time_seconds
        assert pole_seconds >= 70.0, (seed, pole_seconds)
