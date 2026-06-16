"""Test Pilot della schermata Mercato piloti (T5.2.1, sub-issue M5).

Verificano il guscio TUI sopra fm_engine.market: il pool reso a Stime
(mai valori esatti), l'apertura dal grid, la controfferta accettata e
persistita ai Checkpoint, i due motivi di rifiuto strutturati (Cassa
insufficiente e offerta rivale piu' alta) e l'applicazione delle firme al
roster alla transizione di stagione. I valori attesi sono deterministici
dal SEED: con SEED 42 e anno concluso 2027 il pool ha 8 piloti e il primo
(driver 17) ha un'offerta rivale da battere; i piloti del giocatore sono in
scadenza, quindi ha sedili liberi da riempire.
"""

import re
from dataclasses import replace
from datetime import date
from random import Random

import pytest
from textual.widgets import DataTable, Input, Static

from fm_engine.career import Career
from fm_engine.economy import DEFAULT_PLAYER_PRESTIGE, TeamLedger, credit_annual_sponsor
from fm_engine.market import (
    best_rival_salary_usd,
    counter_offer,
    open_market,
    resolve_market,
)
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_engine.world.models import PLAYER_TEAM_ID, WorldConfig
from fm_persistence import connect, load_career, save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import Grid, MarketScreen
from fm_tui.screens.news import NewsScreen

SEED = 42
TEST_SIZE = (140, 50)
# The player's drivers expire in 2027 (contracts 2026-2027): opening the
# market on that year gives the player vacant seats to negotiate.
CONCLUDED_YEAR = 2027
# Pool table column layout: the 6 driver attributes sit in columns 6-11.
_ATTRIBUTE_COLUMNS = slice(6, 12)
_INTERVAL = re.compile(r"^\d+-\d+$")


# Config che neutralizza il ricambio generazionale (FOR-31) senza toccare la
# generazione: Ritiri disabilitati (soglia oltre l'eta' massima) e parco gia'
# a regime (nessun Giovane da generare). Questi test M5 verificano la
# negoziazione del Mercato, non il ricambio: cosi' il pool resta stabile e
# deterministico. Il ricambio ha i suoi test dedicati (test_generational.py).
_NO_CHURN_CONFIG = WorldConfig(retirement_age=41, active_pool_target=22)


def _build_career(ledger: TeamLedger) -> Career:
    """Una Carriera a Setup squadra completato, alla fine della stagione 2027."""
    generated = generate(SEED)
    world = replace(
        generated,
        config=_NO_CHURN_CONFIG,
        player_slot=PlayerSlot(name="Scuderia X", primary_color="#ff2800"),
    )
    free = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free[0].id, free[1].id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    career = Career(name="Scuderia X", world=apply_team_setup(world, choices), ledger=ledger)
    return replace(career, season=replace(career.season, year=CONCLUDED_YEAR))


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
        assert screen.query_one("#market-pool", DataTable).row_count == 8


async def test_driver_attributes_render_as_estimates(funded_career):
    """Gli Attributi pilota sono intervalli (Stime), mai valori esatti."""
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(MarketScreen(funded_career))
        await pilot.pause()

        pool = app.screen.query_one("#market-pool", DataTable)
        assert pool.row_count == 8
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
        # Once signed, the driver leaves the pool: no point re-offering.
        assert target not in screen._row_driver_ids

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
        rows = [log.get_row_at(index) for index in range(log.row_count)]
        moves = {row[2] for row in rows if row[2]}
        assert "Offerta" in moves
        assert "Firma" in moves
        # Le trattative sono separate da una riga vuota.
        assert any(all(cell == "" for cell in row) for row in rows)


async def test_season_advance_applies_open_market_to_roster(db_env):
    """A fine stagione le firme del Mercato diventano Contratti della stagione nuova."""
    ledger = credit_annual_sponsor(TeamLedger(), DEFAULT_PLAYER_PRESTIGE, date(2026, 1, 1))
    career = _build_career(ledger)
    # Apri e risolvi il Mercato dell'anno concluso, poi firma il primo pilota
    # del pool battendo l'offerta rivale (seed identico a quello della schermata).
    market = resolve_market(
        career.world,
        open_market(career.world, CONCLUDED_YEAR),
        Random(SEED * 1_000 + (CONCLUDED_YEAR - 2026) * 100_000 + 800),
    )
    target = market.available_driver_ids[0]
    rival = best_rival_salary_usd(market, target)
    outcome = counter_offer(
        market,
        career.ledger,
        target,
        salary_usd=rival + 2_000_000,
        duration_seasons=2,
        game_date=date(CONCLUDED_YEAR, 11, 1),
        player_prestige=DEFAULT_PLAYER_PRESTIGE,
    )
    assert outcome.accepted
    career = replace(career, market=outcome.market)

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()
        grid = app.screen
        grid._advance_to_next_season()
        await pilot.pause()

        assert not grid._career.market.is_open
        assert grid._career.season.year == CONCLUDED_YEAR + 1
        player_roster = grid._career.world.contracts_of(PLAYER_TEAM_ID)
        assert target in {contract.driver_id for contract in player_roster}
        assert len(player_roster) == 2


def _build_churning_career(ledger: TeamLedger) -> Career:
    """Come _build_career ma col ricambio generazionale attivo (config di default)."""
    generated = generate(SEED)
    world = replace(generated, player_slot=PlayerSlot(name="Scuderia X", primary_color="#ff2800"))
    free = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free[0].id, free[1].id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    career = Career(name="Scuderia X", world=apply_team_setup(world, choices), ledger=ledger)
    return replace(career, season=replace(career.season, year=CONCLUDED_YEAR))


async def test_opening_market_runs_generational_refresh(db_env):
    """Effetto end-to-end: aprire il Mercato applica il ricambio generazionale.

    Coi parametri di default e SEED 42 a fine 2027 due anziani si ritirano e
    dei Giovani entrano nel parco: i ritirati escono dal roster attivo e dal
    pool, i Giovani compaiono tra i liberi, e la rassegna stampa dei Ritiri
    si apre sopra il Mercato. Tutto viene persistito col Checkpoint.
    """
    ledger = credit_annual_sponsor(TeamLedger(), DEFAULT_PLAYER_PRESTIGE, date(2026, 1, 1))
    with connect() as connection:
        career = save_career(connection, _build_churning_career(ledger))
    drivers_before = {driver.id for driver in career.world.drivers}

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()
        await pilot.press("m")
        await pilot.pause()

        # La rassegna stampa dei Ritiri compare sopra il Mercato.
        assert isinstance(app.screen, NewsScreen)
        await pilot.press("escape")
        await pilot.pause()

        market_screen = app.screen
        assert isinstance(market_screen, MarketScreen)
        refreshed = market_screen.career.world

        # I Giovani sono comparsi nel parco (id nuovi rispetto a prima).
        drivers_after = {driver.id for driver in refreshed.drivers}
        new_ids = drivers_after - drivers_before
        assert new_ids, "i Giovani devono entrare nel roster"
        # Sono liberi: presenti nel pool del Mercato come ingaggiabili.
        assert new_ids & set(market_screen.career.market.free_agent_ids)

        # I ritirati sono fuori dal parco attivo e dal pool.
        retired_ids = {driver.id for driver in refreshed.drivers if driver.retired}
        assert retired_ids, "qualche anziano deve essersi ritirato con questo seed"
        assert not (retired_ids & set(market_screen.career.market.available_driver_ids))

        # Il Checkpoint ha persistito il parco aggiornato.
        await pilot.press("escape")
        await pilot.pause()
        with connect() as connection:
            reloaded = load_career(connection, career.id)
        reloaded_ids = {driver.id for driver in reloaded.world.drivers}
        assert new_ids <= reloaded_ids
        reloaded_retired = {driver.id for driver in reloaded.world.drivers if driver.retired}
        assert retired_ids <= reloaded_retired
