"""Aggregati e report leggibile dell'harness di bilanciamento (FOR-14)."""

from collections import Counter, defaultdict
from dataclasses import dataclass

from fm_engine.balance.simulate import SimulationResult


@dataclass(frozen=True)
class Aggregates:
    """Le metriche aggregate su cui ragiona il report e la sanita' pytest."""

    races: int
    mean_dnfs_per_race: float
    safety_car_rate_by_circuit: dict[str, float]
    vsc_rate_by_circuit: dict[str, float]
    rain_rate_by_circuit: dict[str, float]
    # Mean per-season points spread between the best and worst team.
    mean_team_points_spread: float
    # Pearson correlation between combined car+driver performance and
    # total driver points across the whole simulation.
    attribute_correlation: float
    # Pit stop count distribution per car, dry races only.
    dry_stops_distribution: dict[int, int]
    compound_usage: dict[str, int]


def aggregates(result: SimulationResult) -> Aggregates:
    """Calcola le metriche aggregate dal risultato della simulazione."""
    races = len(result.races)
    mean_dnfs = sum(record.dnf_count for record in result.races) / races
    sc_rate: dict[str, float] = {}
    vsc_rate: dict[str, float] = {}
    rain_rate: dict[str, float] = {}
    by_circuit: dict[str, list] = defaultdict(list)
    for record in result.races:
        by_circuit[record.circuit_code].append(record)
    for code, records in by_circuit.items():
        sc_rate[code] = sum(1 for r in records if r.safety_cars > 0) / len(records)
        vsc_rate[code] = sum(1 for r in records if r.vscs > 0) / len(records)
        rain_rate[code] = sum(1 for r in records if r.rained) / len(records)

    season_team_points: dict[int, Counter] = defaultdict(Counter)
    total_driver_points: Counter = Counter()
    for record in result.races:
        for team_id, points in record.team_points.items():
            season_team_points[record.season][team_id] += points
        for driver_id, points in record.driver_points.items():
            total_driver_points[driver_id] += points
    spreads = []
    for standings in season_team_points.values():
        values = list(standings.values())
        spreads.append(max(values) - min(values))
    mean_spread = sum(spreads) / len(spreads)

    correlation = _pearson(
        [result.performance_by_driver[d] for d in sorted(result.performance_by_driver)],
        [total_driver_points.get(d, 0) for d in sorted(result.performance_by_driver)],
    )

    dry_stops: Counter[int] = Counter()
    compound_usage: Counter[str] = Counter()
    for record in result.races:
        if not record.rained:
            for stops in record.stops_by_driver.values():
                dry_stops[stops] += 1
        compound_usage.update(record.compounds_used)

    return Aggregates(
        races=races,
        mean_dnfs_per_race=mean_dnfs,
        safety_car_rate_by_circuit=sc_rate,
        vsc_rate_by_circuit=vsc_rate,
        rain_rate_by_circuit=rain_rate,
        mean_team_points_spread=mean_spread,
        attribute_correlation=correlation,
        dry_stops_distribution=dict(dry_stops),
        compound_usage=dict(compound_usage),
    )


def render_report(result: SimulationResult) -> str:
    """Il report statistico leggibile, identico a parita' di seed."""
    stats = aggregates(result)
    lines: list[str] = []
    lines.append("Formula Manager - report di bilanciamento")
    lines.append(f"Stagioni: {result.seasons}  Seed: {result.seed}  Gare: {stats.races}")
    lines.append("")
    lines.append(f"Abbandoni per gara (media): {stats.mean_dnfs_per_race:.2f}")
    lines.append(f"Spread punti squadre per stagione (media): {stats.mean_team_points_spread:.1f}")
    lines.append(f"Correlazione attributi-risultati (Pearson): {stats.attribute_correlation:.3f}")
    lines.append("")
    lines.append("Frequenza per circuito (quota di gare con almeno un evento):")
    lines.append(f"{'circuito':<20}{'SC':>6}{'VSC':>6}{'pioggia':>9}")
    for code in sorted(stats.safety_car_rate_by_circuit):
        lines.append(
            f"{code:<20}"
            f"{stats.safety_car_rate_by_circuit[code]:>6.2f}"
            f"{stats.vsc_rate_by_circuit[code]:>6.2f}"
            f"{stats.rain_rate_by_circuit[code]:>9.2f}"
        )
    lines.append("")
    lines.append("Distribuzione soste (gare asciutte, per vettura):")
    total = sum(stats.dry_stops_distribution.values()) or 1
    for stops in sorted(stats.dry_stops_distribution):
        share = stats.dry_stops_distribution[stops] / total
        lines.append(f"  {stops} soste: {share:.1%}")
    lines.append("")
    lines.append("Mescole usate (gare in cui compaiono):")
    for compound in sorted(stats.compound_usage):
        lines.append(f"  {compound}: {stats.compound_usage[compound]}")
    return "\n".join(lines)


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / n
    variance_x = sum((x - mean_x) ** 2 for x in xs) / n
    variance_y = sum((y - mean_y) ** 2 for y in ys) / n
    if variance_x == 0 or variance_y == 0:
        return 0.0
    return covariance / (variance_x**0.5 * variance_y**0.5)
