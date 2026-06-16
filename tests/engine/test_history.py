"""Archivio della Carriera: accumulo, statistiche cumulative, Albo d'oro (T5.3.2).

Dataset noto e deterministico (niente RNG): si costruiscono GP archiviati
a mano e si verifica che le statistiche (vittorie, podi, pole, Titoli) e
l'Albo d'oro riflettano esattamente i dati archiviati. Si verifica anche
l'accumulo su piu' stagioni senza perdita e il filtro degli eventi
principali (Safety car e Abbandoni, niente Telecronaca integrale).

Calcolo puro (ADR 0002): nessun database, nessuna TUI.
"""

from fm_engine.events import ClassifiedResult, Dnf, DnfCause, FastestLap, SafetyCarDeployed
from fm_engine.history import (
    CareerArchive,
    PrincipalEventKind,
    archive_grand_prix,
    build_archived_grand_prix,
    driver_stats,
    final_standings,
    finalize_season,
    hall_of_fame,
    team_stats,
)
from fm_engine.season.standings import RoundResult


def _result(position: int, driver_id: int, team_id: int, points: int) -> ClassifiedResult:
    return ClassifiedResult(
        position=position,
        driver_id=driver_id,
        team_id=team_id,
        total_time_seconds=5400.0 + position,
        gap_to_winner_seconds=float(position - 1),
        points=points,
    )


def _grand_prix(round_: int, order: list[tuple[int, int]], grid: list[int]):
    """Una voce di Almanacco: order e' (driver_id, team_id) per posizione."""
    classification = tuple(
        _result(position, driver_id, team_id, points=(25 if position == 1 else 0))
        for position, (driver_id, team_id) in enumerate(order, start=1)
    )
    return build_archived_grand_prix(
        round_=round_,
        circuit_code="albert_park",
        starting_grid=grid,
        classification=classification,
        events=(),
    )


def test_principal_events_keep_only_safety_car_and_dnf():
    gp = build_archived_grand_prix(
        round_=1,
        circuit_code="suzuka",
        starting_grid=[10, 20, 30],
        classification=(_result(1, 10, 0, 25),),
        events=(
            FastestLap(lap=5, driver_id=10, time_seconds=80.0),
            SafetyCarDeployed(lap=7, duration_laps=3),
            Dnf(lap=12, driver_id=30, cause=DnfCause.FAILURE, detail="motore"),
        ),
    )
    kinds = [event.kind for event in gp.principal_events]
    assert kinds == [PrincipalEventKind.SAFETY_CAR, PrincipalEventKind.DNF]
    dnf_event = gp.principal_events[1]
    assert dnf_event.driver_id == 30
    assert "Guasto" in dnf_event.detail
    assert gp.pole_driver_id == 10


def test_driver_stats_on_a_known_dataset():
    # Pilota 1 vince il round 1 e il round 2, sempre in pole; pilota 2 e' P2;
    # pilota 3 e' P3. Pole sempre al pilota 1.
    gp1 = _grand_prix(1, [(1, 0), (2, 0), (3, 1), (4, 1)], grid=[1, 2, 3, 4])
    gp2 = _grand_prix(2, [(1, 0), (3, 1), (2, 0), (4, 1)], grid=[1, 3, 2, 4])
    archive = archive_grand_prix(CareerArchive(), 2026, gp1)
    archive = archive_grand_prix(archive, 2026, gp2)

    stats = {entry.driver_id: entry for entry in driver_stats(archive)}
    assert stats[1].wins == 2
    assert stats[1].podiums == 2
    assert stats[1].poles == 2
    assert stats[1].titles == 0  # stagione non ancora conclusa
    # Pilota 2: P2 e P3 -> due podi, nessuna vittoria, nessuna pole.
    assert stats[2].wins == 0
    assert stats[2].podiums == 2
    assert stats[2].poles == 0
    # Pilota 3: P3 e P2 -> due podi.
    assert stats[3].podiums == 2
    # Pilota 4: mai a podio, non compare nelle statistiche.
    assert 4 not in stats


def test_team_stats_aggregate_drivers_of_the_same_team():
    gp = _grand_prix(1, [(1, 0), (2, 0), (3, 1), (4, 1)], grid=[1, 2, 3, 4])
    archive = archive_grand_prix(CareerArchive(), 2026, gp)
    stats = {entry.team_id: entry for entry in team_stats(archive)}
    # Squadra 0 porta P1 e P2: una vittoria, due podi, una pole (pilota 1).
    assert stats[0].wins == 1
    assert stats[0].podiums == 2
    assert stats[0].poles == 1
    # Squadra 1 porta P3 (e P4 fuori dal podio): un podio.
    assert stats[1].podiums == 1
    assert stats[1].wins == 0


def test_finalize_season_writes_champions_and_hall_of_fame():
    gp = _grand_prix(1, [(1, 0), (2, 0), (3, 1)], grid=[1, 2, 3])
    archive = archive_grand_prix(CareerArchive(), 2026, gp)
    results = (RoundResult(round=1, circuit_code="albert_park", classification=gp.classification),)
    driver_ids = [1, 2, 3]
    team_ids = [0, 1]
    driver_standings, constructor_standings = final_standings(results, driver_ids, team_ids)
    archive = finalize_season(archive, 2026, driver_standings, constructor_standings)

    season = archive.season_for(2026)
    assert season is not None
    assert season.is_concluded
    assert season.driver_champion_id == 1
    assert season.constructor_champion_id == 0
    entries = hall_of_fame(archive)
    assert len(entries) == 1
    assert entries[0].year == 2026
    assert entries[0].driver_champion_id == 1
    # Il Titolo entra nelle statistiche cumulative.
    stats = {entry.driver_id: entry for entry in driver_stats(archive)}
    assert stats[1].titles == 1


def test_multi_season_accumulation_never_loses_past_seasons():
    gp_2026 = _grand_prix(1, [(1, 0), (2, 0), (3, 1)], grid=[1, 2, 3])
    archive = archive_grand_prix(CareerArchive(), 2026, gp_2026)
    results_2026 = (
        RoundResult(round=1, circuit_code="albert_park", classification=gp_2026.classification),
    )
    ds, cs = final_standings(results_2026, [1, 2, 3], [0, 1])
    archive = finalize_season(archive, 2026, ds, cs)

    # Stagione 2: il pilota 2 vince. Le righe del 2026 NON devono sparire.
    gp_2027 = _grand_prix(1, [(2, 0), (1, 0), (3, 1)], grid=[2, 1, 3])
    archive = archive_grand_prix(archive, 2027, gp_2027)
    results_2027 = (
        RoundResult(round=1, circuit_code="albert_park", classification=gp_2027.classification),
    )
    ds, cs = final_standings(results_2027, [1, 2, 3], [0, 1])
    archive = finalize_season(archive, 2027, ds, cs)

    assert [season.year for season in archive.seasons] == [2026, 2027]
    # Il GP del 2026 e' ancora archiviato, intatto.
    season_2026 = archive.season_for(2026)
    assert season_2026 is not None
    assert season_2026.grands_prix[0].classification[0].driver_id == 1
    # Albo d'oro: un Titolo per anno, in ordine.
    entries = hall_of_fame(archive)
    assert [(e.year, e.driver_champion_id) for e in entries] == [(2026, 1), (2027, 2)]
    # Vittorie cumulative su due stagioni: pilota 1 e pilota 2 una a testa.
    stats = {entry.driver_id: entry for entry in driver_stats(archive)}
    assert stats[1].wins == 1
    assert stats[2].wins == 1
    assert stats[1].titles == 1
    assert stats[2].titles == 1


def test_archive_rejects_duplicate_round_in_the_same_season():
    gp = _grand_prix(1, [(1, 0), (2, 0)], grid=[1, 2])
    archive = archive_grand_prix(CareerArchive(), 2026, gp)
    try:
        archive_grand_prix(archive, 2026, gp)
    except ValueError as error:
        assert "already archived" in str(error)
    else:
        raise AssertionError("un round duplicato deve essere rifiutato")


def test_empty_archive_has_no_stats_and_no_hall_of_fame():
    archive = CareerArchive()
    assert archive.is_empty
    assert driver_stats(archive) == ()
    assert team_stats(archive) == ()
    assert hall_of_fame(archive) == ()
