"""Fixture dei test Pilot della TUI (FOR-6).

I test Pilot che toccano il database usano il Postgres effimero Docker
condiviso (tests/conftest.py, mai matilde): la fixture db_env punta
FM_DATABASE_URL al container, cosi' fm_persistence.connect dentro
l'app raggiunge il database di test, e a fine test cancella tutte le
Carriere (cascata sulle FK).
"""

import psycopg
import pytest

from fm_persistence import ENV_VAR


@pytest.fixture
def db_env(ephemeral_database_url, monkeypatch):
    """FM_DATABASE_URL puntata al Postgres effimero, Carriere pulite a fine test."""
    monkeypatch.setenv(ENV_VAR, ephemeral_database_url)
    yield ephemeral_database_url
    with psycopg.connect(ephemeral_database_url, autocommit=True) as connection:
        connection.execute("delete from careers")
