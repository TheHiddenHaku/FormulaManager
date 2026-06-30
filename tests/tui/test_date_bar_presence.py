"""Presenza della DateBar sulle schermate gestionali (data-sempre-visibile).

La data di gioco deve restare visibile passando da una schermata all'altra:
qui si verifica che la barra sia montata e mostri la data interna anche fuori
dalla griglia, sulle schermate gestionali che ricevono la Carriera.
"""

from dataclasses import replace

import psycopg
import pytest

from fm_engine.career import Career
from fm_engine.world import PlayerSlot, generate
from fm_persistence import save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens.almanac import AlmanacScreen
from fm_tui.screens.calendar import CalendarScreen
from fm_tui.screens.finances import FinancesScreen
from fm_tui.screens.hall_of_fame import HallOfFameScreen
from fm_tui.screens.scuderie import ScuderieScreen
from fm_tui.screens.standings import StandingsScreen
from fm_tui.widgets.date_bar import DateBar

SEED = 23


@pytest.fixture
def saved_career(db_env):
    slot = PlayerSlot(name="Scuderia X", primary_color="#ff2800")
    world = replace(generate(SEED), player_slot=slot)
    with psycopg.connect(db_env) as connection:
        return save_career(connection, Career(name="Scuderia X", world=world))


@pytest.mark.parametrize(
    "screen_factory",
    [
        CalendarScreen,
        StandingsScreen,
        ScuderieScreen,
        FinancesScreen,
        AlmanacScreen,
        HallOfFameScreen,
    ],
)
async def test_management_screens_show_the_date_bar(saved_career, screen_factory):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(screen_factory(saved_career))
        await pilot.pause()
        bar = str(app.screen.query_one(DateBar).render())
        assert "Data: 01/01/2026" in bar
