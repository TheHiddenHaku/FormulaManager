"""Test Pilot delle schermate Calendario e Classifiche (T5.1.1).

Dalla griglia (la hub della Carriera) si aprono da tastiera il Calendario
(24 GP, prossimo evidenziato) e le Classifiche (tutti i piloti e le
squadre, a zero punti prima del primo GP). Dopo un GP disputato le
classifiche mostrano i punti. Le schermate leggono la Carriera in
memoria; il db_env serve solo all'elenco Carriere all'avvio.
"""

from dataclasses import replace
from datetime import date

from rich.text import Text
from textual.widgets import DataTable

from fm_engine.career import Career
from fm_engine.circuits import circuit_by_code
from fm_engine.events import ClassifiedResult
from fm_engine.points import points_for_position
from fm_engine.season import SeasonState, record_race
from fm_engine.world import generate
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import CalendarScreen, Grid, StandingsScreen
from fm_tui.screens.race_result import RaceResultScreen

SEED = 11
TEST_SIZE = (120, 50)


def cell_text(value) -> str:
    """Il contenuto testuale di una cella, sia stringa sia Text evidenziato (B03)."""
    return value.plain if isinstance(value, Text) else str(value)


def _full_classification(world) -> tuple[ClassifiedResult, ...]:
    """Una classifica di gara completa coi 22 piloti del Mondo, punti 2026."""
    driver_ids = [driver.id for driver in world.drivers]
    return tuple(
        ClassifiedResult(
            position=position,
            driver_id=driver_ids[position - 1],
            team_id=(position - 1) // 2,
            total_time_seconds=5400.0 + position,
            gap_to_winner_seconds=float(position - 1),
            points=points_for_position(position),
        )
        for position in range(1, len(driver_ids) + 1)
    )


async def test_calendar_and_standings_open_from_the_grid(db_env):
    career = Career(name="Stagione", world=generate(SEED))
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()

        # c apre il Calendario: 24 GP, round 1 evidenziato come prossimo.
        await pilot.press("c")
        await pilot.pause()
        calendar = app.screen
        assert isinstance(calendar, CalendarScreen)
        table = calendar.query_one("#calendar-table", DataTable)
        assert table.row_count == 24
        assert table.get_row_at(0)[0] == "1"
        assert table.get_row_at(0)[5] == "Prossimo <--"
        # Round 2 (Shanghai) e' uno Sprint: post-MVP, non giocabile.
        assert table.get_row_at(1)[5] == "Sprint (post-MVP)"
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, Grid)

        # l apre le Classifiche: tutti a zero prima del primo GP.
        await pilot.press("l")
        await pilot.pause()
        standings = app.screen
        assert isinstance(standings, StandingsScreen)
        drivers = standings.query_one("#drivers-standings", DataTable)
        assert drivers.row_count == 22
        assert all(
            cell_text(drivers.get_row_at(index)[3]) == "0" for index in range(drivers.row_count)
        )
        constructors = standings.query_one("#constructors-standings", DataTable)
        assert constructors.row_count == 11


async def test_standings_reflect_a_recorded_race(db_env):
    world = generate(SEED)
    # Colore squadra impostato per verificare l'evidenziazione (B03).
    world = replace(world, player_slot=replace(world.player_slot, primary_color="#ff2800"))
    classification = _full_classification(world)
    season = record_race(SeasonState(), circuit_by_code("albert_park"), classification)
    career = Career(name="Dopo il GP", world=world, season=season)
    winner_name = next(d.name for d in world.drivers if d.id == classification[0].driver_id)

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()
        standings = app.screen
        assert isinstance(standings, StandingsScreen)
        drivers = standings.query_one("#drivers-standings", DataTable)
        assert cell_text(drivers.get_row_at(0)[1]) == winner_name
        assert cell_text(drivers.get_row_at(0)[3]) == "25"
        # Squadra 0 porta a casa P1 e P2: 25 + 18 punti.
        constructors = standings.query_one("#constructors-standings", DataTable)
        assert cell_text(constructors.get_row_at(0)[2]) == "43"
        # B03: la riga del costruttore del giocatore (leader del GP) e' evidenziata
        # coi colori della squadra.
        leader_name_cell = constructors.get_row_at(0)[1]
        assert isinstance(leader_name_cell, Text)
        assert leader_name_cell.style.color is not None
        assert leader_name_cell.style.color.name == "#ff2800"

        # Il Calendario segna il GP come disputato e avanza il prossimo.
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("c")
        await pilot.pause()
        calendar_table = app.screen.query_one("#calendar-table", DataTable)
        assert calendar_table.get_row_at(0)[5] == "Disputato"
        # Round 3 (Suzuka) e' il prossimo GP standard giocabile.
        assert calendar_table.get_row_at(2)[5] == "Prossimo <--"
        # La data del prossimo GP e' quella del 2026 (Suzuka 29/03/2026).
        assert circuit_by_code("suzuka").race_date_2026 == date(2026, 3, 29)


async def test_race_result_highlights_player_rows_with_team_colour(db_env):
    """Nei risultati finali le righe dei piloti del giocatore portano il colore."""
    world = generate(SEED)
    world = replace(world, player_slot=replace(world.player_slot, primary_color="#ff2800"))
    # team_id 0 (giocatore) arriva P1 e P2; team_id 1 prende P3 e P4.
    classification = _full_classification(world)
    career = Career(name="GP", world=world)
    driver_names = {driver.id: driver.name for driver in world.drivers}
    team_names = {PLAYER_TEAM_ID: "(la tua squadra)"}
    team_names.update({team.id: team.name for team in world.ai_teams})

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(
            RaceResultScreen(
                circuit_name="Monza",
                classification=classification,
                driver_names=driver_names,
                team_names=team_names,
                career=career,
            )
        )
        await pilot.pause()
        table = app.screen.query_one("#classification-table", DataTable)
        # P1 e' un pilota del giocatore: l'intera riga e' evidenziata col colore.
        winner_name_cell = table.get_row_at(0)[1]
        assert isinstance(winner_name_cell, Text)
        assert winner_name_cell.style.color is not None
        assert winner_name_cell.style.color.name == "#ff2800"
        # P3 e' di una squadra avversaria: la riga resta testo semplice.
        rival_name_cell = table.get_row_at(2)[1]
        assert isinstance(rival_name_cell, str)
