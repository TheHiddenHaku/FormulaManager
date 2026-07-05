"""Database SQLite temporaneo, condiviso dai test che toccano la persistenza.

Sostituisce il Postgres effimero Docker (ADR 0004): niente Docker, niente
rete. Un file SQLite in una cartella temporanea, con schema e seed applicati
da fm_persistence.connect al primo avvio. Function-scoped: ogni test parte da
un database nuovo e isolato, quindi non serve pulizia esplicita.
"""

import pytest

from fm_persistence import ENV_VAR, connect


@pytest.fixture
def game_db_path(tmp_path, monkeypatch):
    """Percorso di un DB SQLite temporaneo, schema e seed gia' applicati.

    Punta FM_DB_PATH al file cosi' che fm_persistence.connect (anche dentro
    l'app TUI e nelle connessioni dirette dei test) usi lo stesso database, e
    lo inizializza subito applicando schema.sql e seed.sql.
    """
    path = tmp_path / "formulamanager.db"
    monkeypatch.setenv(ENV_VAR, str(path))
    connect().close()
    return path
