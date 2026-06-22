---
id: t1-1-2-crea-schema-db-multi-carriera-e-seed-dati
titolo: "T1.1.2 Crea schema DB multi-Carriera e seed dati statici"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-3
---

## Contesto
Importata da Linear FOR-3: progetto "Fondamenta", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T1.1.2 [ ] Crea schema DB multi-Carriera e seed dati statici

**Dipendenze**: nessuna.
**Wave**: 1.

**Scope**: definire con migrazioni Supabase l'intero schema radice multi-Carriera del gioco e il seed dei dati statici (24 circuiti 2026, tabelle punti e Premi gara). Il database di destinazione è il **Supabase self-hosted già attivo nel Docker della VPS matilde**, raggiunto via Tailscale (ADR 0001): la CLI Supabase si usa solo come strumento di migrazione puntato al DB remoto, **non** va creato alcuno stack locale. Abilita la Persistenza a Checkpoint (T1.2.2) e la gestione di più Carriere parallele e indipendenti con nomi editabili.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Lo scenario è coperto da T1.3.1. È però prevista una verifica manuale: applicazione delle migrazioni al DB remoto su matilde più editing di un nome squadra via lo Studio self-hosted di matilde (vedi Test manuali).

**Deliverable verificabile**:

* Migrazioni in `supabase/migrations/` applicabili da zero al DB remoto con la CLI puntata a matilde (`supabase db reset --db-url "$FM_DATABASE_URL"`, dove `FM_DATABASE_URL` è il Postgres del Supabase self-hosted su matilde via Tailscale — comando consapevolmente distruttivo sul DB di gioco): tabelle per carriere, squadre, piloti, motoristi, contratti, circuiti, stagioni, gran premi (con flag formato weekend Standard/Sprint), sessioni e risultati, registro transazioni economiche, progetti di sviluppo.
* Ogni tabella di stato di Carriera ha FK `career_id` con `ON DELETE CASCADE`; i nomi (squadre, piloti, motoristi) sono colonne testo editabili, non enum.
* `supabase/seed.sql` inserisce i 24 circuiti del Calendario 2026 con pesi sui 6 Attributi vettura, severità gomme, probabilità Safety car, profilo meteo e date reali, più le tabelle punti e Premi gara.
* Query di verifica documentate ed eseguibili copia-incolla contro il DB remoto: conteggio 24 circuiti, integrità FK, cascade alla cancellazione di una carriera.
* `supabase/README.md` documenta il target remoto: come ottenere `FM_DATABASE_URL` (host Tailscale di matilde), dove raggiungere lo Studio self-hosted, e l'avvertenza che `db reset` è distruttivo.

**File da toccare**:

* `supabase/config.toml` (NEW DIR — da `supabase init`, che crea solo la struttura di cartelle: nessuno stack avviato)
* `supabase/migrations/<timestamp>_schema_radice.sql` (NEW)
* `supabase/seed.sql` (NEW)
* `supabase/README.md` (NEW, target remoto + query di verifica)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile (previsto [N/A]: task DB senza UI; si verifica applicando le migrazioni al DB remoto)
- [ ] Popolata: il seed carica i 24 circuiti e le tabelle punti/Premi gara
- [ ] Cliccabile (previsto [N/A]: nessuna interazione UI)
- [ ] URL canonica (previsto [N/A]: nessuna route; migrazioni con naming timestamp ordinato; connessione via unica env `FM_DATABASE_URL`)
- [ ] Stati UI (previsto [N/A]: nessuna UI)
- [ ] Aggiornata: schema e seed allineati al glossario CONTEXT.md e al Calendario 2026 del PRD
- [ ] Compatibile wireframe (previsto [N/A]: nessuna UI)

**Cosa NON fare**:

* **Niente stack Supabase locale**: NON eseguire `supabase start` né avviare container Supabase sulla macchina di sviluppo. Il DB di gioco è il Supabase self-hosted già attivo nel Docker di matilde (ADR 0001). Un Postgres effimero è ammesso SOLO nei test automatici di T1.2.2, e non è uno stack Supabase.
* Niente RLS né policy (single-player su Supabase self-hosted, raggiungibile solo via Tailscale).
* Niente codice Python di gioco.
* Niente dati di Carriera nel seed: solo dati statici (circuiti, punti, premi).
* Niente PostgREST o layer API.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (story 2, 6, 38, 46).
* `CONTEXT.md` (Carriera, Calendario, Formato weekend, Attributo vettura, Safety car, Premio gara).
* `docs/adr/0001` (persistenza: Supabase self-hosted su matilde via Tailscale, nessuno stack locale).

**Test manuali**:

* esporta `FM_DATABASE_URL` puntata al Postgres di matilde (via Tailscale)
* `supabase db reset --db-url "$FM_DATABASE_URL"` → migrazioni e seed applicati senza errori sul DB remoto
* esegui le query di verifica documentate → 24 circuiti, FK integre
* apri lo Studio self-hosted su matilde, inserisci una carriera e una squadra di prova, edita il nome della squadra → il nuovo nome persiste
* elimina la carriera di prova → cascade sulle squadre; chiudi con un nuovo `supabase db reset --db-url "$FM_DATABASE_URL"`

## Note
Origine: Linear FOR-3 (https://linear.app/haku-inc/issue/FOR-3/t112-crea-schema-db-multi-carriera-e-seed-dati-statici). Etichette Linear: si, ready-for-agent.
