"""Test Pilot delle schermate Almanacco e Albo d'oro (T5.3.2).

Dalla griglia (la hub della Carriera) si aprono da tastiera l'Almanacco
(a) e l'Albo d'oro (o), raggiungibili in ogni momento. L'Almanacco
naviga stagione -> GP -> dettaglio con back (escape) da tastiera; mostra
l'empty state senza GP archiviati. L'Albo d'oro mostra Titoli e
statistiche cumulative dai dati archiviati veri, con empty state per la
stagione in corso. Le schermate leggono la Carriera in memoria; il
db_env serve solo all'elenco Carriere all'avvio.
"""

from textual.widgets import DataTable, Static

from fm_engine.career import Career
from fm_engine.events import ClassifiedResult, Dnf, DnfCause, SafetyCarDeployed
from fm_engine.history import (
    CareerArchive,
    archive_grand_prix,
    build_archived_grand_prix,
    final_standings,
    finalize_season,
)
from fm_engine.season.standings import RoundResult
from fm_engine.world import generate
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import AlmanacScreen, Grid, HallOfFameScreen

SEED = 11
TEST_SIZE = (140, 60)


def _classification(world):
    driver_ids = [driver.id for driver in world.drivers]
    contract_team = {c.driver_id: c.team_id for c in world.contracts}
    return tuple(
        ClassifiedResult(
            position=position,
            driver_id=driver_ids[position - 1],
            team_id=contract_team.get(driver_ids[position - 1], 0),
            total_time_seconds=5400.0 + position,
            gap_to_winner_seconds=float(position - 1),
            points=(25, 18, 15)[position - 1] if position <= 3 else 0,
        )
        for position in range(1, len(driver_ids) + 1)
    )


def _career_with_one_gp(world, *, concluded: bool) -> Career:
    classification = _classification(world)
    driver_ids = [driver.id for driver in world.drivers]
    events = (
        SafetyCarDeployed(lap=3, duration_laps=2),
        Dnf(lap=8, driver_id=driver_ids[-1], cause=DnfCause.ACCIDENT, detail="contatto"),
    )
    gp = build_archived_grand_prix(
        round_=1,
        circuit_code="albert_park",
        starting_grid=driver_ids,
        classification=classification,
        events=events,
    )
    archive = archive_grand_prix(CareerArchive(), 2026, gp)
    if concluded:
        results = (RoundResult(round=1, circuit_code="albert_park", classification=classification),)
        team_ids = sorted({c.team_id for c in world.contracts})
        ds, cs = final_standings(results, driver_ids, team_ids)
        archive = finalize_season(archive, 2026, ds, cs)
    return Career(name="Con storia", world=world, archive=archive)


async def test_almanac_opens_and_navigates_with_back(db_env):
    world = generate(SEED)
    career = _career_with_one_gp(world, concluded=False)
    winner = next(d.name for d in world.drivers if d.id == _classification(world)[0].driver_id)

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()

        # a apre l'Almanacco: livello stagioni.
        await pilot.press("a")
        await pilot.pause()
        almanac = app.screen
        assert isinstance(almanac, AlmanacScreen)
        table = almanac.query_one("#almanac-table", DataTable)
        assert table.row_count == 1
        assert table.get_row_at(0)[0] == "2026"

        # Invio scende ai GP della stagione.
        await pilot.press("enter")
        await pilot.pause()
        table = almanac.query_one("#almanac-table", DataTable)
        assert table.row_count == 1
        assert table.get_row_at(0)[2] == winner  # vincitore

        # Invio apre il dettaglio: griglia, arrivo ed eventi principali.
        await pilot.press("enter")
        await pilot.pause()
        grid_table = almanac.query_one("#almanac-grid", DataTable)
        assert grid_table.row_count == 22
        result_table = almanac.query_one("#almanac-result", DataTable)
        assert result_table.row_count == 22
        assert result_table.get_row_at(0)[1] == winner
        events_table = almanac.query_one("#almanac-events", DataTable)
        assert events_table.row_count == 2  # Safety car + Abbandono

        # Esc risale ai GP, poi alle stagioni, poi chiude.
        await pilot.press("escape")
        await pilot.pause()
        assert almanac.query_one("#almanac-grid").display is False
        await pilot.press("escape")
        await pilot.pause()
        seasons_table = almanac.query_one("#almanac-table", DataTable)
        assert seasons_table.get_row_at(0)[0] == "2026"
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, Grid)


async def test_almanac_empty_state_without_archived_grands_prix(db_env):
    career = Career(name="Vuota", world=generate(SEED))
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        almanac = app.screen
        assert isinstance(almanac, AlmanacScreen)
        empty = almanac.query_one("#almanac-empty", Static)
        assert "vuoto" in str(empty.content).lower()
        # Esc chiude direttamente dall'empty state.
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, Grid)


async def test_hall_of_fame_shows_titles_and_cumulative_stats(db_env):
    world = generate(SEED)
    career = _career_with_one_gp(world, concluded=True)
    champion = next(d.name for d in world.drivers if d.id == _classification(world)[0].driver_id)

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        hall = app.screen
        assert isinstance(hall, HallOfFameScreen)
        titles = hall.query_one("#hall-of-fame", DataTable)
        assert titles.row_count == 1
        assert titles.get_row_at(0)[0] == "2026"
        assert titles.get_row_at(0)[1] == champion
        # Statistiche cumulative: il campione e' in cima con una vittoria.
        driver_table = hall.query_one("#driver-stats", DataTable)
        assert driver_table.get_row_at(0)[0] == champion
        assert driver_table.get_row_at(0)[1] == "1"  # vittorie
        assert driver_table.get_row_at(0)[4] == "1"  # Titoli
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, Grid)


async def test_hall_of_fame_empty_state_during_the_running_season(db_env):
    world = generate(SEED)
    # Stagione in corso: un GP archiviato ma nessun Titolo ancora.
    career = _career_with_one_gp(world, concluded=False)
    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()
        await pilot.press("o")
        await pilot.pause()
        hall = app.screen
        assert isinstance(hall, HallOfFameScreen)
        empty = hall.query_one("#hall-empty", Static)
        assert "vuoto" in str(empty.content).lower()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, Grid)
