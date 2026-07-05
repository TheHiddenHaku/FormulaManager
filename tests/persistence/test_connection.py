"""Test della connessione SQLite via FM_DB_PATH (ADR 0004)."""

from fm_persistence import connect
from fm_persistence.connection import ENV_VAR, database_path


def test_path_read_from_canonical_env_var(monkeypatch, tmp_path):
    target = tmp_path / "sub" / "game.db"
    monkeypatch.setenv(ENV_VAR, str(target))
    assert database_path() == target


def test_default_path_without_env_var(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    path = database_path()
    assert path.name == "formulamanager.db"
    assert path.is_absolute()


def test_connect_bootstraps_schema_and_seed(monkeypatch, tmp_path):
    """Al primo avvio connect crea il file, applica schema e seed, attiva le FK."""
    target = tmp_path / "nested" / "game.db"
    monkeypatch.setenv(ENV_VAR, str(target))
    conn = connect()
    try:
        assert target.exists()
        assert conn.execute("select count(*) from circuits").fetchone()[0] == 24
        assert conn.execute("pragma foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_connect_is_idempotent_on_existing_db(monkeypatch, tmp_path):
    """Riaprire un DB gia' inizializzato non riapplica lo schema."""
    target = tmp_path / "game.db"
    monkeypatch.setenv(ENV_VAR, str(target))
    connect().close()
    conn = connect()
    try:
        assert conn.execute("select count(*) from circuits").fetchone()[0] == 24
    finally:
        conn.close()
