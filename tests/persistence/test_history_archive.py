"""Round-trip e accumulo dell'archivio della Carriera nel Checkpoint (T5.3.2).

Sul Postgres effimero Docker (mai matilde): l'archivio si scrive nelle
tabelle dedicate dentro save_career e si rilegge identico da load_career;
l'accumulo su piu' stagioni e' reale (le stagioni passate restano dopo
ogni Checkpoint); le query dell'Almanacco usano indici dedicati su
(career_id, year), verificati su un dataset simulato di 10+ stagioni.
"""

from dataclasses import replace

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
from fm_persistence import load_career, save_career

SEED = 13


def _classification(driver_ids, team_of):
    return tuple(
        ClassifiedResult(
            position=position,
            driver_id=driver_id,
            team_id=team_of(driver_id),
            total_time_seconds=5400.0 + position,
            gap_to_winner_seconds=float(position - 1),
            points=(25, 18, 15)[position - 1] if position <= 3 else 0,
        )
        for position, driver_id in enumerate(driver_ids, start=1)
    )


def _archived_gp(round_, driver_ids, team_of, events=()):
    classification = _classification(driver_ids, team_of)
    return build_archived_grand_prix(
        round_=round_,
        circuit_code="albert_park",
        starting_grid=list(driver_ids),
        classification=classification,
        events=events,
    )


def _finalize(archive, year, classification, driver_ids, team_ids):
    results = (RoundResult(round=1, circuit_code="albert_park", classification=classification),)
    ds, cs = final_standings(results, driver_ids, team_ids)
    return finalize_season(archive, year, ds, cs)


def test_archived_grand_prix_round_trips(conn):
    world = generate(SEED)
    driver_ids = [driver.id for driver in world.drivers]
    team_of = {c.driver_id: c.team_id for c in world.contracts}.get
    events = (
        SafetyCarDeployed(lap=4, duration_laps=2),
        Dnf(lap=9, driver_id=driver_ids[-1], cause=DnfCause.ACCIDENT, detail="contatto"),
    )
    gp = _archived_gp(1, driver_ids, lambda d: team_of(d, 0), events=events)
    archive = archive_grand_prix(CareerArchive(), 2026, gp)
    career = Career(name="Almanacco", world=world, archive=archive)

    saved = save_career(conn, career)
    loaded = load_career(conn, saved.id)

    assert loaded.archive == archive
    reloaded_gp = loaded.archive.season_for(2026).grands_prix[0]
    assert reloaded_gp.starting_grid == tuple(driver_ids)
    assert reloaded_gp.classification == gp.classification
    assert len(reloaded_gp.principal_events) == 2
    assert reloaded_gp.principal_events[0].kind.value == "safety_car"
    assert reloaded_gp.principal_events[1].driver_id == driver_ids[-1]


def test_starting_archive_round_trips_to_empty(conn):
    career = Career(name="Senza storia", world=generate(SEED))
    saved = save_career(conn, career)
    loaded = load_career(conn, saved.id)
    assert loaded.archive == CareerArchive()
    assert loaded.archive.is_empty


def test_multi_season_accumulation_survives_checkpoints(conn):
    world = generate(SEED)
    driver_ids = [driver.id for driver in world.drivers]
    team_ids = sorted({c.team_id for c in world.contracts})
    contract_team = {c.driver_id: c.team_id for c in world.contracts}
    team_of = lambda d: contract_team.get(d, 0)  # noqa: E731

    # Stagione 2026: un GP, poi fine stagione.
    gp_2026 = _archived_gp(1, driver_ids, team_of)
    archive = archive_grand_prix(CareerArchive(), 2026, gp_2026)
    archive = _finalize(archive, 2026, gp_2026.classification, driver_ids, team_ids)
    career = Career(name="Carriera lunga", world=world, archive=archive)
    saved = save_career(conn, career)

    # Stagione 2027: un altro GP, fine stagione. Checkpoint successivo.
    rotated = driver_ids[1:] + driver_ids[:1]
    gp_2027 = _archived_gp(1, rotated, team_of)
    archive = archive_grand_prix(saved.archive, 2027, gp_2027)
    archive = _finalize(archive, 2027, gp_2027.classification, driver_ids, team_ids)
    saved = save_career(conn, replace(saved, archive=archive))

    loaded = load_career(conn, saved.id)
    # Entrambe le stagioni presenti dopo il secondo Checkpoint: niente perdita.
    assert [season.year for season in loaded.archive.seasons] == [2026, 2027]
    season_2026 = loaded.archive.season_for(2026)
    assert season_2026.grands_prix[0].classification[0].driver_id == driver_ids[0]
    assert season_2026.driver_champion_id == driver_ids[0]
    season_2027 = loaded.archive.season_for(2027)
    assert season_2027.grands_prix[0].classification[0].driver_id == rotated[0]


def test_ten_plus_seasons_use_dedicated_indexes(conn):
    world = generate(SEED)
    driver_ids = [driver.id for driver in world.drivers]
    team_ids = sorted({c.team_id for c in world.contracts})
    contract_team = {c.driver_id: c.team_id for c in world.contracts}
    team_of = lambda d: contract_team.get(d, 0)  # noqa: E731

    archive = CareerArchive()
    for offset in range(12):
        year = 2026 + offset
        rotated = driver_ids[offset:] + driver_ids[:offset]
        # Tre GP per stagione, per dare massa all'Almanacco.
        for round_ in range(1, 4):
            gp = _archived_gp(round_, rotated, team_of)
            archive = archive_grand_prix(archive, year, gp)
        archive = _finalize(archive, year, gp.classification, driver_ids, team_ids)
    career = Career(name="Decennale", world=world, archive=archive)
    saved = save_career(conn, career)

    loaded = load_career(conn, saved.id)
    assert len(loaded.archive.seasons) == 12
    assert len(loaded.archive.concluded_seasons) == 12

    # Indici dedicati su (career_id, year) presenti per le tabelle d'archivio.
    cursor = conn.cursor()
    cursor.execute(
        "select name, tbl_name from sqlite_master "
        "where type = 'index' and tbl_name like 'archive_%' and name like '%career_year%'"
    )
    indexed_tables = {row[1] for row in cursor.fetchall()}
    assert {"archive_seasons", "archive_standings", "archive_grands_prix"} <= indexed_tables

    # Una query tipica dell'Almanacco filtra per (career_id, year) e usa
    # l'indice: il piano deve essere una ricerca su indice, non uno scan pieno.
    cursor.execute(
        "explain query plan select * from archive_grands_prix where career_id = ? and year = ?",
        (saved.id, 2030),
    )
    plan = " ".join(str(row[-1]) for row in cursor.fetchall()).lower()
    assert "using index" in plan


def test_next_checkpoint_rewrites_archive_without_orphans(conn):
    world = generate(SEED)
    driver_ids = [driver.id for driver in world.drivers]
    contract_team = {c.driver_id: c.team_id for c in world.contracts}
    team_of = lambda d: contract_team.get(d, 0)  # noqa: E731
    gp = _archived_gp(1, driver_ids, team_of)
    archive = archive_grand_prix(CareerArchive(), 2026, gp)
    career = Career(name="Rewrite", world=world, archive=archive)
    saved = save_career(conn, career)

    # Aggiunge un secondo GP e risalva: il rewrite non deve lasciare righe
    # del vecchio stato ne' duplicati.
    gp2 = _archived_gp(3, driver_ids, team_of)
    archive = archive_grand_prix(saved.archive, 2026, gp2)
    saved = save_career(conn, replace(saved, archive=archive))

    cursor = conn.cursor()
    cursor.execute("select count(*) from archive_grands_prix where career_id = ?", (saved.id,))
    assert cursor.fetchone()[0] == 2
    loaded = load_career(conn, saved.id)
    rounds = [gp.round for gp in loaded.archive.season_for(2026).grands_prix]
    assert rounds == [1, 3]
