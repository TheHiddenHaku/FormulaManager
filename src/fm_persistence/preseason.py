"""Serializzazione della fase Test pre-season (T5.1.2).

Il PreseasonState del motore viaggia nella colonna careers.preseason_state
come documento JSON: giorni totali e giorni svolti, ciascuno con i
Programmi assegnati ai piloti. Le chiavi pilota diventano stringhe in JSON
e tornano interi al load; i Programmi passano dal loro valore canonico.
Stato di partenza (fase non iniziata) non scritto: colonna NULL e load al
canonico PreseasonState().
"""

from typing import Any

from fm_engine.preseason import PreseasonDay, PreseasonProgramme, PreseasonState


def preseason_state_payload(preseason: PreseasonState) -> dict[str, Any] | None:
    """Il documento JSON della fase, None se non ancora iniziata."""
    if preseason == PreseasonState():
        return None
    return {
        "total_days": preseason.total_days,
        "days_done": [_day_payload(day) for day in preseason.days_done],
    }


def preseason_state_from_payload(payload: dict[str, Any] | None) -> PreseasonState:
    """Ricostruisce la fase dal documento JSON, o il default."""
    if payload is None:
        return PreseasonState()
    return PreseasonState(
        total_days=int(payload["total_days"]),
        days_done=tuple(_day_from_payload(row) for row in payload["days_done"]),
    )


def _day_payload(day: PreseasonDay) -> dict[str, Any]:
    return {
        "day": day.day,
        "programmes": {
            str(driver_id): programme.value for driver_id, programme in day.programmes.items()
        },
    }


def _day_from_payload(payload: dict[str, Any]) -> PreseasonDay:
    return PreseasonDay(
        day=int(payload["day"]),
        programmes={
            int(driver_id): PreseasonProgramme(value)
            for driver_id, value in payload["programmes"].items()
        },
    )
