"""Test della schermata griglia e dei widget di resa (Stime, bandiere).

La griglia mostra 11 squadre e 22 piloti con gli attributi SOLO come
Stime (intervalli) e le bandiere di nazionalita'; il Potenziale e i
valori esatti non compaiono mai. La squadra del giocatore e' onesta:
slot piloti vuoti e nessun motore prima del wizard T1.3.2.
"""

import re
from dataclasses import replace

import psycopg
import pytest
from textual.widgets import DataTable, Static

from fm_engine.career import Career
from fm_engine.world import PlayerSlot, generate
from fm_persistence import save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import Grid
from fm_tui.widgets.estimates import format_estimate
from fm_tui.widgets.flags import FLAG_PLACEHOLDER, flag

SEED = 23

INTERVAL = re.compile(r"^\d+-\d+$")


# ---------------------------------------------------------------------------
# Estimates widget: intervals, never exact values
# ---------------------------------------------------------------------------


def test_format_estimate_band_of_ten():
    assert format_estimate(63) == "60-70"
    assert format_estimate(60) == "60-70"
    assert format_estimate(0) == "0-10"
    assert format_estimate(95) == "90-100"
    assert format_estimate(100) == "90-100"


def test_format_estimate_always_contains_the_true_value():
    for value in range(101):
        lower, upper = format_estimate(value).split("-")
        assert int(lower) <= value <= int(upper)


def test_format_estimate_rejects_out_of_scale_values():
    with pytest.raises(ValueError):
        format_estimate(-1)
    with pytest.raises(ValueError):
        format_estimate(101)


# ---------------------------------------------------------------------------
# Flags widget: emoji from ISO code plus letter code
# ---------------------------------------------------------------------------


def test_flag_emoji_and_code():
    assert flag("it") == "\U0001f1ee\U0001f1f9 IT"
    assert flag("gb") == "\U0001f1ec\U0001f1e7 GB"


def test_flag_missing_or_malformed_code():
    assert flag("") == FLAG_PLACEHOLDER
    assert flag("xyz") == FLAG_PLACEHOLDER
    assert flag("1!") == FLAG_PLACEHOLDER


# ---------------------------------------------------------------------------
# Grid screen (Pilot, ephemeral database)
# ---------------------------------------------------------------------------


@pytest.fixture
def saved_career(db_env):
    """Una Carriera completa salvata e ricaricabile dal database effimero."""
    slot = PlayerSlot(name="Scuderia X Racing", primary_color="#ff2800", secondary_color="bianco")
    world = replace(generate(SEED), player_slot=slot)
    with psycopg.connect(db_env) as connection:
        return save_career(connection, Career(name="Scuderia X", world=world))


async def test_grid_header_shows_the_in_game_date(saved_career):
    """La data di gioco e' sempre visibile nella barra in alto (data-sempre-visibile)."""
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()
        header = str(app.screen.query_one("#grid-header", Static).render())
        # The in-game date of a fresh Career: 1 January 2026 (not the real date).
        assert "Data: 01/01/2026" in header


async def test_grid_eleven_teams_as_estimates(saved_career):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()

        table = app.screen.query_one("#teams-table", DataTable)
        assert table.row_count == 11

        rows = [table.get_row_at(index) for index in range(table.row_count)]
        # Player slot: chosen identity, engine and attributes empty.
        player_row = rows[0]
        assert player_row[0] == "Scuderia X Racing (tu)"
        assert all(cell == "-" for cell in player_row[1:])
        # AI teams: every car attribute rendered as an interval.
        for row in rows[1:]:
            for cell in row[3:]:
                assert INTERVAL.match(cell), f"attributo non a Stima: {cell}"


async def test_grid_twentytwo_drivers_with_estimates_and_flags(saved_career):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()

        table = app.screen.query_one("#drivers-table", DataTable)
        rows = [table.get_row_at(index) for index in range(table.row_count)]

        empty_slots = [row for row in rows if row[0] == "(slot vuoto)"]
        drivers = [row for row in rows if row[0] != "(slot vuoto)"]
        assert len(drivers) == 22
        # The player driver slots are honestly empty.
        assert len(empty_slots) == 2
        assert all(row[3] == "Scuderia X Racing (tu)" for row in empty_slots)

        for row in drivers:
            # Flag: emoji (Regional Indicator) plus letter code.
            assert re.match(r"^[\U0001f1e6-\U0001f1ff]{2} [A-Z]{2}$", row[1])
            # The 6 driver attributes are intervals, never exact values.
            for cell in row[4:]:
                assert INTERVAL.match(cell), f"attributo non a Stima: {cell}"

        # The 2 free agents of the roster are declared as such.
        assert sum(1 for row in drivers if row[3] == "senza Contratto") == 2


async def test_grid_never_shows_the_potential(saved_career):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()

        table = app.screen.query_one("#drivers-table", DataTable)
        labels = [str(column.label) for column in table.columns.values()]
        assert all("otenziale" not in label for label in labels)
        assert all("otential" not in label for label in labels)
