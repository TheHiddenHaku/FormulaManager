"""Difficolta' di sorpasso per circuito e isteresi dei duelli (FOR-36).

Tre proprieta': nei circuiti difficili si sorpassa molto meno che in
quelli facili a parita' di seed; chi viene sorpassato non ritenta il
giro dopo a parita' di passo (niente ping-pong); a Monaco la posizione
di partenza pesa sul risultato molto piu' che a Monza.
"""

from fm_engine.circuits import circuit_by_code
from fm_engine.events import Overtake
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.state import CarAttributes, RaceEntry
from fm_engine.world.models import Driver


def _entry(driver_id: int, race_pace: int, consistency: int = 80) -> RaceEntry:
    """Una iscritta con vettura neutra: conta solo il passo del pilota."""
    driver = Driver(
        id=driver_id,
        name=f"Driver {driver_id}",
        nationality="it",
        age=28,
        one_lap_pace=race_pace,
        race_pace=race_pace,
        duels=70,
        tyre_management=70,
        wet_weather=70,
        consistency=consistency,
        potential=70,
        salary_demand_usd=5_000_000,
    )
    car = CarAttributes(
        engine_power=70,
        downforce=70,
        aero_efficiency=70,
        mechanical_grip=70,
        tyre_management=70,
        reliability=70,
    )
    return RaceEntry(driver=driver, team_id=(driver_id + 1) // 2, car=car)


def _reversed_pace_grid(count: int = 22) -> tuple[RaceEntry, ...]:
    """Griglia al contrario: in pole il piu' lento, in fondo il piu' veloce."""
    return tuple(_entry(index + 1, race_pace=50 + 2 * index) for index in range(count))


def _overtake_count(events) -> int:
    return sum(1 for event in events if isinstance(event, Overtake))


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / n
    variance_x = sum((x - mean_x) ** 2 for x in xs) / n
    variance_y = sum((y - mean_y) ** 2 for y in ys) / n
    return covariance / (variance_x**0.5 * variance_y**0.5)


def test_hard_circuits_see_far_fewer_overtakes(run_race):
    """A parita' di seed Monaco (difficolta' 5) sorpassa molto meno di Monza (1).

    Monaco ha pure 25 giri in piu' di Monza: se i sorpassi restano
    comunque sotto la meta', la modulazione sta lavorando davvero.
    """
    entries = _reversed_pace_grid()
    monza_total = 0
    monaco_total = 0
    for seed in (1, 2, 3):
        _, events = run_race(
            entries, circuit_by_code("monza"), seed, misfortune=MisfortuneConfig.disabled()
        )
        monza_total += _overtake_count(events)
        _, events = run_race(
            entries, circuit_by_code("monaco"), seed, misfortune=MisfortuneConfig.disabled()
        )
        monaco_total += _overtake_count(events)
    assert monza_total > 0
    assert monaco_total < monza_total / 2, (monaco_total, monza_total)


def test_no_overtake_ping_pong_between_equal_pace_cars(run_race):
    """Chi e' appena stato sorpassato non si riprende la posizione al giro dopo."""
    entries = (_entry(1, race_pace=70, consistency=70), _entry(2, race_pace=70, consistency=70))
    swap_backs = 0
    total_overtakes = 0
    for seed in range(1, 9):
        _, events = run_race(
            entries, circuit_by_code("spielberg"), seed, misfortune=MisfortuneConfig.disabled()
        )
        passes = {
            (event.lap, event.driver_id, event.overtaken_driver_id)
            for event in events
            if isinstance(event, Overtake)
        }
        total_overtakes += len(passes)
        swap_backs += sum(1 for lap, winner, loser in passes if (lap + 1, loser, winner) in passes)
    assert total_overtakes > 0
    assert swap_backs == 0, swap_backs


def test_starting_position_counts_at_monaco(run_race):
    """Griglia invertita: a Monza il passo riordina, a Monaco la pole regge."""
    entries = _reversed_pace_grid()
    start_positions = list(range(1, len(entries) + 1))
    correlations: dict[str, float] = {}
    for code in ("monza", "monaco"):
        seed_correlations = []
        for seed in (1, 2, 3):
            state, _ = run_race(
                entries, circuit_by_code(code), seed, misfortune=MisfortuneConfig.disabled()
            )
            final_position = {car.entry.driver.id: car.position for car in state.cars}
            finals = [float(final_position[entry.driver.id]) for entry in entries]
            seed_correlations.append(_pearson([float(p) for p in start_positions], finals))
        correlations[code] = sum(seed_correlations) / len(seed_correlations)
    assert correlations["monaco"] > correlations["monza"] + 0.3, correlations
    assert correlations["monaco"] > 0.5, correlations
