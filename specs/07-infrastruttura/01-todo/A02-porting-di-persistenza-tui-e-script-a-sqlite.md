---
id: porting-di-persistenza-tui-e-script-a-sqlite
titolo: "Porting di persistenza, TUI e script a SQLite"
stato: todo
priorita: media
dipendenze: [schema-e-seed-sqlite-di-baseline]
etichette: [Infra]
creata: 2026-07-05
scadenza:
---

## Contesto
psycopg e' confinato in fm_persistence (connection.py, checkpoint.py, history.py; mapping.py e gli altri moduli costruiscono solo tuple di parametri) e in 5 punti della TUI che catturano psycopg.Error o psycopg.OperationalError. I test col database avviano un Postgres effimero in Docker (tests/conftest.py); play.sh recupera le credenziali via SSH da matilde.

## Obiettivo
Il gioco e l'intera suite di test girano su sqlite3 della stdlib: nessuna dipendenza esterna, niente Docker, niente rete. L'API di fm_persistence (save, load, list, delete a granularita' di Carriera intera) resta invariata per la TUI.

## Criteri di accettazione
- [ ] connection.py apre sqlite3 sul percorso FM_DB_PATH (default ~/.local/share/formulamanager/formulamanager.db); al primo avvio crea le cartelle e applica schema.sql e seed.sql; PRAGMA foreign_keys = ON su ogni connessione; FM_DATABASE_URL non e' piu' letta da nessun punto del codice
- [ ] checkpoint.py e history.py tradotti al dialetto sqlite3: segnaposto ?, uuid come str, datetime come ISO 8601, stati jsonb via json.dumps e json.loads; save_career resta una transazione atomica (delete e reinsert come oggi)
- [ ] la TUI cattura sqlite3.Error al posto di psycopg.Error nei 5 punti esistenti, senza altri cambi di comportamento
- [ ] fixture ephemeral_database_url sostituita da un file SQLite temporaneo con schema e seed applicati: Docker non serve piu' ai test
- [ ] tests/engine/test_pure_imports.py vieta sqlite3 in fm_engine al posto di psycopg
- [ ] play.sh non tocca piu' SSH ne' credenziali; reset_db.sh cancella il file del database (resta la conferma, e' distruttivo); play_market aggiornato
- [ ] psycopg rimosso da pyproject.toml; pytest e ruff verdi

## Dipendenze
- schema-e-seed-sqlite-di-baseline

## Note
Le Carriere salvate su matilde non si migrano: si riparte da zero (deciso il 2026-07-05). Attenzione ai numeric: con psycopg arrivano come Decimal, con sqlite3 come float o int; i test di round trip devono coprire la differenza senza cambiare i modelli del motore.
