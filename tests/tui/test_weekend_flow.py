"""Test Pilot end-to-end del flusso weekend (FOR-21).

Un Gran Premio intero giocato dalla TUI: FP1, FP2 e FP3 coi Programmi,
le Qualifiche con la Classifica tempi di Q1 (22 vetture, 6 eliminate),
Q2 (16, 6 eliminate) e Q3 (10) piu' la griglia risultante, la Gara
interattiva e la schermata risultato coi punti. Dopo ogni sessione il
Checkpoint e' su database (Postgres effimero Docker, mai matilde): la
chiusura a meta' weekend riprende dalla sessione giusta con la griglia
salvata. Edge case: il Checkpoint fallito mostra l'errore ed e'
ritentabile senza perdere la sessione appena conclusa.

La gara usa un circuito accorciato a pochi giri (circuit_by_code
monkeypatchato nel modulo weekend): il flusso e' identico, il test
resta rapido.
"""

import asyncio
from dataclasses import replace

import psycopg
import pytest
from textual.widgets import DataTable, Select

from fm_engine.career import Career
from fm_engine.circuits import circuit_by_code
from fm_engine.economy import TransactionKind, race_prize_usd
from fm_engine.points import constructor_points
from fm_engine.weekend import WeekendPhase
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_persistence import connect, load_career, save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import (
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
# A terminal tall enough for the whole weekend hub and the panels.
TEST_SIZE = (120, 50)

ELIMINATED_LABEL = "Eliminata"


@pytest.fixture
def short_circuit(monkeypatch):
    """Il primo GP del Calendario accorciato a pochi giri, ovunque nel weekend."""
    circuit = replace(circuit_by_code("albert_park"), race_laps=SHORT_RACE_LAPS)
    monkeypatch.setattr("fm_tui.screens.weekend.circuit_by_code", lambda code: circuit)
    return circuit


@pytest.fixture
def saved_career(db_env):
    """Una Carriera a Setup squadra completato, gia' salvata su database."""
    world = generate(SEED)
    world = replace(
        world,
        player_slot=PlayerSlot(name="Scuderia X Racing", primary_color="#ff2800"),
    )
    free_agents = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free_agents[0].id, free_agents[1].id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    career = Career(name="Scuderia X", world=apply_team_setup(world, choices))
    with connect() as connection:
        return save_career(connection, career)


def player_driver_ids(career: Career) -> tuple[int, ...]:
    return tuple(contract.driver_id for contract in career.world.contracts_of(PLAYER_TEAM_ID))


def persisted_weekend(career_id):
    """Lo stato weekend come risulta dal database, per le verifiche."""
    with connect() as connection:
        return load_career(connection, career_id).weekend


async def play_practice_session(pilot, app, hub: WeekendScreen, programmes) -> None:
    """Dalla hub weekend: lancia la sessione di libere coi Programmi dati."""
    await pilot.press("g")
    await pilot.pause()
    screen = app.screen
    assert isinstance(screen, PracticeScreen)
    for driver_id, programme in programmes.items():
        screen.query_one(f"#programme-{driver_id}", Select).value = programme
    await pilot.press("l")
    await pilot.pause()
    assert screen.session_played
    await pilot.press("escape")
    await pilot.pause()
    assert app.screen is hub


async def finish_the_race(pilot, app, screen: RaceScreen) -> None:
    """Porta la gara alla bandiera a scacchi chiudendo le Auto-pause."""
    deadline = asyncio.get_running_loop().time() + WAIT_TIMEOUT_SECONDS
    while not screen.race_finished:
        if asyncio.get_running_loop().time() > deadline:
            pytest.fail("la gara non e' arrivata alla bandiera a scacchi in tempo")
        if isinstance(app.screen, PitOrderPanel):
            await pilot.press("escape")
        elif screen.is_paused or not screen.is_skipping:
            await pilot.press("s")
        await pilot.pause(0.05)


def eliminated_rows(table: DataTable) -> int:
    return sum(
        1 for index in range(table.row_count) if table.get_row_at(index)[4] == ELIMINATED_LABEL
    )


async def test_full_weekend_end_to_end_with_checkpoints(db_env, saved_career, short_circuit):
    """Il Gran Premio intero: sessioni, Checkpoint, ripresa e risultato persistito."""
    first, second = player_driver_ids(saved_career)
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()

        # The canonical path: g on the grid opens the weekend hub at FP1.
        await pilot.press("g")
        await pilot.pause()
        hub = app.screen
        assert isinstance(hub, WeekendScreen)
        assert hub.weekend.phase is WeekendPhase.FP1

        # FP1, FP2, FP3: one checkpoint per session, effects accumulate.
        sessions = (
            (WeekendPhase.FP2, {first: "setup", second: "tyres"}),
            (WeekendPhase.FP3, {first: "qualifying_focus", second: "race_pace"}),
            (WeekendPhase.QUALIFYING, {first: "setup", second: "strategy"}),
        )
        for expected_phase, programmes in sessions:
            await play_practice_session(pilot, app, hub, programmes)
            assert hub.weekend.phase is expected_phase
            assert persisted_weekend(saved_career.id).phase is expected_phase
        assert hub.weekend.effects.for_driver(first).qualifying_bonus_seconds > 0.0

        # Saturday: Q1 (22 cars, 6 out), Q2 (16, 6 out), Q3 (10), then the grid.
        await pilot.press("g")
        await pilot.pause()
        qualifying = app.screen
        assert isinstance(qualifying, QualifyingScreen)
        table = qualifying.query_one("#segment-table", DataTable)
        assert qualifying.current_step == "q1"
        assert table.row_count == 22
        assert eliminated_rows(table) == 6
        await pilot.press("space")
        assert qualifying.current_step == "q2"
        assert table.row_count == 16
        assert eliminated_rows(table) == 6
        await pilot.press("space")
        assert qualifying.current_step == "q3"
        assert table.row_count == 10
        await pilot.press("space")
        assert qualifying.all_revealed
        assert table.row_count == 22
        pole_name = table.get_row_at(0)[1]
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen is hub
        assert hub.weekend.phase is WeekendPhase.RACE
        assert hub.weekend.grid_driver_ids is not None
        assert len(hub.weekend.grid_driver_ids) == 22

        # Mid-weekend close and reopen: the Career resumes at the race,
        # with the saved grid (the qualifying checkpoint covers pre-race).
        resumed = persisted_weekend(saved_career.id)
        assert resumed.phase is WeekendPhase.RACE
        assert resumed.grid_driver_ids == hub.weekend.grid_driver_ids
        with connect() as connection:
            reloaded_career = load_career(connection, saved_career.id)
        app.push_screen(Grid(reloaded_career))
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
        resumed_hub = app.screen
        assert isinstance(resumed_hub, WeekendScreen)
        assert resumed_hub.weekend.phase is WeekendPhase.RACE

        # Sunday: the interactive race on the saved grid, pole on slot 1.
        await pilot.press("g")
        await pilot.pause()
        race = app.screen
        assert isinstance(race, RaceScreen)
        monitor = race.query_one("#monitor", DataTable)
        assert monitor.row_count == 22
        assert monitor.get_row_at(0)[1] == pole_name
        await finish_the_race(pilot, app, race)
        await pilot.press("escape")
        await pilot.pause()

        # The result screen: finishing order with 2026 points.
        result_screen = app.screen
        assert isinstance(result_screen, RaceResultScreen)
        classification_table = result_screen.query_one("#classification-table", DataTable)
        assert classification_table.get_row_at(0)[0] == "1"
        assert classification_table.get_row_at(0)[5] == "25"
        constructors_table = result_screen.query_one("#constructors-table", DataTable)
        assert constructors_table.row_count >= 1
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen is resumed_hub
        assert resumed_hub.weekend.finished

        # The persisted result: classification with driver and team points.
        final = persisted_weekend(saved_career.id)
        assert final.phase is WeekendPhase.FINISHED
        assert final.race_classification is not None
        assert final.race_classification[0].points == 25
        driver_points = sum(result.points for result in final.race_classification)
        assert driver_points == sum(constructor_points(final.race_classification).values())

        # Race economy (FOR-22): prizes for the classified player cars and
        # one salary instalment, cash only, persisted with the checkpoint.
        ledger = resumed_hub.career.ledger
        prize_entries = [e for e in ledger.entries if e.kind is TransactionKind.RACE_PRIZE]
        player_positions = [
            result.position
            for result in final.race_classification
            if result.team_id == PLAYER_TEAM_ID
        ]
        assert len(prize_entries) == sum(
            1 for position in player_positions if race_prize_usd(position) > 0
        )
        salary_entries = [e for e in ledger.entries if e.kind is TransactionKind.SALARY]
        assert len(salary_entries) == 1
        assert salary_entries[0].amount_usd < 0
        assert salary_entries[0].counts_against_cap is False
        assert ledger.cap_remaining_usd == ledger.cap_usd
        with connect() as connection:
            assert load_career(connection, saved_career.id).ledger == ledger


async def test_failed_checkpoint_is_retryable_without_losing_the_session(
    db_env, saved_career, short_circuit, monkeypatch
):
    """Checkpoint fallito: errore mostrato, stato in memoria intatto, retry ok."""
    first, second = player_driver_ids(saved_career)
    failing = {"active": True}

    real_save = save_career

    def flaky_save(connection, career):
        if failing["active"]:
            raise psycopg.OperationalError("connessione al database persa")
        return real_save(connection, career)

    monkeypatch.setattr("fm_tui.screens.weekend.save_career", flaky_save)

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
        hub = app.screen
        assert isinstance(hub, WeekendScreen)

        # FP1 concludes but the checkpoint fails: the session is not lost.
        await play_practice_session(pilot, app, hub, {first: "setup", second: "tyres"})
        assert hub.save_failed
        assert hub.weekend.phase is WeekendPhase.FP2
        assert persisted_weekend(saved_career.id) is None

        # Retry with the database back: the same in-memory state lands on disk.
        failing["active"] = False
        await pilot.press("s")
        await pilot.pause()
        assert not hub.save_failed
        persisted = persisted_weekend(saved_career.id)
        assert persisted is not None
        assert persisted.phase is WeekendPhase.FP2
        assert persisted.effects == hub.weekend.effects
