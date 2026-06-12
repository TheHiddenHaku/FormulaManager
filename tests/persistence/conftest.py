"""Fixture dei test di persistenza (FOR-5).

Il Postgres effimero Docker vive in tests/conftest.py (fixture condivisa
ephemeral_database_url, promossa con FOR-6); qui resta solo la
connessione per-test con pulizia delle Carriere.
"""

import psycopg
import pytest


@pytest.fixture
def conn(ephemeral_database_url):
    """Connessione psycopg al Postgres effimero, una per test.

    A fine test cancella tutte le Carriere (cascata sulle FK): ogni test
    parte da un database con i soli dati statici del seed.
    """
    with psycopg.connect(ephemeral_database_url) as connection:
        yield connection
        connection.rollback()
        with connection.transaction():
            connection.execute("delete from careers")
