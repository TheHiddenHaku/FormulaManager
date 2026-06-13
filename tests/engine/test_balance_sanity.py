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


def test_undercut_window_frequency_in_sane_range(stats):
    """Monitoraggio anti-spam (FOR-40): finestre di undercut su tutta la griglia.

    Range largo: deve restare vivo (mai zero) ma lontano dalla raffica per
    giro del playtest. Caso di un cooldown o di una convenienza saltati.
    """
    assert 10.0 <= stats.mean_undercut_windows_per_race <= 90.0, (
        stats.mean_undercut_windows_per_race
    )


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


def test_overtakes_follow_the_overtaking_difficulty(stats):
    """Sorpassi medi: Monaco molto sotto la media del Calendario, Monza sopra."""
    by_circuit = stats.mean_overtakes_by_circuit
    mean = sum(by_circuit.values()) / len(by_circuit)
    assert by_circuit["monaco"] < 0.5 * mean, (by_circuit["monaco"], mean)
    assert by_circuit["monza"] > mean, (by_circuit["monza"], mean)


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


def test_every_ai_team_spends_but_none_lives_at_the_cap(result, stats):
    """Spesa AI viva e plausibile: mai a zero, mai costantemente al Cap."""
    from fm_engine.economy import SEASON_CAP_USD

    assert len(stats.ai_total_spent_by_team) == 10
    for team_id, total in stats.ai_total_spent_by_team.items():
        assert total > 0, f"squadra {team_id} a spesa zero"
        per_season = total / result.seasons
        assert per_season < 0.9 * SEASON_CAP_USD, f"squadra {team_id} sempre al Cap"


def test_ai_spending_is_differentiated_and_projects_complete(result, stats):
    """Le personalita' producono spese diverse e i Progetti si chiudono."""
    totals = sorted(stats.ai_total_spent_by_team.values())
    assert totals[0] < totals[-1], "tutte le AI spendono uguale"
    assert stats.ai_completed_projects > 0
    # Nessuno Sforamento: i Progetti passano da spend(), che rifiuta oltre il Cap.
    assert stats.ai_overspend_seasons == 0
    assert sum(stats.ai_spend_by_attribute.values()) == sum(totals)


def test_ai_spending_appears_in_the_report(result):
    report = render_report(result)
    assert "Spesa AI per squadra" in report
    assert "Progetti AI completati" in report
