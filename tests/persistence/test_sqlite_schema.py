"""Baseline SQLite: schema.sql e seed.sql applicati a un DB in memoria.

Nessun Docker, nessuna rete: schema e seed sono package data di fm_persistence
(letti via importlib.resources) e devono creare tutte le tabelle e caricare i
dati statici del seed su un semplice SQLite in memoria della stdlib.
"""

import sqlite3
from importlib.resources import files

# Tutte le tabelle della baseline (dati statici, stato di Carriera, archivio).
EXPECTED_TABLES = {
    "circuits",
    "points_tables",
    "race_prizes",
    "careers",
    "engine_suppliers",
    "teams",
    "drivers",
    "contracts",
    "seasons",
    "grands_prix",
    "sessions",
    "results",
    "financial_transactions",
    "development_projects",
    "archive_seasons",
    "archive_standings",
    "archive_grands_prix",
    "archive_starting_grid",
    "archive_results",
    "archive_principal_events",
}


def _sql(name: str) -> str:
    return files("fm_persistence").joinpath(name).read_text(encoding="utf-8")


def _memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(_sql("schema.sql"))
    conn.executescript(_sql("seed.sql"))
    return conn


def test_schema_creates_every_table():
    conn = _memory_db()
    try:
        rows = conn.execute("select name from sqlite_master where type = 'table'").fetchall()
    finally:
        conn.close()
    tables = {row[0] for row in rows}
    assert EXPECTED_TABLES <= tables, EXPECTED_TABLES - tables


def test_schema_sets_user_version():
    conn = _memory_db()
    try:
        version = conn.execute("pragma user_version").fetchone()[0]
    finally:
        conn.close()
    assert version == 1


def test_seed_row_counts():
    conn = _memory_db()
    try:
        circuits = conn.execute("select count(*) from circuits").fetchone()[0]
        points = conn.execute("select count(*) from points_tables").fetchone()[0]
        prizes = conn.execute("select count(*) from race_prizes").fetchone()[0]
        race_points = conn.execute(
            "select sum(points) from points_tables where code = 'race_2026'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert circuits == 24
    # 10 posizioni gara + 8 sprint.
    assert points == 18
    assert prizes == 22
    # 25+18+15+12+10+8+6+4+2+1 = 101.
    assert race_points == 101


def test_seed_is_idempotent():
    conn = _memory_db()
    try:
        conn.executescript(_sql("seed.sql"))
        circuits = conn.execute("select count(*) from circuits").fetchone()[0]
    finally:
        conn.close()
    assert circuits == 24
