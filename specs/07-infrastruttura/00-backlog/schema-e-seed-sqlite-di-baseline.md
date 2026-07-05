---
id: schema-e-seed-sqlite-di-baseline
titolo: "Schema e seed SQLite di baseline"
stato: backlog
priorita: media
dipendenze: []
etichette: [Infra]
creata: 2026-07-05
scadenza:
---

## Contesto
Lo schema di gioco vive in 11 migrazioni Postgres in supabase/migrations/ piu' supabase/seed.sql (dati statici: circuiti, sistemi di punti e premi). La issue sqlite prevede il passaggio a un database SQLite locale: serve prima di tutto lo schema equivalente in dialetto SQLite. Con il cambio di database la storia delle migrazioni Postgres perde valore: si collassa tutto in una baseline unica.

## Obiettivo
Una coppia di file schema.sql e seed.sql in dialetto SQLite, package data di fm_persistence (a runtime servono per creare il database al primo avvio), piu' l'ADR che registra la decisione.

## Criteri di accettazione
- [ ] src/fm_persistence/schema.sql contiene l'intero schema corrente (baseline delle 11 migrazioni) tradotto: uuid -> text, timestamptz e date -> text ISO 8601, numeric -> real, jsonb -> text; vincoli check, unique e foreign key con on delete cascade conservati
- [ ] nessun default gen_random_uuid() o now(): id e timestamp li scrive l'applicazione
- [ ] pragma user_version = 1 nello schema, aggancio per eventuali migrazioni future
- [ ] src/fm_persistence/seed.sql traduce il seed corrente con gli stessi dati statici
- [ ] un test applica schema e seed su un SQLite in memoria e verifica tabelle e conteggi delle righe di seed
- [ ] nuovo ADR "SQLite locale come database di gioco" che supersede la parte database di ADR 0001

## Dipendenze
Nessuna.

## Note
PRAGMA foreign_keys = ON e' un'impostazione per connessione e va nel codice (issue di porting), non nello schema. La cartella supabase/ resta intatta qui: la rimozione avviene nell'issue di dismissione.
