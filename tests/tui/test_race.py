"""Test Pilot della schermata gara (FOR-17, FOR-18).

Una gara breve (circuito reale accorciato a pochi giri) viene guardata
dal via alla bandiera a scacchi: cambio velocita', pausa/riprendi e
skip-to-event non bloccano mai la UI, la Telecronaca scorre nel RichLog
e il monitor tempi mostra l'ordine d'arrivo finale. Il flusso di avvio
parte dalla schermata griglia con una Carriera a Setup squadra
completato.

Per l'Auto-pausa (FOR-18) una gara con Safety car deterministica al
giro 1 (seed fisso, Incidenti alla partenza forzati) attraversa il
flusso completo: Evento chiave -> Auto-pausa -> pannello -> Ordine di
pit -> ripresa fluida, piu' i casi pannello chiuso senza decisione e
Ordine impartito dalla pausa manuale.

La fixture db_env serve solo alla CareerList montata sotto: la gara in
se' non tocca mai il database (ADR 0001).
"""

import asyncio
from dataclasses import replace

import pytest
from textual.widgets import DataTable, RichLog

from fm_engine.balance.simulate import build_grid
from fm_engine.career import Career
from fm_engine.circuits import circuit_by_code
from fm_engine.events import SafetyCarDeployed
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.race import start_race
from fm_engine.tyres import CompoundSlot, nominated_compounds
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import Grid, RaceScreen
from fm_tui.screens.race import PitOrderPanel, commentary_context, race_entries

SEED = 11
SHORT_RACE_LAPS = 4
# Generous ceiling for the waiting loops: a 4-lap race at 4x or in skip
# mode finishes well within it.
WAIT_TIMEOUT_SECONDS = 30.0

# Seed verificato: con gli Incidenti alla partenza forzati e la
# probabilita' Safety car a 1, la SC entra al giro 1 e i 2 piloti del
# giocatore restano in gara.
FORCED_SC_SEED = 5
FORCED_SC_LAPS = 6


def short_race(laps: int = SHORT_RACE_LAPS) -> RaceScreen:
    """Una RaceScreen pronta su una gara accorciata a pochi giri."""
    world = generate(SEED)
    entries = build_grid(SEED)
    circuit = replace(circuit_by_code("monza"), race_laps=laps)
    state, events = start_race(entries, circuit, seed=SEED)
    return RaceScreen(state=state, initial_events=events, context=commentary_context(world))


def forced_sc_race() -> RaceScreen:
    """Una gara con Safety car deterministica al giro 1 (FOR-18)."""
    world = generate(FORCED_SC_SEED)
    entries = build_grid(FORCED_SC_SEED)
    circuit = replace(
        circuit_by_code("monza"), race_laps=FORCED_SC_LAPS, safety_car_probability=1.0
    )
    misfortune = replace(
        MisfortuneConfig.disabled(),
        start_contact_probability=0.25,
        accident_dnf_probability=0.5,
    )
    state, events = start_race(entries, circuit, seed=FORCED_SC_SEED, misfortune=misfortune)
    return RaceScreen(state=state, initial_events=events, context=commentary_context(world))


def player_driver_ids(seed: int) -> tuple[int, ...]:
    """Gli id dei piloti del giocatore nella Griglia del seed dato."""
    return tuple(entry.driver.id for entry in build_grid(seed) if entry.team_id == 0)


async def wait_until(pilot, predicate, message: str) -> None:
    """Attende che il predicato diventi vero tenendo vivo l'event loop."""
    deadline = asyncio.get_running_loop().time() + WAIT_TIMEOUT_SECONDS
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            pytest.fail(message)
        await pilot.pause(0.05)


async def wait_for_finish(pilot, screen: RaceScreen) -> None:
    """Attende la bandiera a scacchi tenendo vivo l'event loop di Textual.

    Se l'Auto-pausa apre il pannello lo chiude senza Ordini; se la
    gara resta in pausa o esce dallo skip, rilancia lo skip: il test
    vuole arrivare in fondo alla gara.
    """
    deadline = asyncio.get_running_loop().time() + WAIT_TIMEOUT_SECONDS
    while not screen.race_finished:
        if asyncio.get_running_loop().time() > deadline:
            pytest.fail("la gara non e' arrivata alla bandiera a scacchi in tempo")
        if isinstance(pilot.app.screen, PitOrderPanel):
            await pilot.press("escape")
        elif screen.is_paused or not screen.is_skipping:
            await pilot.press("s")
        await pilot.pause(0.05)


@pytest.fixture
def ready_career() -> Career:
    """Una Carriera con Setup squadra completato: 22 vetture schierabili."""
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
    return Career(name="Scuderia X", world=apply_team_setup(world, choices))


# ---------------------------------------------------------------------------
# Race entries: the grid of a set-up Career
# ---------------------------------------------------------------------------


def test_race_entries_full_grid(ready_career):
    entries = race_entries(ready_career.world)
    assert len(entries) == 22
    player_entries = [entry for entry in entries if entry.team_id == 0]
    assert len(player_entries) == 2
    # No duplicated drivers across the whole grid.
    driver_ids = [entry.driver.id for entry in entries]
    assert len(set(driver_ids)) == len(driver_ids)


def test_race_entries_require_team_setup():
    world = generate(SEED)
    with pytest.raises(ValueError):
        race_entries(world)


# ---------------------------------------------------------------------------
# Race screen (Pilot): controls and chequered flag
# ---------------------------------------------------------------------------


async def test_race_controls_and_chequered_flag(db_env):
    """Velocita', pausa e ripresa, poi la gara si chiude con la bandiera."""
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(short_race())
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, RaceScreen)
        assert screen.NAME == "race"

        # The live monitor shows the whole field from lap zero.
        table = screen.query_one("#monitor", DataTable)
        assert table.row_count == 22
        labels = [str(column.label) for column in table.columns.values()]
        assert labels == ["Pos", "Pilota", "Distacco", "Mescola", "Eta' gomme"]
        first_row = table.get_row_at(0)
        assert first_row[0] == "1"
        assert first_row[2] == "-"

        # The commentary opens with the race start line.
        log = screen.query_one("#commentary", RichLog)
        assert len(log.lines) >= 1

        # Speed changes: 2x then 4x, no freeze.
        await pilot.press("2")
        assert screen.speed_multiplier == 2
        await pilot.press("4")
        assert screen.speed_multiplier == 4

        # Pause: the simulation freezes, the table stays browsable.
        await pilot.press("space")
        assert screen.is_paused
        lap_when_paused = screen.current_lap
        await pilot.pause(0.5)
        assert screen.current_lap == lap_when_paused
        assert table.row_count == 22

        # Resume at 4x and watch the race to the chequered flag.
        await pilot.press("space")
        assert not screen.is_paused
        await wait_for_finish(pilot, screen)

        # The finishing order is on screen: position 1 with leader gap.
        await pilot.pause()
        final_first = table.get_row_at(0)
        assert final_first[0] == "1"
        assert final_first[2] == "-"
        positions = [table.get_row_at(index)[0] for index in range(table.row_count)]
        classified = [position for position in positions if position != "-"]
        assert classified == [str(n) for n in range(1, len(classified) + 1)]
        # The commentary announced the lights out and then the winner.
        assert len(log.lines) > 1


async def test_race_skip_to_event_reaches_the_flag(db_env):
    """Lo skip-to-event macina i Tick senza ritardi fino alla bandiera."""
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(short_race(laps=6))
        await pilot.pause()
        screen = app.screen

        await pilot.press("s")
        assert screen.is_skipping or screen.race_finished or screen.is_paused
        await wait_for_finish(pilot, screen)

        assert screen.race_finished
        table = screen.query_one("#monitor", DataTable)
        assert table.get_row_at(0)[0] == "1"


# ---------------------------------------------------------------------------
# Auto-pause and pit orders (FOR-18)
# ---------------------------------------------------------------------------


def commentary_text(log: RichLog) -> list[str]:
    """Le righe correnti del RichLog come testo semplice."""
    return [strip.text for strip in log.lines]


async def test_key_event_auto_pauses_once_with_contextual_panel(db_env):
    """Evento chiave -> Auto-pausa -> Ordine di pit -> ripresa fluida."""
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = forced_sc_race()
        app.push_screen(screen)
        await pilot.pause()

        # The deterministic Safety car on lap 1 freezes the simulation
        # and opens the contextual decision panel.
        await wait_until(pilot, lambda: screen.is_auto_paused, "nessuna Auto-pausa sulla SC")
        panel = app.screen
        assert isinstance(panel, PitOrderPanel)
        assert "Safety car" in panel.description
        pause_lap = screen.current_lap
        assert pause_lap == 1
        log = screen.query_one("#commentary", RichLog)
        lines_at_pause = len(log.lines)
        assert any("safety car" in line.lower() for line in commentary_text(log))

        # Frozen for real: no Ticks while the panel is open.
        await pilot.pause(0.3)
        assert screen.current_lap == pause_lap

        # Order the pit for the first player driver on the soft tyre
        # (the default starting set is the medium).
        target = player_driver_ids(FORCED_SC_SEED)[0]
        soft = nominated_compounds(screen.race_state.circuit)[CompoundSlot.SOFT]
        await pilot.click(f"#pit-driver-{target}")
        await pilot.click(f"#pit-compound-{soft.value}")
        await pilot.click("#confirm-pit")
        await pilot.pause()

        # The panel is gone and the race resumed where it stopped.
        assert app.screen is screen
        assert not screen.is_paused
        assert not screen.is_auto_paused

        # The engine applies the order at the next Tick: fresh soft
        # set, pit lines in the commentary, no lines lost in between.
        await wait_until(
            pilot,
            lambda: screen.current_lap >= pause_lap + 1,
            "la gara non e' ripartita dopo la decisione",
        )
        car = screen.race_state.car_of(target)
        assert car.tyres.compound is soft
        assert soft in car.compounds_used
        assert len(log.lines) > lines_at_pause
        await pilot.pause()
        name = screen.race_state.car_of(target).entry.driver.name
        new_lines = commentary_text(log)[lines_at_pause:]
        assert any(name in line for line in new_lines)


async def test_dismissed_panel_resumes_and_the_same_event_never_repauses(db_env):
    """Pannello chiuso senza decidere: ripresa senza Ordini, mai doppia Auto-pausa."""
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = forced_sc_race()
        app.push_screen(screen)
        await pilot.pause()

        await wait_until(pilot, lambda: screen.is_auto_paused, "nessuna Auto-pausa sulla SC")
        assert isinstance(app.screen, PitOrderPanel)
        pause_lap = screen.current_lap

        # Close without deciding: the race resumes with no orders.
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen is screen
        assert not screen.is_paused
        assert screen.pending_pit_orders == {}

        # The Safety car stays out for the following laps, but the same
        # key event never triggers a second auto-pause.
        await pilot.press("4")
        deadline = asyncio.get_running_loop().time() + WAIT_TIMEOUT_SECONDS
        while screen.current_lap < pause_lap + 2:
            if asyncio.get_running_loop().time() > deadline:
                pytest.fail("la gara non e' avanzata dopo la chiusura del pannello")
            assert not screen.is_auto_paused
            await pilot.pause(0.05)


def test_same_key_event_is_a_trigger_only_once():
    """Il registro degli Eventi chiave gestiti filtra le ripetizioni."""
    screen = forced_sc_race()
    event = SafetyCarDeployed(lap=3, duration_laps=2)
    assert screen._new_triggers((event,)) == (event,)
    assert screen._new_triggers((event,)) == ()


async def test_pit_order_from_manual_pause(db_env):
    """L'Ordine di pit con scelta della Mescola e' impartibile in pausa manuale."""
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = short_race(laps=6)
        app.push_screen(screen)
        await pilot.pause()

        # Manual pause, then the box key opens the same panel.
        await pilot.press("space")
        assert screen.is_paused
        assert not screen.is_auto_paused
        await pilot.press("b")
        await pilot.pause()
        panel = app.screen
        assert isinstance(panel, PitOrderPanel)

        # Closing without deciding keeps the manual pause.
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen is screen
        assert screen.is_paused

        # Reopen and order the pit for the second player driver.
        second = player_driver_ids(SEED)[1]
        soft = nominated_compounds(screen.race_state.circuit)[CompoundSlot.SOFT]
        await pilot.press("b")
        await pilot.pause()
        await pilot.click(f"#pit-driver-{second}")
        await pilot.click(f"#pit-compound-{soft.value}")
        await pilot.click("#confirm-pit")
        await pilot.pause()

        # Fluid resume, and the engine applies the order at the next Tick.
        assert not screen.is_paused
        lap_at_resume = screen.current_lap
        await wait_until(
            pilot,
            lambda: screen.current_lap >= lap_at_resume + 1,
            "la gara non e' ripartita dopo l'Ordine in pausa manuale",
        )
        car = screen.race_state.car_of(second)
        assert car.tyres.compound is soft


# ---------------------------------------------------------------------------
# Start flow: from the grid screen into the race
# ---------------------------------------------------------------------------


async def test_grid_starts_the_race(db_env, ready_career):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(Grid(ready_career))
        await pilot.pause()

        await pilot.press("g")
        await pilot.pause()
        assert isinstance(app.screen, RaceScreen)
        assert app.screen.NAME == "race"
        table = app.screen.query_one("#monitor", DataTable)
        assert table.row_count == 22

        # Escape leaves the race and lands back on the grid.
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, Grid)


async def test_grid_blocks_the_race_without_team_setup(db_env):
    """Senza Setup squadra la gara non parte: avviso e nessun cambio schermata."""
    world = replace(generate(SEED), player_slot=PlayerSlot(name="Scuderia X Racing"))
    career = Career(name="Scuderia X", world=world)
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()

        await pilot.press("g")
        await pilot.pause()
        assert isinstance(app.screen, Grid)
