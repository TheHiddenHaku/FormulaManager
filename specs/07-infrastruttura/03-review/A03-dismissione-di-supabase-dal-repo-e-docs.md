---
id: dismissione-di-supabase-dal-repo-e-docs
titolo: "Dismissione di Supabase dal repo e docs"
stato: review
priorita: media
dipendenze: [porting-di-persistenza-tui-e-script-a-sqlite]
etichette: [Infra]
creata: 2026-07-05
scadenza:
---

## Contesto
Dopo il porting a SQLite la cartella supabase/ (migrazioni, seed, config.toml, README) e' peso morto e la documentazione operativa (CLAUDE.md, README.md, CONTEXT.md) descrive ancora il flusso Postgres su matilde.

## Obiettivo
Il repo non contiene piu' riferimenti operativi a Supabase, matilde o FM_DATABASE_URL: un solo posto documenta il database SQLite.

## Criteri di accettazione
- [ ] cartella supabase/ rimossa
- [ ] nuova documentazione del database (docs/database.md o sezione nel README): percorso del file, FM_DB_PATH, bootstrap al primo avvio, reset
- [ ] CLAUDE.md aggiornato: via il divieto su supabase start, la regola delle migrazioni da applicare a matilde e i riferimenti a FM_DATABASE_URL; nuova regola sul database SQLite
- [ ] README.md e CONTEXT.md aggiornati dove citano Supabase o Postgres
- [ ] ADR 0001 marcato superseded con rimando al nuovo ADR
- [ ] grep pulito: nessuna occorrenza residua di psycopg, supabase o FM_DATABASE_URL in codice, script e test (gli ADR restano come storia)

## Dipendenze
- porting-di-persistenza-tui-e-script-a-sqlite

## Note
Lo stack Supabase su matilde resta acceso: la sua dismissione e' fuori scope (deciso il 2026-07-05).
