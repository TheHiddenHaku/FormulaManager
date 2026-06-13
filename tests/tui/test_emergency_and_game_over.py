"""Test Pilot della Misura d'emergenza e del fallimento (FOR-24).

La schermata della Misura si apre da sola quando la Cassa non copre la
scadenza stipendi a fine gara; la scelta e' navigabile da tastiera con
offerte reali del motore. Il fallimento porta alla schermata di fine
Carriera, da cui si torna solo all'elenco; una Carriera fallita si apre
direttamente sul riepilogo e non scende piu' in pista.
"""

import asyncio
from dataclasses import replace
from datetime import date

import pytest
from textual.widgets import OptionList, Select

from fm_engine.career import Career
from fm_engine.circuits import circuit_by_code
from fm_engine.economy import (
    BANKRUPTCY_RACES,
    SolvencyState,
    TeamLedger,
    Transaction,
    TransactionKind,
)
from fm_engine.weekend import WeekendPhase
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_persistence import connect, load_career, save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import (
    CareerList,
    EmergencyMeasureScreen,
    GameOverScreen,
    Grid,
    PracticeScreen,
    QualifyingScreen,
    RaceResultScreen,
    RaceScreen,
    WeekendScreen,
)
from fm_tui.screens.race import PitOrderPanel

SEED = 11
SHORT_RACE_LAPS = 4
WAIT_TIMEOUT_SECONDS = 30.0
TEST_SIZE = (120, 50)

OLD_DEBTS_USD = -50_000_000


def _set_up_world():
    world = generate(SEED)
    world = replace(world, player_slot=PlayerSlot(name="Scuderia Crisi"))
    free_agents = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free_agents[0].id, free_agents[1].id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    return apply_team_setup(world, choices)


def _in_debt_ledger() -> TeamLedger:
    """Una Cassa cosi' negativa che nessun Premio gara puo' coprirla."""
    return TeamLedger().record(
        Transaction(
            kind=TransactionKind.OTHER,
            amount_usd=OLD_DEBTS_USD,
            game_date=date(2026, 1, 1),
            description="Debiti pregressi",
        )
    )


def _bankrupt_solvency() -> SolvencyState:
    return SolvencyState(emergency_used=True, insolvent_races=BANKRUPTCY_RACES)


@pytest.fixture
def short_circuit(monkeypatch):
    circuit = replace(circuit_by_code("albert_park"), race_laps=SHORT_RACE_LAPS)
    monkeypatch.setattr("fm_tui.screens.weekend.circuit_by_code", lambda code: circuit)
    return circuit


@pytest.fixture
def indebted_career(db_env):
    """Una Carriera completa ma con la Cassa in profondo rosso."""
    career = Career(name="In crisi", world=_set_up_world(), ledger=_in_debt_ledger())
    with connect() as connection:
        return save_career(connection, career)


@pytest.fixture
def bankrupt_career(db_env):
    """Una Carriera gia' fallita, salvata sul database effimero."""
    career = Career(
        name="Fallita",
        world=_set_up_world(),
        ledger=_in_debt_ledger(),
        solvency=_bankrupt_solvency(),
    )
    with connect() as connection:
        return save_career(connection, career)


# ---------------------------------------------------------------------------
# Emergency measure screen, in isolation
# ---------------------------------------------------------------------------


async def test_emergency_screen_offers_are_real_and_selectable(db_env):
    chosen: list[str | None] = []
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(EmergencyMeasureScreen(650_000), chosen.append)
        await pilot.pause()

        options = app.screen.query_one("#emergency-options", OptionList)
        assert options.option_count == 2
        loan_text = str(options.get_option_at_index(0).prompt)
        stopgap_text = str(options.get_option_at_index(1).prompt)
        assert "Prestito" in loan_text
        assert "rata" in loan_text
        assert "Sponsor-tampone" in stopgap_text
        assert "Prestigio" in stopgap_text

        # Navigazione e conferma da tastiera: freccia giu' e invio.
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause()
    assert chosen == ["stopgap"]


# ---------------------------------------------------------------------------
# Game over screen and bankrupt careers
# ---------------------------------------------------------------------------


async def test_game_over_returns_only_to_the_career_list(bankrupt_career):
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(bankrupt_career))
        await pilot.pause()
        app.push_screen(GameOverScreen(bankrupt_career))
        await pilot.pause()

        summary = str(app.screen.query_one("#game-over-summary").content)
        assert "fallita" in summary
        assert str(BANKRUPTCY_RACES) in summary

        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, CareerList)


async def test_bankrupt_career_opens_on_the_game_over_screen(bankrupt_career):
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, CareerList)
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, GameOverScreen)


async def test_bankrupt_career_never_races_again(bankrupt_career):
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(bankrupt_career))
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
        assert isinstance(app.screen, Grid)


# ---------------------------------------------------------------------------
# End to end: the measure opens by itself at the salary deadline
# ---------------------------------------------------------------------------


async def _play_practice(pilot, app, hub, driver_ids) -> None:
    await pilot.press("g")
    await pilot.pause()
    screen = app.screen
    assert isinstance(screen, PracticeScreen)
    for driver_id, programme in zip(driver_ids, ("setup", "tyres"), strict=True):
        screen.query_one(f"#programme-{driver_id}", Select).value = programme
    await pilot.press("l")
    await pilot.pause()
    assert screen.session_played
    await pilot.press("escape")
    await pilot.pause()
    assert app.screen is hub


async def _finish_the_race(pilot, app, screen: RaceScreen) -> None:
    deadline = asyncio.get_running_loop().time() + WAIT_TIMEOUT_SECONDS
    while not screen.race_finished:
        if asyncio.get_running_loop().time() > deadline:
            pytest.fail("la gara non e' arrivata alla bandiera a scacchi in tempo")
        if isinstance(app.screen, PitOrderPanel):
            await pilot.press("escape")
        elif screen.is_paused or not screen.is_skipping:
            await pilot.press("s")
        await pilot.pause(0.05)


async def test_emergency_opens_by_itself_at_the_salary_deadline(
    db_env, indebted_career, short_circuit
):
    driver_ids = tuple(
        contract.driver_id for contract in indebted_career.world.contracts_of(PLAYER_TEAM_ID)
    )
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(indebted_career))
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
        hub = app.screen
        assert isinstance(hub, WeekendScreen)

        for _ in range(3):
            await _play_practice(pilot, app, hub, driver_ids)
        await pilot.press("g")
        await pilot.pause()
        assert isinstance(app.screen, QualifyingScreen)
        for _ in range(3):
            await pilot.press("space")
        await pilot.press("escape")
        await pilot.pause()
        assert hub.weekend.phase is WeekendPhase.RACE

        await pilot.press("g")
        await pilot.pause()
        race = app.screen
        assert isinstance(race, RaceScreen)
        await _finish_the_race(pilot, app, race)
        await pilot.press("escape")
        await pilot.pause()

        # La Misura si apre da sola: la Cassa non copre gli stipendi.
        emergency = app.screen
        assert isinstance(emergency, EmergencyMeasureScreen)
        await pilot.press("enter")  # prestito (prima opzione)
        await pilot.pause()

        # Scelta applicata: si prosegue al risultato col registro sanato.
        assert isinstance(app.screen, RaceResultScreen)
        ledger = hub.career.ledger
        loan_entries = [e for e in ledger.entries if e.kind is TransactionKind.LOAN]
        assert len(loan_entries) == 1
        assert loan_entries[0].amount_usd > 0
        assert hub.career.solvency.emergency_used
        assert hub.career.solvency.loan_active

        # Persistito col Checkpoint di fine gara.
        with connect() as connection:
            persisted = load_career(connection, indebted_career.id)
        assert persisted.solvency == hub.career.solvency
        assert persisted.ledger == ledger
