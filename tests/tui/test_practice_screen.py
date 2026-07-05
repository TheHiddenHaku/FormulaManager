"""Test Pilot della schermata prove libere (FOR-20, FOR-21).

Flusso assegna Programma -> sessione -> report: scheda circuito con
Mescole nominate e previsione meteo, slot Programma per pilota, lancio
con conferma per i Programmi mancanti (default segnalato nel report),
report di fine sessione e Classifica tempi esatta. La schermata gioca
UNA sessione del weekend (FOR-21) e alla chiusura restituisce l'esito
al chiamante; gli effetti ricevuti in ingresso si cumulano. Database
SQLite temporaneo via db_env.
"""

from dataclasses import replace

import pytest
from rich.text import Text
from textual.widgets import DataTable, Select, Static

from fm_engine.circuits import CALENDAR_2026
from fm_engine.practice import PracticeSession, simulate_practice_session
from fm_engine.world import PlayerSlot, generate
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_engine.world.team_setup import TeamSetupChoices, apply_team_setup
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import PracticeScreen
from fm_tui.screens.practice import DefaultProgrammeConfirmation
from fm_tui.screens.race import race_entries

SEED = 23
CIRCUIT_SEED = 99


@pytest.fixture
def ready_world():
    """Un Mondo col Setup squadra completato: pronto a scendere in pista."""
    slot = PlayerSlot(name="Scuderia X Racing", primary_color="#ff2800", secondary_color="bianco")
    world = replace(generate(SEED), player_slot=slot)
    free_agents = tuple(driver.id for driver in world.drivers_without_contract)
    choices = TeamSetupChoices(
        driver_ids=free_agents[:2],
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    return apply_team_setup(world, choices)


def _practice_screen(world, session=PracticeSession.FP1, effects=None):
    return PracticeScreen(
        world=world,
        circuit=CALENDAR_2026[0],
        seed=CIRCUIT_SEED,
        session=session,
        effects=effects,
    )


def _player_driver_ids(world):
    return tuple(contract.driver_id for contract in world.contracts_of(PLAYER_TEAM_ID))


async def test_practice_screen_shows_the_circuit_card(db_env, ready_world):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.push_screen(_practice_screen(ready_world))
        await pilot.pause()

        assert app.screen.name == "practice"
        card = str(app.screen.query_one("#circuit-card", Static).render())
        assert "Albert Park" in card
        # Nominated compounds with their relative role.
        for label in ("Soft", "Medium", "Hard"):
            assert label in card
        # Weekend weather forecast and track characteristics.
        assert "pioggia" in card
        assert "Severita' gomme" in card
        # One programme slot per player driver.
        selects = app.screen.query(Select)
        assert len(selects) == len(_player_driver_ids(ready_world))


async def test_assign_programmes_launch_and_read_the_report(db_env, ready_world):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = _practice_screen(ready_world)
        app.push_screen(screen)
        await pilot.pause()

        first, second = _player_driver_ids(ready_world)
        screen.query_one(f"#programme-{first}", Select).value = "setup"
        screen.query_one(f"#programme-{second}", Select).value = "tyres"
        await pilot.press("l")
        await pilot.pause()

        # FP1 done, no confirmation needed: every driver had a programme.
        assert screen.session_played
        report = str(screen.query_one("#session-report", Static).render())
        assert "Report FP1" in report
        assert "Setup al" in report
        assert "Curve di Degrado rivelate" in report
        assert "(default)" not in report

        # The exact timesheet covers all 22 cars.
        table = screen.query_one("#timesheet", DataTable)
        assert table.row_count == 22
        assert table.get_row_at(0)[0] == "1"


async def test_incoming_effects_accumulate_across_sessions(db_env, ready_world):
    """FP2 riceve gli effetti di FP1 e li cumula nel weekend (FOR-21)."""
    first, second = _player_driver_ids(ready_world)
    fp1 = simulate_practice_session(
        race_entries(ready_world),
        CALENDAR_2026[0],
        PracticeSession.FP1,
        {first: None, second: None},
        seed=CIRCUIT_SEED,
    )
    setup_after_fp1 = fp1.effects.for_driver(first).setup_percentage

    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = _practice_screen(ready_world, session=PracticeSession.FP2, effects=fp1.effects)
        app.push_screen(screen)
        await pilot.pause()

        screen.query_one(f"#programme-{first}", Select).value = "setup"
        screen.query_one(f"#programme-{second}", Select).value = "qualifying_focus"
        await pilot.press("l")
        await pilot.pause()

        assert screen.session_played
        assert screen.effects.for_driver(first).setup_percentage > setup_after_fp1
        assert screen.effects.for_driver(second).qualifying_bonus_seconds > 0.0
        report = str(screen.query_one("#session-report", Static).render())
        assert "Report FP2" in report


async def test_launch_without_programme_asks_confirmation_and_flags_default(db_env, ready_world):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = _practice_screen(ready_world)
        app.push_screen(screen)
        await pilot.pause()

        # No programme assigned: the launch asks for confirmation.
        await pilot.press("l")
        await pilot.pause()
        assert isinstance(app.screen, DefaultProgrammeConfirmation)
        assert not screen.session_played

        # Confirm: the session runs with the default programme, flagged.
        await pilot.press("s")
        await pilot.pause()
        assert screen.session_played
        report = str(screen.query_one("#session-report", Static).render())
        assert "(default)" in report
        assert all(item.defaulted for item in screen.result.reports)


async def test_cancelling_the_confirmation_does_not_launch(db_env, ready_world):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = _practice_screen(ready_world)
        app.push_screen(screen)
        await pilot.pause()

        await pilot.press("l")
        await pilot.pause()
        assert isinstance(app.screen, DefaultProgrammeConfirmation)
        await pilot.press("n")
        await pilot.pause()
        assert not screen.session_played


async def test_one_session_per_screen_and_dismiss_returns_the_result(db_env, ready_world):
    """Una sola sessione per schermata; esc restituisce l'esito al chiamante."""
    outcome: list[object] = []
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = _practice_screen(ready_world)
        app.push_screen(screen, outcome.append)
        await pilot.pause()

        first, second = _player_driver_ids(ready_world)
        screen.query_one(f"#programme-{first}", Select).value = "setup"
        screen.query_one(f"#programme-{second}", Select).value = "race_pace"
        await pilot.press("l")
        await pilot.pause()
        assert screen.session_played

        # A second launch does nothing: one session per screen.
        await pilot.press("l")
        await pilot.pause()
        assert not isinstance(app.screen, DefaultProgrammeConfirmation)

        await pilot.press("escape")
        await pilot.pause()
        assert outcome and outcome[0] is screen.result
        assert outcome[0].session is PracticeSession.FP1


async def test_dismiss_before_launching_returns_none(db_env, ready_world):
    outcome: list[object] = ["sentinel"]
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = _practice_screen(ready_world)

        def on_close(result) -> None:
            outcome[0] = result

        app.push_screen(screen, on_close)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert outcome[0] is None


async def test_player_drivers_highlighted_in_the_timesheet(db_env, ready_world):
    """Colorazione pilota: i piloti del giocatore sono evidenziati come in classifica."""
    first, second = _player_driver_ids(ready_world)
    player_ids = set(_player_driver_ids(ready_world))
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = _practice_screen(ready_world)
        app.push_screen(screen)
        await pilot.pause()
        screen.query_one(f"#programme-{first}", Select).value = "setup"
        screen.query_one(f"#programme-{second}", Select).value = "tyres"
        await pilot.press("l")
        await pilot.pause()

        table = screen.query_one("#timesheet", DataTable)
        highlighted = 0
        for index in range(table.row_count):
            driver_id = screen.result.classification[index].driver_id
            name_cell = table.get_row_at(index)[1]
            if driver_id in player_ids:
                assert isinstance(name_cell, Text)
                assert name_cell.style.color is not None
                assert name_cell.style.color.name == "#ff2800"
                highlighted += 1
            else:
                # Rivals carry the team colour squares but no player highlight.
                assert isinstance(name_cell, Text)
                assert name_cell.style.color is None
        assert highlighted == 2


def test_practice_screen_registered_with_a_stable_name():
    assert PracticeScreen.NAME == "practice"
