"""Connessione al database SQLite di gioco via FM_DB_PATH (ADR 0004).

Il database di gioco e' un singolo file SQLite locale: nessun servizio
remoto, niente rete, niente Docker. Il percorso si configura con l'unica
variabile d'ambiente FM_DB_PATH; in assenza si usa un default sotto la home
dell'utente. Al primo avvio (file assente o senza tabelle) connect() crea le
cartelle e applica schema.sql e seed.sql, package data di questo pacchetto.

sqlite3 e' nella standard library: il layer di persistenza non ha piu'
dipendenze esterne. Gli id (uuid) e i timestamp (datetime, date) viaggiano
come testo, coerenti con lo schema; gli adapter registrati qui sotto fanno la
serializzazione in scrittura, la lettura riconverte esplicitamente dove serve.
"""

import os
import sqlite3
import uuid
from datetime import date, datetime
from importlib.resources import files
from pathlib import Path

ENV_VAR = "FM_DB_PATH"

# Default sotto la home dell'utente (XDG data dir), creato al primo avvio.
_DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "formulamanager" / "formulamanager.db"

# Serializzazione in scrittura verso le colonne text dello schema:
#   uuid -> forma canonica, datetime e date -> ISO 8601.
# I bool sono sottoclasse di int e sqlite3 li scrive come 0/1 nativamente.
sqlite3.register_adapter(uuid.UUID, str)
sqlite3.register_adapter(datetime, lambda value: value.isoformat())
sqlite3.register_adapter(date, lambda value: value.isoformat())


def database_path() -> Path:
    """Percorso del file SQLite di gioco: FM_DB_PATH, o il default sotto la home."""
    raw = os.environ.get(ENV_VAR, "").strip()
    return Path(raw).expanduser() if raw else _DEFAULT_DB_PATH


def connect() -> sqlite3.Connection:
    """Apre il database SQLite di gioco, creandolo al primo avvio.

    Crea la cartella contenitrice se manca, apre il file con sqlite3 e attiva
    i vincoli di foreign key (impostazione per connessione, non nello schema).
    Se il database e' vuoto (primo avvio) applica schema.sql e seed.sql. Le
    transazioni dei Checkpoint restano esplicite (una transazione atomica per
    save), gestite dal modulo checkpoint.
    """
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("pragma foreign_keys = on")
    if _is_empty(conn):
        _initialize(conn)
    return conn


def _is_empty(conn: sqlite3.Connection) -> bool:
    """True se il database non ha ancora tabelle (primo avvio)."""
    row = conn.execute("select count(*) from sqlite_master where type = 'table'").fetchone()
    return row[0] == 0


def _initialize(conn: sqlite3.Connection) -> None:
    """Crea lo schema e carica i dati statici del seed su un database vuoto."""
    conn.executescript(_read_sql("schema.sql"))
    conn.executescript(_read_sql("seed.sql"))
    conn.commit()


def _read_sql(name: str) -> str:
    """Legge un file SQL dai package data di fm_persistence."""
    return files("fm_persistence").joinpath(name).read_text(encoding="utf-8")
