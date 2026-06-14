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
from textual.widgets import DataTable, RadioButton, RadioSet, RichLog, Static

from fm_engine.balance.simulate import build_grid
from fm_engine.career import Career
from fm_engine.circuits import circuit_by_code
from fm_engine.commentary import CommentaryContext
from fm_engine.events import CarFailure, SafetyCarDeployed, UndercutWindow
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.preseason import PRESEASON_DAYS, PreseasonDay, PreseasonState
from fm_engine.race import start_race, step
from fm_engine.state import (
    Aggression,
    CarAttributes,
    DuelInstruction,
    RaceEntry,
    TeamOrder,
)
from fm_engine.tyres import CompoundSlot, nominated_compounds
from fm_engine.weekend import WeekendPhase
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_engine.world.models import PLAYER_TEAM_ID, Driver
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import Grid, RaceScreen, WeekendScreen
from fm_tui.screens.race import (
    UNDERCUT_AUTOPAUSE_COOLDOWN_LAPS,
    DriverOrdersPanel,
    PitOrderPanel,
    commentary_context,
    race_entries,
)

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
    # Test pre-season gia' conclusi: questo test parte dal primo GP (T5.1.2).
    preseason = PreseasonState(
        days_done=tuple(
            PreseasonDay(day=day, programmes={}) for day in range(1, PRESEASON_DAYS + 1)
        )
    )
    return Career(name="Scuderia X", world=apply_team_setup(world, choices), preseason=preseason)


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
# Undercut window auto-pause (FOR-38)
# ---------------------------------------------------------------------------

# Seed verificato: nella gara a 2 sotto (Sakhir, gara lunga e gomme che
# si consumano), con il pilota del giocatore in NO_RISK dietro al rivale,
# la finestra di undercut si apre al giro 9. Serve una gara lunga: la
# convenienza (FOR-40) chiede abbastanza giri perche' la gomma fresca
# ripaghi il pit. Il rivale AI si ferma molto piu' tardi (giro ~28).
UNDERCUT_SEED = 11
UNDERCUT_WINDOW_LAP = 9
UNDERCUT_PLAYER_DRIVER_ID = 901
UNDERCUT_RIVAL_DRIVER_ID = 902
UNDERCUT_PLAYER_SECOND_DRIVER_ID = 903


def _undercut_entry(driver_id: int, team_id: int, strength: int = 70) -> RaceEntry:
    """Una iscritta su misura per la gara a 2 della finestra di undercut."""
    driver = Driver(
        id=driver_id,
        name=f"Driver {driver_id}",
        nationality="it",
        age=28,
        one_lap_pace=strength,
        race_pace=strength,
        duels=strength,
        tyre_management=strength,
        wet_weather=strength,
        consistency=strength,
        potential=50,
        salary_demand_usd=5_000_000,
    )
    car = CarAttributes(
        engine_power=strength,
        downforce=strength,
        aero_efficiency=strength,
        mechanical_grip=strength,
        tyre_management=strength,
        reliability=strength,
    )
    return RaceEntry(driver=driver, team_id=team_id, car=car)


def undercut_window_race() -> RaceScreen:
    """Una gara a 2 dove il pilota del giocatore matura l'undercut al giro 9."""
    entries = (
        _undercut_entry(UNDERCUT_RIVAL_DRIVER_ID, team_id=5),
        _undercut_entry(UNDERCUT_PLAYER_DRIVER_ID, team_id=PLAYER_TEAM_ID),
    )
    circuit = circuit_by_code("sakhir")
    state, events = start_race(
        entries, circuit, seed=UNDERCUT_SEED, misfortune=MisfortuneConfig.disabled()
    )
    context = CommentaryContext(
        driver_names={
            UNDERCUT_PLAYER_DRIVER_ID: "Pilota Uno",
            UNDERCUT_RIVAL_DRIVER_ID: "Rivale Uno",
        }
    )
    screen = RaceScreen(state=state, initial_events=events, context=context)
    # The player driver never attacks on track: the position is only
    # winnable through the pit lane, the pair stays stable.
    screen._driver_orders[UNDERCUT_PLAYER_DRIVER_ID] = (
        Aggression.NORMAL,
        DuelInstruction.NO_RISK,
    )
    return screen


def two_player_undercut_race() -> RaceScreen:
    """Una gara con due piloti del giocatore piu' un rivale.

    Serve a coprire il caso reale (la squadra schiera 2 vetture) in cui la
    finestra di undercut riguarda il secondo pilota, non il primo della
    lista del pannello.
    """
    entries = (
        _undercut_entry(UNDERCUT_RIVAL_DRIVER_ID, team_id=5),
        _undercut_entry(UNDERCUT_PLAYER_DRIVER_ID, team_id=PLAYER_TEAM_ID),
        _undercut_entry(UNDERCUT_PLAYER_SECOND_DRIVER_ID, team_id=PLAYER_TEAM_ID),
    )
    circuit = circuit_by_code("sakhir")
    state, events = start_race(
        entries, circuit, seed=UNDERCUT_SEED, misfortune=MisfortuneConfig.disabled()
    )
    context = CommentaryContext(
        driver_names={
            UNDERCUT_PLAYER_DRIVER_ID: "Pilota Uno",
            UNDERCUT_PLAYER_SECOND_DRIVER_ID: "Pilota Due",
            UNDERCUT_RIVAL_DRIVER_ID: "Rivale Uno",
        }
    )
    return RaceScreen(state=state, initial_events=events, context=context)


def test_trigger_focus_driver_targets_the_player_in_undercut_or_failure():
    """Gli inneschi su un pilota preciso impongono il focus su quel pilota."""
    screen = undercut_window_race()
    player = UNDERCUT_PLAYER_DRIVER_ID
    rival = UNDERCUT_RIVAL_DRIVER_ID
    opportunity = UndercutWindow(lap=5, driver_id=player, target_driver_id=rival, gap_seconds=1.0)
    threat = UndercutWindow(lap=5, driver_id=rival, target_driver_id=player, gap_seconds=1.0)
    rivals_only = UndercutWindow(lap=5, driver_id=rival, target_driver_id=999, gap_seconds=1.0)
    failure = CarFailure(lap=5, driver_id=player, component="cambio")
    safety_car = SafetyCarDeployed(lap=5, duration_laps=3)
    assert screen._trigger_focus_driver((opportunity,)) == player
    assert screen._trigger_focus_driver((threat,)) == player
    assert screen._trigger_focus_driver((rivals_only,)) is None
    assert screen._trigger_focus_driver((failure,)) == player
    assert screen._trigger_focus_driver((safety_car,)) is None


async def test_undercut_panel_preselects_the_player_driver_in_the_window(db_env):
    """Con due piloti, l'Ordine di pit dell'undercut cade sul pilota giusto.

    Regressione FOR-42: il pannello pre-selezionava sempre il primo pilota
    della lista, cosi' confermando dalla finestra di undercut sul secondo
    pilota la vettura coinvolta restava in pista.
    """
    app = FormulaManagerApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        screen = two_player_undercut_race()
        app.push_screen(screen)
        await pilot.pause()

        # Pick the player driver that is NOT first in the panel list: that is
        # the one the old default would have missed.
        listed = [
            car.entry.driver.id
            for car in screen.race_state.cars
            if car.entry.team_id == PLAYER_TEAM_ID
        ]
        focus = listed[1]
        window = UndercutWindow(
            lap=screen.current_lap,
            driver_id=focus,
            target_driver_id=UNDERCUT_RIVAL_DRIVER_ID,
            gap_seconds=1.0,
        )
        screen._auto_pause((window,))
        await pilot.pause()

        panel = app.screen
        assert isinstance(panel, PitOrderPanel)
        pressed = panel.query_one("#pit-drivers", RadioSet).pressed_button
        assert pressed is not None
        assert pressed.id == f"pit-driver-{focus}"

        # Confirming with the panel as opened never queues the first-listed
        # driver: the order can only fall on the focus driver.
        soft = nominated_compounds(screen.race_state.circuit)[CompoundSlot.SOFT]
        await pilot.click(f"#pit-compound-{soft.value}")
        await pilot.click("#confirm-pit")
        await pilot.pause()
        assert listed[0] not in screen.pending_pit_orders


def test_undercut_window_triggers_only_for_player_pairs():
    """Solo la coppia che coinvolge il giocatore innesca l'Auto-pausa."""
    screen = short_race()
    player = player_driver_ids(SEED)[0]
    own = UndercutWindow(lap=5, driver_id=player, target_driver_id=999, gap_seconds=1.2)
    rivals_only = UndercutWindow(lap=5, driver_id=998, target_driver_id=999, gap_seconds=1.2)
    assert screen._new_triggers((own, rivals_only)) == (own,)
    # The handled-events registry filters the repetitions, like any trigger.
    assert screen._new_triggers((own,)) == ()


def test_undercut_descriptions_distinguish_opportunity_and_threat():
    """Il pannello descrive l'opportunita' e la minaccia con parole diverse."""
    screen = undercut_window_race()
    opportunity = UndercutWindow(
        lap=7,
        driver_id=UNDERCUT_PLAYER_DRIVER_ID,
        target_driver_id=UNDERCUT_RIVAL_DRIVER_ID,
        gap_seconds=1.0,
    )
    threat = UndercutWindow(
        lap=7,
        driver_id=UNDERCUT_RIVAL_DRIVER_ID,
        target_driver_id=UNDERCUT_PLAYER_DRIVER_ID,
        gap_seconds=1.0,
    )
    assert "Finestra di undercut" in screen._trigger_description(opportunity)
    assert "Pilota Uno" in screen._trigger_description(opportunity)
    assert "Minaccia di undercut" in screen._trigger_description(threat)
    assert "Rivale Uno" in screen._trigger_description(threat)


async def test_undercut_window_auto_pauses_with_contextual_panel(db_env):
    """Finestra di undercut propria -> Auto-pausa -> Ordine di pit -> ripresa."""
    app = FormulaManagerApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        screen = undercut_window_race()
        app.push_screen(screen)
        await pilot.pause()

        # Skip to the event: the undercut window freezes the race once.
        await pilot.press("s")
        await wait_until(
            pilot, lambda: screen.is_auto_paused, "nessuna Auto-pausa sulla finestra di undercut"
        )
        await pilot.pause()
        panel = app.screen
        assert isinstance(panel, PitOrderPanel)
        assert "undercut" in panel.description.lower()
        assert "Pilota Uno" in panel.description
        pause_lap = screen.current_lap

        # Order the pit on fresh softs to attack the rival ahead.
        soft = nominated_compounds(screen.race_state.circuit)[CompoundSlot.SOFT]
        await pilot.click(f"#pit-driver-{UNDERCUT_PLAYER_DRIVER_ID}")
        await pilot.click(f"#pit-compound-{soft.value}")
        await pilot.click("#confirm-pit")
        await pilot.pause()
        assert app.screen is screen
        assert not screen.is_paused
        assert not screen.is_auto_paused

        # The engine applies the order at the next Tick.
        await pilot.press("4")
        await wait_until(
            pilot,
            lambda: screen.current_lap >= pause_lap + 1,
            "la gara non e' ripartita dopo la decisione",
        )
        car = screen.race_state.car_of(UNDERCUT_PLAYER_DRIVER_ID)
        assert car.tyres.compound is soft


async def test_dismissed_undercut_panel_never_repauses_while_open(db_env):
    """La stessa finestra non ri-scatena l'Auto-pausa ai giri successivi."""
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = undercut_window_race()
        app.push_screen(screen)
        await pilot.pause()

        await pilot.press("s")
        await wait_until(
            pilot, lambda: screen.is_auto_paused, "nessuna Auto-pausa sulla finestra di undercut"
        )
        pause_lap = screen.current_lap

        # Close without deciding: the race resumes with no orders.
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen is screen
        assert not screen.is_paused
        assert screen.pending_pit_orders == {}

        # The window stays open on the following laps (conditions
        # unchanged), but the engine emitted it once: no second pause.
        await pilot.press("4")
        deadline = asyncio.get_running_loop().time() + WAIT_TIMEOUT_SECONDS
        while screen.current_lap < pause_lap + 3:
            if asyncio.get_running_loop().time() > deadline:
                pytest.fail("la gara non e' avanzata dopo la chiusura del pannello")
            assert not screen.is_auto_paused
            await pilot.pause(0.05)


# ---------------------------------------------------------------------------
# Undercut auto-pause tuning: cooldown and traffic (FOR-40)
# ---------------------------------------------------------------------------


def full_traffic_race(seed: int = SEED) -> RaceScreen:
    """Una gara completa a griglia piena: traffico vero per la finestra."""
    world = generate(seed)
    entries = build_grid(seed)
    circuit = circuit_by_code("monza")
    state, events = start_race(entries, circuit, seed=seed)
    return RaceScreen(state=state, initial_events=events, context=commentary_context(world))


def test_undercut_auto_pause_respects_the_cooldown():
    """Dopo un'Auto-pausa di undercut lo stesso pilota tace per il cooldown."""
    screen = short_race()
    player = player_driver_ids(SEED)[0]

    screen._state = replace(screen._state, lap=5)
    first = UndercutWindow(lap=5, driver_id=player, target_driver_id=999, gap_seconds=1.0)
    assert screen._new_triggers((first,)) == (first,)

    # A new window for the same driver within the cooldown stays silent,
    # even if the pair (the rival) has changed.
    screen._state = replace(screen._state, lap=5 + UNDERCUT_AUTOPAUSE_COOLDOWN_LAPS - 1)
    during = UndercutWindow(
        lap=screen._state.lap, driver_id=player, target_driver_id=998, gap_seconds=1.0
    )
    assert screen._new_triggers((during,)) == ()

    # Once the cooldown has elapsed the same driver can pause again.
    screen._state = replace(screen._state, lap=5 + UNDERCUT_AUTOPAUSE_COOLDOWN_LAPS)
    after = UndercutWindow(
        lap=screen._state.lap, driver_id=player, target_driver_id=997, gap_seconds=1.0
    )
    assert screen._new_triggers((after,)) == (after,)


def test_undercut_auto_pauses_stay_few_in_a_full_race():
    """In una gara trafficata la finestra non apre il pannello a ogni giro."""
    screen = full_traffic_race()
    undercut_pauses = 0
    while not screen._state.finished:
        screen._state, events = step(screen._state, screen._take_orders())
        triggers = screen._new_triggers(events)
        undercut_pauses += sum(1 for event in triggers if isinstance(event, UndercutWindow))
    # Poche unita' su tutta la gara, mai la raffica per giro del playtest.
    assert 1 <= undercut_pauses <= 12, undercut_pauses
    assert undercut_pauses < screen._state.total_laps / 3, undercut_pauses


# ---------------------------------------------------------------------------
# AI pit strategy in the interactive race (FOR-39)
# ---------------------------------------------------------------------------


async def test_ai_teams_pit_during_the_interactive_race(db_env):
    """Le squadre AI si fermano ai box anche nella Gara interattiva."""
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = short_race(laps=10)
        app.push_screen(screen)
        await pilot.pause()

        await pilot.press("s")
        await wait_for_finish(pilot, screen)

        # At least one non-player car fitted a second compound: an AI stop
        # the manager never ordered.
        cars = screen.race_state.cars + screen.race_state.dnfs
        ai_pitted = [
            car
            for car in cars
            if car.entry.team_id != PLAYER_TEAM_ID and len(car.compounds_used) > 1
        ]
        assert ai_pitted, "nessuna sosta AI nella gara interattiva"


# ---------------------------------------------------------------------------
# Driver orders: aggression, team orders, duel instructions (FOR-19)
# ---------------------------------------------------------------------------

# A terminal tall enough to show the whole orders panel for clicks.
ORDERS_TEST_SIZE = (120, 50)


def race_with_retired_player(laps: int = SHORT_RACE_LAPS) -> tuple[RaceScreen, int]:
    """Una gara dove il primo pilota del giocatore e' gia' in Abbandono."""
    world = generate(SEED)
    entries = build_grid(SEED)
    circuit = replace(circuit_by_code("monza"), race_laps=laps)
    state, events = start_race(entries, circuit, seed=SEED)
    target = player_driver_ids(SEED)[0]
    retired = next(car for car in state.cars if car.entry.driver.id == target)
    remaining = tuple(car for car in state.cars if car is not retired)
    cars = tuple(replace(car, position=index + 1) for index, car in enumerate(remaining))
    state = replace(state, cars=cars, dnfs=(replace(retired, position=0),))
    screen = RaceScreen(state=state, initial_events=events, context=commentary_context(world))
    return screen, target


def test_take_orders_feeds_engine_inputs():
    """Gli Ordini persistenti e i pit one-shot confluiscono negli input del motore."""
    screen = short_race()
    first, second = screen.driver_order_settings.keys()
    soft = nominated_compounds(screen.race_state.circuit)[CompoundSlot.SOFT]
    screen._driver_orders[first] = (Aggression.PUSH, DuelInstruction.DEFEND_HARD)
    screen._team_order = TeamOrder.HOLD_POSITIONS
    screen._pending_pits[second] = soft

    orders = screen._take_orders()
    assert orders.for_driver(first).aggression is Aggression.PUSH
    assert orders.for_driver(first).duel_instruction is DuelInstruction.DEFEND_HARD
    assert orders.for_driver(second).pit is not None
    assert orders.for_driver(second).pit.compound is soft
    assert orders.for_team(PLAYER_TEAM_ID) is TeamOrder.HOLD_POSITIONS

    # The pit queue is one-shot, the driver settings persist.
    assert screen.pending_pit_orders == {}
    again = screen._take_orders()
    assert again.for_driver(second).pit is None
    assert again.for_driver(first).aggression is Aggression.PUSH
    assert again.for_team(PLAYER_TEAM_ID) is TeamOrder.HOLD_POSITIONS


async def test_driver_orders_from_manual_pause(db_env):
    """Pausa -> pannello Ordini -> conferma -> ripresa, con feedback radio."""
    app = FormulaManagerApp()
    async with app.run_test(size=ORDERS_TEST_SIZE) as pilot:
        await pilot.pause()
        screen = short_race(laps=6)
        app.push_screen(screen)
        await pilot.pause()

        # The orders bar is visible from the start, with the defaults.
        status = screen.query_one("#orders-status", Static)
        assert "Ordini" in str(status.render())
        assert "Normale" in str(status.render())

        await pilot.press("space")
        assert screen.is_paused
        log = screen.query_one("#commentary", RichLog)
        lines_before = len(log.lines)

        await pilot.press("o")
        await pilot.pause()
        panel = app.screen
        assert isinstance(panel, DriverOrdersPanel)

        # Push and defend hard for the first player driver (preselected).
        target = player_driver_ids(SEED)[0]
        assert panel.query_one(f"#orders-driver-{target}", RadioButton).value
        await pilot.click("#orders-aggression-push")
        await pilot.click("#orders-duel-defend_hard")
        await pilot.click("#confirm-orders")
        await pilot.pause()

        # Confirm resumes the race and applies the settings.
        assert app.screen is screen
        assert not screen.is_paused
        assert screen.driver_order_settings[target] == (
            Aggression.PUSH,
            DuelInstruction.DEFEND_HARD,
        )

        # Two changed groups, two radio confirmation lines with the name.
        name = screen.race_state.car_of(target).entry.driver.name
        new_lines = commentary_text(log)[lines_before : lines_before + 2]
        assert len(new_lines) == 2
        assert all(name in line for line in new_lines)

        # The orders bar reflects the new state at once.
        assert "Push" in str(status.render())
        assert "difendi duro" in str(status.render()).lower()


async def test_orders_panel_from_auto_pause_via_pit_panel(db_env):
    """In Auto-pausa il pannello pit da' accesso al pannello Ordini."""
    app = FormulaManagerApp()
    async with app.run_test(size=ORDERS_TEST_SIZE) as pilot:
        await pilot.pause()
        screen = forced_sc_race()
        app.push_screen(screen)
        await pilot.pause()

        await wait_until(pilot, lambda: screen.is_auto_paused, "nessuna Auto-pausa sulla SC")
        assert isinstance(app.screen, PitOrderPanel)

        # The pit panel hands over to the orders panel, pause intact.
        await pilot.click("#open-orders")
        await pilot.pause()
        assert isinstance(app.screen, DriverOrdersPanel)
        assert screen.is_paused

        # Freeze the positions between the teammates and confirm.
        await pilot.click("#orders-team-hold_positions")
        await pilot.click("#confirm-orders")
        await pilot.pause()
        assert app.screen is screen
        assert not screen.is_paused
        assert screen.team_order is TeamOrder.HOLD_POSITIONS


async def test_orders_panel_disables_retired_driver(db_env):
    """Il pilota in Abbandono e' disabilitato nel pannello, con motivo visibile."""
    app = FormulaManagerApp()
    async with app.run_test(size=ORDERS_TEST_SIZE) as pilot:
        await pilot.pause()
        screen, retired_id = race_with_retired_player(laps=6)
        app.push_screen(screen)
        await pilot.pause()

        # The orders bar marks the retired driver instead of his orders.
        status = screen.query_one("#orders-status", Static)
        assert "Abbandono" in str(status.render())

        await pilot.press("space")
        await pilot.press("o")
        await pilot.pause()
        panel = app.screen
        assert isinstance(panel, DriverOrdersPanel)

        # Retired driver: disabled radio with the visible reason.
        retired_button = panel.query_one(f"#orders-driver-{retired_id}", RadioButton)
        assert retired_button.disabled
        assert "Abbandono" in str(retired_button.label)

        # The other driver is preselected and can still get orders.
        other = next(d for d in player_driver_ids(SEED) if d != retired_id)
        assert panel.query_one(f"#orders-driver-{other}", RadioButton).value
        await pilot.click("#orders-aggression-conserve")
        await pilot.click("#confirm-orders")
        await pilot.pause()
        assert screen.driver_order_settings[other][0] is Aggression.CONSERVE


# ---------------------------------------------------------------------------
# Driver orders: exclusive radio selection across driver switches (FOR-41)
# ---------------------------------------------------------------------------


def _pressed_ids(panel: DriverOrdersPanel, group: str) -> list[str]:
    """Gli id dei RadioButton premuti nel gruppo indicato del pannello."""
    return [
        button.id
        for button in panel.query(f"#orders-{group} RadioButton").results(RadioButton)
        if button.value
    ]


async def test_orders_panel_keeps_one_selection_after_driver_switch(db_env):
    """Cambiando pilota ogni gruppo resta con un solo bottone premuto (FOR-41)."""
    app = FormulaManagerApp()
    async with app.run_test(size=ORDERS_TEST_SIZE) as pilot:
        await pilot.pause()
        screen = short_race(laps=6)
        first, second = player_driver_ids(SEED)
        # Distinct orders per driver: the reload must actually move the
        # selection from one button to another.
        screen._driver_orders[first] = (Aggression.PUSH, DuelInstruction.DEFEND_HARD)
        screen._driver_orders[second] = (Aggression.CONSERVE, DuelInstruction.NO_RISK)
        app.push_screen(screen)
        await pilot.pause()

        await pilot.press("space")
        await pilot.press("o")
        await pilot.pause()
        panel = app.screen
        assert isinstance(panel, DriverOrdersPanel)

        # First driver preselected: exactly his settings are lit.
        assert _pressed_ids(panel, "aggression") == ["orders-aggression-push"]
        assert _pressed_ids(panel, "duel") == ["orders-duel-defend_hard"]

        # Switch driver, twice, then back: never two dots in a group.
        for driver_id, aggression, duel in (
            (second, "conserve", "no_risk"),
            (first, "push", "defend_hard"),
            (second, "conserve", "no_risk"),
        ):
            await pilot.click(f"#orders-driver-{driver_id}")
            await pilot.pause()
            assert _pressed_ids(panel, "aggression") == [f"orders-aggression-{aggression}"]
            assert _pressed_ids(panel, "duel") == [f"orders-duel-{duel}"]

        # The decision reflects the displayed selection, not a stale one.
        await pilot.click("#confirm-orders")
        await pilot.pause()
        assert screen.driver_order_settings[second] == (
            Aggression.CONSERVE,
            DuelInstruction.NO_RISK,
        )


async def test_pit_panel_has_one_compound_and_one_driver_selected(db_env):
    """Verifica difensiva: il PitOrderPanel apre con un solo preset per gruppo."""
    app = FormulaManagerApp()
    async with app.run_test(size=ORDERS_TEST_SIZE) as pilot:
        await pilot.pause()
        screen = short_race(laps=6)
        app.push_screen(screen)
        await pilot.pause()

        await pilot.press("space")
        await pilot.press("b")
        await pilot.pause()
        panel = app.screen
        assert isinstance(panel, PitOrderPanel)

        for group in ("pit-drivers", "pit-compounds"):
            pressed = [
                button.id
                for button in panel.query(f"#{group} RadioButton").results(RadioButton)
                if button.value
            ]
            assert len(pressed) == 1, (group, pressed)
        # The preselected compound is the medium, the documented default.
        medium = nominated_compounds(screen.race_state.circuit)[CompoundSlot.MEDIUM]
        assert panel.query_one(f"#pit-compound-{medium.value}", RadioButton).value


# ---------------------------------------------------------------------------
# Start flow: from the grid screen into the weekend (FOR-21)
# ---------------------------------------------------------------------------


async def test_grid_opens_the_weekend(db_env, ready_career):
    """Il binding g apre il flusso weekend, percorso canonico del GP."""
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(Grid(ready_career))
        await pilot.pause()

        await pilot.press("g")
        await pilot.pause()
        assert isinstance(app.screen, WeekendScreen)
        assert app.screen.NAME == "weekend"
        assert app.screen.weekend.phase is WeekendPhase.FP1

        # Escape leaves the weekend and lands back on the grid.
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, Grid)


async def test_grid_blocks_the_weekend_without_team_setup(db_env):
    """Senza Setup squadra il weekend non parte: avviso e nessun cambio schermata."""
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
