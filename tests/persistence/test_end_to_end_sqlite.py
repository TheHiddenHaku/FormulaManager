"""Verifica end-to-end SQLite: crea, salva e ricarica una Carriera offline.

Issue ombrello "sqlite": il gioco parte, crea una Carriera, salva e ricarica
senza rete, senza Docker e senza Tailscale. Qui si esercita il flusso vero su
un file SQLite reale in una cartella temporanea, attraverso due "sessioni"
(due connect() distinti, come un riavvio del gioco): la prima crea il database
e salva, la seconda riapre lo stesso file e ricarica identico.
"""

from dataclasses import replace

from fm_engine.career import Career
from fm_engine.world import PlayerSlot, generate
from fm_persistence import connect, list_careers, load_career, save_career
from fm_persistence.connection import ENV_VAR
from fm_persistence.mapping import persistable_projection

SEED = 42


def test_create_save_reload_across_sessions(monkeypatch, tmp_path):
    db_path = tmp_path / "game" / "formulamanager.db"
    monkeypatch.setenv(ENV_VAR, str(db_path))
    world = replace(generate(SEED), player_slot=PlayerSlot(name="Scuderia E2E"))

    # Sessione 1: primo avvio. connect() crea il file (cartelle incluse),
    # applica schema e seed, poi si salva una Carriera.
    assert not db_path.exists()
    conn = connect()
    try:
        assert db_path.exists()
        saved = save_career(conn, Career(name="Carriera E2E", world=world))
    finally:
        conn.close()

    # Sessione 2: riavvio del gioco. Un nuovo connect() sullo stesso file NON
    # riapplica lo schema e ritrova la Carriera, ricaricata identica.
    conn2 = connect()
    try:
        summaries = list_careers(conn2)
        reloaded = load_career(conn2, saved.id)
    finally:
        conn2.close()

    assert [summary.name for summary in summaries] == ["Carriera E2E"]
    assert reloaded == replace(saved, world=persistable_projection(world))
