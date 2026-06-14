"""Programmi e costanti dei Test pre-season (T5.1.2).

Prima del primo GP la squadra dispone di alcuni giorni di Test: per ogni
giorno e pilota si sceglie un Programma. Sono distinti dai Programmi delle
prove libere (Setup, Gomme, ...): qui valgono solo Sviluppo, Conoscenza e
Affidabilita'. La Conoscenza e' l'unico Programma che stringe le Stime
sugli attributi propri (T5.1.2).

Motore puro (ADR 0002).
"""

from enum import Enum


class PreseasonProgramme(Enum):
    """Un Programma assegnabile a un pilota in un giorno di Test."""

    DEVELOPMENT = "development"
    KNOWLEDGE = "knowledge"
    RELIABILITY = "reliability"


# Days of the pre-season test before the opening grand prix.
PRESEASON_DAYS = 6

# The venue of the pre-season test (Bahrain, the real winter test track).
TEST_CIRCUIT_CODE = "sakhir"

# Knowledge levels gained on a driver and the player car by a Knowledge
# programme day (the only programme that tightens the own estimates).
KNOWLEDGE_GAIN_PER_DAY = 1
