"""Test Pilot della schermata Mercato piloti (T5.2.1, sub-issue M5).

Verificano il guscio TUI sopra fm_engine.market: il pool reso a Stime
(mai valori esatti), l'apertura dal grid, la controfferta accettata e
persistita ai Checkpoint, e i due motivi di rifiuto strutturati (Cassa
insufficiente e offerta rivale piu' alta). I valori attesi sono
deterministici dal SEED: con SEED 42 e anno concluso 2026 il pool ha 9
piloti e il primo (driver 13) ha un'offerta rivale da battere.
"""

import re
from dataclasses import replace
from datetime import date

import pytest
from textual.widgets import DataTable, Input, Static

from fm_engine.career import Career
from fm_engine.economy import DEFAULT_PLAYER_PRESTIGE, TeamLedger, credit_annual_sponsor
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_persistence import connect, load_career, save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import Grid, MarketScreen

SEED = 42
TEST_SIZE = (140, 50)
# Pool table column layout: the 6 driver attributes sit in columns 6-11.
_ATTRIBUTE_COLUMNS = slice(6, 12)
_INTERVAL = re.compile(r"^\d+-\d+$")


def _build_career(ledger: TeamLedger) -> Career:
    """Una Carriera a Setup squadra completato, con il registro dato."""
    world = replace(
        generate(SEED), player_slot=PlayerSlot(name="Scuderia X", primary_color="#ff2800")
    )
    free = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free[0].id, free[1].id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    return Career(name="Scuderia X", world=apply_team_setup(world, choices), ledger=ledger)


@pytest.fixture
def funded_career(db_env):
    """Carriera con la Cassa dello Sponsor annuale (Prestigio di partenza)."""
    ledger = credit_annual_sponsor(TeamLedger(), DEFAULT_PLAYER_PRESTIGE, date(2026, 1, 1))
    with connect() as connection:
        return save_career(connection, _build_career(ledger))


@pytest.fixture
def broke_career(db_env):
    """Carriera a Cassa vuota: ogni stipendio sostanziale e' insostenibile."""
    with connect() as connection:
        return save_career(connection, _build_career(TeamLedger()))


async def test_opens_from_grid_and_populates_pool(funded_career):
    """Il tasto m apre il Mercato dal grid e popola il pool dei piloti."""
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(funded_career))
        await pilot.pause()
        await pilot.press("m")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, MarketScreen)
        assert screen.career.market.is_open
        assert screen.query_one("#market-pool", DataTable).row_count == 9


async def test_driver_attributes_render_as_estimates(funded_career):
    """Gli Attributi pilota sono intervalli (Stime), mai valori esatti."""
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(MarketScreen(funded_career))
        await pilot.pause()

        pool = app.screen.query_one("#market-pool", DataTable)
        assert pool.row_count == 9
        for index in range(pool.row_count):
            row = pool.get_row_at(index)
            for cell in row[_ATTRIBUTE_COLUMNS]:
                assert _INTERVAL.match(cell), f"attributo non a Stima: {cell}"


async def test_counter_offer_signs_driver_and_persists(funded_career):
    """Una controfferta sostenibile e vincente fa firmare e finisce nel Checkpoint."""
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(MarketScreen(funded_career))
        await pilot.pause()

        screen = app.screen
        target = screen.career.market.available_driver_ids[0]
        pool = screen.query_one("#market-pool", DataTable)
        pool.move_cursor(row=0)
        await pilot.pause()
        # Beat the rival: salary plus the prestige bonus clears the rival offer.
        screen.query_one("#salary-input", Input).value = "11000000"
        pool.focus()
        await pilot.press("o")
        await pilot.pause()

        assert target in screen.career.market.signings_for(PLAYER_TEAM_ID)
        assert str(screen.query_one("#market-error", Static).content) == ""

        await pilot.press("escape")
        await pilot.pause()
        with connect() as connection:
            reloaded = load_career(connection, funded_career.id)
        assert target in reloaded.market.signings_for(PLAYER_TEAM_ID)


async def test_counter_offer_blocked_by_cash_explains_reason(broke_career):
    """Una controfferta oltre la Cassa e' bloccata col motivo esplicito."""
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(MarketScreen(broke_career))
        await pilot.pause()

        screen = app.screen
        pool = screen.query_one("#market-pool", DataTable)
        pool.move_cursor(row=0)
        await pilot.pause()
        screen.query_one("#salary-input", Input).value = "20000000"
        pool.focus()
        await pilot.press("o")
        await pilot.pause()

        error = str(screen.query_one("#market-error", Static).content)
        assert "Cassa" in error
        assert screen.career.market.signings_for(PLAYER_TEAM_ID) == ()


async def test_counter_offer_rejected_shows_rival_offer(funded_career):
    """Una controfferta troppo bassa viene rifiutata, mostrando l'offerta rivale."""
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(MarketScreen(funded_career))
        await pilot.pause()

        screen = app.screen
        pool = screen.query_one("#market-pool", DataTable)
        pool.move_cursor(row=0)
        await pilot.pause()
        # Sustainable on the Cassa, but well below the rival offer.
        screen.query_one("#salary-input", Input).value = "1000000"
        pool.focus()
        await pilot.press("o")
        await pilot.pause()

        error = str(screen.query_one("#market-error", Static).content)
        assert "rivale" in error.lower()
        assert screen.career.market.signings_for(PLAYER_TEAM_ID) == ()


async def test_ai_moves_are_logged(funded_career):
    """Il log mosse mostra le offerte e le firme delle squadre AI."""
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(MarketScreen(funded_career))
        await pilot.pause()

        log = app.screen.query_one("#market-log", DataTable)
        assert log.row_count > 0
        moves = {log.get_row_at(index)[2] for index in range(log.row_count)}
        assert "Offerta" in moves
        assert "Firma" in moves
