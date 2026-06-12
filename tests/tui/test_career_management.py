"""Test Pilot della gestione Carriere (FOR-6).

Coprono il primo loop completo motore -> persistenza -> UI: empty state,
creazione fino al wizard di Setup squadra (FOR-7), elenco aggiornato
senza riavvio, riapertura da una nuova istanza dell'app, eliminazione
con conferma e annullamento. Il wizard stesso e' coperto da
test_team_setup.py.
"""

from dataclasses import replace

import psycopg
import pytest
from textual.widgets import DataTable, Input, OptionList, Static

from fm_engine.career import Career
from fm_engine.world import PlayerSlot, generate
from fm_persistence import list_careers, save_career
from fm_tui.app import FormulaManagerApp, main
from fm_tui.screens import CareerList, DeleteConfirmation, Grid, NewCareer, TeamSetup

SEED = 11


def _save_sample_career(url: str, name: str = "Scuderia X") -> Career:
    """Crea su database una Carriera completa, senza passare dalla TUI."""
    slot = PlayerSlot(name=f"{name} Racing", primary_color="#ff2800", secondary_color="bianco")
    world = replace(generate(SEED), player_slot=slot)
    with psycopg.connect(url) as connection:
        return save_career(connection, Career(name=name, world=world))


async def _fill_and_create(pilot, app: FormulaManagerApp, name: str, team: str) -> None:
    """Dal modulo di nuova Carriera: compila i campi e conferma."""
    form = app.screen
    form.query_one("#career-name-input", Input).value = name
    form.query_one("#team-name-input", Input).value = team
    form.query_one("#primary-color-input", Input).value = "#ff2800"
    form.query_one("#secondary-color-input", Input).value = "bianco"
    await pilot.press("ctrl+s")
    await pilot.pause()


async def test_empty_state_on_first_start(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, CareerList)
        assert screen.query_one("#empty-state", Static).display is True
        assert screen.query_one("#career-list", OptionList).display is False


async def test_full_creation_up_to_the_team_setup_wizard(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        assert isinstance(app.screen, NewCareer)
        assert app.screen.name == "new_career"

        # The team setup wizard (FOR-7) starts right after the creation.
        await _fill_and_create(pilot, app, "Scuderia X", "Scuderia X Racing")
        assert isinstance(app.screen, TeamSetup)
        assert app.screen.name == "team_setup"

    # The creation checkpoint is on the database.
    with psycopg.connect(db_env) as connection:
        careers = list_careers(connection)
    assert [summary.name for summary in careers] == ["Scuderia X"]


async def test_creation_without_names_shows_error_and_does_not_save(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert isinstance(app.screen, NewCareer)
        assert "nome" in str(app.screen.query_one("#error", Static).render())
    with psycopg.connect(db_env) as connection:
        assert list_careers(connection) == []


async def test_list_reflects_creation_and_deletion_without_restart(db_env):
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        # Creation: from the empty list up to the team setup wizard.
        await pilot.press("n")
        await pilot.pause()
        await _fill_and_create(pilot, app, "Scuderia X", "Scuderia X Racing")
        assert isinstance(app.screen, TeamSetup)

        # Back to the list: the new career shows up without a restart.
        await pilot.press("escape")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, CareerList)
        option_list = screen.query_one("#career-list", OptionList)
        assert option_list.display is True
        assert option_list.option_count == 1
        assert "Scuderia X" in str(option_list.get_option_at_index(0).prompt)

        # Deletion with confirmation: back to the empty state, no restart.
        await pilot.press("e")
        await pilot.pause()
        assert isinstance(app.screen, DeleteConfirmation)
        assert app.screen.name == "delete_confirmation"
        await pilot.press("s")
        await pilot.pause()
        assert isinstance(app.screen, CareerList)
        assert screen.query_one("#empty-state", Static).display is True

    with psycopg.connect(db_env) as connection:
        assert list_careers(connection) == []


async def test_reopening_from_new_instance_finds_the_same_grid(db_env):
    saved = _save_sample_career(db_env)

    # New app instance: simulates closing and relaunching fm.
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        option_list = app.screen.query_one("#career-list", OptionList)
        assert option_list.option_count == 1
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, Grid)
        table = app.screen.query_one("#teams-table", DataTable)
        assert table.row_count == 11
        grid_names = {table.get_row_at(index)[0] for index in range(table.row_count)}
        assert "Scuderia X Racing (tu)" in grid_names
        for team in saved.world.ai_teams:
            assert team.name in grid_names


async def test_cancelled_deletion_does_not_delete(db_env):
    _save_sample_career(db_env)
    app = FormulaManagerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("e")
        await pilot.pause()
        assert isinstance(app.screen, DeleteConfirmation)
        await pilot.press("n")
        await pilot.pause()
        assert isinstance(app.screen, CareerList)
        assert app.screen.query_one("#career-list", OptionList).option_count == 1
    with psycopg.connect(db_env) as connection:
        assert len(list_careers(connection)) == 1


def test_bindings_visible_in_footer_on_the_list():
    keys = {binding.key for binding in CareerList.BINDINGS}
    assert {"n", "enter", "e"} <= keys


def test_main_without_database_exits_cleanly(monkeypatch, capsys):
    """Senza FM_DATABASE_URL il gioco non parte: errore chiaro, exit 1."""
    monkeypatch.delenv("FM_DATABASE_URL", raising=False)
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 1
    assert "FM_DATABASE_URL" in capsys.readouterr().err
