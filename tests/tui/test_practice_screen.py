"""Test Pilot della schermata prove libere (FOR-20).

Flusso assegna Programma -> sessione -> report: scheda circuito con
Mescole nominate e previsione meteo, slot Programma per pilota, lancio
con conferma per i Programmi mancanti (default segnalato nel report),
report di fine sessione e Classifica tempi esatta; gli effetti si
cumulano tra FP1 e FP2. Database effimero Docker via db_env, mai matilde.
"""

from dataclasses import replace

import pytest
from textual.widgets import DataTable, Select, Static

from fm_engine.circuits import CALENDAR_2026
from fm_engine.world import PlayerSlot, generate
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_engine.world.team_setup import TeamSetupChoices, apply_team_setup
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import Grid, PracticeScreen
from fm_tui.screens.practice import DefaultProgrammeConfirmation

SEED = 23
CIRCUIT_SEED = 99


@pytest.fixture
def ready_world():
    """Un Mondo col Setup squadra completato: pronto a scendere in pista."""
    slot = PlayerSlot(name="Scuderia X Racing", primary_color="#ff2800", secondary_color="bianco")
    world = replace(generate(SEED), player_slot=slot)
    free_agents = tuple(driver.id for driver in world.drivers_without_contract)
    choices = TeamSetupChoices(
        driver_ids=free_agents[:2],
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    return apply_team_setup(world, choices)


def _practice_screen(world):
    return PracticeScreen(world=world, circuit=CALENDAR_2026[0], seed=CIRCUIT_SEED)


def _player_driver_ids(world):
    return tuple(contract.driver_id for contract in world.contracts_of(PLAYER_TEAM_ID))


async def test_practice_screen_shows_the_circuit_card(db_env, ready_world):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(_practice_screen(ready_world))
        await pilot.pause()

        assert app.screen.name == "practice"
        card = str(app.screen.query_one("#circuit-card", Static).render())
        assert "Albert Park" in card
        # Nominated compounds with their relative role.
        for label in ("Soft", "Medium", "Hard"):
            assert label in card
        # Weekend weather forecast and track characteristics.
        assert "pioggia" in card
        assert "Severita' gomme" in card
        # One programme slot per player driver.
        selects = app.screen.query(Select)
        assert len(selects) == len(_player_driver_ids(ready_world))


async def test_assign_programmes_launch_and_read_the_report(db_env, ready_world):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = _practice_screen(ready_world)
        app.push_screen(screen)
        await pilot.pause()

        first, second = _player_driver_ids(ready_world)
        screen.query_one(f"#programme-{first}", Select).value = "setup"
        screen.query_one(f"#programme-{second}", Select).value = "tyres"
        await pilot.press("l")
        await pilot.pause()

        # FP1 done, no confirmation needed: every driver had a programme.
        assert screen.sessions_completed == 1
        report = str(screen.query_one("#session-report", Static).render())
        assert "Report FP1" in report
        assert "Setup al" in report
        assert "Curve di Degrado rivelate" in report
        assert "(default)" not in report

        # The exact timesheet covers all 22 cars.
        table = screen.query_one("#timesheet", DataTable)
        assert table.row_count == 22
        assert table.get_row_at(0)[0] == "1"

        # FP2 with new programmes: the effects accumulate in the weekend.
        setup_after_fp1 = screen.effects.for_driver(first).setup_percentage
        screen.query_one(f"#programme-{second}", Select).value = "qualifying_focus"
        await pilot.press("l")
        await pilot.pause()
        assert screen.sessions_completed == 2
        assert screen.effects.for_driver(first).setup_percentage > setup_after_fp1
        assert screen.effects.for_driver(second).qualifying_bonus_seconds > 0.0
        report = str(screen.query_one("#session-report", Static).render())
        assert "Report FP2" in report


async def test_launch_without_programme_asks_confirmation_and_flags_default(db_env, ready_world):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = _practice_screen(ready_world)
        app.push_screen(screen)
        await pilot.pause()

        # No programme assigned: the launch asks for confirmation.
        await pilot.press("l")
        await pilot.pause()
        assert isinstance(app.screen, DefaultProgrammeConfirmation)
        assert screen.sessions_completed == 0

        # Confirm: the session runs with the default programme, flagged.
        await pilot.press("s")
        await pilot.pause()
        assert screen.sessions_completed == 1
        report = str(screen.query_one("#session-report", Static).render())
        assert "(default)" in report
        assert all(item.defaulted for item in screen.last_result.reports)


async def test_cancelling_the_confirmation_does_not_launch(db_env, ready_world):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = _practice_screen(ready_world)
        app.push_screen(screen)
        await pilot.pause()

        await pilot.press("l")
        await pilot.pause()
        assert isinstance(app.screen, DefaultProgrammeConfirmation)
        await pilot.press("n")
        await pilot.pause()
        assert screen.sessions_completed == 0


async def test_weekend_has_exactly_three_practice_sessions(db_env, ready_world):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = _practice_screen(ready_world)
        app.push_screen(screen)
        await pilot.pause()

        first, second = _player_driver_ids(ready_world)
        for _ in range(3):
            screen.query_one(f"#programme-{first}", Select).value = "setup"
            screen.query_one(f"#programme-{second}", Select).value = "race_pace"
            await pilot.press("l")
            await pilot.pause()
        assert screen.sessions_over is True
        # A fourth launch does nothing: the weekend has 3 free practices.
        await pilot.press("l")
        await pilot.pause()
        assert screen.sessions_completed == 3


def test_practice_screen_registered_with_a_stable_name():
    assert PracticeScreen.NAME == "practice"


def test_grid_binds_the_practice_screen():
    keys = {binding.key for binding in Grid.BINDINGS}
    assert "p" in keys
