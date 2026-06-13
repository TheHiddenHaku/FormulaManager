"""Test Pilot del wizard di Setup squadra (FOR-7).

Coprono il flusso completo: avvio automatico dopo la creazione della
Carriera, vincolo dei 2 piloti, navigazione avanti e indietro da
tastiera, conferma con Checkpoint e griglia con la squadra del giocatore
completa, ricaricabile da una nuova istanza dell'app. Coprono anche
l'edge accettato per il MVP: uscita a meta' wizard, Carriera senza
setup e wizard che non riparte.
"""

import re

from textual.widgets import DataTable, Input, Static

from fm_engine.economy import (
    DEFAULT_PLAYER_PRESTIGE,
    PLAYER_STARTING_CASH_USD,
    SEASON_CAP_USD,
    TransactionKind,
    annual_sponsor_usd,
)
from fm_persistence import connect, list_careers, load_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import CareerList, Grid, TeamSetup

INTERVAL = re.compile(r"^\d+-\d+$")


async def _create_career(pilot, app: FormulaManagerApp) -> None:
    """Dall'elenco vuoto: crea una Carriera e arriva al wizard."""
    await pilot.press("n")
    await pilot.pause()
    form = app.screen
    form.query_one("#career-name-input", Input).value = "Scuderia X"
    form.query_one("#team-name-input", Input).value = "Scuderia X Racing"
    await pilot.press("ctrl+s")
    await pilot.pause()


async def _select_first_two_drivers(pilot) -> None:
    """Nel passo piloti: seleziona le prime due righe del roster."""
    await pilot.press("space")
    await pilot.press("down")
    await pilot.press("space")
    await pilot.pause()


async def _complete_wizard(pilot, app: FormulaManagerApp) -> None:
    """Dal passo piloti alla conferma: 2 piloti, Cliente, telaio veloce."""
    await _select_first_two_drivers(pilot)
    await pilot.press("a")
    await pilot.pause()
    # Engine step: down to the first supplier, enter adopts and advances.
    await pilot.press("down")
    await pilot.press("enter")
    await pilot.pause()
    # Chassis step: enter on the highlighted philosophy (fast).
    await pilot.press("enter")
    await pilot.pause()
    # Summary: confirm and save.
    await pilot.press("ctrl+s")
    await pilot.pause()


def _error_text(app: FormulaManagerApp) -> str:
    return str(app.screen.query_one("#wizard-error", Static).render())


# ---------------------------------------------------------------------------
# Wizard start and driver constraint
# ---------------------------------------------------------------------------


async def test_wizard_starts_automatically_after_creation(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await _create_career(pilot, app)
        assert isinstance(app.screen, TeamSetup)
        assert app.screen.name == "team_setup"
        # The wizard opens on the drivers step with the full roster.
        assert app.screen.query_one("#step-drivers").display is True
        assert app.screen.query_one("#roster-table", DataTable).row_count == 22


async def test_cannot_advance_with_fewer_than_two_drivers(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await _create_career(pilot, app)

        # No selection: the step does not advance.
        await pilot.press("a")
        await pilot.pause()
        assert app.screen.query_one("#step-drivers").display is True
        assert "2 piloti" in _error_text(app)

        # One driver only: still not enough.
        await pilot.press("space")
        await pilot.press("a")
        await pilot.pause()
        assert app.screen.query_one("#step-drivers").display is True
        assert "2 piloti" in _error_text(app)


async def test_third_selection_is_rejected(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await _create_career(pilot, app)
        await _select_first_two_drivers(pilot)
        await pilot.press("down")
        await pilot.press("space")
        await pilot.pause()
        assert "gia' selezionato 2" in _error_text(app)
        status = str(app.screen.query_one("#selection-status", Static).render())
        assert "2/2" in status


# ---------------------------------------------------------------------------
# Keyboard navigation, forward and back
# ---------------------------------------------------------------------------


async def test_back_navigation_keeps_the_selection(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await _create_career(pilot, app)
        await _select_first_two_drivers(pilot)
        await pilot.press("a")
        await pilot.pause()
        assert app.screen.query_one("#step-engine").display is True

        # Escape: back to the drivers step, selection intact.
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen.query_one("#step-drivers").display is True
        status = str(app.screen.query_one("#selection-status", Static).render())
        assert "2/2" in status


def test_wizard_bindings_visible_in_footer():
    keys = {binding.key for binding in TeamSetup.BINDINGS}
    assert {"space", "a", "escape", "ctrl+s"} <= keys
    assert all(binding.show for binding in TeamSetup.BINDINGS)


# ---------------------------------------------------------------------------
# Full flow: confirmation, checkpoint, complete grid
# ---------------------------------------------------------------------------


async def test_full_wizard_up_to_the_complete_grid(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await _create_career(pilot, app)
        await _complete_wizard(pilot, app)
        assert isinstance(app.screen, Grid)

        # Player team row: engine, philosophy and attributes as estimates.
        teams = app.screen.query_one("#teams-table", DataTable)
        player_row = teams.get_row_at(0)
        assert player_row[0] == "Scuderia X Racing (tu)"
        assert player_row[1] != "-"
        assert player_row[2] == "fast"
        assert all(INTERVAL.match(cell) for cell in player_row[3:])

        # Driver roster: no empty slots, 2 drivers in the player team,
        # nobody left without a contract.
        drivers = app.screen.query_one("#drivers-table", DataTable)
        rows = [drivers.get_row_at(index) for index in range(drivers.row_count)]
        assert all(row[0] != "(slot vuoto)" for row in rows)
        assert sum(1 for row in rows if row[3] == "Scuderia X Racing (tu)") == 2
        assert all(row[3] != "senza Contratto" for row in rows)


async def test_setup_is_persisted_and_reloadable(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await _create_career(pilot, app)
        await _complete_wizard(pilot, app)
        assert isinstance(app.screen, Grid)

    # New app instance: reopening the career finds the complete team.
    reopened = FormulaManagerApp()
    async with reopened.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(reopened.screen, Grid)

        teams = reopened.screen.query_one("#teams-table", DataTable)
        player_row = teams.get_row_at(0)
        assert player_row[0] == "Scuderia X Racing (tu)"
        assert player_row[2] == "fast"
        assert all(INTERVAL.match(cell) for cell in player_row[3:])

        drivers = reopened.screen.query_one("#drivers-table", DataTable)
        rows = [drivers.get_row_at(index) for index in range(drivers.row_count)]
        assert all(row[0] != "(slot vuoto)" for row in rows)
        assert sum(1 for row in rows if row[3] == "Scuderia X Racing (tu)") == 2


async def test_confirm_credits_the_starting_cash_and_sponsor(db_env):
    """Alla conferma del wizard arrivano dotazione e Sponsor (FOR-22, FOR-43).

    La squadra entra nel campionato: il registro persistito col Checkpoint
    di conferma ha la dotazione di Cassa di partenza e lo Sponsor annuale,
    col Prestigio di partenza, e il Cap resta intatto. La dotazione porta il
    giocatore al livello della griglia (le AI partono con la loro cash_usd).
    """
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await _create_career(pilot, app)
        await _complete_wizard(pilot, app)
        assert isinstance(app.screen, Grid)

    with connect() as connection:
        summaries = list_careers(connection)
        assert len(summaries) == 1
        career = load_career(connection, summaries[0].id)
    kinds = [entry.kind for entry in career.ledger.entries]
    assert kinds == [TransactionKind.OTHER, TransactionKind.ANNUAL_SPONSOR]
    assert career.ledger.cash_usd == (
        PLAYER_STARTING_CASH_USD + annual_sponsor_usd(DEFAULT_PLAYER_PRESTIGE)
    )
    assert career.ledger.cap_remaining_usd == SEASON_CAP_USD


# ---------------------------------------------------------------------------
# Documented MVP edge: exit mid-wizard
# ---------------------------------------------------------------------------


async def test_exit_mid_wizard_leaves_the_career_without_setup(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await _create_career(pilot, app)

        # Escape from the first step: out of the wizard, back to the list.
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, CareerList)

        # Reopening: the grid shows the empty slots, the wizard does
        # NOT restart (accepted MVP edge).
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, Grid)
        teams = app.screen.query_one("#teams-table", DataTable)
        player_row = teams.get_row_at(0)
        assert all(cell == "-" for cell in player_row[1:])
        drivers = app.screen.query_one("#drivers-table", DataTable)
        rows = [drivers.get_row_at(index) for index in range(drivers.row_count)]
        assert sum(1 for row in rows if row[0] == "(slot vuoto)") == 2
