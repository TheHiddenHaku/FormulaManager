"""Configurazione della connessione Postgres via FM_DATABASE_URL.

FM_DATABASE_URL e' l'unica variabile d'ambiente canonica letta dal layer
di persistenza. In gioco punta al Postgres del Supabase self-hosted sulla
VPS matilde via Tailscale (come costruirla: supabase/README.md); per test
e sviluppo e' ammesso un Postgres effimero o locale. Il codice non
distingue i due casi: cambia solo il valore della variabile.
"""

import os

import psycopg

ENV_VAR = "FM_DATABASE_URL"


def database_url() -> str:
    """Ritorna l'URL Postgres da FM_DATABASE_URL.

    Solleva RuntimeError se la variabile manca o e' vuota: senza database
    raggiungibile il gioco non parte (limite accettato, ADR 0001).
    """
    url = os.environ.get(ENV_VAR, "").strip()
    if not url:
        # Player-facing message (printed at startup): stays in Italian.
        raise RuntimeError(
            f"variabile d'ambiente {ENV_VAR} assente o vuota: "
            "deve contenere l'URL Postgres del database di gioco "
            "(vedi supabase/README.md per costruirla)"
        )
    return url


def connect() -> psycopg.Connection:
    """Apre una connessione Postgres all'URL di FM_DATABASE_URL.

    Autocommit disattivo: le operazioni di Checkpoint gestiscono le
    transazioni in modo esplicito (una transazione atomica per save).
    """
    return psycopg.connect(database_url())
