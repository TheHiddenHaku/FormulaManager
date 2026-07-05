# CLAUDE.md

Regole operative per lavorare su Formula Manager. I contenuti canonici stanno altrove e NON vanno duplicati qui: [CONTEXT.md](CONTEXT.md) (glossario di dominio e mappa dei nomi), [docs/adr/](docs/adr/) (decisioni architetturali), [docs/database.md](docs/database.md) (database SQLite: percorso, bootstrap, reset).

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

- Motore puro: `fm_engine` non importa mai `textual` ne' `sqlite3` ([ADR 0002](docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md)). Il vincolo e' protetto da `tests/engine/test_pure_imports.py`: deve restare verde.
- La TUI e' un guscio sopra il motore; la persistenza scrive solo ai Checkpoint, a granularita' di Carriera intera ([ADR 0001](docs/adr/0001-supabase-self-hosted-su-vps-con-salvataggi-a-checkpoint.md)), oggi su un database SQLite locale ([ADR 0004](docs/adr/0004-sqlite-locale-come-database-di-gioco.md)).

## Database

- Il DB di gioco e' un file SQLite locale ([ADR 0004](docs/adr/0004-sqlite-locale-come-database-di-gioco.md)): nessun servizio remoto, niente Docker, niente rete. Al primo avvio il gioco crea il file e applica `schema.sql` e `seed.sql` (package data di `fm_persistence`).
- `FM_DB_PATH` e' l'unica variabile: il percorso del file (default sotto la home). Dettagli, bootstrap e reset: [docs/database.md](docs/database.md).
- Lo schema baseline vive in `src/fm_persistence/schema.sql` (dialetto SQLite, `pragma user_version` come aggancio per eventuali migrazioni future); i dati statici in `src/fm_persistence/seed.sql`. Niente migrazioni incrementali ne' stack esterni da tenere allineati.

## Comandi canonici

- Test: `.venv/bin/python -m pytest` (niente Docker: i test di persistenza e TUI girano su un SQLite temporaneo).
- Lint: `.venv/bin/python -m ruff check .` e `.venv/bin/python -m ruff format --check .`
- Avvio gioco: `scripts/play.sh` (prepara il venv; il database SQLite si crea da solo al primo avvio).
- Reset DB: `scripts/reset_db.sh` (DISTRUTTIVO: cancella il file del database e tutte le Carriere; ricreato vuoto al prossimo avvio).

## Disciplina

- Niente refactor fuori scope, niente formattazione di file non toccati.
- Errori preesistenti non correlati al task: segnalarli, non fixarli in massa.
- Prima di ogni commit: pytest e ruff verdi.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
