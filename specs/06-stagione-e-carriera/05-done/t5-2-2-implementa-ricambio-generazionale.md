---
id: t5-2-2-implementa-ricambio-generazionale
titolo: "T5.2.2 Implementa ricambio generazionale"
stato: done
priorita: media
dipendenze: [t5-2-1-implementa-mercato-piloti]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-31
---

## Contesto
Importata da Linear FOR-31: progetto "Stagione e carriera", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T5.2.2 [ ] Implementa ricambio generazionale

**Dipendenze**: T5.2.1.
**Wave**: 3.

**Scope**: far vivere il parco piloti tra le stagioni: evoluzione degli attributi guidata da età e Potenziale nascosto (crescita dei giovani, declino degli anziani), Ritiri di carriera probabilistici per gli anziani a fine stagione, generazione di Giovani con Potenziale nascosto che entrano nel pool del Mercato piloti.

**Scenario utente**:
A fine stagione, prima del Mercato piloti, il giocatore legge le Notizie: un veterano annuncia il Ritiro di carriera. Aprendo il mercato trova tra i piloti disponibili un Giovane generato, con Stime larghe e Potenziale tutto da scoprire. Tra una stagione e l'altra nota che la sua giovane promessa è cresciuta nel Passo gara, mentre il veterano della rivale ha perso Giro secco. Edge case: i Ritiri sono possibili ma non obbligatori — può capitare una stagione senza alcun Ritiro, e il mercato funziona comunque.

**Deliverable verificabile**:

* Esiste l'evoluzione annuale degli attributi pilota guidata da età e Potenziale nascosto (crescita giovani, declino anziani), verificabile via test pytest sul motore headless.
* I Ritiri di carriera sono estratti probabilisticamente per gli anziani a fine stagione: possibili, mai obbligatori; verificabile via test su distribuzioni seedate (esistono run senza Ritiri e run con Ritiri).
* I Giovani generati entrano nel pool del Mercato piloti con Potenziale nascosto e Stime larghe, verificabile via schermata mercato e test.
* Ogni Ritiro di carriera produce una Notizia leggibile dal giocatore, verificabile via Pilot.
* Simulazione headless di 10 stagioni: parco piloti a regime (numero piloti sufficiente a riempire la Griglia, età media stabile entro una banda definita), verificata da test pytest dedicato.

**File da toccare**:

* `engine/drivers/aging.py` (NEW)
* `engine/drivers/retirement.py` (NEW)
* `engine/drivers/youth_generation.py` (NEW)
* `engine/market/driver_market.py`
* `persistence/repositories/drivers.py`
* `supabase/migrations/<timestamp>_driver_generations.sql` (NEW)
* `tests/engine/test_aging_curves.py` (NEW)
* `tests/engine/test_generational_longrun.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: le Notizie dei Ritiri sono visibili nel flusso di fine stagione; i Giovani sono raggiungibili nel Mercato piloti
- [ ] Popolata: pool mercato arricchito dei Giovani generati; Notizia con nome e congedo del ritirato
- [ ] Cliccabile: consultazione Notizie e schede dei Giovani da tastiera (riuso schermate esistenti)
- [ ] URL canonica (previsto [N/A]: nessuna schermata nuova, riuso di Notizie e Mercato piloti)
- [ ] Stati UI: stagione senza Ritiri (nessuna Notizia di ritiro, mercato regolare)
- [ ] Aggiornata: attributi, età e pool aggiornati a ogni cambio stagione, dentro il Checkpoint di transizione
- [ ] Compatibile wireframe (previsto [N/A]: nessuna schermata nuova)

**Cosa NON fare**:

* Niente accademie o scouting dei Giovani (post-MVP).
* Niente Ritiri obbligatori né quote fisse di ricambio per stagione.
* Niente modifiche alla logica di offerta AI del mercato (è T5.2.1).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 41)
* `CONTEXT.md` (Potenziale, Ritiro (carriera), Giovane, Notizia, Mercato piloti, Stima)
* `docs/adr/0001` (persistenza: scritture solo a Checkpoint)
* `docs/adr/0002` (Textual + motore puro)
* Task a monte: T5.2.1

## Note
Origine: Linear FOR-31 (https://linear.app/haku-inc/issue/FOR-31/t522-implementa-ricambio-generazionale). Etichette Linear: si, ready-for-agent.
