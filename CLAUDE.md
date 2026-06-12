# CLAUDE.md

Regole operative per lavorare su Formula Manager. I contenuti canonici stanno altrove e NON vanno duplicati qui: [CONTEXT.md](CONTEXT.md) (glossario di dominio e mappa dei nomi), [docs/adr/](docs/adr/) (decisioni architetturali), [supabase/README.md](supabase/README.md) (procedure DB).

## Lingua

- Codice SEMPRE in inglese: identificatori, nomi di file e moduli, commenti inline, schema SQL (tabelle, colonne, vincoli).
- In italiano restano: documentazione, docstring discorsive, stringhe UI mostrate al giocatore, messaggi di commit, COMMENT SQL.
- La traduzione dominio -> identificatore segue la sezione "Mappa dei nomi nel codice" di [CONTEXT.md](CONTEXT.md): vincolante, lessico britannico (tyre, non tire).

## Commit e PR

- MAI riferimenti ad AI: niente Co-Authored-By di modelli o agenti, niente "Generated with ...", niente nomi di assistenti nei messaggi di commit o nelle descrizioni PR.
- Conventional Commits in italiano (feat, fix, refactor, test, docs, chore).
- Lavoro derivato da una issue Linear: mantenere "Riferimento: FOR-NNN" nel body del commit.
- Niente emoji, em-dash o virgolette curve nei messaggi.

## Architettura

- Motore puro: `fm_engine` non importa mai `textual` ne' `psycopg` ([ADR 0002](docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md)). Il vincolo e' protetto da `tests/engine/test_pure_imports.py`: deve restare verde.
- La TUI e' un guscio sopra il motore; la persistenza scrive solo ai Checkpoint, a granularita' di Carriera intera ([ADR 0001](docs/adr/0001-supabase-self-hosted-su-vps-con-salvataggi-a-checkpoint.md)).

## Database

- VIETATO `supabase start` e qualunque stack Supabase locale: il DB di gioco e' il Supabase self-hosted su matilde, raggiunto via Tailscale. Un Postgres effimero in Docker e' ammesso SOLO nei test automatici.
- `FM_DATABASE_URL` e' l'unica variabile di connessione. Credenziali, Studio e tunnel SSH per la CLI: [supabase/README.md](supabase/README.md).
- MAI eseguire test o esperimenti contro il DB di matilde.

## Comandi canonici

- Test: `.venv/bin/python -m pytest` (Docker necessario per i test di persistenza e TUI).
- Lint: `.venv/bin/python -m ruff check .` e `.venv/bin/python -m ruff format --check .`
- Avvio gioco: `scripts/play.sh` (prepara venv e credenziali da solo).
- Reset DB: `scripts/reset_db.sh` (DISTRUTTIVO: cancella tutte le Carriere; `--full` ricrea il DB da zero).

## Disciplina

- Niente refactor fuori scope, niente formattazione di file non toccati.
- Errori preesistenti non correlati al task: segnalarli, non fixarli in massa.
- Prima di ogni commit: pytest e ruff verdi.
