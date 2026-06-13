"""Test Pilot della fase Test pre-season (T5.1.2).

A inizio stagione, prima del primo GP, la griglia apre da sola i Test
pre-season: si assegnano i Programmi, si svolgono i giorni leggendo la
Classifica tempi, e a fine fase si apre il report. I Programmi di
Conoscenza stringono le Stime sui propri piloti; 0 giorni di Conoscenza
lasciano un avviso esplicito nel report.
"""

from dataclasses import replace
from datetime import date

import pytest
from textual.widgets import DataTable, Select

from fm_engine.career import Career
from fm_engine.economy import DEFAULT_PLAYER_PRESTIGE, TeamLedger, credit_annual_sponsor
from fm_engine.info import driver_subject
from fm_engine.preseason import PRESEASON_DAYS
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_persistence import connect, load_career, save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import Grid, PreseasonReportScreen, PreseasonScreen

SEED = 11
TEST_SIZE = (120, 50)


@pytest.fixture
def saved_career(db_env):
    """Una Carriera a Setup squadra completato, gia' salvata su database."""
    world = replace(
        generate(SEED), player_slot=PlayerSlot(name="Scuderia X", primary_color="#ff2800")
    )
    free = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free[0].id, free[1].id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    ledger = credit_annual_sponsor(TeamLedger(), DEFAULT_PLAYER_PRESTIGE, date(2026, 1, 1))
    career = Career(name="Scuderia X", world=apply_team_setup(world, choices), ledger=ledger)
    with connect() as connection:
        return save_career(connection, career)


def player_driver_ids(career: Career) -> tuple[int, ...]:
    return tuple(contract.driver_id for contract in career.world.contracts_of(PLAYER_TEAM_ID))


def _set_programmes(screen: PreseasonScreen, driver_ids, value: str) -> None:
    for driver_id in driver_ids:
        screen.query_one(f"#programme-{driver_id}", Select).value = value


async def test_preseason_opens_from_grid_and_knowledge_tightens(db_env, saved_career):
    drivers = player_driver_ids(saved_career)
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()

        # g on the grid opens the pre-season automatically (before the first GP).
        await pilot.press("g")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, PreseasonScreen)

        # Run every day with the Knowledge programme (the Select default).
        for _ in range(PRESEASON_DAYS):
            assert isinstance(app.screen, PreseasonScreen)
            _set_programmes(app.screen, drivers, "knowledge")
            await pilot.press("g")
            await pilot.pause()
            timesheet = screen.query_one("#timesheet", DataTable)
            assert timesheet.row_count == 22

        # The phase ends on the report screen, with no zero-knowledge warning.
        report = app.screen
        assert isinstance(report, PreseasonReportScreen)
        assert len(report.query("#report-warning")) == 0
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, Grid)

        # Persisted: the phase is complete and the own drivers are better known.
        with connect() as connection:
            loaded = load_career(connection, saved_career.id)
        assert loaded.preseason.completed
        assert loaded.preseason.knowledge_days == PRESEASON_DAYS
        for driver_id in drivers:
            assert loaded.knowledge.level_for(driver_subject(driver_id)) >= 1


async def test_zero_knowledge_days_warns_in_the_report(db_env, saved_career):
    drivers = player_driver_ids(saved_career)
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
        assert isinstance(app.screen, PreseasonScreen)
        for _ in range(PRESEASON_DAYS):
            _set_programmes(app.screen, drivers, "development")
            await pilot.press("g")
            await pilot.pause()
        report = app.screen
        assert isinstance(report, PreseasonReportScreen)
        assert len(report.query("#report-warning")) == 1
        with connect() as connection:
            loaded = load_career(connection, saved_career.id)
        assert loaded.preseason.knowledge_days == 0
        for driver_id in drivers:
            assert loaded.knowledge.level_for(driver_subject(driver_id)) == 0
