"""Operazioni di Checkpoint sulle Carriere (ADR 0004, FOR-5).

L'API lavora solo a granularita' di Carriera intera: save, load, list,
delete. Nessuna scrittura per-Tick e nessun salvataggio incrementale per
design: durante il gioco lo stato vive in memoria e il database si tocca
solo ai Checkpoint (fine sessione, pre-gara).

Strategia del Checkpoint successivo sulla stessa Carriera: dentro la
stessa transazione del save si aggiornano nome e last_checkpoint_at
della riga radice, si svuota lo stato precedente (delete) e lo si
reinserisce per intero (reinsert). Semplice, atomico e idempotente: se la
transazione fallisce a meta', il rollback ripristina il Checkpoint
precedente intatto. Le tabelle coperte sono quelle che questo modulo
persiste (financial_transactions, contracts, teams, drivers,
engine_suppliers, seasons): i moduli futuri che persisteranno altre
tabelle di stato dovranno estendere questo elenco.

Dialetto SQLite (ADR 0004): segnaposto ?, id come str (uuid), timestamp
come ISO 8601, documenti di stato jsonb serializzati con json.dumps/loads.
L'id della Carriera e i timestamp li scrive l'applicazione (niente default
gen_random_uuid() o now() nello schema).
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from fm_engine.career import Career
from fm_engine.world.models import World
from fm_persistence import development, economy, history, mapping
from fm_persistence.estimates import knowledge_state_from_payload, knowledge_state_payload
from fm_persistence.market import market_state_from_payload, market_state_payload
from fm_persistence.preseason import preseason_state_from_payload, preseason_state_payload
from fm_persistence.season import season_state_from_payload, season_state_payload
from fm_persistence.weekend import weekend_state_from_payload, weekend_state_payload


class CareerNotFoundError(Exception):
    """Nessuna Carriera salvata con l'id richiesto."""


@dataclass(frozen=True)
class CareerSummary:
    """Metadati di una Carriera salvata, per la schermata di caricamento."""

    id: uuid.UUID
    name: str
    created_at: datetime
    last_checkpoint_at: datetime | None


# Delete order compatible with the FKs: referencing tables first, then the
# referenced ones (financial_transactions and development_projects ->
# teams/seasons, contracts -> teams/drivers, teams -> engine_suppliers).
_STATE_TABLES = (
    # Career archive (T5.3.2): referencing only careers, deleted first.
    *history.ARCHIVE_TABLES,
    "financial_transactions",
    "development_projects",
    "contracts",
    "teams",
    "drivers",
    "engine_suppliers",
    "seasons",
)

_INSERT_ENGINE_SUPPLIER = (
    "insert into engine_suppliers (id, career_id, name, engine_power, customer_fee_usd) "
    "values (?, ?, ?, ?, ?)"
)

_INSERT_TEAM = (
    "insert into teams (id, career_id, name, primary_color, secondary_color, "
    "is_player, prestige, cash_usd, "
    "chassis_philosophy, engine_supplier_id, engine_power, downforce, "
    "aero_efficiency, mechanical_grip, tyre_management, reliability) "
    "values (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

# The player slot before the team setup wizard: identity only (name and
# livery colors), everything else stays at the schema defaults.
_INSERT_PLAYER_SLOT = (
    "insert into teams (id, career_id, name, primary_color, secondary_color, "
    "is_player) values (?, ?, ?, ?, ?, 1)"
)

# The player team after the team setup wizard (FOR-7): identity plus
# chassis philosophy, engine supply and the 6 initial car attributes.
_INSERT_PLAYER_TEAM = (
    "insert into teams (id, career_id, name, primary_color, secondary_color, "
    "is_player, chassis_philosophy, engine_supplier_id, engine_power, downforce, "
    "aero_efficiency, mechanical_grip, tyre_management, reliability) "
    "values (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)"
)

_INSERT_DRIVER = (
    "insert into drivers (id, career_id, name, nationality, age, one_lap_pace, race_pace, "
    "duels, tyre_management, wet_weather, consistency, potential, retired) "
    "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

_INSERT_CONTRACT = (
    "insert into contracts (id, career_id, team_id, driver_id, start_season, "
    "duration_seasons, salary_usd) "
    "values (?, ?, ?, ?, ?, ?, ?)"
)

_INSERT_SEASON = "insert into seasons (id, career_id, year, cap_usd) values (?, ?, ?, ?)"

_INSERT_TRANSACTION = (
    "insert into financial_transactions (id, career_id, team_id, season_id, "
    "kind, amount_usd, counts_against_cap, description, game_date, recorded_at) "
    "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

_INSERT_PROJECT = (
    "insert into development_projects (id, career_id, team_id, season_id, "
    "attribute, cost_usd, start_date, duration_days, status, outcome) "
    "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _json_dump(payload: object | None) -> str | None:
    """Serializza un documento di stato in testo JSON, None se assente."""
    return None if payload is None else json.dumps(payload)


def _json_load(value: str | None) -> object | None:
    """Deserializza un documento di stato dal testo JSON della colonna."""
    return None if value is None else json.loads(value)


def _parse_datetime(value: str | None) -> datetime | None:
    """Ricostruisce un datetime da testo ISO 8601, None se la colonna e' NULL."""
    return None if value is None else datetime.fromisoformat(value)


def _dict_row(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """Row factory: righe come dict per accesso per nome (uso in lettura)."""
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


def save_career(conn: sqlite3.Connection, career: Career) -> Career:
    """Scrive l'intera Carriera (Mondo + stato) in una transazione atomica.

    Carriera nuova (id None): genera l'id (uuid) e i timestamp lato
    applicazione, inserisce la riga radice e tutto lo stato. Checkpoint
    successivo (id valorizzato): delete e reinsert dello stato dentro la
    stessa transazione (vedi docstring del modulo); solleva
    CareerNotFoundError se l'id non esiste piu' sul database.

    Ritorna la Career con i metadati di Checkpoint aggiornati (id,
    created_at, last_checkpoint_at); il Mondo in memoria resta intatto.
    """
    weekend_value = _json_dump(weekend_state_payload(career.weekend))
    solvency_value = _json_dump(economy.solvency_payload(career.solvency))
    season_value = _json_dump(season_state_payload(career.season))
    knowledge_value = _json_dump(knowledge_state_payload(career.knowledge))
    preseason_value = _json_dump(preseason_state_payload(career.preseason))
    market_value = _json_dump(market_state_payload(career.market))
    now = datetime.now(UTC)
    is_new = career.id is None
    career_id = uuid.uuid4() if is_new else career.id
    created_at = now if is_new else career.created_at
    with conn:  # transazione atomica: commit all'uscita, rollback su eccezione
        cursor = conn.cursor()
        if is_new:
            cursor.execute(
                "insert into careers (id, name, created_at, last_checkpoint_at, "
                "weekend_state, solvency_state, season_state, knowledge_state, "
                "preseason_state, market_state) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    career_id,
                    career.name,
                    created_at,
                    now,
                    weekend_value,
                    solvency_value,
                    season_value,
                    knowledge_value,
                    preseason_value,
                    market_value,
                ),
            )
        else:
            cursor.execute(
                "update careers set name = ?, last_checkpoint_at = ?, weekend_state = ?, "
                "solvency_state = ?, season_state = ?, knowledge_state = ?, "
                "preseason_state = ?, market_state = ? where id = ?",
                (
                    career.name,
                    now,
                    weekend_value,
                    solvency_value,
                    season_value,
                    knowledge_value,
                    preseason_value,
                    market_value,
                    career_id,
                ),
            )
            if cursor.rowcount != 1:
                raise CareerNotFoundError(f"no Career with id {career_id}")
            for table in _STATE_TABLES:
                cursor.execute(  # noqa: S608 - table names from internal constant
                    f"delete from {table} where career_id = ?", (career_id,)
                )
        _insert_world(cursor, career_id, career.world)
        _insert_ledger(cursor, career_id, career, now)
        # Career archive (T5.3.2): rewrite the whole accumulated archive
        # inside the same Checkpoint transaction (ADR 0004).
        history.insert_archive(cursor, career_id, career.archive)
    return replace(career, id=career_id, created_at=created_at, last_checkpoint_at=now)


def _insert_world(cursor: sqlite3.Cursor, career_id: uuid.UUID, world: World) -> None:
    """Inserisce tutte le righe del Mondo, in ordine compatibile con le FK."""
    cursor.executemany(
        _INSERT_ENGINE_SUPPLIER,
        [
            mapping.engine_supplier_params(career_id, supplier)
            for supplier in world.engine_suppliers
        ],
    )
    cursor.executemany(
        _INSERT_TEAM,
        [mapping.team_params(career_id, team) for team in world.ai_teams],
    )
    if world.player_slot.name is not None:
        if world.player_slot.is_set_up:
            cursor.execute(
                _INSERT_PLAYER_TEAM,
                mapping.player_team_params(career_id, world.player_slot),
            )
        else:
            cursor.execute(
                _INSERT_PLAYER_SLOT,
                mapping.player_slot_params(career_id, world.player_slot),
            )
    cursor.executemany(
        _INSERT_DRIVER,
        [mapping.driver_params(career_id, driver) for driver in world.drivers],
    )
    cursor.executemany(
        _INSERT_CONTRACT,
        [
            mapping.contract_params(career_id, position, contract)
            for position, contract in enumerate(world.contracts, start=1)
        ],
    )


def _insert_ledger(
    cursor: sqlite3.Cursor, career_id: uuid.UUID, career: Career, recorded_at: datetime
) -> None:
    """Inserisce la stagione corrente e i movimenti del registro (FOR-15).

    La riga di stagione esiste sempre (porta il Cap stagionale); i
    movimenti referenziano la squadra del giocatore, che deve avere una
    riga in teams quando il registro non e' vuoto. recorded_at (metadato di
    scrittura, non riletto) e' il timestamp del Checkpoint: lo scrive
    l'applicazione, come tutti i timestamp (ADR 0004).
    """
    ledger = career.ledger
    cursor.execute(_INSERT_SEASON, economy.season_params(career_id, ledger))
    if (career.ledger.entries or career.projects) and career.world.player_slot.name is None:
        raise ValueError("economy state requires a named player team")
    if ledger.entries:
        cursor.executemany(
            _INSERT_TRANSACTION,
            [
                (
                    *economy.transaction_params(career_id, position, transaction, ledger),
                    recorded_at,
                )
                for position, transaction in enumerate(ledger.entries, start=1)
            ],
        )
    if career.projects:
        cursor.executemany(
            _INSERT_PROJECT,
            [
                development.project_params(career_id, position, project, ledger)
                for position, project in enumerate(career.projects, start=1)
            ],
        )


def load_career(conn: sqlite3.Connection, career_id: uuid.UUID) -> Career:
    """Ricostruisce per intero una Carriera salvata.

    Il Mondo ricostruito e' la proiezione persistibile dello stato al
    momento del save: i campi senza colonna nello schema tornano ai
    valori canonici di mapping (vedi mapping.persistable_projection).
    Solleva CareerNotFoundError se l'id non esiste.
    """
    cursor = conn.cursor()
    cursor.row_factory = _dict_row
    player_team_id = mapping.row_uuid(career_id, "team", mapping.PLAYER_SLOT_ID)
    cursor.execute(
        "select id, name, created_at, last_checkpoint_at, weekend_state, "
        "solvency_state, season_state, knowledge_state, preseason_state, "
        "market_state "
        "from careers where id = ?",
        (career_id,),
    )
    root = cursor.fetchone()
    if root is None:
        raise CareerNotFoundError(f"no Career with id {career_id}")
    cursor.execute(
        "select id, name, engine_power, customer_fee_usd from engine_suppliers where career_id = ?",
        (career_id,),
    )
    engine_supplier_rows = cursor.fetchall()
    cursor.execute(
        "select id, name, primary_color, secondary_color, prestige, cash_usd, "
        "chassis_philosophy, engine_supplier_id, "
        "engine_power, downforce, aero_efficiency, mechanical_grip, "
        "tyre_management, reliability "
        "from teams where career_id = ? and is_player = 0",
        (career_id,),
    )
    ai_team_rows = cursor.fetchall()
    cursor.execute(
        "select name, primary_color, secondary_color, chassis_philosophy, "
        "engine_supplier_id, engine_power, downforce, aero_efficiency, "
        "mechanical_grip, tyre_management, reliability "
        "from teams where career_id = ? and is_player = 1",
        (career_id,),
    )
    player_slot_row = cursor.fetchone()
    cursor.execute(
        "select id, name, nationality, age, one_lap_pace, race_pace, duels, "
        "tyre_management, wet_weather, consistency, potential, retired "
        "from drivers where career_id = ?",
        (career_id,),
    )
    driver_rows = cursor.fetchall()
    cursor.execute(
        "select id, team_id, driver_id, start_season, duration_seasons, "
        "salary_usd "
        "from contracts where career_id = ?",
        (career_id,),
    )
    contract_rows = cursor.fetchall()
    # Current season: the latest year (one row per year, FOR-15).
    cursor.execute(
        "select id, year, cap_usd from seasons where career_id = ? order by year desc limit 1",
        (career_id,),
    )
    season_row = cursor.fetchone()
    cursor.execute(
        "select id, kind, amount_usd, counts_against_cap, description, "
        "game_date from financial_transactions "
        "where career_id = ? and team_id = ?",
        (career_id, player_team_id),
    )
    transaction_rows = cursor.fetchall()
    cursor.execute(
        "select id, attribute, cost_usd, start_date, duration_days, "
        "status, outcome from development_projects "
        "where career_id = ? and team_id = ?",
        (career_id, player_team_id),
    )
    project_rows = cursor.fetchall()
    # Career archive (T5.3.2): the whole accumulated history of the
    # Career, one read per dedicated table, indexed on (career_id, year).
    cursor.execute(
        "select year, driver_champion_id, constructor_champion_id "
        "from archive_seasons where career_id = ?",
        (career_id,),
    )
    archive_season_rows = cursor.fetchall()
    cursor.execute(
        "select year, scope, position, entity_id, points, wins "
        "from archive_standings where career_id = ?",
        (career_id,),
    )
    archive_standing_rows = cursor.fetchall()
    cursor.execute(
        "select year, round, circuit_code from archive_grands_prix where career_id = ?",
        (career_id,),
    )
    archive_grand_prix_rows = cursor.fetchall()
    cursor.execute(
        "select year, round, grid_position, driver_id "
        "from archive_starting_grid where career_id = ?",
        (career_id,),
    )
    archive_grid_rows = cursor.fetchall()
    cursor.execute(
        "select year, round, position, driver_id, team_id, points, "
        "total_time_seconds, gap_to_winner_seconds, penalty_seconds "
        "from archive_results where career_id = ?",
        (career_id,),
    )
    archive_result_rows = cursor.fetchall()
    cursor.execute(
        "select year, round, ordinal, kind, lap, driver_id, detail "
        "from archive_principal_events where career_id = ?",
        (career_id,),
    )
    archive_event_rows = cursor.fetchall()
    world = mapping.world_from_rows(
        engine_supplier_rows=engine_supplier_rows,
        ai_team_rows=ai_team_rows,
        player_slot_row=player_slot_row,
        driver_rows=driver_rows,
        contract_rows=contract_rows,
    )
    return Career(
        name=root["name"],
        world=world,
        id=uuid.UUID(root["id"]),
        created_at=_parse_datetime(root["created_at"]),
        last_checkpoint_at=_parse_datetime(root["last_checkpoint_at"]),
        weekend=weekend_state_from_payload(_json_load(root["weekend_state"])),
        ledger=economy.ledger_from_rows(season_row, transaction_rows),
        solvency=economy.solvency_from_payload(_json_load(root["solvency_state"])),
        projects=development.projects_from_rows(project_rows),
        season=season_state_from_payload(_json_load(root["season_state"])),
        knowledge=knowledge_state_from_payload(_json_load(root["knowledge_state"])),
        preseason=preseason_state_from_payload(_json_load(root["preseason_state"])),
        market=market_state_from_payload(_json_load(root["market_state"])),
        archive=history.archive_from_rows(
            season_rows=archive_season_rows,
            standing_rows=archive_standing_rows,
            grand_prix_rows=archive_grand_prix_rows,
            grid_rows=archive_grid_rows,
            result_rows=archive_result_rows,
            event_rows=archive_event_rows,
        ),
    )


def list_careers(conn: sqlite3.Connection) -> list[CareerSummary]:
    """Elenca le Carriere salvate con i metadati di Checkpoint.

    Ordinate dal Checkpoint piu' recente: e' l'ordine naturale di una
    schermata "continua la partita". In SQLite i NULL, in ordinamento
    discendente, finiscono in coda (Checkpoint mai fatto per ultimo).
    """
    cursor = conn.cursor()
    cursor.row_factory = _dict_row
    cursor.execute(
        "select id, name, created_at, last_checkpoint_at from careers "
        "order by last_checkpoint_at desc, created_at desc"
    )
    return [
        CareerSummary(
            id=uuid.UUID(row["id"]),
            name=row["name"],
            created_at=_parse_datetime(row["created_at"]),
            last_checkpoint_at=_parse_datetime(row["last_checkpoint_at"]),
        )
        for row in cursor.fetchall()
    ]


def delete_career(conn: sqlite3.Connection, career_id: uuid.UUID) -> bool:
    """Elimina una Carriera intera, a cascata sulle FK dello schema.

    La cancellazione della riga radice propaga ON DELETE CASCADE a tutto
    lo stato della Carriera (foreign_keys attivo sulla connessione). Ritorna
    True se la Carriera esisteva.
    """
    with conn:
        cursor = conn.cursor()
        cursor.execute("delete from careers where id = ?", (career_id,))
        return cursor.rowcount == 1
