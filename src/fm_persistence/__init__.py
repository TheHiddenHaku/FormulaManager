"""Persistenza a Checkpoint delle Carriere su SQLite (ADR 0004, FOR-5).

L'API pubblica espone solo operazioni a granularita' di Carriera intera:
save_career, load_career, list_careers, delete_career. Per design non
esistono query piu' fini: durante il gioco lo stato vive in memoria e il
database si tocca solo ai Checkpoint.

Il database e' un file SQLite locale, configurato con l'unica variabile
d'ambiente FM_DB_PATH (vedi connection.py). Questo pacchetto importa
fm_engine (i modelli da persistere); il motore non importa mai questo
pacchetto (ADR 0002).
"""

from fm_persistence.checkpoint import (
    CareerNotFoundError,
    CareerSummary,
    delete_career,
    list_careers,
    load_career,
    save_career,
)
from fm_persistence.connection import ENV_VAR, connect, database_path

__all__ = [
    "ENV_VAR",
    "CareerNotFoundError",
    "CareerSummary",
    "connect",
    "database_path",
    "delete_career",
    "list_careers",
    "load_career",
    "save_career",
]
