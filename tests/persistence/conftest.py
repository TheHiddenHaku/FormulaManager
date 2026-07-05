"""Fixture dei test di persistenza (ADR 0004, FOR-5).

Il DB SQLite temporaneo vive in tests/conftest.py (fixture game_db_path,
condivisa con i test Pilot della TUI); qui resta la connessione per-test.
"""

import pytest

from fm_persistence import connect


@pytest.fixture
def conn(game_db_path):
    """Connessione al DB SQLite temporaneo, una per test.

    Il file e' gia' inizializzato (schema + seed) da game_db_path; qui si apre
    una connessione con foreign_keys attivo e la si chiude a fine test. Ogni
    test parte da un database nuovo, quindi non serve pulizia delle Carriere.
    """
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()
