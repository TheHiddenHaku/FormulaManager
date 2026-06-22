---
id: t3-2-1-implementa-auto-pausa-e-ordine-pit
titolo: "T3.2.1 Implementa Auto-pausa e ordine pit"
stato: done
priorita: media
dipendenze: [t3-1-2-costruisci-schermata-gara-cronaca-e]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-18
---

## Contesto
Importata da Linear FOR-18: progetto "Weekend interattivo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T3.2.1 [ ] Implementa Auto-pausa e ordine pit

**Dipendenze**: T3.1.2.
**Wave**: 2.

**Scope**: gli Eventi chiave del motore (Safety car, VSC, pioggia/Crossover, Guasto proprio, finestra di undercut) scatenano l'Auto-pausa con pannello di decisione contestuale; il manager può impartire l'Ordine di pit stop con scelta della Mescola sia dal pannello sia in pausa manuale, con ripresa fluida della simulazione. È il cuore decisionale della Gara interattiva.

**Scenario utente**: giro 30, il motore estrae un Incidente che innesca la Safety car: la simulazione si ferma da sola e sul monitor compare il pannello "SC in pista: box ora? quale Mescola?" con le opzioni contestuali. Il manager ordina il pit per il primo pilota con Mescola Media e conferma; il pannello si chiude e la gara riprende esattamente da dove si era fermata. Nella Telecronaca compare la riga del pit stop e la tabella tempi aggiorna Mescola ed età gomme. Più tardi mette pausa manualmente e ordina il pit anche al secondo pilota. Edge case: se il manager chiude il pannello senza decidere, la gara riprende senza Ordini e lo stesso Evento chiave non ri-scatena l'Auto-pausa.

**Deliverable verificabile**:

* Ogni Evento chiave (Safety car, VSC, pioggia/Crossover, Guasto proprio, finestra di undercut) scatena l'Auto-pausa esattamente una volta, con pannello contestuale che descrive l'evento e le opzioni pertinenti.
* L'Ordine di pit con scelta della Mescola è impartibile sia dal pannello di Auto-pausa sia in pausa manuale; il motore lo applica al Tick successivo (verificato da test unitario con seed fisso).
* La ripresa dopo la decisione è fluida: nessuna riga di Telecronaca persa né salti nel monitor tempi.
* Test Pilot sul flusso completo evento → Auto-pausa → decisione → ripresa; test che lo stesso Evento chiave non causi doppia Auto-pausa.

**File da toccare**:

* `src/formula_manager/tui/screens/race.py`
* `src/formula_manager/tui/widgets/decision_panel.py` (NEW)
* `src/formula_manager/tui/workers/race_worker.py`
* `src/formula_manager/engine/race/orders.py` (NEW)
* `tests/tui/test_autopause_pit.py` (NEW)
* `tests/engine/test_pit_order.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il pannello decisione compare in Auto-pausa e in pausa manuale dalla schermata gara
- [ ] Popolata: il pannello mostra contesto reale dell'Evento chiave (tipo, giro, opzioni Mescola)
- [ ] Cliccabile: scelta box/resta fuori e scelta Mescola confermabili da tastiera
- [ ] URL canonica (previsto [N/A]: pannello modale dentro la schermata gara, nessuna route propria)
- [ ] Stati UI: Auto-pausa con pannello, pausa manuale con ordine pit, ripresa post-decisione, nessuna decisione presa
- [ ] Aggiornata: l'Ordine impartito si riflette al Tick successivo in Telecronaca e monitor tempi
- [ ] Compatibile wireframe (previsto [N/A]: nessun wireframe formale; pannello contestuale come da PRD)

**Cosa NON fare**:

* Niente altri Ordini (Aggressività, Ordini di scuderia, Istruzioni sui duelli): sono T3.2.2.
* Niente nuovi tipi di Evento chiave nel motore: si consumano quelli esistenti.
* Niente Programmi di libere né flusso weekend (T3.3.x).
* Niente scritture su DB in gara (i Checkpoint restano fuori, ADR 0001).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 17, 18).
* `CONTEXT.md` (Auto-pausa, Evento chiave, Ordine, Mescola, Safety car, VSC, Crossover, Guasto).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md` (feedback del pit in cronaca).
* T3.1.2 (schermata gara che ospita pannello e pause).

## Note
Origine: Linear FOR-18 (https://linear.app/haku-inc/issue/FOR-18/t321-implementa-auto-pausa-e-ordine-pit). Etichette Linear: si, ready-for-agent.
