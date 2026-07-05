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
import sqlite3
from dataclasses import replace
from datetime import date

import pytest
from rich.text import Text
from textual.widgets import DataTable, Select, Static

from fm_engine.career import Career
from fm_engine.circuits import circuit_by_code
from fm_engine.economy import (
    DEFAULT_PLAYER_PRESTIGE,
    TeamLedger,
    TransactionKind,
    credit_annual_sponsor,
    race_prize_usd,
)
from fm_engine.points import constructor_points
from fm_engine.preseason import PRESEASON_DAYS, PreseasonDay, PreseasonState
from fm_engine.tyres import CompoundSlot, nominated_compounds
from fm_engine.weekend import WeekendPhase, start_weekend
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
from fm_tui.screens.race_strategy import RaceStrategyScreen

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
def short_sprint_circuit(monkeypatch):
    """Un GP in Formato Sprint accorciato a pochi giri, ovunque nel weekend."""
    circuit = replace(
        circuit_by_code("shanghai"), race_laps=SHORT_RACE_LAPS, weekend_format_2026="sprint"
    )
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
    # Lo Sponsor annuale come dopo il wizard (FOR-22): senza, la prima
    # scadenza stipendi farebbe scattare la Misura d'emergenza (FOR-24).
    ledger = credit_annual_sponsor(TeamLedger(), DEFAULT_PLAYER_PRESTIGE, date(2026, 1, 1))
    # Test pre-season gia' conclusi: questo flusso parte dal primo GP (T5.1.2).
    preseason = PreseasonState(
        days_done=tuple(
            PreseasonDay(day=day, programmes={}) for day in range(1, PRESEASON_DAYS + 1)
        )
    )
    career = Career(
        name="Scuderia X",
        world=apply_team_setup(world, choices),
        ledger=ledger,
        preseason=preseason,
    )
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
    # The outcome cell can be a plain string or a highlighted Text (player rows).
    return sum(
        1
        for index in range(table.row_count)
        if cell_text(table.get_row_at(index)[4]) == ELIMINATED_LABEL
    )


def cell_text(value) -> str:
    """Il contenuto testuale di una cella, sia stringa sia Text evidenziato (B03)."""
    return value.plain if isinstance(value, Text) else str(value)


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
        pole_name = cell_text(table.get_row_at(0)[1])
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

        # Sunday: the pre-race strategy choice (Strategia Pit Stop), then the race.
        await pilot.press("g")
        await pilot.pause()
        strategy = app.screen
        assert isinstance(strategy, RaceStrategyScreen)
        nominated = nominated_compounds(short_circuit)
        soft = nominated[CompoundSlot.SOFT]
        hard = nominated[CompoundSlot.HARD]
        # The two player drivers can start on different compounds.
        await pilot.click(f"#strategy-{first}-{soft.value}")
        await pilot.click(f"#strategy-{second}-{hard.value}")
        await pilot.click("#confirm-strategy")
        await pilot.pause()
        race = next(s for s in reversed(app.screen_stack) if isinstance(s, RaceScreen))
        # The chosen starting compounds reach the race, differentiated per driver.
        assert race.race_state.car_of(first).tyres.compound is soft
        assert race.race_state.car_of(second).tyres.compound is hard
        # Rivals start on differentiated compounds, not all identical.
        ai_compounds = {
            car.tyres.compound
            for car in race.race_state.cars
            if car.entry.team_id != PLAYER_TEAM_ID
        }
        assert len(ai_compounds) > 1
        monitor = race.query_one("#monitor", DataTable)
        assert monitor.row_count == 22
        # The monitor name cell carries the two team colour squares before the name.
        assert pole_name in cell_text(monitor.get_row_at(0)[1])
        await finish_the_race(pilot, app, race)
        await pilot.press("escape")
        await pilot.pause()

        # The result screen: finishing order with 2026 points.
        result_screen = app.screen
        assert isinstance(result_screen, RaceResultScreen)
        classification_table = result_screen.query_one("#classification-table", DataTable)
        assert cell_text(classification_table.get_row_at(0)[0]) == "1"
        assert cell_text(classification_table.get_row_at(0)[5]) == "25"
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
        # Il Cap si erode solo per gli eventuali Danni del GP (FOR-23).
        damage_total = -sum(
            e.amount_usd for e in ledger.entries if e.kind is TransactionKind.DAMAGE
        )
        assert ledger.cap_remaining_usd == ledger.cap_usd - damage_total
        with connect() as connection:
            assert load_career(connection, saved_career.id).ledger == ledger


async def play_full_weekend(pilot, app, hub, first, second) -> None:
    """Gioca FP, Qualifiche e Gara fino al risultato, dalla hub weekend."""
    sessions = (
        {first: "setup", second: "tyres"},
        {first: "qualifying_focus", second: "race_pace"},
        {first: "setup", second: "strategy"},
    )
    for programmes in sessions:
        await play_practice_session(pilot, app, hub, programmes)
    # Qualifiche: rivela i tre segmenti e torna alla hub con la griglia.
    await pilot.press("g")
    await pilot.pause()
    qualifying = app.screen
    assert isinstance(qualifying, QualifyingScreen)
    for _ in range(3):
        await pilot.press("space")
    await pilot.press("escape")
    await pilot.pause()
    # Gara: scelta strategia pre-gara (default), poi alla bandiera e risultato.
    await pilot.press("g")
    await pilot.pause()
    assert isinstance(app.screen, RaceStrategyScreen)
    await pilot.click("#confirm-strategy")
    await pilot.pause()
    race = next(s for s in reversed(app.screen_stack) if isinstance(s, RaceScreen))
    await finish_the_race(pilot, app, race)
    await pilot.press("escape")
    await pilot.pause()
    result_screen = app.screen
    assert isinstance(result_screen, RaceResultScreen)
    await pilot.press("escape")
    await pilot.pause()


async def test_archive_populates_end_to_end_and_persists(db_env, saved_career, short_circuit):
    """Il GP concluso archivia davvero nell'Almanacco e l'archivio si rilegge.

    Effetto end-to-end (T5.3.2): giocare un GP intero dalla TUI scrive la
    voce di Almanacco (griglia di partenza, ordine d'arrivo, eventi
    principali) nell'archivio in memoria, e il Checkpoint di fine gara la
    persiste: ricaricando la Carriera da database l'archivio e' intatto.
    """
    first, second = player_driver_ids(saved_career)
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(saved_career))
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
        hub = app.screen
        assert isinstance(hub, WeekendScreen)

        await play_full_weekend(pilot, app, hub, first, second)

        # Archivio in memoria: la stagione 2026 ha la voce di Almanacco del
        # primo GP, con griglia di partenza e ordine d'arrivo veri.
        archive = hub.career.archive
        season = archive.season_for(2026)
        assert season is not None
        assert len(season.grands_prix) == 1
        gp = season.grands_prix[0]
        assert gp.round == 1
        # La griglia di partenza schiera sempre tutte le 22 vetture;
        # l'ordine d'arrivo combacia con quello del weekend (gli Abbandoni
        # non sono classificati, quindi possono essere meno di 22).
        assert len(gp.starting_grid) == 22
        assert gp.classification
        assert gp.classification == hub.weekend.race_classification
        assert gp.starting_grid == hub.weekend.grid_driver_ids
        # La stagione e' ancora in corso: nessun Titolo finche' non finisce.
        assert not season.is_concluded

        # Persistito davvero: ricaricando da database l'archivio combacia.
        with connect() as connection:
            reloaded = load_career(connection, saved_career.id)
        assert reloaded.archive == archive


async def _reveal_qualifying(pilot, app, hub) -> None:
    """Apre le Qualifiche (sprint o normali) dalla hub, rivela i 3 segmenti e torna."""
    await pilot.press("g")
    await pilot.pause()
    qualifying = app.screen
    assert isinstance(qualifying, QualifyingScreen)
    for _ in range(3):
        await pilot.press("space")
    await pilot.press("escape")
    await pilot.pause()
    assert app.screen is hub


async def _run_race(pilot, app, hub) -> None:
    """Apre la Gara dalla hub, la porta alla bandiera e chiude lo schermo gara."""
    await pilot.press("g")
    await pilot.pause()
    # The main race opens the pre-race strategy choice first; confirm it.
    if isinstance(app.screen, RaceStrategyScreen):
        await pilot.click("#confirm-strategy")
        await pilot.pause()
    # The race may auto-pause into the pit panel at once: find the race screen.
    race = next(screen for screen in reversed(app.screen_stack) if isinstance(screen, RaceScreen))
    await finish_the_race(pilot, app, race)
    await pilot.press("escape")
    await pilot.pause()


async def test_sprint_weekend_flow_scores_sprint_points(db_env, saved_career, short_sprint_circuit):
    """Weekend sprint intero dalla TUI: FP unica, sprint, GP; i punti sprint contano.

    Effetto end-to-end (Weekend sprint): la hub instrada le cinque sessioni
    del Formato Sprint (FP1, Qualifiche sprint, Gara sprint, Qualifiche,
    Gara). La Gara sprint assegna i punti sprint (8 al vincitore) e, a fine
    GP, quei punti entrano nelle classifiche di campionato della stagione.
    """
    career = replace(saved_career, weekend=start_weekend(short_sprint_circuit, seed=123))
    with connect() as connection:
        career = save_career(connection, career)
    first, second = player_driver_ids(career)

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        hub = WeekendScreen(career)
        app.push_screen(hub)
        await pilot.pause()
        assert hub.weekend.is_sprint
        assert "Formato weekend: Sprint" in str(hub.query_one("#weekend-sessions", Static).render())

        # A single free practice, then the sprint sessions.
        await play_practice_session(pilot, app, hub, {first: "setup", second: "tyres"})
        assert hub.weekend.phase is WeekendPhase.SPRINT_QUALIFYING

        # Sprint qualifying sets the sprint grid.
        await _reveal_qualifying(pilot, app, hub)
        assert hub.weekend.phase is WeekendPhase.SPRINT_RACE
        assert hub.weekend.sprint_grid_driver_ids is not None

        # The sprint race scores the sprint points and hands over to qualifying.
        await _run_race(pilot, app, hub)
        assert app.screen is hub
        assert hub.weekend.phase is WeekendPhase.QUALIFYING
        assert hub.weekend.sprint_classification is not None
        assert hub.weekend.sprint_classification[0].points == 8
        # The sprint result is persisted in the mid-weekend checkpoint.
        persisted = persisted_weekend(career.id)
        assert persisted.phase is WeekendPhase.QUALIFYING
        assert persisted.sprint_classification[0].points == 8

        # The normal qualifying and Grand Prix close the weekend.
        await _reveal_qualifying(pilot, app, hub)
        assert hub.weekend.phase is WeekendPhase.RACE
        await _run_race(pilot, app, hub)
        result_screen = app.screen
        assert isinstance(result_screen, RaceResultScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert hub.weekend.finished

        # The recorded round carries the sprint classification: sprint points
        # join the championship standings.
        recorded = hub.career.season.results[-1]
        assert recorded.sprint_classification
        assert recorded.sprint_classification[0].points == 8


async def test_failed_checkpoint_is_retryable_without_losing_the_session(
    db_env, saved_career, short_circuit, monkeypatch
):
    """Checkpoint fallito: errore mostrato, stato in memoria intatto, retry ok."""
    first, second = player_driver_ids(saved_career)
    failing = {"active": True}

    real_save = save_career

    def flaky_save(connection, career):
        if failing["active"]:
            raise sqlite3.OperationalError("connessione al database persa")
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
