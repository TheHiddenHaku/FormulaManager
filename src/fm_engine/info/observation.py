"""Aggiornamento della conoscenza osservando le sessioni (T5.1.2).

Le gare disputate e le prove libere stringono le Stime: vedere correre
un pilota e la sua vettura alza il livello di conoscenza dei soggetti
coinvolti. Qui si traduce una classifica (o una sessione del giocatore)
nei soggetti osservati e si applica il guadagno di conoscenza.

Motore puro (ADR 0002).
"""

from collections.abc import Iterable, Sequence

from fm_engine.events import ClassifiedResult
from fm_engine.info.estimates import KnowledgeState, car_subject, driver_subject


def race_subjects(classification: Sequence[ClassifiedResult]) -> list[str]:
    """I soggetti osservati in una gara: ogni pilota e ogni vettura in pista."""
    subjects: list[str] = []
    for result in classification:
        subjects.append(driver_subject(result.driver_id))
        subjects.append(car_subject(result.team_id))
    return subjects


def observe_race(
    knowledge: KnowledgeState, classification: Sequence[ClassifiedResult]
) -> KnowledgeState:
    """Stringe le Stime di tutti i piloti e le vetture viste correre."""
    return knowledge.observed(race_subjects(classification))


def observe_practice(
    knowledge: KnowledgeState, driver_ids: Iterable[int], team_id: int
) -> KnowledgeState:
    """Stringe le Stime dei piloti del giocatore e della sua vettura."""
    subjects = [driver_subject(driver_id) for driver_id in driver_ids]
    subjects.append(car_subject(team_id))
    return knowledge.observed(subjects)
