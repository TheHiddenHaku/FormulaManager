"""Test della Telecronaca a template (FOR-16, ADR 0003).

Quattro garanzie: copertura totale dei tipi evento del motore (la
copertura non puo' regredire in silenzio), resa corretta di ogni
variante, determinismo dato il seed (golden test) e anti-ripetizione
delle varianti in righe ravvicinate.
"""

import random
from typing import get_args

import pytest

from fm_engine import events
from fm_engine.commentary import (
    REPETITION_WINDOW,
    TEMPLATES,
    CommentaryContext,
    narrate,
    render_variants,
)

# Every event type the engine can emit, taken from the unions in
# fm_engine.events: a new event type lands here automatically.
ALL_EVENT_TYPES = frozenset(get_args(events.RaceEvent)) | frozenset(
    get_args(events.QualifyingEvent)
)

CONTEXT = CommentaryContext(
    driver_names={1: "Marco Verdi", 2: "Luca Bianchi", 3: "Jules Aubert"},
    team_names={10: "Aurora Racing"},
    circuit_names={"monza": "Autodromo Nazionale di Monza"},
)


def _sample_events() -> dict[type, object]:
    """Un'istanza realistica per ogni tipo evento del motore."""
    classification = (
        events.ClassifiedResult(
            position=1,
            driver_id=1,
            team_id=10,
            total_time_seconds=5000.0,
            gap_to_winner_seconds=0.0,
            points=25,
        ),
        events.ClassifiedResult(
            position=2,
            driver_id=2,
            team_id=10,
            total_time_seconds=5004.2,
            gap_to_winner_seconds=4.2,
            points=18,
        ),
    )
    samples = [
        events.RaceStarted(lap=0, circuit_code="monza", total_laps=53),
        events.Overtake(lap=3, driver_id=1, overtaken_driver_id=2, position=4),
        events.TeamOrderSwap(
            lap=5, team_id=10, promoted_driver_id=1, demoted_driver_id=2, position=3
        ),
        events.FastestLap(lap=7, driver_id=3, time_seconds=83.456),
        events.CarFailure(lap=9, driver_id=2, component="engine"),
        events.DriverError(
            lap=10, driver_id=1, cause="cold_tyres", time_lost_seconds=2.5, in_duel=False
        ),
        events.Accident(lap=11, driver_ids=(1, 2), severity=events.AccidentSeverity.MINOR),
        events.CarDamage(lap=11, driver_id=1, amount_usd=120000),
        events.Dnf(lap=12, driver_id=2, cause=events.DnfCause.FAILURE, detail="engine"),
        events.SafetyCarDeployed(lap=12, duration_laps=3),
        events.SafetyCarEnding(lap=15),
        events.VscDeployed(lap=20, duration_laps=2),
        events.VscEnding(lap=22),
        events.RainStarted(lap=25, intensity=0.6),
        events.RainStopped(lap=30),
        events.Crossover(
            lap=26, from_category="slick", to_category="intermediate", track_wetness=0.5
        ),
        events.PitEntry(lap=27, driver_id=1),
        events.TyreChange(lap=27, driver_id=1, old_compound="c3", new_compound="intermediate"),
        events.PitExit(lap=27, driver_id=1, time_lost_seconds=21.4),
        events.BiCompoundPenalty(lap=53, driver_id=3, penalty_seconds=10.0),
        events.ChequeredFlag(lap=53, classification=classification),
        events.QualifyingTimeSet(
            segment=events.QualifyingSegment.Q1, driver_id=1, time_seconds=84.123
        ),
        events.QualifyingElimination(segment=events.QualifyingSegment.Q1, driver_id=2, position=18),
        events.PolePosition(driver_id=1, time_seconds=82.001),
    ]
    return {type(sample): sample for sample in samples}


def test_every_engine_event_type_has_templates():
    """La copertura della Telecronaca non puo' regredire in silenzio."""
    missing = sorted(t.__name__ for t in ALL_EVENT_TYPES if t not in TEMPLATES)
    assert not missing, f"tipi evento senza template di Telecronaca: {missing}"


def test_template_families_have_enough_distinct_variants():
    """Ogni famiglia ha varianti distinte e piu' della finestra anti-ripetizione."""
    for family, variants in TEMPLATES.items():
        assert len(variants) > REPETITION_WINDOW, family.__name__
        assert len(set(variants)) == len(variants), family.__name__


def test_sample_factory_covers_all_event_types():
    """Il factory dei campioni va aggiornato quando nasce un tipo evento."""
    assert set(_sample_events()) == set(ALL_EVENT_TYPES)


def test_every_variant_renders_in_italian():
    """Ogni variante formatta senza errori e senza segnaposto residui."""
    for family, sample in _sample_events().items():
        rendered = render_variants(sample, CONTEXT)
        assert len(rendered) == len(TEMPLATES[family])
        for line in rendered:
            assert line.strip(), family.__name__
            assert "{" not in line and "}" not in line, line


def test_golden_same_events_same_seed_same_text():
    """Stessa sequenza di eventi e stesso seed: testo identico."""
    event_stream = list(_sample_events().values()) * 3
    first = narrate(event_stream, CONTEXT, random.Random(1234))
    second = narrate(event_stream, CONTEXT, random.Random(1234))
    assert first == second
    assert len(first) == len(event_stream)


def test_different_seed_changes_the_text():
    """Seed diverso, scelta diversa delle varianti (sequenza lunga)."""
    event_stream = list(_sample_events().values()) * 3
    first = narrate(event_stream, CONTEXT, random.Random(1))
    other = narrate(event_stream, CONTEXT, random.Random(2))
    assert first != other


@pytest.mark.parametrize("seed", [0, 7, 99])
def test_no_variant_repeats_within_the_window(seed):
    """Una variante non riappare mai entro REPETITION_WINDOW righe.

    Eventi identici nei parametri: due righe uguali implicano la stessa
    variante, quindi basta confrontare le stringhe.
    """
    overtake = events.Overtake(lap=10, driver_id=1, overtaken_driver_id=2, position=5)
    pit_entry = events.PitEntry(lap=10, driver_id=1)
    event_stream = [overtake] * 200 + [overtake, pit_entry] * 100
    lines = narrate(event_stream, CONTEXT, random.Random(seed))
    for i, line in enumerate(lines):
        window = lines[i + 1 : i + 1 + REPETITION_WINDOW]
        assert line not in window, f"variante ripetuta entro {REPETITION_WINDOW} righe da {i}"


def test_unknown_event_type_raises():
    """Un evento senza template e' un errore esplicito, non una riga muta."""
    with pytest.raises(ValueError, match="Telecronaca"):
        narrate([object()], CONTEXT, random.Random(0))


def test_unknown_ids_fall_back_to_neutral_names():
    """Id sconosciuti non rompono la cronaca: ripieghi neutri."""
    empty_context = CommentaryContext(driver_names={})
    overtake = events.Overtake(lap=1, driver_id=7, overtaken_driver_id=8, position=2)
    (line,) = narrate([overtake], empty_context, random.Random(0))
    assert "il pilota 7" in line and "il pilota 8" in line
