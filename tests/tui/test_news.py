"""Test Pilot della rassegna stampa tra due GP (FOR-27).

La schermata Notizie compare solo quando l'intervallo ha prodotto
qualcosa: e' scorribile da tastiera e si chiude proseguendo verso il
weekend. L'effetto dell'evento (entrata in Cassa) e' gia' applicato
quando la rassegna appare.
"""

from dataclasses import replace

import pytest
from textual.widgets import OptionList

from fm_engine.career import Career
from fm_engine.economy import Transaction, TransactionKind
from fm_engine.events_extra import ExtraEventKind
from fm_engine.events_extra.draw import ExtraEventOutcome
from fm_engine.events_extra.pool import EXTRA_EVENT_POOL
from fm_engine.weekend import WeekendPhase, WeekendState
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_persistence import connect, save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import Grid, NewsScreen, WeekendScreen
from fm_tui.widgets.balance_bar import BalanceBar

SEED = 17
SPONSOR_EVENT = next(
    event for event in EXTRA_EVENT_POOL if event.kind is ExtraEventKind.ONE_OFF_SPONSOR
)


def _set_up_career() -> Career:
    world = generate(SEED)
    world = replace(world, player_slot=PlayerSlot(name="Scuderia Notizie"))
    free_agents = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free_agents[0].id, free_agents[1].id),
        engine_supplier_id=None,
        chassis_philosophy="balanced",
    )
    finished = WeekendState(
        circuit_code="albert_park",
        seed=1,
        phase=WeekendPhase.FINISHED,
        race_classification=None,
    )
    return Career(name="Notizie", world=apply_team_setup(world, choices), weekend=finished)


@pytest.fixture
def saved_career(db_env):
    with connect() as connection:
        return save_career(connection, _set_up_career())


async def test_news_screen_is_scrollable_and_proceeds(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(NewsScreen(("Prima Notizia", "Seconda Notizia")))
        await pilot.pause()

        news_list = app.screen.query_one("#news-list", OptionList)
        assert news_list.option_count == 2
        await pilot.press("down")
        assert news_list.highlighted == 1
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, NewsScreen)


async def test_interval_event_shows_the_news_and_applies_the_effect(saved_career, monkeypatch):
    """L'evento dell'intervallo: rassegna visibile, Cassa gia' aggiornata."""

    def forced_sponsor(world, ledger, projects, game_date, rng, probability=0.25):
        news = SPONSOR_EVENT.headline_template.format(amount="$2.0M")
        charged = ledger.record(
            Transaction(
                kind=TransactionKind.ONE_OFF_SPONSOR,
                amount_usd=SPONSOR_EVENT.amount_usd,
                game_date=game_date,
                description=news,
            )
        )
        return ExtraEventOutcome(
            event=SPONSOR_EVENT, news=news, ledger=charged, projects=projects, world=world
        )

    monkeypatch.setattr("fm_tui.screens.grid.draw_extra_event", forced_sponsor)

    app = FormulaManagerApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        grid = Grid(saved_career)
        app.push_screen(grid)
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()

        news_screen = app.screen
        assert isinstance(news_screen, NewsScreen)
        news_list = news_screen.query_one("#news-list", OptionList)
        assert "bonus una tantum" in str(news_list.get_option_at_index(0).prompt)

        # L'effetto e' gia' nel registro: la barra saldi della griglia lo mostra.
        bar_text = str(grid.query_one(BalanceBar).content)
        assert "Cassa: $2.0M" in bar_text

        # Si prosegue verso il weekend del GP successivo.
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, WeekendScreen)
        assert app.screen.career.ledger.cash_usd == SPONSOR_EVENT.amount_usd


async def test_silent_interval_opens_the_weekend_directly(saved_career, monkeypatch):
    """Intervallo senza eventi: nessuna Notizia forzata, dritti al weekend."""
    monkeypatch.setattr(
        "fm_tui.screens.grid.draw_extra_event",
        lambda *args, **kwargs: None,
    )
    app = FormulaManagerApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
        assert isinstance(app.screen, WeekendScreen)
