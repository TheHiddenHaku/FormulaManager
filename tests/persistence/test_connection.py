"""Test della configurazione via FM_DATABASE_URL (senza database)."""

import pytest

from fm_persistence.connection import ENV_VAR, database_url


def test_url_read_from_canonical_env_var(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "postgresql://utente:segreto@host:5432/gioco")
    assert database_url() == "postgresql://utente:segreto@host:5432/gioco"


def test_missing_env_var_raises_with_clear_message(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    with pytest.raises(RuntimeError, match=ENV_VAR):
        database_url()


def test_empty_env_var_equals_missing(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "   ")
    with pytest.raises(RuntimeError, match=ENV_VAR):
        database_url()
