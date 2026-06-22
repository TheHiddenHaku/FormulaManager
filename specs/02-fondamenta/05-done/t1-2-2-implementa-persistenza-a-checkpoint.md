---
id: t1-2-2-implementa-persistenza-a-checkpoint
titolo: "T1.2.2 Implementa Persistenza a Checkpoint"
stato: done
priorita: media
dipendenze: [t1-1-2-crea-schema-db-multi-carriera-e-seed-dati, t1-2-1-implementa-modulo-mondo-generazione-griglia]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-5
---

## Contesto
Importata da Linear FOR-5: progetto "Fondamenta", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T1.2.2 [ ] Implementa Persistenza a Checkpoint

**Dipendenze**: T1.1.2, T1.2.1.
**Wave**: 2.

**Scope**: costruire il layer di persistenza psycopg che salva e ricarica una Carriera intera (Mondo + stato) in una transazione atomica al Checkpoint, elenca le Carriere esistenti e le elimina a cascata. Le scritture avvengono solo ai Checkpoint, come da ADR 0001: durante il gioco lo stato vive in memoria. L'ambiente di gioco è il **Supabase self-hosted già attivo nel Docker della VPS matilde** (via Tailscale); nessuno stack Supabase locale.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Lo scenario è coperto da T1.3.1.

**Deliverable verificabile**:

* `save_carriera(conn, carriera)` scrive l'intera Carriera (Mondo + stato) in una sola transazione atomica; `load_carriera(conn, career_id)` la ricostruisce per intero.
* `elenca_carriere(conn)` ritorna le Carriere con metadati (nome, data ultimo Checkpoint); `elimina_carriera(conn, career_id)` cancella a cascata sfruttando le FK dello schema di T1.1.2.
* Connessione configurabile via variabile d'ambiente canonica `FM_DATABASE_URL`: in gioco punta al Postgres del Supabase self-hosted su matilde via Tailscale (default documentato); un Postgres effimero/locale è ammesso SOLO per test e sviluppo. Nessuna modifica al codice tra i due casi.
* Round-trip test su Postgres effimero Docker (mai contro matilde): il Mondo generato da T1.2.1, salvato e ricaricato, è strutturalmente identico (stato salvato == stato ricaricato).
* Nessuna query fuori dai Checkpoint per design: l'API pubblica del modulo espone solo operazioni a granularità di Carriera intera.

**File da toccare**:

* `src/fm_persistenza/__init__.py` (NEW DIR)
* `src/fm_persistenza/connessione.py` (NEW: configurazione da env)
* `src/fm_persistenza/checkpoint.py` (NEW: save/load/elenca/elimina)
* `src/fm_persistenza/mappatura.py` (NEW: Mondo e stato ↔ righe SQL)
* `tests/persistenza/conftest.py` (NEW DIR: Postgres effimero Docker)
* `tests/persistenza/test_round_trip.py` (NEW)
* `pyproject.toml` (dipendenza psycopg)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile (previsto [N/A]: task backend, nessuna UI)
- [ ] Popolata (previsto [N/A]: nessuna vista; la completezza dei dati è provata dal round-trip test)
- [ ] Cliccabile (previsto [N/A]: nessuna interazione UI)
- [ ] URL canonica: la connessione usa una sola variabile d'ambiente canonica `FM_DATABASE_URL` documentata nel README
- [ ] Stati UI (previsto [N/A]: nessuna UI)
- [ ] Aggiornata: `load_carriera` ritorna sempre l'ultimo Checkpoint salvato
- [ ] Compatibile wireframe (previsto [N/A]: nessuna UI)

**Cosa NON fare**:

* Niente scritture per-Tick né salvataggi incrementali: solo Checkpoint.
* Niente PostgREST né supabase-py: SQL diretto con psycopg, come da ADR 0001.
* **Niente stack Supabase locale**: non eseguire `supabase start`; il DB di gioco è quello già attivo su matilde. Il Postgres effimero dei test è un container Postgres nudo, non uno stack Supabase.
* Niente UI (è T1.3.1).
* Niente nuove migrazioni: lo schema è di T1.1.2 (eventuali lacune si segnalano lì, non si patchano qui).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (story 44, 46).
* `CONTEXT.md` (Checkpoint, Carriera).
* `docs/adr/0001` (persistenza: Supabase self-hosted su matilde via Tailscale), `docs/adr/0002` (il motore puro non importa questo layer).
* T1.1.2 (schema DB), T1.2.1 (modulo Mondo).

## Note
Origine: Linear FOR-5 (https://linear.app/haku-inc/issue/FOR-5/t122-implementa-persistenza-a-checkpoint). Etichette Linear: si, ready-for-agent.
