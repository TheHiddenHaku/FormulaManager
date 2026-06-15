"""Serializzazione dello stato di Mercato piloti per il Checkpoint (sub-issue M4).

Il MarketState del motore viaggia nella colonna careers.market_state come
documento JSON: fase, anno concluso, dimensione del roster, pool dei
Contratti in scadenza, piloti liberi e loro richieste salariali transitorie,
sedili vacanti, firme e log mosse. Stesso schema degli altri stati di
Carriera (season, preseason): lo stato di partenza (fase chiusa) non si
scrive (colonna NULL) e al load torna al canonico MarketState().

Le chiavi intere delle mappe (id di pilota o squadra) diventano stringhe in
JSON e tornano interi al load; le firme tornano tuple. La richiesta
salariale dei liberi vive qui, nel payload transitorio, non in una colonna
drivers. Di default si persiste l'intero log mosse mentre la fase e' aperta.
Motore puro a monte (ADR 0002): qui vive la sola persistenza.
"""

from typing import Any

from fm_engine.market import (
    AiMove,
    AiMoveKind,
    ExpiringContract,
    MarketPhase,
    MarketState,
)


def market_state_payload(market: MarketState) -> dict[str, Any] | None:
    """Il documento JSON dello stato di Mercato, None a fase chiusa (default).

    Lo stato di partenza non si scrive: la colonna resta NULL e il load
    torna al canonico MarketState(), identico per costruzione. Chiusa la
    finestra lo stato torna al default e la colonna a NULL.
    """
    if market == MarketState():
        return None
    return {
        "phase": market.phase.value,
        "concluded_year": market.concluded_year,
        "seats_per_team": market.seats_per_team,
        "pool": [_expiring_payload(item) for item in market.pool],
        "free_agent_ids": list(market.free_agent_ids),
        "salary_demands": {str(key): value for key, value in market.salary_demands.items()},
        "vacant_seats": {str(key): value for key, value in market.vacant_seats.items()},
        "signings": {str(key): list(value) for key, value in market.signings.items()},
        "ai_moves": [_move_payload(move) for move in market.ai_moves],
    }


def market_state_from_payload(payload: dict[str, Any] | None) -> MarketState:
    """Ricostruisce lo stato di Mercato dal documento JSON, o il default."""
    if payload is None:
        return MarketState()
    return MarketState(
        phase=MarketPhase(payload["phase"]),
        concluded_year=payload["concluded_year"],
        seats_per_team=int(payload["seats_per_team"]),
        pool=tuple(_expiring_from_payload(row) for row in payload["pool"]),
        free_agent_ids=tuple(int(driver_id) for driver_id in payload["free_agent_ids"]),
        salary_demands={int(key): int(value) for key, value in payload["salary_demands"].items()},
        vacant_seats={int(key): int(value) for key, value in payload["vacant_seats"].items()},
        signings={
            int(key): tuple(int(driver_id) for driver_id in value)
            for key, value in payload["signings"].items()
        },
        ai_moves=tuple(_move_from_payload(row) for row in payload["ai_moves"]),
    )


def _expiring_payload(contract: ExpiringContract) -> dict[str, Any]:
    return {
        "driver_id": contract.driver_id,
        "team_id": contract.team_id,
        "salary_usd": contract.salary_usd,
        "last_season": contract.last_season,
    }


def _expiring_from_payload(payload: dict[str, Any]) -> ExpiringContract:
    return ExpiringContract(
        driver_id=int(payload["driver_id"]),
        team_id=int(payload["team_id"]),
        salary_usd=int(payload["salary_usd"]),
        last_season=int(payload["last_season"]),
    )


def _move_payload(move: AiMove) -> dict[str, Any]:
    return {
        "team_id": move.team_id,
        "driver_id": move.driver_id,
        "kind": move.kind.value,
        "salary_usd": move.salary_usd,
        "duration_seasons": move.duration_seasons,
    }


def _move_from_payload(payload: dict[str, Any]) -> AiMove:
    return AiMove(
        team_id=int(payload["team_id"]),
        driver_id=int(payload["driver_id"]),
        kind=AiMoveKind(payload["kind"]),
        salary_usd=int(payload["salary_usd"]),
        duration_seasons=int(payload["duration_seasons"]),
    )
