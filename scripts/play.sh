#!/bin/sh
#
# Avvia Formula Manager collegato al Supabase self-hosted su matilde.
#
# Cosa fa, in ordine:
#   1. crea il venv e installa il progetto al primo avvio (uv se presente, pip altrimenti);
#   2. se FM_DATABASE_URL non e' gia' impostata, recupera la password del DB
#      via SSH da matilde (nessun segreto salvato nel repo);
#   3. lancia il gioco (comando fm).
#
# Prerequisiti: Tailscale attivo (matilde raggiungibile via SSH), python3 o uv.
#
# Uso: scripts/play.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DB_HOST="matilde"
DB_USER="postgres.formulamanager"
STACK_DIR="/opt/formulamanager-supabase"

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

# Reuse FM_DATABASE_URL if the caller already exported it
if [ -z "$FM_DATABASE_URL" ]; then
    echo "Recupero le credenziali da $DB_HOST..."
    DB_PASSWORD="$(ssh -o BatchMode=yes -o ConnectTimeout=8 "root@$DB_HOST" \
        "grep '^POSTGRES_PASSWORD=' $STACK_DIR/.env | cut -d= -f2-")" || {
        echo "ERRORE: $DB_HOST non raggiungibile via SSH." >&2
        echo "Controlla che Tailscale sia attivo, poi riprova." >&2
        exit 1
    }
    if [ -z "$DB_PASSWORD" ]; then
        echo "ERRORE: POSTGRES_PASSWORD non trovata in $STACK_DIR/.env su $DB_HOST." >&2
        exit 1
    fi
    FM_DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:5432/postgres"
    export FM_DATABASE_URL
fi

exec .venv/bin/fm
