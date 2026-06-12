#!/bin/sh
#
# Ripulisce il DB di gioco sul Supabase self-hosted di matilde.
#
# Due modalita':
#   scripts/reset_db.sh          cancella tutte le Carriere (cascata sulle tabelle
#                                di stato); schema e dati statici del seed restano
#   scripts/reset_db.sh --full   ricrea il DB da zero: drop di tutte le tabelle di
#                                gioco, migrazioni e seed riapplicati con la CLI
#
# Flag:
#   --yes, -y   salta la conferma interattiva (ATTENZIONE: comando distruttivo)
#
# Prerequisiti: Tailscale attivo (matilde via SSH); per --full anche la CLI supabase.

set -e

DB_HOST="matilde"
DB_USER="postgres.formulamanager"
STACK_DIR="/opt/formulamanager-supabase"
DB_CONTAINER="supabase-db"
TUNNEL_PORT=54322
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

MODE="careers"
ASSUME_YES=0
for arg in "$@"; do
    case "$arg" in
        --full) MODE="full" ;;
        --yes|-y) ASSUME_YES=1 ;;
        *) echo "Argomento sconosciuto: $arg (ammessi: --full, --yes)" >&2; exit 1 ;;
    esac
done

# Run SQL from stdin inside the db container on matilde
run_sql() {
    ssh -o BatchMode=yes -o ConnectTimeout=8 "root@$DB_HOST" \
        "docker exec -i $DB_CONTAINER psql -U postgres -d postgres -v ON_ERROR_STOP=1 -tA"
}

if [ "$ASSUME_YES" -ne 1 ]; then
    if [ "$MODE" = "full" ]; then
        echo "Sto per RICREARE DA ZERO il DB di gioco su $DB_HOST:"
        echo "tutte le tabelle vengono cancellate, poi migrazioni e seed riapplicati."
    else
        echo "Sto per CANCELLARE TUTTE le Carriere salvate su $DB_HOST."
        echo "Schema e dati statici (circuiti, punti, premi) restano intatti."
    fi
    printf "Scrivi '%s' per confermare: " "$DB_HOST"
    read -r answer
    if [ "$answer" != "$DB_HOST" ]; then
        echo "Annullato."
        exit 1
    fi
fi

if [ "$MODE" = "careers" ]; then
    before="$(echo 'select count(*) from careers;' | run_sql)"
    echo "Carriere presenti: $before"
    echo 'delete from careers;' | run_sql >/dev/null
    after="$(echo 'select count(*) from careers;' | run_sql)"
    circuits="$(echo 'select count(*) from circuits;' | run_sql)"
    echo "Carriere dopo la pulizia: $after (circuiti intatti: $circuits)"
    echo "Fatto."
    exit 0
fi

# Full mode: drop every game table plus the CLI migration bookkeeping
echo "Cancello tutte le tabelle dello schema public..."
run_sql <<'SQL' >/dev/null
do $$
declare r record;
begin
    for r in (select tablename from pg_tables where schemaname = 'public') loop
        execute format('drop table if exists public.%I cascade', r.tablename);
    end loop;
end $$;
drop schema if exists supabase_migrations cascade;
SQL

echo "Recupero credenziali e apro il tunnel verso $DB_HOST..."
DB_PASSWORD="$(ssh -o BatchMode=yes "root@$DB_HOST" \
    "grep '^POSTGRES_PASSWORD=' $STACK_DIR/.env | cut -d= -f2-")"
TAILSCALE_IP="$(ssh -o BatchMode=yes "root@$DB_HOST" 'tailscale ip -4')"

# The Supabase CLI refuses non-TLS remote hosts: tunnel through localhost
cleanup_tunnel() { pkill -f "$TUNNEL_PORT:$TAILSCALE_IP:5432" 2>/dev/null || true; }
trap cleanup_tunnel EXIT
ssh -f -N -o BatchMode=yes -o ExitOnForwardFailure=yes \
    -L "$TUNNEL_PORT:$TAILSCALE_IP:5432" "root@$DB_HOST"

echo "Applico migrazioni e seed..."
cd "$REPO_DIR"
supabase db push \
    --db-url "postgresql://$DB_USER:$DB_PASSWORD@127.0.0.1:$TUNNEL_PORT/postgres" \
    --include-seed --yes

circuits="$(echo 'select count(*) from circuits;' | run_sql)"
careers="$(echo 'select count(*) from careers;' | run_sql)"
if [ "$circuits" = "24" ] && [ "$careers" = "0" ]; then
    echo "Verifica OK: 24 circuiti, 0 Carriere. DB ricreato da zero."
else
    echo "ATTENZIONE: verifica inattesa (circuiti: $circuits, carriere: $careers)" >&2
    exit 1
fi
