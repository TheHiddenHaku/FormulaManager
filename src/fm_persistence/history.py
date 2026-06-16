"""Persistenza dell'archivio della Carriera ai Checkpoint (T5.3.2).

L'archivio permanente (fm_engine.history.CareerArchive) viaggia su tabelle
relazionali dedicate, NON su una colonna jsonb: Albo d'oro (archive_seasons),
classifiche finali (archive_standings), Almanacco dei GP (archive_grands_prix)
con griglia di partenza (archive_starting_grid), ordine d'arrivo
(archive_results) ed eventi principali (archive_principal_events). Indici
dedicati su (career_id, year) per query efficienti su Carriere lunghe.

Strategia di scrittura: rewrite dell'intero archivio dentro la transazione
di save_career (delete delle righe della Carriera, poi reinsert), come per
il resto dello stato (checkpoint.py). Niente scritture incrementali fuori
Checkpoint (ADR 0001). L'accumulo (mai perdere le stagioni passate) e' una
proprieta' del modello in memoria; qui si riscrive sempre tutto cio' che
l'archivio contiene, quindi le stagioni passate sono presenti a ogni save.

Gli id riusano row_uuid di mapping con chiavi deterministiche, cosi' due
save della stessa Carriera producono gli stessi uuid e il load non tiene
mappe id->uuid. Importa fm_engine; il motore non importa mai questo
pacchetto (ADR 0002).
"""

import uuid
from typing import Any

from fm_engine.events import ClassifiedResult
from fm_engine.history import (
    ArchivedGrandPrix,
    CareerArchive,
    PrincipalEvent,
    PrincipalEventKind,
    SeasonArchive,
)
from fm_engine.season.standings import ConstructorStanding, DriverStanding
from fm_persistence.mapping import row_uuid

# Le tabelle dell'archivio, in ordine di delete compatibile con le FK
# (tutte referenziano solo careers via career_id, quindi l'ordine e'
# indifferente per le FK, ma resta esplicito e stabile).
ARCHIVE_TABLES = (
    "archive_principal_events",
    "archive_results",
    "archive_starting_grid",
    "archive_grands_prix",
    "archive_standings",
    "archive_seasons",
)

INSERT_SEASON = (
    "insert into archive_seasons (id, career_id, year, driver_champion_id, "
    "constructor_champion_id) values (%s, %s, %s, %s, %s)"
)
INSERT_STANDING = (
    "insert into archive_standings (id, career_id, year, scope, position, "
    "entity_id, points, wins) values (%s, %s, %s, %s, %s, %s, %s, %s)"
)
INSERT_GRAND_PRIX = (
    "insert into archive_grands_prix (id, career_id, year, round, circuit_code) "
    "values (%s, %s, %s, %s, %s)"
)
INSERT_GRID = (
    "insert into archive_starting_grid (id, career_id, year, round, "
    "grid_position, driver_id) values (%s, %s, %s, %s, %s, %s)"
)
INSERT_RESULT = (
    "insert into archive_results (id, career_id, year, round, position, "
    "driver_id, team_id, points, total_time_seconds, gap_to_winner_seconds, "
    "penalty_seconds) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
INSERT_PRINCIPAL_EVENT = (
    "insert into archive_principal_events (id, career_id, year, round, "
    "ordinal, kind, lap, driver_id, detail) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
)

# Chiavi per gli uuid deterministici di riga, separate per tabella.
_SEASON_UUID_KIND = "archive_season"
_STANDING_UUID_KIND = "archive_standing"
_GRAND_PRIX_UUID_KIND = "archive_grand_prix"
_GRID_UUID_KIND = "archive_grid"
_RESULT_UUID_KIND = "archive_result"
_PRINCIPAL_EVENT_UUID_KIND = "archive_principal_event"

# I round per stagione (24 GP, FOR-21) per comporre un id univoco
# (year, round, ordinal) entro la Carriera senza collisioni.
_MAX_ROUNDS_PER_SEASON = 100
_MAX_ROWS_PER_GP = 100


def _row_uuid(career_id: uuid.UUID, kind: str, internal_id: int) -> uuid.UUID:
    return row_uuid(career_id, kind, internal_id)


def _season_internal_id(year: int) -> int:
    return year


def _gp_internal_id(year: int, round_: int) -> int:
    return year * _MAX_ROUNDS_PER_SEASON + round_


def _row_internal_id(year: int, round_: int, ordinal: int) -> int:
    return (year * _MAX_ROUNDS_PER_SEASON + round_) * _MAX_ROWS_PER_GP + ordinal


def _standing_internal_id(year: int, scope_offset: int, position: int) -> int:
    return (year * _MAX_ROWS_PER_GP + scope_offset) * _MAX_ROWS_PER_GP + position


def season_params(career_id: uuid.UUID, season: SeasonArchive) -> tuple[Any, ...]:
    """Parametri per l'INSERT in archive_seasons."""
    return (
        _row_uuid(career_id, _SEASON_UUID_KIND, _season_internal_id(season.year)),
        career_id,
        season.year,
        season.driver_champion_id,
        season.constructor_champion_id,
    )


def standing_params_for_season(
    career_id: uuid.UUID, season: SeasonArchive
) -> list[tuple[Any, ...]]:
    """Parametri per gli INSERT delle classifiche finali di una stagione."""
    params: list[tuple[Any, ...]] = []
    for standing in season.driver_standings:
        params.append(
            (
                _row_uuid(
                    career_id,
                    _STANDING_UUID_KIND,
                    _standing_internal_id(season.year, 0, standing.position),
                ),
                career_id,
                season.year,
                "driver",
                standing.position,
                standing.driver_id,
                standing.points,
                standing.wins,
            )
        )
    for standing in season.constructor_standings:
        params.append(
            (
                _row_uuid(
                    career_id,
                    _STANDING_UUID_KIND,
                    _standing_internal_id(season.year, 1, standing.position),
                ),
                career_id,
                season.year,
                "constructor",
                standing.position,
                standing.team_id,
                standing.points,
                standing.wins,
            )
        )
    return params


def grand_prix_params(
    career_id: uuid.UUID, year: int, grand_prix: ArchivedGrandPrix
) -> tuple[Any, ...]:
    """Parametri per l'INSERT in archive_grands_prix."""
    return (
        _row_uuid(career_id, _GRAND_PRIX_UUID_KIND, _gp_internal_id(year, grand_prix.round)),
        career_id,
        year,
        grand_prix.round,
        grand_prix.circuit_code,
    )


def grid_params_for_gp(
    career_id: uuid.UUID, year: int, grand_prix: ArchivedGrandPrix
) -> list[tuple[Any, ...]]:
    """Parametri per gli INSERT della griglia di partenza di un GP."""
    return [
        (
            _row_uuid(
                career_id,
                _GRID_UUID_KIND,
                _row_internal_id(year, grand_prix.round, grid_position),
            ),
            career_id,
            year,
            grand_prix.round,
            grid_position,
            driver_id,
        )
        for grid_position, driver_id in enumerate(grand_prix.starting_grid, start=1)
    ]


def result_params_for_gp(
    career_id: uuid.UUID, year: int, grand_prix: ArchivedGrandPrix
) -> list[tuple[Any, ...]]:
    """Parametri per gli INSERT dell'ordine d'arrivo di un GP."""
    return [
        (
            _row_uuid(
                career_id,
                _RESULT_UUID_KIND,
                _row_internal_id(year, grand_prix.round, result.position),
            ),
            career_id,
            year,
            grand_prix.round,
            result.position,
            result.driver_id,
            result.team_id,
            result.points,
            result.total_time_seconds,
            result.gap_to_winner_seconds,
            result.penalty_seconds,
        )
        for result in grand_prix.classification
    ]


def principal_event_params_for_gp(
    career_id: uuid.UUID, year: int, grand_prix: ArchivedGrandPrix
) -> list[tuple[Any, ...]]:
    """Parametri per gli INSERT degli eventi principali di un GP."""
    return [
        (
            _row_uuid(
                career_id,
                _PRINCIPAL_EVENT_UUID_KIND,
                _row_internal_id(year, grand_prix.round, ordinal),
            ),
            career_id,
            year,
            grand_prix.round,
            ordinal,
            event.kind.value,
            event.lap,
            event.driver_id,
            event.detail,
        )
        for ordinal, event in enumerate(grand_prix.principal_events, start=1)
    ]


def insert_archive(cursor: Any, career_id: uuid.UUID, archive: CareerArchive) -> None:
    """Reinserisce l'intero archivio della Carriera (rewrite del Checkpoint).

    Una executemany per tabella, in ordine compatibile con la lettura.
    Chiamata dentro la transazione di save_career, dopo il delete delle
    righe della Carriera: l'archivio scritto e' sempre quello completo
    accumulato in memoria (stagioni passate incluse).
    """
    season_rows = [season_params(career_id, season) for season in archive.seasons]
    if season_rows:
        cursor.executemany(INSERT_SEASON, season_rows)
    standing_rows: list[tuple[Any, ...]] = []
    gp_rows: list[tuple[Any, ...]] = []
    grid_rows: list[tuple[Any, ...]] = []
    result_rows: list[tuple[Any, ...]] = []
    event_rows: list[tuple[Any, ...]] = []
    for season in archive.seasons:
        standing_rows.extend(standing_params_for_season(career_id, season))
        for grand_prix in season.grands_prix:
            gp_rows.append(grand_prix_params(career_id, season.year, grand_prix))
            grid_rows.extend(grid_params_for_gp(career_id, season.year, grand_prix))
            result_rows.extend(result_params_for_gp(career_id, season.year, grand_prix))
            event_rows.extend(principal_event_params_for_gp(career_id, season.year, grand_prix))
    if standing_rows:
        cursor.executemany(INSERT_STANDING, standing_rows)
    if gp_rows:
        cursor.executemany(INSERT_GRAND_PRIX, gp_rows)
    if grid_rows:
        cursor.executemany(INSERT_GRID, grid_rows)
    if result_rows:
        cursor.executemany(INSERT_RESULT, result_rows)
    if event_rows:
        cursor.executemany(INSERT_PRINCIPAL_EVENT, event_rows)


def archive_from_rows(
    season_rows: list[dict[str, Any]],
    standing_rows: list[dict[str, Any]],
    grand_prix_rows: list[dict[str, Any]],
    grid_rows: list[dict[str, Any]],
    result_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
) -> CareerArchive:
    """Ricostruisce l'archivio dalle righe lette, accumulo intatto.

    Le righe arrivano gia' filtrate per career_id. L'ordine finale e'
    deterministico: stagioni per anno, GP per round, righe per posizione
    e per ordinale.
    """
    if not season_rows:
        return CareerArchive()

    standings_by_year: dict[int, dict[str, list[dict[str, Any]]]] = {}
    for row in standing_rows:
        year_scope = standings_by_year.setdefault(row["year"], {"driver": [], "constructor": []})
        year_scope[row["scope"]].append(row)

    grids_by_gp: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in grid_rows:
        grids_by_gp.setdefault((row["year"], row["round"]), []).append(row)
    results_by_gp: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in result_rows:
        results_by_gp.setdefault((row["year"], row["round"]), []).append(row)
    events_by_gp: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in event_rows:
        events_by_gp.setdefault((row["year"], row["round"]), []).append(row)

    gps_by_year: dict[int, list[dict[str, Any]]] = {}
    for row in grand_prix_rows:
        gps_by_year.setdefault(row["year"], []).append(row)

    seasons: list[SeasonArchive] = []
    for season_row in sorted(season_rows, key=lambda row: row["year"]):
        year = season_row["year"]
        grands_prix = tuple(
            _grand_prix_from_rows(
                gp_row,
                grids_by_gp.get((year, gp_row["round"]), []),
                results_by_gp.get((year, gp_row["round"]), []),
                events_by_gp.get((year, gp_row["round"]), []),
            )
            for gp_row in sorted(gps_by_year.get(year, []), key=lambda row: row["round"])
        )
        scopes = standings_by_year.get(year, {"driver": [], "constructor": []})
        driver_standings = tuple(
            DriverStanding(
                position=row["position"],
                driver_id=row["entity_id"],
                points=row["points"],
                wins=row["wins"],
            )
            for row in sorted(scopes["driver"], key=lambda row: row["position"])
        )
        constructor_standings = tuple(
            ConstructorStanding(
                position=row["position"],
                team_id=row["entity_id"],
                points=row["points"],
                wins=row["wins"],
            )
            for row in sorted(scopes["constructor"], key=lambda row: row["position"])
        )
        seasons.append(
            SeasonArchive(
                year=year,
                grands_prix=grands_prix,
                driver_standings=driver_standings,
                constructor_standings=constructor_standings,
                driver_champion_id=season_row["driver_champion_id"],
                constructor_champion_id=season_row["constructor_champion_id"],
            )
        )
    return CareerArchive(seasons=tuple(seasons))


def _grand_prix_from_rows(
    gp_row: dict[str, Any],
    grid_rows: list[dict[str, Any]],
    result_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
) -> ArchivedGrandPrix:
    starting_grid = tuple(
        row["driver_id"] for row in sorted(grid_rows, key=lambda row: row["grid_position"])
    )
    classification = tuple(
        ClassifiedResult(
            position=row["position"],
            driver_id=row["driver_id"],
            team_id=row["team_id"],
            total_time_seconds=float(row["total_time_seconds"]),
            gap_to_winner_seconds=float(row["gap_to_winner_seconds"]),
            points=row["points"],
            penalty_seconds=float(row["penalty_seconds"]),
        )
        for row in sorted(result_rows, key=lambda row: row["position"])
    )
    principal_events = tuple(
        PrincipalEvent(
            kind=PrincipalEventKind(row["kind"]),
            lap=row["lap"],
            detail=row["detail"],
            driver_id=row["driver_id"],
        )
        for row in sorted(event_rows, key=lambda row: row["ordinal"])
    )
    return ArchivedGrandPrix(
        round=gp_row["round"],
        circuit_code=gp_row["circuit_code"],
        starting_grid=starting_grid,
        classification=classification,
        principal_events=principal_events,
    )
