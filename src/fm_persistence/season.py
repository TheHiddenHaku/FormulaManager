"""Serializzazione dello stato di stagione per il Checkpoint (T5.1.1).

Il SeasonState del motore viaggia nella colonna careers.season_state come
documento JSON: anno, data di gioco e i risultati dei GP disputati (round,
circuito e classifica finale coi punti). Stesso schema degli altri stati
di Carriera (weekend, solvibilita'): lo stato di partenza non si scrive
(colonna NULL) e al load torna al canonico SeasonState().

Le date passano dalla forma ISO; i risultati conservano l'ordine di
disputa. Motore puro a monte (ADR 0002): qui vive la sola persistenza.
"""

from datetime import date
from typing import Any

from fm_engine.events import ClassifiedResult
from fm_engine.season import RoundResult, SeasonState


def season_state_payload(season: SeasonState) -> dict[str, Any] | None:
    """Il documento JSON dello stato di stagione, None per lo stato di partenza.

    Lo stato default non si scrive: la colonna resta NULL e il load torna
    al canonico SeasonState(), identico per costruzione.
    """
    if season == SeasonState():
        return None
    return {
        "year": season.year,
        "game_date": season.game_date.isoformat(),
        "results": [_round_result_payload(result) for result in season.results],
    }


def season_state_from_payload(payload: dict[str, Any] | None) -> SeasonState:
    """Ricostruisce lo stato di stagione dal documento JSON, o il default."""
    if payload is None:
        return SeasonState()
    return SeasonState(
        year=int(payload["year"]),
        game_date=date.fromisoformat(payload["game_date"]),
        results=tuple(_round_result_from_payload(row) for row in payload["results"]),
    )


def _round_result_payload(result: RoundResult) -> dict[str, Any]:
    return {
        "round": result.round,
        "circuit_code": result.circuit_code,
        "classification": [_classified_result_payload(row) for row in result.classification],
    }


def _round_result_from_payload(payload: dict[str, Any]) -> RoundResult:
    return RoundResult(
        round=int(payload["round"]),
        circuit_code=payload["circuit_code"],
        classification=tuple(
            _classified_result_from_payload(row) for row in payload["classification"]
        ),
    )


def _classified_result_payload(result: ClassifiedResult) -> dict[str, Any]:
    return {
        "position": result.position,
        "driver_id": result.driver_id,
        "team_id": result.team_id,
        "total_time_seconds": result.total_time_seconds,
        "gap_to_winner_seconds": result.gap_to_winner_seconds,
        "points": result.points,
        "penalty_seconds": result.penalty_seconds,
    }


def _classified_result_from_payload(payload: dict[str, Any]) -> ClassifiedResult:
    return ClassifiedResult(
        position=int(payload["position"]),
        driver_id=int(payload["driver_id"]),
        team_id=int(payload["team_id"]),
        total_time_seconds=float(payload["total_time_seconds"]),
        gap_to_winner_seconds=float(payload["gap_to_winner_seconds"]),
        points=int(payload["points"]),
        penalty_seconds=float(payload["penalty_seconds"]),
    )
