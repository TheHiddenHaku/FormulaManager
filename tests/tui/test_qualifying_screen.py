"""Test Pilot della schermata Qualifiche: evidenziazione dei piloti del giocatore.

Colorazione pilota: nei risultati delle Qualifiche (e nella griglia) i
piloti della scuderia del giocatore sono evidenziati coi colori squadra,
come gia' avviene in classifica e in gara. Database SQLite temporaneo
via db_env.
"""

from dataclasses import replace

from rich.text import Text
from textual.widgets import DataTable

from fm_engine.circuits import CALENDAR_2026
from fm_engine.world import PlayerSlot, generate
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_engine.world.team_setup import TeamSetupChoices, apply_team_setup
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import QualifyingScreen
from fm_tui.screens.race import race_entries

SEED = 23
CIRCUIT_SEED = 99
TEST_SIZE = (120, 50)


def _ready_world():
    """Un Mondo col Setup squadra completato e i colori di livrea scelti."""
    slot = PlayerSlot(name="Scuderia X", primary_color="#ff2800", secondary_color="bianco")
    world = replace(generate(SEED), player_slot=slot)
    free_agents = tuple(driver.id for driver in world.drivers_without_contract)
    choices = TeamSetupChoices(
        driver_ids=free_agents[:2],
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    return apply_team_setup(world, choices)


async def test_player_drivers_highlighted_in_qualifying_and_grid(db_env):
    world = _ready_world()
    entries = race_entries(world)
    driver_names = {driver.id: driver.name for driver in world.drivers}
    player_ids = {contract.driver_id for contract in world.contracts_of(PLAYER_TEAM_ID)}

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        screen = QualifyingScreen(
            entries=entries,
            driver_names=driver_names,
            circuit=CALENDAR_2026[0],
            seed=CIRCUIT_SEED,
            player_color="#ff2800",
        )
        app.push_screen(screen)
        await pilot.pause()

        # Q1 lists all 22 cars: the two player drivers are highlighted.
        table = screen.query_one("#segment-table", DataTable)
        segment = screen.result.segments[0]
        highlighted = 0
        for index in range(table.row_count):
            driver_id = segment.rows[index].driver_id
            name_cell = table.get_row_at(index)[1]
            if driver_id in player_ids:
                assert isinstance(name_cell, Text)
                assert name_cell.style.color is not None
                assert name_cell.style.color.name == "#ff2800"
                highlighted += 1
            else:
                assert isinstance(name_cell, str)
        assert highlighted == 2

        # The starting grid view highlights the player rows too.
        for _ in range(3):
            await pilot.press("space")
        assert screen.all_revealed
        grid_ids = [entry.driver.id for entry in screen.result.grid]
        for index in range(table.row_count):
            name_cell = table.get_row_at(index)[1]
            if grid_ids[index] in player_ids:
                assert isinstance(name_cell, Text)
                assert name_cell.style.color.name == "#ff2800"
