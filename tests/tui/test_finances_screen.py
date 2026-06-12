"""Test Pilot della schermata finanze e della barra saldi (FOR-15).

La griglia mostra la barra persistente con Cassa e Cap residuo e apre la
schermata finanze col binding f; la schermata presenta lo storico dei
movimenti (dal piu' recente) o l'empty state a registro vuoto, e torna
indietro con escape.
"""

from dataclasses import replace
from datetime import date

import psycopg
import pytest
from textual.widgets import DataTable, Static

from fm_engine.career import Career
from fm_engine.economy import TeamLedger, Transaction, TransactionKind
from fm_engine.world import PlayerSlot, generate
from fm_persistence import save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import FinancesScreen, Grid
from fm_tui.widgets.balance_bar import BalanceBar, format_usd

SEED = 11
GAME_DATE = date(2026, 3, 8)


def _sample_ledger() -> TeamLedger:
    ledger = TeamLedger().record(
        Transaction(
            kind=TransactionKind.OTHER,
            amount_usd=30_000_000,
            game_date=GAME_DATE,
            description="Dotazione iniziale",
        )
    )
    return ledger.spend(
        TransactionKind.OTHER, 4_000_000, date(2026, 3, 15), description="Spesa di prova"
    )


@pytest.fixture
def saved_career(db_env):
    """Una Carriera con movimenti nel registro, salvata sul database effimero."""
    slot = PlayerSlot(name="Scuderia Finanze")
    world = replace(generate(SEED), player_slot=slot)
    career = Career(name="Finanze", world=world, ledger=_sample_ledger())
    with psycopg.connect(db_env) as connection:
        return save_career(connection, career)


def test_format_usd_compact_amounts():
    assert format_usd(30_000_000) == "$30.0M"
    assert format_usd(-4_000_000) == "-$4.0M"
    assert format_usd(215_000_000) == "$215.0M"
    assert format_usd(1_500) == "$1.5K"
    assert format_usd(0) == "$0"


async def test_balance_bar_visible_on_grid(saved_career):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()

        bar = app.screen.query_one(BalanceBar)
        text = str(bar.content)
        assert "Cassa: $26.0M" in text
        assert "Cap residuo: $211.0M" in text


async def test_finances_opens_from_grid_and_back(saved_career):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()

        await pilot.press("f")
        await pilot.pause()
        assert isinstance(app.screen, FinancesScreen)
        # La barra dei saldi resta visibile anche qui.
        app.screen.query_one(BalanceBar)

        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, Grid)


async def test_finances_lists_movements_newest_first(saved_career):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(FinancesScreen(saved_career))
        await pilot.pause()

        table = app.screen.query_one("#transactions-table", DataTable)
        assert table.row_count == 2
        newest = table.get_row_at(0)
        assert newest[0] == "15/03/2026"
        assert newest[1] == "Altro"
        assert newest[2] == "-$4.0M"
        assert newest[3] == "si"
        assert newest[4] == "Spesa di prova"
        oldest = table.get_row_at(1)
        assert oldest[2] == "$30.0M"
        assert oldest[3] == ""


async def test_finances_empty_state(saved_career):
    empty = replace(saved_career, ledger=TeamLedger())
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(FinancesScreen(empty))
        await pilot.pause()

        empty_state = app.screen.query_one("#finances-empty", Static)
        assert "Nessun movimento registrato" in str(empty_state.content)
        assert not app.screen.query("#transactions-table")
