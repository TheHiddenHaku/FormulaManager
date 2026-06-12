"""Statistica degli Abbandoni: range realistico e sfortuna onesta (FOR-11)."""

from fm_engine.circuits import CALENDAR_2026
from fm_engine.events import Dnf
from fm_engine.race import start_race, step


def _dnf_counts(entries, races: int) -> list[int]:
    counts = []
    for seed in range(races):
        circuit = CALENDAR_2026[seed % len(CALENDAR_2026)]
        state, _ = start_race(entries, circuit, seed=seed)
        dnfs = 0
        while not state.finished:
            state, events = step(state)
            dnfs += sum(1 for event in events if isinstance(event, Dnf))
        counts.append(dnfs)
    return counts


def test_average_dnf_per_race_in_realistic_range(entry_factory):
    """Su 1000 gare la media degli Abbandoni cade in 3-5 (deliverable)."""
    counts = _dnf_counts(entry_factory(), races=1000)
    average = sum(counts) / len(counts)
    assert 3.0 <= average <= 5.0, f"media Abbandoni {average:.2f} fuori dal range 3-5"


def test_no_hidden_anti_streak_corrector(entry_factory):
    """Sfortuna onesta: il conteggio DNF di una gara non dipende dalla precedente.

    Correlazione lag-1 tra gare consecutive vicina a zero: nessun
    correttivo nascosto che compensa le strisce di sfortuna.
    """
    counts = _dnf_counts(entry_factory(), races=400)
    first, second = counts[:-1], counts[1:]
    n = len(first)
    mean_first = sum(first) / n
    mean_second = sum(second) / n
    covariance = (
        sum((a - mean_first) * (b - mean_second) for a, b in zip(first, second, strict=True)) / n
    )
    variance_first = sum((a - mean_first) ** 2 for a in first) / n
    variance_second = sum((b - mean_second) ** 2 for b in second) / n
    correlation = covariance / (variance_first**0.5 * variance_second**0.5)
    assert abs(correlation) < 0.12, f"correlazione lag-1 sospetta: {correlation:.3f}"
