"""Costruzione delle voci di archivio dai dati veri del flusso di gara (T5.3.2).

Trasforma i dati prodotti dal weekend (griglia di partenza dalle
Qualifiche, ordine d'arrivo e eventi di gara) nelle voci dell'Almanacco,
e ricava le classifiche finali di stagione dai risultati gia' registrati
nello SeasonState. E' la cerniera tra il flusso di gioco (T5.1.1) e
l'archivio permanente (history.models), tutta calcolo puro (ADR 0002).
"""

from collections.abc import Sequence

from fm_engine.events import ClassifiedResult, Dnf, SafetyCarDeployed
from fm_engine.history.models import (
    ArchivedGrandPrix,
    PrincipalEvent,
    PrincipalEventKind,
)
from fm_engine.season.standings import (
    ConstructorStanding,
    DriverStanding,
    RoundResult,
    constructor_standings,
    driver_standings,
)

# Causa leggibile dell'Abbandono per il dettaglio archiviato.
_DNF_CAUSE_LABELS = {
    "failure": "Guasto",
    "driver_error": "Errore",
    "accident": "Incidente",
}


def _principal_events(events: Sequence[object]) -> tuple[PrincipalEvent, ...]:
    """Filtra gli eventi principali da archiviare: Safety car e Abbandoni.

    Non si archivia la Telecronaca integrale (ADR 0003): si tengono solo
    gli accadimenti che meritano memoria storica, in ordine di giro e
    poi di apparizione (l'ordine d'arrivo degli eventi e' stabile).
    """
    archived: list[PrincipalEvent] = []
    for event in events:
        if isinstance(event, SafetyCarDeployed):
            archived.append(
                PrincipalEvent(
                    kind=PrincipalEventKind.SAFETY_CAR,
                    lap=event.lap,
                    detail=f"Safety car per {event.duration_laps} giri",
                )
            )
        elif isinstance(event, Dnf):
            cause = _DNF_CAUSE_LABELS.get(event.cause.value, event.cause.value)
            detail = f"Abbandono ({cause}): {event.detail}"
            archived.append(
                PrincipalEvent(
                    kind=PrincipalEventKind.DNF,
                    lap=event.lap,
                    detail=detail,
                    driver_id=event.driver_id,
                )
            )
    archived.sort(key=lambda item: item.lap)
    return tuple(archived)


def build_archived_grand_prix(
    round_: int,
    circuit_code: str,
    starting_grid: Sequence[int],
    classification: Sequence[ClassifiedResult],
    events: Sequence[object],
) -> ArchivedGrandPrix:
    """Costruisce la voce di Almanacco di un GP dai dati veri del weekend.

    starting_grid e' la griglia di partenza in ordine di pole (dalle
    Qualifiche); classification l'ordine d'arrivo coi punti; events gli
    eventi di gara da cui si estraggono gli eventi principali.
    """
    return ArchivedGrandPrix(
        round=round_,
        circuit_code=circuit_code,
        starting_grid=tuple(starting_grid),
        classification=tuple(classification),
        principal_events=_principal_events(events),
    )


def final_standings(
    season_results: Sequence[RoundResult],
    driver_ids: Sequence[int],
    team_ids: Sequence[int],
) -> tuple[tuple[DriverStanding, ...], tuple[ConstructorStanding, ...]]:
    """Le classifiche finali piloti e costruttori di una stagione conclusa.

    Si ricostruiscono dai risultati dei GP della stagione (SeasonState)
    prima che l'orologio le azzeri (advance_to_next_season, T5.1.1): per
    questo l'archiviazione di fine stagione va eseguita sul SeasonState
    ancora pieno.
    """
    return (
        driver_standings(season_results, driver_ids),
        constructor_standings(season_results, team_ids),
    )
