"""Informazione imperfetta: le Stime degli attributi (T5.1.2).

Il giocatore non vede mai i valori esatti degli Attributi (vettura o
pilota): vede Stime, intervalli con un margine di incertezza che si
stringe man mano che accumula informazione (Test pre-season, prove
libere, gare disputate). Motore puro (ADR 0002).
"""

from fm_engine.info.estimates import (
    INITIAL_MARGIN,
    MINIMUM_MARGIN,
    Estimate,
    KnowledgeState,
    car_subject,
    default_estimate,
    driver_subject,
    format_estimate,
    margin_for_level,
)
from fm_engine.info.observation import observe_practice, observe_race, race_subjects

__all__ = [
    "INITIAL_MARGIN",
    "MINIMUM_MARGIN",
    "Estimate",
    "KnowledgeState",
    "car_subject",
    "default_estimate",
    "driver_subject",
    "format_estimate",
    "margin_for_level",
    "observe_practice",
    "observe_race",
    "race_subjects",
]
