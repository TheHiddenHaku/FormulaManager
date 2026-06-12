"""Mappatura tra i modelli del Mondo e le righe dello schema DB.

Strategia degli id. I modelli del motore usano id interi progressivi,
validi solo dentro al Mondo; lo schema usa uuid. Ogni riga riceve un uuid
costruito da row_uuid(career_id, kind, internal_id): i 64 bit alti sono
deterministici per (carriera, tipo di entita'), i 64 bit bassi contengono
l'id interno. Il load decodifica l'id interno con id_from_uuid senza
colonne aggiuntive, e l'ordinamento per id interno ricostruisce le tuple
del Mondo nell'ordine originale di generazione. I Contratti non hanno id
nel motore: si codifica la loro posizione (1-based) nella tupla
world.contracts. Lo slot del giocatore usa l'id riservato PLAYER_SLOT_ID
(0) nella tabella teams, distinto dalle squadre AI (id da 1 in su).

Lacune dello schema (campi del Mondo senza colonna): seed e config della
generazione, ingaggio richiesto dei piloti, personalita' di spesa delle
squadre AI. Nazionalita' dei piloti e colori dello slot giocatore hanno
colonna e sopravvivono al round-trip. Il load normalizza i campi mancanti
ai valori canonici definiti qui sotto; persistable_projection applica la
stessa normalizzazione a un Mondo in memoria. L'equivalenza canonica del
round-trip e' quindi:

    load_career(conn, save_career(conn, career).id).world
        == persistable_projection(career.world)

Tutto cio' che ha una colonna nello schema e' strutturalmente identico
dopo il round-trip; i campi mancanti vanno segnalati come lacune di schema.
"""

import uuid
from dataclasses import replace
from typing import Any

from fm_engine.world.models import (
    PLAYER_TEAM_ID,
    Contract,
    Driver,
    EngineSupplier,
    PlayerSlot,
    SpendingPersonality,
    Team,
    World,
    WorldConfig,
)

# Canonical values for the World fields with no column in the schema.
UNPERSISTED_SEED = 0
UNPERSISTED_SALARY_DEMAND = 0
UNPERSISTED_PERSONALITY = SpendingPersonality(
    profile="unpersisted", spending_propensity=0.0, risk_tolerance=0.0
)

# Internal id reserved for the player slot row in teams: the same id the
# engine uses for the player's contracts (fm_engine.world.models).
PLAYER_SLOT_ID = PLAYER_TEAM_ID

_INTERNAL_ID_BITS = 64
_INTERNAL_ID_MASK = (1 << _INTERNAL_ID_BITS) - 1


def row_uuid(career_id: uuid.UUID, kind: str, internal_id: int) -> uuid.UUID:
    """Uuid della riga: 64 bit alti da (carriera, tipo), id interno nei bassi.

    Deterministico: le FK interne alla Carriera si calcolano senza tenere
    mappe id->uuid, e due save della stessa Carriera producono gli stessi
    uuid. Unico per costruzione: i bit alti separano carriere e tipi, i
    bit bassi separano le righe dello stesso tipo.
    """
    if not 0 <= internal_id <= _INTERNAL_ID_MASK:
        raise ValueError(f"internal id out of range for uuid encoding: {internal_id}")
    high = uuid.uuid5(career_id, kind).int >> _INTERNAL_ID_BITS
    return uuid.UUID(int=(high << _INTERNAL_ID_BITS) | internal_id)


def id_from_uuid(value: uuid.UUID) -> int:
    """Decodifica l'id interno dai 64 bit bassi di un uuid di riga."""
    return value.int & _INTERNAL_ID_MASK


def persistable_projection(world: World) -> World:
    """Il Mondo come lo schema sa rappresentarlo.

    Normalizza ai valori canonici i campi senza colonna: seed e config
    (non persistiti a livello di Carriera), ingaggio richiesto dei piloti,
    personalita' di spesa delle squadre AI. Nazionalita' e colori dello
    slot giocatore hanno colonna e restano intatti. E' il termine di
    confronto del round-trip save/load (vedi docstring modulo).
    """
    return replace(
        world,
        seed=UNPERSISTED_SEED,
        config=WorldConfig(),
        ai_teams=tuple(
            replace(team, personality=UNPERSISTED_PERSONALITY) for team in world.ai_teams
        ),
        drivers=tuple(
            replace(driver, salary_demand_usd=UNPERSISTED_SALARY_DEMAND) for driver in world.drivers
        ),
    )


# ---------------------------------------------------------------------------
# Models -> INSERT parameters (order follows the columns in checkpoint.py)
# ---------------------------------------------------------------------------


def engine_supplier_params(career_id: uuid.UUID, supplier: EngineSupplier) -> tuple[Any, ...]:
    """Parametri per l'INSERT in engine_suppliers."""
    return (
        row_uuid(career_id, "engine_supplier", supplier.id),
        career_id,
        supplier.name,
        supplier.engine_power,
        supplier.customer_fee_usd,
    )


def team_params(career_id: uuid.UUID, team: Team) -> tuple[Any, ...]:
    """Parametri per l'INSERT in teams (squadra AI, is_player false)."""
    supplier_uuid = (
        None
        if team.engine_supplier_id is None
        else row_uuid(career_id, "engine_supplier", team.engine_supplier_id)
    )
    return (
        row_uuid(career_id, "team", team.id),
        career_id,
        team.name,
        team.prestige,
        team.cash_usd,
        team.chassis_philosophy,
        supplier_uuid,
        team.engine_power,
        team.downforce,
        team.aero_efficiency,
        team.mechanical_grip,
        team.tyre_management,
        team.reliability,
    )


def player_slot_params(career_id: uuid.UUID, slot: PlayerSlot) -> tuple[Any, ...]:
    """Parametri per l'INSERT dello slot del giocatore in teams (pre-setup).

    Solo per slot con nome valorizzato: lo slot vuoto pre-creazione non ha
    una riga (teams.name e' NOT NULL) e il load lo ricostruisce vuoto.
    I colori della livrea viaggiano con lo slot (NULL se non scelti);
    motore e attributi restano ai default dello schema finche' il wizard
    di Setup squadra non completa (vedi player_team_params).
    """
    return (
        row_uuid(career_id, "team", PLAYER_SLOT_ID),
        career_id,
        slot.name,
        slot.primary_color,
        slot.secondary_color,
    )


def player_team_params(career_id: uuid.UUID, slot: PlayerSlot) -> tuple[Any, ...]:
    """Parametri per l'INSERT della squadra del giocatore (post-setup).

    A Setup squadra completato (FOR-7) la riga porta anche Filosofia
    telaio, fornitura motore e i 6 Attributi vettura iniziali; prestige e
    cash_usd restano ai default dello schema (economia runtime: T4.x).
    """
    supplier_uuid = (
        None
        if slot.engine_supplier_id is None
        else row_uuid(career_id, "engine_supplier", slot.engine_supplier_id)
    )
    return (
        row_uuid(career_id, "team", PLAYER_SLOT_ID),
        career_id,
        slot.name,
        slot.primary_color,
        slot.secondary_color,
        slot.chassis_philosophy,
        supplier_uuid,
        slot.engine_power,
        slot.downforce,
        slot.aero_efficiency,
        slot.mechanical_grip,
        slot.tyre_management,
        slot.reliability,
    )


def driver_params(career_id: uuid.UUID, driver: Driver) -> tuple[Any, ...]:
    """Parametri per l'INSERT in drivers.

    L'ingaggio richiesto non ha colonna (lacuna di schema) e non viene
    scritto; nazionalita' e Potenziale hanno le loro colonne.
    """
    return (
        row_uuid(career_id, "driver", driver.id),
        career_id,
        driver.name,
        driver.nationality,
        driver.age,
        driver.one_lap_pace,
        driver.race_pace,
        driver.duels,
        driver.tyre_management,
        driver.wet_weather,
        driver.consistency,
        driver.potential,
    )


def contract_params(career_id: uuid.UUID, position: int, contract: Contract) -> tuple[Any, ...]:
    """Parametri per l'INSERT in contracts.

    La posizione (1-based) nella tupla world.contracts e' codificata
    nell'uuid della riga per ricostruire l'ordine originale al load.
    """
    return (
        row_uuid(career_id, "contract", position),
        career_id,
        row_uuid(career_id, "team", contract.team_id),
        row_uuid(career_id, "driver", contract.driver_id),
        contract.start_season,
        contract.duration_seasons,
        contract.salary_usd,
    )


# ---------------------------------------------------------------------------
# Rows (dict) -> models
# ---------------------------------------------------------------------------


def engine_supplier_from_row(row: dict[str, Any]) -> EngineSupplier:
    """Ricostruisce un Motorista da una riga di engine_suppliers."""
    return EngineSupplier(
        id=id_from_uuid(row["id"]),
        name=row["name"],
        engine_power=int(row["engine_power"]),
        customer_fee_usd=int(row["customer_fee_usd"]),
    )


def team_from_row(row: dict[str, Any]) -> Team:
    """Ricostruisce una Squadra AI da una riga di teams.

    La personalita' di spesa non e' persistita (lacuna di schema): torna
    al valore canonico UNPERSISTED_PERSONALITY.
    """
    supplier_uuid = row["engine_supplier_id"]
    return Team(
        id=id_from_uuid(row["id"]),
        name=row["name"],
        prestige=int(row["prestige"]),
        cash_usd=int(row["cash_usd"]),
        chassis_philosophy=row["chassis_philosophy"],
        engine_supplier_id=None if supplier_uuid is None else id_from_uuid(supplier_uuid),
        engine_power=int(row["engine_power"]),
        downforce=int(row["downforce"]),
        aero_efficiency=int(row["aero_efficiency"]),
        mechanical_grip=int(row["mechanical_grip"]),
        tyre_management=int(row["tyre_management"]),
        reliability=int(row["reliability"]),
        personality=UNPERSISTED_PERSONALITY,
    )


def driver_from_row(row: dict[str, Any]) -> Driver:
    """Ricostruisce un Pilota da una riga di drivers.

    L'ingaggio richiesto non e' persistito (lacuna di schema): torna al
    valore canonico. La nazionalita' si legge dalla sua colonna.
    """
    return Driver(
        id=id_from_uuid(row["id"]),
        name=row["name"],
        nationality=row["nationality"],
        age=int(row["age"]),
        one_lap_pace=int(row["one_lap_pace"]),
        race_pace=int(row["race_pace"]),
        duels=int(row["duels"]),
        tyre_management=int(row["tyre_management"]),
        wet_weather=int(row["wet_weather"]),
        consistency=int(row["consistency"]),
        potential=int(row["potential"]),
        salary_demand_usd=UNPERSISTED_SALARY_DEMAND,
    )


def contract_from_row(row: dict[str, Any]) -> Contract:
    """Ricostruisce un Contratto da una riga di contracts."""
    return Contract(
        driver_id=id_from_uuid(row["driver_id"]),
        team_id=id_from_uuid(row["team_id"]),
        start_season=int(row["start_season"]),
        duration_seasons=int(row["duration_seasons"]),
        salary_usd=int(row["salary_usd"]),
    )


def player_slot_from_row(row: dict[str, Any] | None, set_up: bool) -> PlayerSlot:
    """Ricostruisce lo slot del giocatore dalla sua riga di teams.

    Riga assente = slot vuoto pre-creazione (nessuna identita' scelta).
    Le colonne di vettura hanno default NOT NULL nello schema, quindi una
    riga pre-setup le ha comunque valorizzate: set_up (la presenza dei
    Contratti del giocatore, vedi world_from_rows) distingue il Setup
    squadra completato dalla riga ai default, e prima del setup i campi
    di vettura tornano None come nel Mondo mai salvato.
    """
    if row is None:
        return PlayerSlot()
    if not set_up:
        return PlayerSlot(
            name=row["name"],
            primary_color=row["primary_color"],
            secondary_color=row["secondary_color"],
        )
    supplier_uuid = row["engine_supplier_id"]
    return PlayerSlot(
        name=row["name"],
        primary_color=row["primary_color"],
        secondary_color=row["secondary_color"],
        chassis_philosophy=row["chassis_philosophy"],
        engine_supplier_id=None if supplier_uuid is None else id_from_uuid(supplier_uuid),
        engine_power=int(row["engine_power"]),
        downforce=int(row["downforce"]),
        aero_efficiency=int(row["aero_efficiency"]),
        mechanical_grip=int(row["mechanical_grip"]),
        tyre_management=int(row["tyre_management"]),
        reliability=int(row["reliability"]),
    )


def world_from_rows(
    engine_supplier_rows: list[dict[str, Any]],
    ai_team_rows: list[dict[str, Any]],
    player_slot_row: dict[str, Any] | None,
    driver_rows: list[dict[str, Any]],
    contract_rows: list[dict[str, Any]],
) -> World:
    """Riassembla il Mondo dalle righe delle tabelle di stato.

    Le tuple sono ordinate per id interno decodificato: coincide con
    l'ordine di generazione originale. Seed e config tornano ai valori
    canonici (lacuna di schema: non esiste dove persisterli). Il Setup
    squadra e' completato se e solo se esistono Contratti del giocatore
    (il wizard li scrive insieme alla vettura, atomicamente).
    """

    def _by_internal_id(row: dict[str, Any]) -> int:
        return id_from_uuid(row["id"])

    player_set_up = any(id_from_uuid(row["team_id"]) == PLAYER_SLOT_ID for row in contract_rows)
    return World(
        seed=UNPERSISTED_SEED,
        config=WorldConfig(),
        ai_teams=tuple(team_from_row(row) for row in sorted(ai_team_rows, key=_by_internal_id)),
        player_slot=player_slot_from_row(player_slot_row, set_up=player_set_up),
        drivers=tuple(driver_from_row(row) for row in sorted(driver_rows, key=_by_internal_id)),
        engine_suppliers=tuple(
            engine_supplier_from_row(row)
            for row in sorted(engine_supplier_rows, key=_by_internal_id)
        ),
        contracts=tuple(
            contract_from_row(row) for row in sorted(contract_rows, key=_by_internal_id)
        ),
    )
