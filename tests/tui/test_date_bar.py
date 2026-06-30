"""Test del widget DateBar: data di gioco e conto alla rovescia al prossimo GP.

Resa pura: si verifica il testo prodotto da _text nei casi chiave (inizio
stagione, dopo un GP disputato, stagione conclusa) senza montare la TUI ne'
toccare il database.
"""

from fm_engine.circuits import CALENDAR_2026
from fm_engine.season import (
    SeasonState,
    next_grand_prix,
    record_race,
    season_calendar,
)
from fm_tui.widgets.date_bar import DateBar


def test_start_of_season_shows_date_and_countdown_to_first_gp():
    text = DateBar(SeasonState())._text()
    assert "Data: 01/01/2026" in text
    first = season_calendar(2026)[0]
    assert f"Prossimo GP: {first.circuit.name}" in text
    # Conto alla rovescia in giorni: la pausa fino al via e' leggibile.
    assert "tra" in text and "giorni" in text


def test_after_a_race_the_date_advances_and_points_to_the_next_gp():
    season = record_race(SeasonState(), CALENDAR_2026[0], ())
    text = DateBar(season)._text()
    expected = season.game_date.strftime("%d/%m/%Y")
    assert f"Data: {expected}" in text
    assert "Data: 01/01/2026" not in text
    upcoming = next_grand_prix(season)
    assert f"Prossimo GP: {upcoming.circuit.name}" in text


def test_season_over_shows_no_next_gp():
    season = SeasonState()
    for entry in season_calendar(2026):
        season = record_race(season, entry.circuit, ())
    text = DateBar(season)._text()
    assert "Stagione conclusa" in text
