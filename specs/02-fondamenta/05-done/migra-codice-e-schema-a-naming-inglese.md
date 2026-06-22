---
id: migra-codice-e-schema-a-naming-inglese
titolo: "Migra codice e schema a naming inglese"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-35
---

## Contesto
Importata da Linear FOR-35: progetto "Fondamenta", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### Migra codice e schema a naming inglese

**Dipendenze**: nessuna (il codice di <issue id="41e561f3-4ecc-4e25-935a-239b17e5b63a" href="https://linear.app/haku-inc/issue/FOR-2/t111-imposta-scaffolding-repo-e-pacchetti">FOR-2</issue>..<issue id="d71eab6d-ba5c-4432-86ad-0de590e6ed14" href="https://linear.app/haku-inc/issue/FOR-6/t131-costruisci-tui-shell-e-gestione-carriere">FOR-6</issue> e' gia' mergiato su develop).
**Origine**: regola di progetto dettata da Alessio il 2026-06-12: il codice si scrive in inglese (identificatori, moduli, file, commenti inline, schema SQL); l'italiano resta per documentazione, UI di gioco, docstring discorsive e glossario di dominio. Il codice di Fondamenta e' nato in italiano e va migrato ora, prima di T1.3.2, finche' la base e' piccola e il DB e' senza Carriere.

**Scope**: rinomina integrale, a comportamento invariato, di pacchetti, moduli, identificatori e schema SQL verso l'inglese, con mappa canonica dei termini di dominio in CONTEXT.md. Le migrazioni italiane vengono sostituite da una baseline inglese unica e il DB su matilde viene ricreato (oggi e' vuoto: il reset non perde nulla).

**Deliverable verificabile**:

* CONTEXT.md ha una sezione "Mappa dei nomi nel codice" che fissa la traduzione canonica termine di dominio -> identificatore inglese, vincolante per tutto il codice futuro.
* Nessun identificatore italiano in src/ e tests/: pacchetto fm_persistenza -> fm_persistence; moduli (mondo -> world, modelli -> models, generazione -> generation, nazionalita -> nationalities, carriera -> career, connessione -> connection, mappatura -> mapping, schermate -> screens, widget -> widgets, elenco_carriere -> career_list, nuova_carriera -> new_career, griglia -> grid, stime -> estimates, bandiere -> flags); funzioni, classi, variabili e nomi dei test in inglese.
* Stringhe UI mostrate al giocatore, docstring discorsive e COMMENT SQL restano in italiano. FM_DATABASE_URL resta invariata.
* supabase/migrations/ contiene una sola baseline inglese (nuovo timestamp) che sostituisce le due migrazioni italiane; seed.sql con identificatori inglesi; supabase/README.md aggiornato (tabelle e query di verifica).
* DB su matilde ripulito e ricreato con lo schema inglese; query di verifica del README passate.
* pytest interamente verde e ruff pulito; il test di architettura sugli import puri continua a coprire fm_engine.

**Cosa NON fare**:

* Nessun cambiamento funzionale o di design: pura rinomina, i test rinominati coprono gli stessi casi.
* Niente traduzione di CONTEXT.md, ADR, README, messaggi di commit o testi UI.
* Niente migrazioni incrementali di rinomina (ALTER TABLE RENAME): baseline nuova, il DB non ha dati di Carriera.

**Riferimenti**:

* CONTEXT.md (glossario di dominio, resta in italiano).
* Commenti su <issue id="6f76a25e-9dfe-42dd-8878-70f68d481d5d" href="https://linear.app/haku-inc/issue/FOR-3/t112-crea-schema-db-multi-carriera-e-seed-dati-statici">FOR-3</issue> e <issue id="13aef04f-fb4a-4c6a-b364-b1513438015b" href="https://linear.app/haku-inc/issue/FOR-5/t122-implementa-persistenza-a-checkpoint">FOR-5</issue> (lacune schema note: nazionalita' e colori gia' risolte in <issue id="d71eab6d-ba5c-4432-86ad-0de590e6ed14" href="https://linear.app/haku-inc/issue/FOR-6/t131-costruisci-tui-shell-e-gestione-carriere">FOR-6</issue>; ingaggio richiesto, personalita' di spesa e seed/config restano fuori scope anche qui).
* docs/adr/0001 e 0002 (invariati nella sostanza).

## Note
Origine: Linear FOR-35 (https://linear.app/haku-inc/issue/FOR-35/migra-codice-e-schema-a-naming-inglese). Etichette Linear: si, ready-for-agent.
