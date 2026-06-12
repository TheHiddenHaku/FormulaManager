"""Test Pilot della schermata sviluppo (FOR-25).

Navigazione da tastiera: slot Progetto con consegna stimata, avvio di
un nuovo Progetto con investimento, rifiuti spiegati a schermo (terzo
Progetto, vincolo Cliente, doppio vincolo di spesa) e avanzamento al
passaggio tra un GP e l'altro.
"""

from dataclasses import replace
from datetime import date

import pytest
from textual.widgets import DataTable, OptionList, Static

from fm_engine.career import Career
from fm_engine.economy import TeamLedger, Transaction, TransactionKind
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_persistence import connect, save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import DevelopmentScreen, Grid
from fm_tui.widgets.balance_bar import BalanceBar

SEED = 13
GAME_DATE = date(2026, 3, 8)


def _set_up_world(customer: bool):
    world = generate(SEED)
    world = replace(world, player_slot=PlayerSlot(name="Scuderia Sviluppo"))
    free_agents = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free_agents[0].id, free_agents[1].id),
        engine_supplier_id=world.engine_suppliers[0].id if customer else None,
        chassis_philosophy="balanced",
    )
    return apply_team_setup(world, choices)


def _funded_ledger(amount_usd: int = 60_000_000) -> TeamLedger:
    return TeamLedger().record(
        Transaction(
            kind=TransactionKind.ANNUAL_SPONSOR,
            amount_usd=amount_usd,
            game_date=date(2026, 1, 1),
            description="Sponsor annuale",
        )
    )


@pytest.fixture
def customer_career(db_env):
    """Una Carriera Cliente di un Motorista, con Cassa per sviluppare."""
    career = Career(name="Sviluppo", world=_set_up_world(customer=True), ledger=_funded_ledger())
    with connect() as connection:
        return save_career(connection, career)


async def test_development_opens_from_grid_with_empty_state(customer_career):
    app = FormulaManagerApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        app.push_screen(Grid(customer_career))
        await pilot.pause()
        await pilot.press("s")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, DevelopmentScreen)
        empty = screen.query_one("#development-empty", Static)
        assert empty.display is True
        assert "Nessun Progetto attivo" in str(empty.content)


async def test_start_project_from_keyboard_updates_slots_and_balances(customer_career):
    app = FormulaManagerApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        screen = DevelopmentScreen(customer_career, GAME_DATE)
        app.push_screen(screen)
        await pilot.pause()

        # Cliente: la Potenza motore e' presente ma disabilitata e spiegata.
        options = screen.query_one("#attribute-list", OptionList)
        first = options.get_option_at_index(0)
        assert first.id == "engine_power"
        assert first.disabled
        assert "non disponibile" in str(first.prompt)

        # Avvio sul Carico aerodinamico (seconda opzione) da tastiera.
        options.highlighted = 1
        await pilot.press("a")
        await pilot.pause()

        table = screen.query_one("#projects-table", DataTable)
        assert table.row_count == 1
        row = table.get_row_at(0)
        assert row[0] == "Carico aerodinamico"
        assert row[1] == "in corso"
        assert row[4] != "-"  # consegna stimata reale
        # Il costo e' uscito da Cassa e Cap: la barra saldi lo riflette.
        bar_text = str(screen.query_one(BalanceBar).content)
        assert "Cassa: $52.0M" in bar_text
        assert "Cap residuo: $207.0M" in bar_text


async def test_third_project_and_customer_rule_are_explained(customer_career):
    app = FormulaManagerApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        screen = DevelopmentScreen(customer_career, GAME_DATE)
        app.push_screen(screen)
        await pilot.pause()
        options = screen.query_one("#attribute-list", OptionList)

        # Due avvii leciti, il terzo e' rifiutato con messaggio chiaro.
        options.highlighted = 1
        await pilot.press("a")
        options.highlighted = 2
        await pilot.press("a")
        options.highlighted = 3
        await pilot.press("a")
        await pilot.pause()
        error = str(screen.query_one("#development-error", Static).content)
        assert "2 Progetti in corso" in error

        # Vincolo Cliente: l'avvio sulla Potenza motore spiega il perche'.
        options.highlighted = 0
        await pilot.press("a")
        await pilot.pause()
        error = str(screen.query_one("#development-error", Static).content)
        assert "Cliente" in error
        assert "Potenza motore" in error


async def test_spending_bind_refusal_is_explained(customer_career):
    poor = replace(customer_career, ledger=_funded_ledger(1_000_000))
    app = FormulaManagerApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        screen = DevelopmentScreen(poor, GAME_DATE)
        app.push_screen(screen)
        await pilot.pause()

        screen.query_one("#attribute-list", OptionList).highlighted = 1
        await pilot.press("a")
        await pilot.pause()
        error = str(screen.query_one("#development-error", Static).content)
        assert "Spesa rifiutata" in error
        assert "Cassa" in error


async def test_projects_advance_crossing_to_the_next_grand_prix(customer_career):
    """Il passaggio tra un GP concluso e il successivo avanza i Progetti."""
    from fm_engine.development import DevelopmentProject
    from fm_engine.weekend import WeekendPhase, WeekendState
    from fm_tui.screens import WeekendScreen

    # GP 1 concluso e un Progetto che maturera' prima del GP 2.
    finished = WeekendState(
        circuit_code="albert_park",
        seed=1,
        phase=WeekendPhase.FINISHED,
        race_classification=None,
    )
    short_project = DevelopmentProject(
        attribute="downforce",
        cost_usd=8_000_000,
        start_date=date(2026, 3, 1),
        duration_days=7,
    )
    career = replace(customer_career, weekend=finished, projects=(short_project,))
    initial_downforce = career.world.player_slot.downforce

    app = FormulaManagerApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        grid = Grid(career)
        app.push_screen(grid)
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()

        # Si apre il weekend del GP successivo (Shanghai, round 2).
        hub = app.screen
        assert isinstance(hub, WeekendScreen)
        assert hub.career.weekend.circuit_code != "albert_park"
        # Il Progetto e' stato consegnato e l'attributo aggiornato.
        delivered = hub.career.projects[0]
        assert not delivered.in_progress
        assert delivered.outcome is not None
        expected = min(100, initial_downforce + delivered.outcome)
        assert hub.career.world.player_slot.downforce == expected
