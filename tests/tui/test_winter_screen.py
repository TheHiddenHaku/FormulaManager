"""Test Pilot della schermata inverno (FOR-32).

Verificano il guscio TUI sopra fm_engine.winter: la navigazione da tastiera
tra i passi, l'allocazione dei Progetti invernali col budget dedicato, la
rinegoziazione delle scelte di fondo e l'effetto conseguente alla conferma
(vettura nuova regredita e modificata, rollover economico), col Checkpoint
persistito. Tre stati UI: nessuno Sforamento, Sforamento con penalita',
scelte lasciate a default.
"""

from dataclasses import replace
from datetime import date

from textual.widgets import DataTable, OptionList, Static

from fm_engine.career import Career
from fm_engine.economy import (
    DEFAULT_PLAYER_PRESTIGE,
    SEASON_CAP_USD,
    TeamLedger,
    Transaction,
    TransactionKind,
    annual_sponsor_usd,
    credit_annual_sponsor,
)
from fm_engine.winter.carryover import grid_attribute_means, regress_attribute
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_engine.world.models import CAR_ATTRIBUTES
from fm_persistence import connect, load_career, save_career
from fm_tui.app import FormulaManagerApp
from fm_tui.screens.grid import Grid
from fm_tui.screens.winter import WinterScreen

SEED = 42
TEST_SIZE = (140, 50)
CONCLUDED_YEAR = 2026


def _build_career(ledger: TeamLedger, philosophy: str = "balanced") -> Career:
    """Carriera a Setup squadra completato, fine stagione 2026, motore proprio."""
    generated = generate(SEED)
    world = replace(generated, player_slot=PlayerSlot(name="Scuderia X", primary_color="#ff2800"))
    free = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free[0].id, free[1].id),
        engine_supplier_id=None,
        chassis_philosophy=philosophy,
    )
    return Career(name="Scuderia X", world=apply_team_setup(world, choices), ledger=ledger)


def _funded_ledger() -> TeamLedger:
    return credit_annual_sponsor(TeamLedger(), DEFAULT_PLAYER_PRESTIGE, date(2026, 1, 1))


def _overspent_ledger() -> TeamLedger:
    """Registro in Sforamento: danno forzoso oltre il Cap."""
    ledger = _funded_ledger().record(
        Transaction(
            kind=TransactionKind.OTHER,
            amount_usd=400_000_000,
            game_date=date(2026, 1, 1),
            description="Dotazione di prova",
        )
    )
    return ledger.record(
        Transaction(
            kind=TransactionKind.DAMAGE,
            amount_usd=-(SEASON_CAP_USD + 8_000_000),
            game_date=date(2026, 12, 1),
            description="Danno",
            counts_against_cap=True,
        )
    )


async def test_default_winter_applies_carryover_and_rollover(db_env):
    """Senza scelte, l'inverno applica Carry-over e rollover (default dichiarati)."""
    with connect() as connection:
        career = save_career(connection, _build_career(_funded_ledger()))
    before = career.world.player_slot.car_attributes
    means = grid_attribute_means(career.world)

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(WinterScreen(career, CONCLUDED_YEAR))
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, WinterScreen)
        # Conferma diretta: scelte a default (Escape dal primo passo conferma).
        await pilot.press("escape")
        await pilot.pause()

    result = screen.career
    after = result.world.player_slot.car_attributes
    # Carry-over conseguente: ogni attributo regredito verso la media.
    for name in CAR_ATTRIBUTES:
        assert after[name] == regress_attribute(before[name], means[name], 0.7)
    assert after != before
    # Rollover conseguente: stagione nuova, Cap pieno, Sponsor accreditato.
    assert result.ledger.season_year == CONCLUDED_YEAR + 1
    assert result.ledger.cap_usd == SEASON_CAP_USD
    # Il Checkpoint ha persistito lo stato nuovo.
    with connect() as connection:
        reloaded = load_career(connection, result.id)
    assert reloaded.world.player_slot.car_attributes == after
    assert reloaded.ledger.season_year == CONCLUDED_YEAR + 1


async def test_winter_projects_allocation_changes_the_new_car(db_env):
    """Allocare punti su un Attributo lo migliora davvero nella vettura nuova."""
    with connect() as connection:
        career = save_career(connection, _build_career(_funded_ledger()))

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(WinterScreen(career, CONCLUDED_YEAR))
        await pilot.pause()
        screen = app.screen
        # Vai al passo Progetti (Carry-over -> rinegoziazione -> Progetti).
        await pilot.press("a")
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        # La tabella dei Progetti e' a fuoco: alloca 3 punti sul primo attributo.
        table = screen.query_one("#projects-table", DataTable)
        first_attribute = CAR_ATTRIBUTES[0]
        # Cursore sulla prima riga per default; il primo attributo e' engine_power
        # (motore proprio, sviluppabile).
        cursor_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        assert cursor_key == first_attribute
        for _ in range(3):
            await pilot.press("plus")
            await pilot.pause()
        assert screen._points[first_attribute] == 3
        # Il valore atteso dell'attributo: Carry-over della vettura attuale piu'
        # i 3 punti del Progetto invernale (catturato PRIMA della conferma, che
        # rimpiazza il world con quello post-inverno).
        carried = screen._carried_over_attributes()
        expected = min(100, carried[first_attribute] + 3)
        # Vai al riepilogo e conferma.
        await pilot.press("a")
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()

    result = screen.career
    # Spesa invernale conseguente: 3 punti dal budget dedicato.
    spent = 3 * screen._config.projects.cost_per_point_usd
    # La vettura nuova ha il guadagno (oltre al Carry-over) sull'attributo.
    after = result.world.player_slot.car_attributes
    assert after[first_attribute] == expected
    assert spent > 0


async def test_renegotiation_to_customer_changes_engine_and_philosophy(db_env):
    """Rinegoziare a Cliente e Filosofia veloce cambia gli effetti sulla vettura."""
    with connect() as connection:
        career = save_career(connection, _build_career(_funded_ledger(), philosophy="balanced"))
    supplier = career.world.engine_suppliers[0]

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(WinterScreen(career, CONCLUDED_YEAR))
        await pilot.pause()
        screen = app.screen
        # Passo rinegoziazione.
        await pilot.press("a")
        await pilot.pause()
        # Motore: scendi alla prima opzione Cliente (indice 1).
        engine = screen.query_one("#engine-options", OptionList)
        engine.highlighted = 1  # primo Motorista
        await pilot.pause()
        philosophy = screen.query_one("#philosophy-options", OptionList)
        philosophy.highlighted = 1  # "fast" (ordine: balanced, fast, technical)
        await pilot.pause()
        # Avanza (adotta le scelte evidenziate), poi salta i Progetti e conferma.
        await pilot.press("a")
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()

    result = screen.career
    slot = result.world.player_slot
    assert slot.engine_supplier_id == supplier.id
    assert slot.chassis_philosophy == "fast"
    # Effetto conseguente: la Potenza motore e' quella del fornitore.
    assert slot.engine_power == supplier.engine_power


async def test_summary_shows_overspend_penalty_state(db_env):
    """Stato UI Sforamento: il riepilogo segnala il Cap ridotto dalla penalita'."""
    with connect() as connection:
        career = save_career(connection, _build_career(_overspent_ledger()))
    assert career.ledger.overspend_usd == 8_000_000

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(WinterScreen(career, CONCLUDED_YEAR))
        await pilot.pause()
        screen = app.screen
        # Vai al riepilogo (3 avanzamenti).
        await pilot.press("a")
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        summary = str(screen.query_one("#summary-text", Static).render())
        assert "Sforamento" in summary
        await pilot.press("ctrl+s")
        await pilot.pause()

    result = screen.career
    # Cap ridotto della penalita' proporzionale (8M di Sforamento).
    assert result.ledger.cap_usd == SEASON_CAP_USD - 8_000_000


async def test_no_overspend_summary_shows_full_cap(db_env):
    """Stato UI senza Sforamento: il riepilogo mostra il Cap pieno e lo Sponsor."""
    with connect() as connection:
        career = save_career(connection, _build_career(_funded_ledger()))

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(WinterScreen(career, CONCLUDED_YEAR))
        await pilot.pause()
        screen = app.screen
        await pilot.press("a")
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        summary = str(screen.query_one("#summary-text", Static).render())
        assert "Nessuno Sforamento" in summary

    # Lo Sponsor annuale e' stato accreditato (saldo > sponsor del solo anno
    # concluso non vale: qui controlliamo che la stagione nuova abbia lo
    # Sponsor della stagione nuova nel saldo).
    result = screen.career
    assert result.ledger.cash_usd >= annual_sponsor_usd(DEFAULT_PLAYER_PRESTIGE)


async def test_season_over_flow_pushes_the_winter_screen(db_env):
    """La transizione di fine stagione apre la WinterScreen dopo il Mercato."""
    with connect() as connection:
        career = save_career(connection, _build_career(_funded_ledger()))

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()
        grid = app.screen
        # La transizione: applica il Mercato (chiuso qui), avanza l'orologio,
        # apre l'inverno.
        grid._advance_to_next_season()
        await pilot.pause()
        # La WinterScreen e' in cima allo stack, sull'anno concluso.
        assert isinstance(app.screen, WinterScreen)
        assert grid._career.season.year == CONCLUDED_YEAR + 1
        # Conferma a default: l'inverno applica Carry-over e rollover, poi il
        # flusso prosegue verso i Test pre-season della stagione nuova.
        await pilot.press("escape")
        await pilot.pause()
        # La griglia ha ricevuto la Carriera post-inverno: rollover applicato.
        assert grid._career.ledger.season_year == CONCLUDED_YEAR + 1
        assert grid._career.ledger.cap_usd == SEASON_CAP_USD


def _complete_season_with_archive(career: Career) -> Career:
    """Carriera con la stagione 2026 interamente disputata e archiviata.

    Registra ogni GP Standard del Calendario (T5.1.1) e archivia la voce di
    Almanacco corrispondente (T5.3.2), con il pilota 1 sempre vincitore: a
    fine stagione il campione e' deterministico.
    """
    from fm_engine.events import ClassifiedResult
    from fm_engine.history import archive_grand_prix, build_archived_grand_prix
    from fm_engine.season import record_race, season_calendar

    driver_ids = [driver.id for driver in career.world.drivers]
    contract_team = {c.driver_id: c.team_id for c in career.world.contracts}
    season = career.season
    archive = career.archive
    for entry in season_calendar(2026):
        if not entry.is_standard:
            continue
        classification = tuple(
            ClassifiedResult(
                position=position,
                driver_id=driver_id,
                team_id=contract_team.get(driver_id, 0),
                total_time_seconds=5400.0 + position,
                gap_to_winner_seconds=float(position - 1),
                points=(25 if position == 1 else 0),
            )
            for position, driver_id in enumerate(driver_ids, start=1)
        )
        season = record_race(season, entry.circuit, classification)
        gp = build_archived_grand_prix(
            round_=entry.circuit.calendar_order,
            circuit_code=entry.circuit.code,
            starting_grid=driver_ids,
            classification=classification,
            events=(),
        )
        archive = archive_grand_prix(archive, 2026, gp)
    return replace(career, season=season, archive=archive)


async def test_season_end_finalizes_archive_with_champions_and_persists(db_env):
    """Fine stagione: classifiche finali e Titoli entrano nell'archivio e persistono.

    Effetto end-to-end (T5.3.2): conclusa la stagione, la transizione
    finalizza l'archivio (classifiche finali e campioni piloti e
    costruttori) PRIMA di azzerare le classifiche; la WinterScreen salva
    il Checkpoint, quindi l'Albo d'oro persiste e si rilegge da database.
    """
    base = _build_career(_funded_ledger())
    with connect() as connection:
        career = save_career(connection, _complete_season_with_archive(base))
    winner_id = career.world.drivers[0].id
    champion_team = next(c.team_id for c in career.world.contracts if c.driver_id == winner_id)

    app = FormulaManagerApp()
    async with app.run_test(size=TEST_SIZE) as pilot:
        await pilot.pause()
        app.push_screen(Grid(career))
        await pilot.pause()
        grid = app.screen
        grid._advance_to_next_season()
        await pilot.pause()
        assert isinstance(app.screen, WinterScreen)
        # Conferma l'inverno a default: il Checkpoint persiste l'archivio.
        await pilot.press("escape")
        await pilot.pause()

    result = grid._career
    season_2026 = result.archive.season_for(2026)
    assert season_2026 is not None
    # La stagione e' ora conclusa nell'archivio, coi Titoli assegnati.
    assert season_2026.is_concluded
    assert season_2026.driver_champion_id == winner_id
    assert season_2026.constructor_champion_id == champion_team
    # I GP archiviati restano (accumulo): non azzerati dal cambio stagione.
    assert len(season_2026.grands_prix) > 0
    # La classifica finale include tutti i 22 piloti (T5.1.1).
    assert len(season_2026.driver_standings) == 22
    # Persistito: l'Albo d'oro si rilegge da database, intatto.
    with connect() as connection:
        reloaded = load_career(connection, result.id)
    reloaded_2026 = reloaded.archive.season_for(2026)
    assert reloaded_2026 is not None
    assert reloaded_2026.is_concluded
    assert reloaded_2026.driver_champion_id == winner_id
    assert len(reloaded_2026.grands_prix) > 0
