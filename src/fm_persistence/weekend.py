"""Serializzazione dello stato weekend per il Checkpoint (FOR-21).

Il WeekendState del motore viaggia nella colonna careers.weekend_state
come documento JSON: questo modulo definisce il payload (solo primitivi
JSON) e la ricostruzione simmetrica. Le chiavi dei dizionari per pilota
diventano stringhe in JSON e tornano interi al load; gli enum passano
dal loro valore canonico.
"""

from typing import Any

from fm_engine.events import ClassifiedResult
from fm_engine.practice import DriverPracticeEffects, PracticeEffects
from fm_engine.tyres import Compound
from fm_engine.weekend import WeekendFormat, WeekendPhase, WeekendState


def weekend_state_payload(state: WeekendState | None) -> dict[str, Any] | None:
    """Il documento JSON-serializzabile dello stato weekend, o None."""
    if state is None:
        return None
    return {
        "circuit_code": state.circuit_code,
        "seed": state.seed,
        "phase": state.phase.value,
        "weekend_format": state.weekend_format.value,
        "effects": _effects_payload(state.effects),
        "grid_driver_ids": (None if state.grid_driver_ids is None else list(state.grid_driver_ids)),
        "race_classification": (
            None
            if state.race_classification is None
            else [_classified_result_payload(result) for result in state.race_classification]
        ),
    }


def weekend_state_from_payload(payload: dict[str, Any] | None) -> WeekendState | None:
    """Ricostruisce il WeekendState dal documento JSON, o None."""
    if payload is None:
        return None
    grid = payload["grid_driver_ids"]
    classification = payload["race_classification"]
    return WeekendState(
        circuit_code=payload["circuit_code"],
        seed=int(payload["seed"]),
        phase=WeekendPhase(payload["phase"]),
        weekend_format=WeekendFormat(payload["weekend_format"]),
        effects=_effects_from_payload(payload["effects"]),
        grid_driver_ids=None if grid is None else tuple(int(value) for value in grid),
        race_classification=(
            None
            if classification is None
            else tuple(_classified_result_from_payload(row) for row in classification)
        ),
    )


def _effects_payload(effects: PracticeEffects) -> dict[str, Any]:
    return {
        "drivers": {
            str(driver_id): {
                "setup_percentage": driver.setup_percentage,
                "qualifying_bonus_seconds": driver.qualifying_bonus_seconds,
                "race_pace_bonus_seconds": driver.race_pace_bonus_seconds,
            }
            for driver_id, driver in effects.drivers.items()
        },
        "revealed_compounds": sorted(compound.value for compound in effects.revealed_compounds),
        "strategy_insight": effects.strategy_insight,
    }


def _effects_from_payload(payload: dict[str, Any]) -> PracticeEffects:
    return PracticeEffects(
        drivers={
            int(driver_id): DriverPracticeEffects(
                setup_percentage=float(driver["setup_percentage"]),
                qualifying_bonus_seconds=float(driver["qualifying_bonus_seconds"]),
                race_pace_bonus_seconds=float(driver["race_pace_bonus_seconds"]),
            )
            for driver_id, driver in payload["drivers"].items()
        },
        revealed_compounds=frozenset(Compound(value) for value in payload["revealed_compounds"]),
        strategy_insight=int(payload["strategy_insight"]),
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
