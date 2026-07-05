#!/bin/sh
#
# Avvia Formula Manager sul database SQLite locale.
#
# Cosa fa, in ordine:
#   1. crea il venv e installa il progetto al primo avvio (uv se presente, pip altrimenti);
#   2. lancia il gioco (comando fm).
#
# Il database e' un file SQLite locale, creato al primo avvio (percorso di
# default sotto la home dell'utente, override con FM_DB_PATH). Nessuna rete,
# nessun Docker, nessun servizio remoto: il gioco parte e salva offline.
#
# Uso: scripts/play.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# First run: create the venv and install the project
if [ ! -x .venv/bin/fm ]; then
    echo "Preparo l'ambiente (.venv)..."
    if command -v uv >/dev/null 2>&1; then
        uv venv .venv
        uv pip install -e . --python .venv/bin/python
    else
        python3 -m venv .venv
        .venv/bin/pip install -e .
    fi
fi

exec .venv/bin/fm
