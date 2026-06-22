---
id: t1-3-1-costruisci-tui-shell-e-gestione-carriere
titolo: "T1.3.1 Costruisci TUI shell e gestione Carriere"
stato: done
priorita: media
dipendenze: [t1-2-2-implementa-persistenza-a-checkpoint]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-6
---

## Contesto
Importata da Linear FOR-6: progetto "Fondamenta", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T1.3.1 [ ] Costruisci TUI shell e gestione Carriere

**Dipendenze**: T1.2.2.
**Wave**: 3.

**Scope**: costruire la shell TUI del gioco: schermata iniziale con l'elenco delle Carriere (crea/apri/elimina) e flusso di nuova Carriera (nome, colori, identità squadra) che genera il Mondo via motore, lo persiste al Checkpoint e porta alla schermata griglia con le 11 squadre e i 22 piloti mostrati a Stime. È il primo loop completo motore → persistenza → UI.

**Scenario utente**: il giocatore lancia `fm`. Vede l'elenco delle Carriere; al primo avvio è un empty state che invita a crearne una. Sceglie "Nuova Carriera", inserisce il nome "Scuderia X", colori e identità squadra. Il Mondo viene generato e atterra sulla schermata griglia: 11 squadre e 22 piloti, attributi mostrati come Stime (intervalli), bandiere di nazionalità accanto ai piloti. Esce con `q`. Rilancia `fm`: "Scuderia X" è nell'elenco; la apre e ritrova la stessa griglia. Dall'elenco può eliminare una Carriera con conferma. Edge case: se non esistono Carriere, vede l'empty state, mai un elenco vuoto silenzioso.

**Deliverable verificabile**:

* Schermata elenco Carriere con azioni crea/apri/elimina, binding visibili in Footer ed empty state per elenco vuoto.
* Flusso nuova Carriera (nome, colori, identità squadra) che invoca `fm_engine.mondo.genera` e salva al Checkpoint via `fm_persistenza`.
* Schermata griglia: 11 squadre e 22 piloti con attributi a Stime (intervalli, mai valori esatti) e bandiere di nazionalità.
* Carriera persistita e ricaricabile: chiudi l'app, riapri, riapri la Carriera e ritrovi la stessa griglia.
* Nomi editati via Supabase Studio appaiono al load successivo (verificabile con i Test manuali).
* Eliminazione con conferma e cancellazione a cascata.
* Test Pilot: creazione Carriera, navigazione alla griglia, riapertura, eliminazione.

**File da toccare**:

* `src/fm_tui/app.py`
* `src/fm_tui/schermate/__init__.py` (NEW DIR)
* `src/fm_tui/schermate/elenco_carriere.py` (NEW)
* `src/fm_tui/schermate/nuova_carriera.py` (NEW)
* `src/fm_tui/schermate/griglia.py` (NEW)
* `src/fm_tui/widget/stime.py` (NEW DIR: rendering intervalli di Stima)
* `tests/tui/test_gestione_carriere.py` (NEW)
* `tests/tui/test_griglia.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: `fm` apre l'elenco Carriere; la griglia si raggiunge da crea/apri
- [ ] Popolata: la griglia mostra 11 squadre e 22 piloti con Stime e bandiere
- [ ] Cliccabile: ogni azione (crea/apri/elimina, navigazione) ha binding da tastiera visibile in Footer
- [ ] URL canonica (previsto [N/A]: TUI senza routing; ogni schermata ha nome canonico nello stack Textual)
- [ ] Stati UI: empty state a elenco vuoto; conferma su eliminazione
- [ ] Aggiornata: l'elenco riflette creazioni ed eliminazioni senza riavvio; il load mostra l'ultimo Checkpoint, inclusi i nomi editati via Studio
- [ ] Compatibile wireframe (previsto [N/A]: nessun wireframe; il riferimento di layout è il PRD)

**Cosa NON fare**:

* Niente wizard di Setup squadra (è T1.3.2).
* Niente economia (Cassa, Cap, stipendi).
* Niente sessioni, Telecronaca o calendario navigabile.
* Niente Mercato piloti.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (story 1, 2, 6).
* `CONTEXT.md` (Carriera, Checkpoint, Griglia, Stima).
* `docs/adr/0001` (persistenza), `docs/adr/0002` (Textual + motore puro).
* T1.2.1 (generazione Mondo), T1.2.2 (Persistenza a Checkpoint).

**Test manuali**:

* lancia `fm` → empty state dell'elenco Carriere
* crea la Carriera "Scuderia X" → griglia con 11 squadre e 22 piloti a Stime con bandiere
* `q` per uscire, rilancia `fm` → "Scuderia X" in elenco, aprila → stessa griglia
* edita un nome squadra via Supabase Studio → riapri la Carriera → il nome aggiornato è visibile
* elimina la Carriera → conferma richiesta, poi elenco di nuovo in empty state

## Note
Origine: Linear FOR-6 (https://linear.app/haku-inc/issue/FOR-6/t131-costruisci-tui-shell-e-gestione-carriere). Etichette Linear: si, ready-for-agent.
