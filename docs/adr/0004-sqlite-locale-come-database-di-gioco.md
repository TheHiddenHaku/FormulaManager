# SQLite locale come database di gioco

La persistenza passa da un Supabase self-hosted (Postgres su Docker sulla VPS "matilde", raggiunta via Tailscale) a un database SQLite locale, un singolo file sulla macchina che gioca. Il gioco non dipende piu' da un servizio remoto ne' dalla rete per partire e salvare: si apre il file con `sqlite3` della standard library, al primo avvio si crea il database applicando `schema.sql` e `seed.sql` (package data di `fm_persistence`), e i Checkpoint scrivono in transazioni atomiche come prima. Questa decisione supersede la parte "trasporto e collocazione del database" di [ADR 0001](0001-supabase-self-hosted-su-vps-con-salvataggi-a-checkpoint.md): resta invariato tutto il resto di quell'ADR, ovvero i salvataggi a Checkpoint a granularita' di Carriera intera, lo stato in memoria durante la sessione e nessuna query nel loop di simulazione.

Con il cambio di database la storia delle 11 migrazioni Postgres perde valore: si collassa tutto in una baseline unica (`src/fm_persistence/schema.sql`) tradotta al dialetto SQLite. La traduzione dei tipi e' meccanica: uuid diventa text (gli id li genera l'applicazione, niente `gen_random_uuid()`), timestamptz e date diventano text ISO 8601 (niente `now()`), numeric e double precision diventano real, boolean diventa integer 0/1 con check, jsonb diventa text con i documenti JSON serializzati dall'applicazione. Vincoli check, unique e foreign key con `on delete cascade` sono conservati; `pragma foreign_keys = on` e' un'impostazione per connessione e vive nel codice, non nello schema. Lo schema porta `pragma user_version = 1` come aggancio per eventuali migrazioni future.

## Considered Options

- **Restare su Supabase self-hosted su matilde**: nessun costo di migrazione, ma il gioco resta legato a una VPS accesa e a Tailscale per girare e salvare, con la CLI Supabase e un tunnel SSH nel flusso operativo. Complessita' sproporzionata per un gioco single player locale.
- **Postgres locale (Docker sulla macchina di sviluppo)**: elimina la rete ma non la dipendenza da Docker e da un server che parte; `supabase start` era gia' vietato per scelta.
- **SQLite locale (scelto)**: zero dipendenze esterne, niente Docker, niente rete. `sqlite3` e' nella standard library; il database e' un file che si crea da solo al primo avvio. Un Postgres effimero in Docker non serve piu' neanche ai test.

## Consequences

- Il gioco parte e salva offline: nessuna connettivita' Tailscale, nessun Docker, nessun servizio remoto richiesto. Il limite "senza rete il gioco non parte" di ADR 0001 decade.
- La suite di test gira su un file SQLite temporaneo con schema e seed applicati: la fixture del Postgres effimero in Docker viene sostituita, i test non richiedono piu' Docker ne' rete.
- Le Carriere salvate sul Supabase di matilde non si migrano: si riparte da zero (deciso il 2026-07-05). Lo stack Supabase su matilde resta acceso, la sua dismissione e' fuori scope.
- Il percorso del file e' configurabile via `FM_DB_PATH` (default sotto la home dell'utente); `FM_DATABASE_URL` e psycopg escono dal progetto. Lo Studio self-hosted come editor manuale di ADR 0001 non e' piu' disponibile: l'editing a mano dei dati passa da un client SQLite qualsiasi sul file.
- Attenzione ai tipi al confine: con psycopg i numeric arrivavano come Decimal, con `sqlite3` i real arrivano come float. I round trip devono coprire la differenza senza cambiare i modelli del motore.

## Nota

Questo ADR registra la decisione (issue "Schema e seed SQLite di baseline"). Il porting del codice di persistenza, della TUI e degli script, la sostituzione della fixture di test e la rimozione di psycopg vivono nelle issue derivate; la marcatura di ADR 0001 come superseded e la dismissione della cartella `supabase/` avvengono nell'issue di dismissione.
