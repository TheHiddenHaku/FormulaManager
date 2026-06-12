# Supabase: schema e migrazioni

La persistenza di Formula Manager vive nel Supabase self-hosted nel Docker della VPS personale "matilde", raggiunta via Tailscale (vedi `docs/adr/0001-supabase-self-hosted-su-vps-con-salvataggi-a-checkpoint.md`). Lo stack (docker compose ufficiale, Postgres 17, installato il 2026-06-12) vive in `/opt/formulamanager-supabase` sulla VPS e si gestisce con `sh run.sh start|stop|status|logs|secrets`; le porte sono pubblicate solo sull'IP Tailscale della VPS.

La CLI Supabase si usa SOLO come strumento di migrazione puntato al DB remoto con `--db-url`. Non esiste e non deve esistere uno stack locale: `supabase start` e' vietato.

## Contenuto

- `migrations/`: lo schema versionato. `20260612004743_initial_schema.sql` e' la baseline unica con identificatori inglesi (FOR-35): sostituisce le due migrazioni italiane del 2026-06-11 (`schema_radice`, `nazionalita_e_colori`), che sono state eliminate; il database di gioco e' stato ricreato da zero con questa baseline. Crea lo schema radice multi-Carriera: dati statici globali (`circuits`, `points_tables`, `race_prizes`) e tabelle di stato di Carriera (`careers`, `engine_suppliers`, `teams`, `drivers`, `contracts`, `seasons`, `grands_prix`, `sessions`, `results`, `financial_transactions`, `development_projects`), tutte con FK `career_id` ON DELETE CASCADE. Vincoli e semantica sono identici allo schema precedente; la baseline incorpora anche `drivers.nationality` e `teams.primary_color`/`secondary_color`.
- `seed.sql`: i dati statici globali. I 24 circuiti del Calendario 2026 (annuncio originale 2025, inclusi Bahrain e Jeddah) con pesi sui 6 Attributi vettura, severita' gomme, probabilita' Safety car, profilo meteo, mescole nominate e date reali; le tabelle punti 2026 (gara e sprint); i Premi gara. I valori numerici di gioco (pesi, probabilita', importi) sono parametri di partenza da tarare.
- `config.toml`: configurazione della CLI. La sezione `[db.seed]` aggancia `seed.sql` ai comandi di reset.

## Come ottenere FM_DATABASE_URL

`FM_DATABASE_URL` e' l'UNICA variabile d'ambiente letta dal layer di persistenza (`src/fm_persistence`). In gioco punta al Postgres di matilde via Tailscale (il default documentato qui sotto); per test e sviluppo e' ammesso un Postgres effimero o locale (i test di `tests/persistence/` ne avviano uno in Docker, mai contro matilde). Il codice non cambia tra i due casi: cambia solo il valore della variabile.

La connessione e' Postgres sull'indirizzo Tailscale di matilde. Le credenziali stanno nel file `.env` dello stack sulla VPS:

```sh
ssh root@matilde
cd /opt/formulamanager-supabase
sh run.sh secrets        # stampa POSTGRES_PASSWORD e le altre chiavi
```

Lo stack espone Postgres attraverso il pooler Supavisor (porta 5432 in session mode, tenant `formulamanager`). L'URL ha questa forma:

```sh
export FM_DATABASE_URL="postgresql://postgres.formulamanager:<POSTGRES_PASSWORD>@matilde:5432/postgres"
```

Se la password contiene caratteri speciali va percent-encoded. psycopg (il gioco) si connette in chiaro senza problemi: lo stack non espone TLS e il transito e' comunque cifrato da Tailscale (WireGuard).

Nota: verificato il 2026-06-12, `SHOW server_version;` ritorna 17.6, coerente con `major_version = 17` in `config.toml`.

### Tunnel SSH per la CLI Supabase

La CLI Supabase forza TLS verso gli host remoti e lo stack non lo espone: i comandi `supabase db push` e `supabase migration list` falliscono con "server refused TLS connection" se puntati a matilde. Verso `localhost` la CLI non usa TLS, quindi i comandi CLI passano da un tunnel SSH locale:

```sh
ssh -f -N -o ExitOnForwardFailure=yes -L 54322:100.101.127.89:5432 root@matilde
supabase db push --db-url "postgresql://postgres.formulamanager:<POSTGRES_PASSWORD>@127.0.0.1:54322/postgres"
pkill -f "54322:100.101.127.89:5432"   # chiude il tunnel
```

## Studio

Lo Studio self-hosted e' l'interfaccia con cui si editano a mano i nomi di squadre, piloti e motoristi (colonne `name`, testo libero). Si raggiunge sull'ingresso Kong dello stack, solo dalla tailnet:

```
http://matilde:8000
```

Credenziali: `DASHBOARD_USERNAME` e `DASHBOARD_PASSWORD` (visibili con `sh run.sh secrets`). La porta HTTPS di Kong e' 8444, non 8443: quella sull'IP Tailscale e' occupata da tailscaled.

## Applicare migrazioni e seed

I comandi CLI richiedono il tunnel SSH descritto sopra: in questi esempi `FM_DATABASE_URL` punta a `127.0.0.1:54322` attraverso il tunnel. La prima applicazione del 2026-06-12 (2 migrazioni italiane piu' seed) e' stata sostituita: con FOR-35 il database e' stato ricreato da zero con la sola baseline inglese piu' il seed.

```sh
# stato delle migrazioni sul DB remoto
supabase migration list --db-url "$FM_DATABASE_URL"

# prova a vuoto: mostra cosa verrebbe applicato
supabase db push --db-url "$FM_DATABASE_URL" --dry-run

# prima applicazione da zero: migrazioni + seed dei dati statici
supabase db push --db-url "$FM_DATABASE_URL" --include-seed

# applicazioni successive (il seed e' idempotente, ma non serve ripeterlo)
supabase db push --db-url "$FM_DATABASE_URL"
```

## Reset del DB (distruttivo)

La via consigliata e' lo script, che chiede conferma e verifica l'esito:

```sh
scripts/reset_db.sh          # cancella tutte le Carriere; schema e seed intatti
scripts/reset_db.sh --full   # ricrea il DB da zero (drop tabelle, migrazioni + seed)
```

Entrambe le modalita' cancellano TUTTE le Carriere salvate, senza possibilita' di recupero. E' il DB di gioco, non un ambiente usa e getta. Il flag `--yes` salta la conferma (per automazioni).

Nota: NON usare `supabase db reset --db-url` contro lo stack self-hosted: ricrea l'intero database e puo' rompere gli schemi interni di Supabase (auth, storage). Lo script `--full` cancella solo le tabelle di gioco. Per applicare nuove migrazioni si usa sempre `db push`.

## Query di verifica

Da eseguire copia-incolla contro il DB remoto, per esempio con `psql "$FM_DATABASE_URL"` o dall'SQL editor dello Studio.

### 1. Conteggio circuiti (atteso: 24)

```sql
select count(*) as circuiti from circuits;
```

### 2. Seed punti e premi (atteso: race_2026 10 posizioni 101 punti, sprint_2026 8 posizioni 36 punti, premi 22 posizioni)

```sql
select code, count(*) as posizioni, sum(points) as punti_totali
from points_tables group by code order by code;

select code, count(*) as posizioni, sum(amount_usd) as totale_usd
from race_prizes group by code;
```

### 3. Integrita' FK: ogni tabella di stato cascata dalla Carriera (atteso: 10 righe, tutte CASCADE)

```sql
select tc.table_name as tabella, rc.delete_rule
from information_schema.referential_constraints rc
join information_schema.table_constraints tc
  on tc.constraint_name = rc.constraint_name
 and tc.constraint_schema = rc.constraint_schema
join information_schema.constraint_column_usage ccu
  on ccu.constraint_name = rc.constraint_name
 and ccu.constraint_schema = rc.constraint_schema
where ccu.table_name = 'careers'
  and tc.constraint_type = 'FOREIGN KEY'
order by tc.table_name;
```

### 4. Tabelle con colonna career_id (atteso: le stesse 10 tabelle)

```sql
select table_name
from information_schema.columns
where table_schema = 'public' and column_name = 'career_id'
order by table_name;
```

### 5. Cascade alla cancellazione di una Carriera (atteso: 10 righe, tutte con residui = 0)

Lo script crea una Carriera di prova con una riga in ogni tabella di stato, la cancella e conta i residui. Gira in transazione con ROLLBACK finale: non lascia tracce nel DB di gioco.

```sql
begin;

insert into careers (id, name) values
    ('11111111-1111-1111-1111-111111111111', 'TEST cascata');

insert into engine_suppliers (id, career_id, name) values
    ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'Motorista test');

insert into teams (id, career_id, name, is_player, engine_supplier_id) values
    ('33333333-3333-3333-3333-333333333333', '11111111-1111-1111-1111-111111111111', 'Squadra test', true, '22222222-2222-2222-2222-222222222222');

insert into drivers (id, career_id, name, age) values
    ('44444444-4444-4444-4444-444444444444', '11111111-1111-1111-1111-111111111111', 'Pilota test', 25);

insert into contracts (career_id, team_id, driver_id, start_season, duration_seasons, salary_usd) values
    ('11111111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333', '44444444-4444-4444-4444-444444444444', 2026, 2, 5000000);

insert into seasons (id, career_id, year) values
    ('55555555-5555-5555-5555-555555555555', '11111111-1111-1111-1111-111111111111', 2026);

insert into grands_prix (id, career_id, season_id, circuit_id, round, race_date) values
    ('66666666-6666-6666-6666-666666666666', '11111111-1111-1111-1111-111111111111', '55555555-5555-5555-5555-555555555555',
     (select id from circuits where code = 'albert_park'), 1, '2026-03-08');

insert into sessions (id, career_id, grand_prix_id, kind) values
    ('77777777-7777-7777-7777-777777777777', '11111111-1111-1111-1111-111111111111', '66666666-6666-6666-6666-666666666666', 'race');

insert into results (career_id, session_id, driver_id, team_id, position, laps_completed, points) values
    ('11111111-1111-1111-1111-111111111111', '77777777-7777-7777-7777-777777777777',
     '44444444-4444-4444-4444-444444444444', '33333333-3333-3333-3333-333333333333', 1, 58, 25);

insert into financial_transactions (career_id, team_id, season_id, grand_prix_id, kind, amount_usd, counts_against_cap, game_date) values
    ('11111111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333',
     '55555555-5555-5555-5555-555555555555', '66666666-6666-6666-6666-666666666666', 'race_prize', 3000000, false, '2026-03-08');

insert into development_projects (career_id, team_id, season_id, attribute, cost_usd, start_date, duration_days) values
    ('11111111-1111-1111-1111-111111111111', '33333333-3333-3333-3333-333333333333',
     '55555555-5555-5555-5555-555555555555', 'mechanical_grip', 4000000, '2026-03-10', 30);

delete from careers where id = '11111111-1111-1111-1111-111111111111';

select 'engine_suppliers' as tabella, count(*) as residui from engine_suppliers where career_id = '11111111-1111-1111-1111-111111111111'
union all select 'teams', count(*) from teams where career_id = '11111111-1111-1111-1111-111111111111'
union all select 'drivers', count(*) from drivers where career_id = '11111111-1111-1111-1111-111111111111'
union all select 'contracts', count(*) from contracts where career_id = '11111111-1111-1111-1111-111111111111'
union all select 'seasons', count(*) from seasons where career_id = '11111111-1111-1111-1111-111111111111'
union all select 'grands_prix', count(*) from grands_prix where career_id = '11111111-1111-1111-1111-111111111111'
union all select 'sessions', count(*) from sessions where career_id = '11111111-1111-1111-1111-111111111111'
union all select 'results', count(*) from results where career_id = '11111111-1111-1111-1111-111111111111'
union all select 'financial_transactions', count(*) from financial_transactions where career_id = '11111111-1111-1111-1111-111111111111'
union all select 'development_projects', count(*) from development_projects where career_id = '11111111-1111-1111-1111-111111111111';

rollback;
```

## Scelte di modellazione

- Isolamento tra Carriere: ogni tabella di stato ha `unique (career_id, id)` e le FK interne alla Carriera sono composite su `(career_id, ...)`. Una riga non puo' referenziare dati di un'altra Carriera.
- Nomi editabili: `name` di squadre, piloti, motoristi e carriere e' testo libero, pensato per l'editing via Studio.
- Tipi chiusi come CHECK su text (non enum): aggiungere un valore non richiede `ALTER TYPE`.
- Formato weekend: il flag `sprint` esiste gia' su `grands_prix.weekend_format` e su `circuits.weekend_format_2026`; il MVP gioca tutto in `standard`.
- Motore in proprio o Cliente: `teams.engine_supplier_id` NULL significa motore in proprio; valorizzato significa Cliente del Motorista.
- Economia a registro: `financial_transactions` e' append-only per disegno; Cassa e Cap residuo si ricostruiscono per somma. Il flag `counts_against_cap` separa i movimenti che consumano Cap.
- Niente RLS e niente policy: gioco single-player su rete Tailscale privata.
