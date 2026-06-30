"""Test Pilot del passaggio del tempo tra i GP (tempo-tra-i-gran-premi).

Attraversare l'intervallo verso il GP successivo fa avanzare l'orologio
di stagione: la data di gioco non resta congelata sull'ultima gara, la
DateBar mostra la data del prossimo Gran Premio e la Telecronaca di
rientro da' voce ai giorni di pausa. Un weekend aperto senza pausa (primo
GP o ripresa da Checkpoint) non mostra alcuna riga di rientro.
"""

from dataclasses import replace

from textual.widgets import Static

from fm_engine.career import Career
from fm_engine.circuits import CALENDAR_2026
from fm_engine.season import SeasonState, race_date_in, record_race
from fm_engine.weekend import WeekendPhase, WeekendState, start_weekend
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_persistence import connect, save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens import Grid, WeekendScreen
from fm_tui.widgets.date_bar import DateBar

SEED = 19


def _career_after_first_gp() -> Career:
    """Una Carriera col primo GP disputato e il weekend concluso.

    L'orologio e' sulla data della prima gara (record_race), la prima
    gara e' registrata in classifica e il weekend e' chiuso: aprire il
    GP successivo attraversa l'intervallo.
    """
    world = generate(SEED)
    world = replace(world, player_slot=PlayerSlot(name="Scuderia Tempo"))
    free_agents = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free_agents[0].id, free_agents[1].id),
        engine_supplier_id=None,
        chassis_philosophy="balanced",
    )
    season = record_race(SeasonState(), CALENDAR_2026[0], ())
    finished = WeekendState(
        circuit_code=CALENDAR_2026[0].code,
        seed=1,
        phase=WeekendPhase.FINISHED,
        race_classification=None,
    )
    return Career(
        name="Tempo",
        world=apply_team_setup(world, choices),
        weekend=finished,
        season=season,
    )


async def test_crossing_the_interval_advances_the_clock_and_announces_the_pause(
    db_env, monkeypatch
):
    """Aprendo il GP successivo la data avanza e il rientro e' raccontato."""
    # Intervallo silenzioso (nessun Evento extra-gara): dritti al weekend.
    monkeypatch.setattr("fm_tui.screens.grid.draw_extra_event", lambda *args, **kwargs: None)
    with connect() as connection:
        career = save_career(connection, _career_after_first_gp())

    next_circuit = CALENDAR_2026[1]
    last_race_date = race_date_in(CALENDAR_2026[0], 2026)
    next_race_date = race_date_in(next_circuit, 2026)
    pause_days = (next_race_date - last_race_date).days

    app = FormulaManagerApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()
        await pilot.press("g")
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, WeekendScreen)

        # La data di gioco non resta ferma all'ultima gara: la DateBar
        # mostra la data del GP successivo, raggiunta nell'intervallo.
        bar = str(screen.query_one(DateBar).render())
        assert f"Data: {next_race_date.strftime('%d/%m/%Y')}" in bar
        assert f"Data: {last_race_date.strftime('%d/%m/%Y')}" not in bar

        # La Telecronaca di rientro nomina il circuito e i giorni di pausa.
        telecronaca = str(screen.query_one("#weekend-telecronaca", Static).render())
        assert next_circuit.name in telecronaca
        assert f"{pause_days} giorni" in telecronaca


async def test_a_weekend_without_a_pause_has_no_return_to_track_line(db_env):
    """Un weekend aperto senza pausa non mostra alcuna riga di rientro."""
    world = generate(SEED)
    world = replace(world, player_slot=PlayerSlot(name="Scuderia Tempo"))
    career = Career(name="Tempo", world=world, weekend=start_weekend(CALENDAR_2026[1], seed=5))

    app = FormulaManagerApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        hub = WeekendScreen(career)
        app.push_screen(hub)
        await pilot.pause()
        assert len(hub.query("#weekend-telecronaca")) == 0
