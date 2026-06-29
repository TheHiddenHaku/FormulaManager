"""Calendario e orologio di stagione (T5.1.1).

Il Calendario 2026 si replica ogni anno con il solo anno che avanza; il
tempo avanza a giorni di Calendario arrivando esattamente al GP
successivo, saltando i GP Sprint (post-MVP); a fine stagione l'anno
avanza con le classifiche azzerate.
"""

from datetime import date

import pytest

from fm_engine.circuits import circuit_by_code
from fm_engine.events import ClassifiedResult
from fm_engine.season import (
    SeasonState,
    advance_to_next_grand_prix,
    advance_to_next_season,
    days_until_next_grand_prix,
    next_grand_prix,
    record_race,
    season_calendar,
    season_completed,
)


def _classification(circuit_code: str) -> tuple[ClassifiedResult, ...]:
    """Una classifica minima a 2 vetture, sufficiente a registrare un GP."""
    return (
        ClassifiedResult(
            position=1,
            driver_id=1,
            team_id=0,
            total_time_seconds=5400.0,
            gap_to_winner_seconds=0.0,
            points=25,
        ),
        ClassifiedResult(
            position=2,
            driver_id=2,
            team_id=1,
            total_time_seconds=5410.0,
            gap_to_winner_seconds=10.0,
            points=18,
        ),
    )


def test_season_calendar_has_24_rounds_in_order():
    calendar = season_calendar(2026)
    assert len(calendar) == 24
    assert [entry.round for entry in calendar] == list(range(1, 25))
    assert calendar[0].circuit.code == "albert_park"
    assert calendar[0].race_date == date(2026, 3, 8)
    assert calendar[-1].circuit.code == "yas_marina"


def test_calendar_repeats_with_the_year_shifted():
    calendar_2027 = season_calendar(2027)
    assert calendar_2027[0].race_date == date(2027, 3, 8)
    assert calendar_2027[-1].race_date == date(2027, 12, 6)
    # Stessi circuiti, stesso ordine: cambia solo l'anno della data.
    assert [entry.circuit.code for entry in calendar_2027] == [
        entry.circuit.code for entry in season_calendar(2026)
    ]


def test_next_grand_prix_starts_at_round_one():
    season = SeasonState()
    upcoming = next_grand_prix(season)
    assert upcoming is not None
    assert upcoming.round == 1
    assert upcoming.circuit.code == "albert_park"


def test_advance_lands_exactly_on_the_next_grand_prix():
    season = SeasonState()
    # Default game date is 1 January 2026: 66 days to the opener.
    assert days_until_next_grand_prix(season) == (date(2026, 3, 8) - date(2026, 1, 1)).days
    advanced = advance_to_next_grand_prix(season)
    assert advanced.game_date == date(2026, 3, 8)
    assert days_until_next_grand_prix(advanced) == 0


def test_recording_a_race_moves_to_the_next_grand_prix_including_sprints():
    season = SeasonState()
    albert_park = circuit_by_code("albert_park")
    season = record_race(season, albert_park, _classification("albert_park"))
    assert season.completed_rounds == frozenset({1})
    assert season.game_date == date(2026, 3, 8)
    # Round 2 (Shanghai) is a sprint, now playable: it is the next GP.
    upcoming = next_grand_prix(season)
    assert upcoming is not None
    assert upcoming.round == 2
    assert upcoming.circuit.code == "shanghai"


def test_recording_the_same_round_twice_is_rejected():
    albert_park = circuit_by_code("albert_park")
    season = record_race(SeasonState(), albert_park, _classification("albert_park"))
    with pytest.raises(ValueError, match="already recorded"):
        record_race(season, albert_park, _classification("albert_park"))


def test_full_season_completes_then_year_advances():
    season = SeasonState()
    for entry in season_calendar(2026):
        season = record_race(season, entry.circuit, _classification(entry.circuit.code))
    assert season_completed(season)
    assert next_grand_prix(season) is None
    with pytest.raises(ValueError, match="season finished"):
        advance_to_next_grand_prix(season)
    new_season = advance_to_next_season(season)
    assert new_season.year == 2027
    assert new_season.results == ()
    assert new_season.game_date == date(2027, 1, 1)
    assert next_grand_prix(new_season).round == 1
