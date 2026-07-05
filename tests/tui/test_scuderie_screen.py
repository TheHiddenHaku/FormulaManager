"""Test Pilot della visuale Scuderie (visuale-scuderie).

La visuale elenca tutte le squadre in ordine di classifica e, selezionando una
riga, mostra il dettaglio della scuderia: piloti con stipendio, Attributi
vettura a Stime, Cassa, e gli Sviluppi (i Progetti del giocatore; per le
avversarie non disponibili). Database SQLite temporaneo via db_env.
"""

from dataclasses import replace

import pytest
from textual.widgets import DataTable, Static

from fm_engine.career import Career
from fm_engine.world import PlayerSlot, generate
from fm_engine.world.team_setup import TeamSetupChoices, apply_team_setup
from fm_persistence import connect, save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import Grid
from fm_tui.screens.scuderie import ScuderieScreen

SEED = 23
TEST_SIZE = (120, 50)


@pytest.fixture
def ready_career(db_env):
    """Una Carriera col Setup squadra completato, salvata sul database effimero."""
    slot = PlayerSlot(name="Scuderia X", primary_color="#ff2800", secondary_color="bianco")
    world = replace(generate(SEED), player_slot=slot)
    free_agents = tuple(driver.id for driver in world.drivers_without_contract)
    choices = TeamSetupChoices(
        driver_ids=free_agents[:2],
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    career = Career(name="Scuderia X", world=apply_team_setup(world, choices))
    with connect() as connection:
        return save_career(connection, career)


async def test_scuderie_opens_from_grid_and_lists_all_teams(ready_career):
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(ready_career))
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, ScuderieScreen)
        table = screen.query_one("#scuderie-table", DataTable)
        # Eleven teams: the player plus the ten AI teams.
        assert table.row_count == 11
        # The detail opens on the player team (id 0, top at zero points).
        detail = str(screen.query_one("#scuderie-detail", Static).render())
        assert "(tu)" in detail
        assert "Piloti:" in detail
        assert "Valori auto (Stime):" in detail
        assert "Sviluppi: nessuno in corso." in detail


async def test_scuderie_detail_switches_to_the_selected_ai_team(ready_career):
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        screen = ScuderieScreen(ready_career)
        app.push_screen(screen)
        await pilot.pause()

        table = screen.query_one("#scuderie-table", DataTable)
        # Select the last row (an AI team, since the player opens first).
        table.move_cursor(row=table.row_count - 1)
        await pilot.pause()
        detail = str(screen.query_one("#scuderie-detail", Static).render())
        # AI teams: developments are not tracked, the car values are estimates.
        assert "Sviluppi: non disponibili" in detail
        assert "Valori auto (Stime):" in detail
        assert "(tu)" not in detail
