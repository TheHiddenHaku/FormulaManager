#!/bin/sh
#
# Harness manuale del Mercato piloti su un Postgres effimero in Docker.
#
# NON tocca matilde: avvia un Postgres usa-e-getta, semina una Carriera di
# fine stagione 2027 pronta per il Mercato e lancia la TUI. Alla chiusura il
# container viene rimosso. Dettagli e passi: scripts/play_market.py.
#
# Prerequisiti: Docker attivo, python3 o uv.
#
# Uso: scripts/play_market.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# First run: create the venv and install the project (like play.sh).
if [ ! -x .venv/bin/python ]; then
    echo "Preparo l'ambiente (.venv)..."
    if command -v uv >/dev/null 2>&1; then
        uv venv .venv
        uv pip install -e . --python .venv/bin/python
    else
        python3 -m venv .venv
        .venv/bin/pip install -e .
    fi
fi

exec .venv/bin/python scripts/play_market.py
