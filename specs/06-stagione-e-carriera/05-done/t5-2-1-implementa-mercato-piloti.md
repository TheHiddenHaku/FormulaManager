---
id: t5-2-1-implementa-mercato-piloti
titolo: "T5.2.1 Implementa Mercato piloti"
stato: done
priorita: media
dipendenze: [t5-1-1-implementa-calendario-e-classifiche]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-30
---

## Contesto
Importata da Linear FOR-30: progetto "Stagione e carriera", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T5.2.1 [ ] Implementa Mercato piloti

**Dipendenze**: T5.1.1, T4.1.2.
**Wave**: 2.

**Scope**: la fase di fine stagione in cui i Contratti in scadenza entrano nel Mercato piloti: le squadre AI fanno offerte credibili (il Prestigio alto attrae i piloti migliori), il giocatore negozia ingaggio e durata (1-3 anni) entro i vincoli di Cassa, e i piloti si valutano a Stime.

**Scenario utente**:
A fine stagione si apre il Mercato piloti. La seconda guida del giocatore ha il Contratto in scadenza: una rivale con Prestigio più alto le presenta un'offerta. Il giocatore apre la schermata mercato, vede gli attributi del pilota come Stime e l'esistenza dell'offerta rivale; può controfferire alzando ingaggio o durata (1-3 anni), ma solo nei limiti della Cassa: se gli stipendi proposti non sono sostenibili, l'offerta è bloccata con motivo esplicito. Se rilancia bene tiene il pilota; altrimenti lo perde e ripiega su un pilota libero. Le mosse delle AI compaiono in un log consultabile. Edge case: il mercato converge sempre — alla chiusura ogni squadra della Griglia ha esattamente 2 piloti sotto Contratto, nessun sedile vuoto.

**Deliverable verificabile**:

* Esiste la fase Mercato piloti a fine stagione: tutti i Contratti in scadenza entrano nel pool, verificabile via schermata mercato e test pytest.
* Le AI producono offerte credibili guidate dal Prestigio (le squadre più prestigiose attraggono i piloti migliori), verificabile via test statistici sul motore headless con seed fissati.
* Il giocatore negozia ingaggio e durata (1-3 anni) con vincolo di Cassa applicato (offerte insostenibili rifiutate con motivo esplicito), verificabile via test e via UI.
* I piloti nel mercato sono presentati a Stime, mai a valori esatti, verificabile via schermata.
* La convergenza è garantita: a chiusura mercato ogni squadra ha esattamente 2 piloti; test pytest su molte esecuzioni seedate lo dimostra.
* Esiste il log delle mosse AI consultabile dal giocatore, verificabile via Pilot.

**File da toccare**:

* `engine/market/__init__.py` (NEW DIR)
* `engine/market/driver_market.py` (NEW)
* `engine/market/ai_offers.py` (NEW)
* `engine/market/negotiation.py` (NEW)
* `tui/screens/market.py` (NEW)
* `persistence/repositories/contracts.py` (NEW)
* `supabase/migrations/<timestamp>_driver_market.sql` (NEW)
* `tests/engine/test_market_convergence.py` (NEW)
* `tests/engine/test_market_economics.py` (NEW)
* `tests/tui/test_market_screen.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il Mercato piloti si apre nel flusso di fine stagione, dopo l'ultimo GP
- [ ] Popolata: pool con tutti i piloti a Contratto in scadenza, offerte AI e log mosse
- [ ] Cliccabile: negoziazione (offerta, controfferta, rinuncia) interamente da tastiera
- [ ] URL canonica: schermata mercato con id/binding canonico nell'app Textual
- [ ] Stati UI: nessun pilota in scadenza, offerta bloccata per vincolo di Cassa, mercato chiuso
- [ ] Aggiornata: offerte e sedili aggiornati a ogni turno di mercato; Checkpoint a chiusura fase
- [ ] Compatibile wireframe: layout coerente con le schermate TUI esistenti

**Cosa NON fare**:

* Niente trasferimenti in-season (post-MVP): il mercato vive solo a fine stagione.
* Niente infortuni o indisponibilità dei piloti.
* Niente generazione di Giovani né Ritiri di carriera (è T5.2.2).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 40)
* `CONTEXT.md` (Mercato piloti, Contratto, Prestigio, Cassa, Stima, Griglia)
* `docs/adr/0001` (persistenza: scritture solo a Checkpoint)
* `docs/adr/0002` (Textual + motore puro)
* Task a monte: T5.1.1, T4.1.2

## Note
Origine: Linear FOR-30 (https://linear.app/haku-inc/issue/FOR-30/t521-implementa-mercato-piloti). Etichette Linear: si, ready-for-agent.
Dipendenze cross-progetto su Linear (non risolte come slug locali): t4-1-2-implementa-entrate-e-stipendi (FOR-22).
