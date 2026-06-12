"""Test Pilot della schermata gara (FOR-17).

Una gara breve (circuito reale accorciato a pochi giri) viene guardata
dal via alla bandiera a scacchi: cambio velocita', pausa/riprendi e
skip-to-event non bloccano mai la UI, la Telecronaca scorre nel RichLog
e il monitor tempi mostra l'ordine d'arrivo finale. Il flusso di avvio
parte dalla schermata griglia con una Carriera a Setup squadra
completato.

La fixture db_env serve solo alla CareerList montata sotto: la gara in
se' non tocca mai il database (ADR 0001).
"""

import asyncio
from dataclasses import replace

import pytest
from textual.widgets import DataTable, RichLog

from fm_engine.balance.simulate import build_grid
from fm_engine.career import Career
from fm_engine.circuits import circuit_by_code
from fm_engine.race import start_race
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import Grid, RaceScreen
from fm_tui.screens.race import commentary_context, race_entries

SEED = 11
SHORT_RACE_LAPS = 4
# Generous ceiling for the waiting loops: a 4-lap race at 4x or in skip
# mode finishes well within it.
WAIT_TIMEOUT_SECONDS = 30.0


def short_race(laps: int = SHORT_RACE_LAPS) -> RaceScreen:
    """Una RaceScreen pronta su una gara accorciata a pochi giri."""
    world = generate(SEED)
    entries = build_grid(SEED)
    circuit = replace(circuit_by_code("monza"), race_laps=laps)
    state, events = start_race(entries, circuit, seed=SEED)
    return RaceScreen(state=state, initial_events=events, context=commentary_context(world))


async def wait_for_finish(pilot, screen: RaceScreen) -> None:
    """Attende la bandiera a scacchi tenendo vivo l'event loop di Textual.

    Se lo skip si ferma su un Evento chiave intermedio, lo rilancia: il
    test vuole arrivare in fondo alla gara.
    """
    deadline = asyncio.get_running_loop().time() + WAIT_TIMEOUT_SECONDS
    while not screen.race_finished:
        if asyncio.get_running_loop().time() > deadline:
            pytest.fail("la gara non e' arrivata alla bandiera a scacchi in tempo")
        if screen.is_paused:
            await pilot.press("s")
        await pilot.pause(0.05)


@pytest.fixture
def ready_career() -> Career:
    """Una Carriera con Setup squadra completato: 22 vetture schierabili."""
    world = generate(SEED)
    world = replace(
        world,
        player_slot=PlayerSlot(name="Scuderia X Racing", primary_color="#ff2800"),
    )
    free_agents = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free_agents[0].id, free_agents[1].id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    return Career(name="Scuderia X", world=apply_team_setup(world, choices))


# ---------------------------------------------------------------------------
# Race entries: the grid of a set-up Career
# ---------------------------------------------------------------------------


def test_race_entries_full_grid(ready_career):
    entries = race_entries(ready_career.world)
    assert len(entries) == 22
    player_entries = [entry for entry in entries if entry.team_id == 0]
    assert len(player_entries) == 2
    # No duplicated drivers across the whole grid.
    driver_ids = [entry.driver.id for entry in entries]
    assert len(set(driver_ids)) == len(driver_ids)


def test_race_entries_require_team_setup():
    world = generate(SEED)
    with pytest.raises(ValueError):
        race_entries(world)


# ---------------------------------------------------------------------------
# Race screen (Pilot): controls and chequered flag
# ---------------------------------------------------------------------------


async def test_race_controls_and_chequered_flag(db_env):
    """Velocita', pausa e ripresa, poi la gara si chiude con la bandiera."""
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(short_race())
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, RaceScreen)
        assert screen.NAME == "race"

        # The live monitor shows the whole field from lap zero.
        table = screen.query_one("#monitor", DataTable)
        assert table.row_count == 22
        labels = [str(column.label) for column in table.columns.values()]
        assert labels == ["Pos", "Pilota", "Distacco", "Mescola", "Eta' gomme"]
        first_row = table.get_row_at(0)
        assert first_row[0] == "1"
        assert first_row[2] == "-"

        # The commentary opens with the race start line.
        log = screen.query_one("#commentary", RichLog)
        assert len(log.lines) >= 1

        # Speed changes: 2x then 4x, no freeze.
        await pilot.press("2")
        assert screen.speed_multiplier == 2
        await pilot.press("4")
        assert screen.speed_multiplier == 4

        # Pause: the simulation freezes, the table stays browsable.
        await pilot.press("space")
        assert screen.is_paused
        lap_when_paused = screen.current_lap
        await pilot.pause(0.5)
        assert screen.current_lap == lap_when_paused
        assert table.row_count == 22

        # Resume at 4x and watch the race to the chequered flag.
        await pilot.press("space")
        assert not screen.is_paused
        await wait_for_finish(pilot, screen)

        # The finishing order is on screen: position 1 with leader gap.
        await pilot.pause()
        final_first = table.get_row_at(0)
        assert final_first[0] == "1"
        assert final_first[2] == "-"
        positions = [table.get_row_at(index)[0] for index in range(table.row_count)]
        classified = [position for position in positions if position != "-"]
        assert classified == [str(n) for n in range(1, len(classified) + 1)]
        # The commentary announced the lights out and then the winner.
        assert len(log.lines) > 1


async def test_race_skip_to_event_reaches_the_flag(db_env):
    """Lo skip-to-event macina i Tick senza ritardi fino alla bandiera."""
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(short_race(laps=6))
        await pilot.pause()
        screen = app.screen

        await pilot.press("s")
        assert screen.is_skipping or screen.race_finished or screen.is_paused
        await wait_for_finish(pilot, screen)

        assert screen.race_finished
        table = screen.query_one("#monitor", DataTable)
        assert table.get_row_at(0)[0] == "1"


# ---------------------------------------------------------------------------
# Start flow: from the grid screen into the race
# ---------------------------------------------------------------------------


async def test_grid_starts_the_race(db_env, ready_career):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(Grid(ready_career))
        await pilot.pause()

        await pilot.press("g")
        await pilot.pause()
        assert isinstance(app.screen, RaceScreen)
        assert app.screen.NAME == "race"
        table = app.screen.query_one("#monitor", DataTable)
        assert table.row_count == 22

        # Escape leaves the race and lands back on the grid.
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, Grid)


async def test_grid_blocks_the_race_without_team_setup(db_env):
    """Senza Setup squadra la gara non parte: avviso e nessun cambio schermata."""
    world = replace(generate(SEED), player_slot=PlayerSlot(name="Scuderia X Racing"))
    career = Career(name="Scuderia X", world=world)
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()

        await pilot.press("g")
        await pilot.pause()
        assert isinstance(app.screen, Grid)
