"""Operazioni di Checkpoint sulle Carriere (ADR 0001, FOR-5).

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
"""

import uuid
from dataclasses import dataclass, replace
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from fm_engine.career import Career
from fm_engine.world.models import World
from fm_persistence import development, economy, mapping
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
    "values (%s, %s, %s, %s, %s)"
)

_INSERT_TEAM = (
    "insert into teams (id, career_id, name, is_player, prestige, cash_usd, "
    "chassis_philosophy, engine_supplier_id, engine_power, downforce, "
    "aero_efficiency, mechanical_grip, tyre_management, reliability) "
    "values (%s, %s, %s, false, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)

# The player slot before the team setup wizard: identity only (name and
# livery colors), everything else stays at the schema defaults.
_INSERT_PLAYER_SLOT = (
    "insert into teams (id, career_id, name, primary_color, secondary_color, "
    "is_player) values (%s, %s, %s, %s, %s, true)"
)

# The player team after the team setup wizard (FOR-7): identity plus
# chassis philosophy, engine supply and the 6 initial car attributes.
_INSERT_PLAYER_TEAM = (
    "insert into teams (id, career_id, name, primary_color, secondary_color, "
    "is_player, chassis_philosophy, engine_supplier_id, engine_power, downforce, "
    "aero_efficiency, mechanical_grip, tyre_management, reliability) "
    "values (%s, %s, %s, %s, %s, true, %s, %s, %s, %s, %s, %s, %s, %s)"
)

_INSERT_DRIVER = (
    "insert into drivers (id, career_id, name, nationality, age, one_lap_pace, race_pace, "
    "duels, tyre_management, wet_weather, consistency, potential, retired) "
    "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)

_INSERT_CONTRACT = (
    "insert into contracts (id, career_id, team_id, driver_id, start_season, "
    "duration_seasons, salary_usd) "
    "values (%s, %s, %s, %s, %s, %s, %s)"
)

_INSERT_SEASON = "insert into seasons (id, career_id, year, cap_usd) values (%s, %s, %s, %s)"

_INSERT_TRANSACTION = (
    "insert into financial_transactions (id, career_id, team_id, season_id, "
    "kind, amount_usd, counts_against_cap, description, game_date) "
    "values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
)

_INSERT_PROJECT = (
    "insert into development_projects (id, career_id, team_id, season_id, "
    "attribute, cost_usd, start_date, duration_days, status, outcome) "
    "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)


def save_career(conn: psycopg.Connection, career: Career) -> Career:
    """Scrive l'intera Carriera (Mondo + stato) in una transazione atomica.

    Carriera nuova (id None): inserisce la riga radice e tutto lo stato.
    Checkpoint successivo (id valorizzato): delete e reinsert dello stato
    dentro la stessa transazione (vedi docstring del modulo); solleva
    CareerNotFoundError se l'id non esiste piu' sul database.

    Ritorna la Career con i metadati di Checkpoint aggiornati (id,
    created_at, last_checkpoint_at); il Mondo in memoria resta intatto.
    """
    weekend_payload = weekend_state_payload(career.weekend)
    weekend_value = None if weekend_payload is None else Jsonb(weekend_payload)
    solvency_payload = economy.solvency_payload(career.solvency)
    solvency_value = None if solvency_payload is None else Jsonb(solvency_payload)
    season_payload = season_state_payload(career.season)
    season_value = None if season_payload is None else Jsonb(season_payload)
    knowledge_payload = knowledge_state_payload(career.knowledge)
    knowledge_value = None if knowledge_payload is None else Jsonb(knowledge_payload)
    preseason_payload = preseason_state_payload(career.preseason)
    preseason_value = None if preseason_payload is None else Jsonb(preseason_payload)
    market_payload = market_state_payload(career.market)
    market_value = None if market_payload is None else Jsonb(market_payload)
    with conn.transaction(), conn.cursor() as cursor:
        if career.id is None:
            cursor.execute(
                "insert into careers (name, last_checkpoint_at, weekend_state, "
                "solvency_state, season_state, knowledge_state, preseason_state, "
                "market_state) "
                "values (%s, now(), %s, %s, %s, %s, %s, %s) "
                "returning id, created_at, last_checkpoint_at",
                (
                    career.name,
                    weekend_value,
                    solvency_value,
                    season_value,
                    knowledge_value,
                    preseason_value,
                    market_value,
                ),
            )
            row = cursor.fetchone()
        else:
            cursor.execute(
                "update careers set name = %s, last_checkpoint_at = now(), "
                "weekend_state = %s, solvency_state = %s, season_state = %s, "
                "knowledge_state = %s, preseason_state = %s, market_state = %s "
                "where id = %s returning id, created_at, last_checkpoint_at",
                (
                    career.name,
                    weekend_value,
                    solvency_value,
                    season_value,
                    knowledge_value,
                    preseason_value,
                    market_value,
                    career.id,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise CareerNotFoundError(f"no Career with id {career.id}")
            for table in _STATE_TABLES:
                cursor.execute(  # noqa: S608 - table names from internal constant
                    f"delete from {table} where career_id = %s", (career.id,)
                )
        career_id, created_at, checkpoint_at = row
        _insert_world(cursor, career_id, career.world)
        _insert_ledger(cursor, career_id, career)
    return replace(career, id=career_id, created_at=created_at, last_checkpoint_at=checkpoint_at)


def _insert_world(cursor: psycopg.Cursor, career_id: uuid.UUID, world: World) -> None:
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


def _insert_ledger(cursor: psycopg.Cursor, career_id: uuid.UUID, career: Career) -> None:
    """Inserisce la stagione corrente e i movimenti del registro (FOR-15).

    La riga di stagione esiste sempre (porta il Cap stagionale); i
    movimenti referenziano la squadra del giocatore, che deve avere una
    riga in teams quando il registro non e' vuoto.
    """
    ledger = career.ledger
    cursor.execute(_INSERT_SEASON, economy.season_params(career_id, ledger))
    if (career.ledger.entries or career.projects) and career.world.player_slot.name is None:
        raise ValueError("economy state requires a named player team")
    if ledger.entries:
        cursor.executemany(
            _INSERT_TRANSACTION,
            [
                economy.transaction_params(career_id, position, transaction, ledger)
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


def load_career(conn: psycopg.Connection, career_id: uuid.UUID) -> Career:
    """Ricostruisce per intero una Carriera salvata.

    Il Mondo ricostruito e' la proiezione persistibile dello stato al
    momento del save: i campi senza colonna nello schema tornano ai
    valori canonici di mapping (vedi mapping.persistable_projection).
    Solleva CareerNotFoundError se l'id non esiste.
    """
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "select id, name, created_at, last_checkpoint_at, weekend_state, "
            "solvency_state, season_state, knowledge_state, preseason_state, "
            "market_state "
            "from careers where id = %s",
            (career_id,),
        )
        root = cursor.fetchone()
        if root is None:
            raise CareerNotFoundError(f"no Career with id {career_id}")
        cursor.execute(
            "select id, name, engine_power, customer_fee_usd "
            "from engine_suppliers where career_id = %s",
            (career_id,),
        )
        engine_supplier_rows = cursor.fetchall()
        cursor.execute(
            "select id, name, prestige, cash_usd, chassis_philosophy, engine_supplier_id, "
            "engine_power, downforce, aero_efficiency, mechanical_grip, "
            "tyre_management, reliability "
            "from teams where career_id = %s and not is_player",
            (career_id,),
        )
        ai_team_rows = cursor.fetchall()
        cursor.execute(
            "select name, primary_color, secondary_color, chassis_philosophy, "
            "engine_supplier_id, engine_power, downforce, aero_efficiency, "
            "mechanical_grip, tyre_management, reliability "
            "from teams where career_id = %s and is_player",
            (career_id,),
        )
        player_slot_row = cursor.fetchone()
        cursor.execute(
            "select id, name, nationality, age, one_lap_pace, race_pace, duels, "
            "tyre_management, wet_weather, consistency, potential, retired "
            "from drivers where career_id = %s",
            (career_id,),
        )
        driver_rows = cursor.fetchall()
        cursor.execute(
            "select id, team_id, driver_id, start_season, duration_seasons, "
            "salary_usd "
            "from contracts where career_id = %s",
            (career_id,),
        )
        contract_rows = cursor.fetchall()
        # Current season: the latest year (one row per year, FOR-15).
        cursor.execute(
            "select id, year, cap_usd from seasons where career_id = %s order by year desc limit 1",
            (career_id,),
        )
        season_row = cursor.fetchone()
        cursor.execute(
            "select id, kind, amount_usd, counts_against_cap, description, "
            "game_date from financial_transactions "
            "where career_id = %s and team_id = %s",
            (career_id, mapping.row_uuid(career_id, "team", mapping.PLAYER_SLOT_ID)),
        )
        transaction_rows = cursor.fetchall()
        cursor.execute(
            "select id, attribute, cost_usd, start_date, duration_days, "
            "status, outcome from development_projects "
            "where career_id = %s and team_id = %s",
            (career_id, mapping.row_uuid(career_id, "team", mapping.PLAYER_SLOT_ID)),
        )
        project_rows = cursor.fetchall()
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
        id=root["id"],
        created_at=root["created_at"],
        last_checkpoint_at=root["last_checkpoint_at"],
        weekend=weekend_state_from_payload(root["weekend_state"]),
        ledger=economy.ledger_from_rows(season_row, transaction_rows),
        solvency=economy.solvency_from_payload(root["solvency_state"]),
        projects=development.projects_from_rows(project_rows),
        season=season_state_from_payload(root["season_state"]),
        knowledge=knowledge_state_from_payload(root["knowledge_state"]),
        preseason=preseason_state_from_payload(root["preseason_state"]),
        market=market_state_from_payload(root["market_state"]),
    )


def list_careers(conn: psycopg.Connection) -> list[CareerSummary]:
    """Elenca le Carriere salvate con i metadati di Checkpoint.

    Ordinate dal Checkpoint piu' recente: e' l'ordine naturale di una
    schermata "continua la partita".
    """
    with conn.transaction(), conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "select id, name, created_at, last_checkpoint_at from careers "
            "order by last_checkpoint_at desc nulls last, created_at desc"
        )
        return [CareerSummary(**row) for row in cursor.fetchall()]


def delete_career(conn: psycopg.Connection, career_id: uuid.UUID) -> bool:
    """Elimina una Carriera intera, a cascata sulle FK dello schema.

    La cancellazione della riga radice propaga ON DELETE CASCADE a tutto
    lo stato della Carriera. Ritorna True se la Carriera esisteva.
    """
    with conn.transaction(), conn.cursor() as cursor:
        cursor.execute("delete from careers where id = %s", (career_id,))
        return cursor.rowcount == 1
