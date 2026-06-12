"""Sanita' permanente del bilanciamento del motore (FOR-14).

Asserzioni sui range attesi del comportamento del motore: se il
bilanciamento degenera in silenzio, questa suite diventa rossa.
"""

import pytest

from fm_engine.balance.report import aggregates, render_report
from fm_engine.balance.simulate import simulate
from fm_engine.circuits import CALENDAR_2026

# La frequenza SC si confronta tra gruppi di circuiti, non sul singolo:
# con poche stagioni il singolo circuito e' troppo rumoroso.
HIGH_SC_PROBABILITY = 0.50
LOW_SC_PROBABILITY = 0.30


@pytest.fixture(scope="module")
def result():
    return simulate(seasons=6, seed=2026)


@pytest.fixture(scope="module")
def stats(result):
    return aggregates(result)


def test_dnf_per_race_in_realistic_range(stats):
    assert 3.0 <= stats.mean_dnfs_per_race <= 5.0, stats.mean_dnfs_per_race


def test_safety_cars_follow_the_circuit_profile(stats):
    """Monaco, Baku e gli altri profili alti vedono piu' SC dei profili bassi."""
    high_codes = [c.code for c in CALENDAR_2026 if c.safety_car_probability >= HIGH_SC_PROBABILITY]
    low_codes = [c.code for c in CALENDAR_2026 if c.safety_car_probability <= LOW_SC_PROBABILITY]
    assert "monaco" in high_codes and "baku" in high_codes
    high_rate = sum(stats.safety_car_rate_by_circuit[c] for c in high_codes) / len(high_codes)
    low_rate = sum(stats.safety_car_rate_by_circuit[c] for c in low_codes) / len(low_codes)
    assert high_rate > low_rate, (high_rate, low_rate)


def test_rain_follows_the_circuit_profile(stats):
    wet_codes = [c.code for c in CALENDAR_2026 if c.rain_probability >= 0.40]
    dry_codes = [c.code for c in CALENDAR_2026 if c.rain_probability <= 0.10]
    wet_rate = sum(stats.rain_rate_by_circuit[c] for c in wet_codes) / len(wet_codes)
    dry_rate = sum(stats.rain_rate_by_circuit[c] for c in dry_codes) / len(dry_codes)
    assert wet_rate > dry_rate, (wet_rate, dry_rate)


def test_attributes_correlate_with_results(stats):
    assert stats.attribute_correlation > 0.3, stats.attribute_correlation


def test_team_points_spread_is_alive(stats):
    """Ne' tutto piatto (motore casuale) ne' oltre il massimo teorico."""
    theoretical_maximum = (25 + 18) * 24
    assert 100 <= stats.mean_team_points_spread <= theoretical_maximum


def test_one_or_two_stops_dominate_dry_races(stats):
    total = sum(stats.dry_stops_distribution.values())
    assert total > 0
    one_or_two = stats.dry_stops_distribution.get(1, 0) + stats.dry_stops_distribution.get(2, 0)
    assert one_or_two / total >= 0.9, stats.dry_stops_distribution


def test_compound_variety_in_use(stats):
    dry_used = {c for c in stats.compound_usage if c.startswith("c")}
    assert len(dry_used) >= 2, stats.compound_usage


def test_report_is_deterministic_end_to_end():
    first = render_report(simulate(seasons=1, seed=99))
    second = render_report(simulate(seasons=1, seed=99))
    assert first == second
    assert "Abbandoni per gara" in first
