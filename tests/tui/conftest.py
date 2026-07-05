"""Fixture dei test Pilot della TUI (ADR 0004, FOR-6).

I test Pilot che toccano il database usano il DB SQLite temporaneo condiviso
(tests/conftest.py, fixture game_db_path): db_env punta FM_DB_PATH al file e
ne ritorna il percorso, cosi' fm_persistence.connect dentro l'app raggiunge
il database di test e i test possono ispezionarlo con una connessione
sqlite3 diretta. Database nuovo per test: niente pulizia esplicita.
"""

import pytest


@pytest.fixture
def db_env(game_db_path):
    """FM_DB_PATH puntata a un DB SQLite temporaneo, gia' inizializzato.

    Ritorna il percorso del file (str) per le connessioni dirette dei test.
    """
    return str(game_db_path)
