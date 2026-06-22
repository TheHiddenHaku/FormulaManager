---
id: t5-3-2-costruisci-almanacco-e-albo-d-oro
titolo: "T5.3.2 Costruisci Almanacco e Albo d'oro"
stato: done
priorita: media
dipendenze: [t5-1-1-implementa-calendario-e-classifiche]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-33
---

## Contesto
Importata da Linear FOR-33: progetto "Stagione e carriera", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T5.3.2 [ ] Costruisci Almanacco e Albo d'oro

**Dipendenze**: T5.1.1.
**Wave**: 3.

**Scope**: l'archivio permanente e consultabile della Carriera: risultato completo di ogni GP giocato (griglia di partenza, ordine d'arrivo, eventi principali), classifiche finali di ogni stagione, statistiche cumulative per pilota e squadra (vittorie, podi, pole, titoli) e Albo d'oro dei campioni.

**Scenario utente**:
Durante la terza stagione il giocatore apre l'Almanacco dal menu della Carriera. Naviga da tastiera alla stagione 2026, scorre l'elenco dei 24 GP e riapre il GP di Monza: rivede la griglia di partenza, l'ordine d'arrivo completo e gli eventi principali (safety car, Abbandoni). Torna su, apre le classifiche finali 2026 e poi l'Albo d'oro, dove i titoli piloti e costruttori sono elencati anno per anno. Da ogni vista torna indietro col binding di back. Edge case: nella prima stagione, con nessuna stagione conclusa, l'Albo d'oro mostra un empty state esplicito invece di una lista vuota.

**Deliverable verificabile**:

* Ogni GP concluso persiste griglia di partenza, ordine d'arrivo ed eventi principali; il dato è rileggibile dall'Almanacco, verificabile via Pilot e via query.
* Le classifiche finali di ogni stagione sono archiviate e consultabili, verificabili via test multi-stagione.
* Le statistiche cumulative per pilota e squadra (vittorie, podi, pole, titoli) sono calcolate correttamente, verificabili via test pytest con dataset noto.
* Esiste l'Albo d'oro con i titoli piloti e costruttori anno per anno, verificabile via schermata.
* I dati storici non vengono mai cancellati né sovrascritti dai cambi di stagione, verificabile via test di accumulo su più stagioni simulate (Postgres effimero Docker).
* Le query dell'Almanacco restano efficienti su Carriere lunghe (indici dedicati, tempo di risposta verificato su dataset simulato di 10+ stagioni).

**File da toccare**:

* `engine/history/__init__.py` (NEW DIR)
* `engine/history/stats.py` (NEW)
* `tui/screens/almanac.py` (NEW)
* `tui/screens/hall_of_fame.py` (NEW)
* `persistence/repositories/history.py` (NEW)
* `supabase/migrations/<timestamp>_almanac_history.sql` (NEW)
* `tests/engine/test_career_stats.py` (NEW)
* `tests/persistence/test_history_accumulation.py` (NEW)
* `tests/tui/test_almanac_screens.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: Almanacco e Albo d'oro raggiungibili dal menu della Carriera in ogni momento
- [ ] Popolata: ogni GP giocato con griglia, arrivo ed eventi; statistiche cumulative complete
- [ ] Cliccabile: navigazione stagione → GP → dettaglio interamente da tastiera, con back funzionante
- [ ] URL canonica: schermate con id/binding canonici nell'app Textual
- [ ] Stati UI: empty state per Albo d'oro senza stagioni concluse e per la stagione in corso
- [ ] Aggiornata: l'archivio si arricchisce a ogni GP e a ogni fine stagione, mai cancellato
- [ ] Compatibile wireframe: layout coerente con le schermate TUI esistenti

**Cosa NON fare**:

* Niente salvataggio della Telecronaca integrale dei GP (deciso nel grill: si archiviano solo griglia, arrivo ed eventi principali).
* Niente statistiche avanzate o grafici (post-MVP).
* Niente export esterno dei dati storici.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 43)
* `CONTEXT.md` (Carriera, Telecronaca, Abbandono, Checkpoint)
* `docs/adr/0001` (persistenza: scritture solo a Checkpoint)
* `docs/adr/0002` (Textual + motore puro)
* `docs/adr/0003` (telecronaca a template: il flusso integrale non si archivia)
* Task a monte: T5.1.1

## Note
Origine: Linear FOR-33 (https://linear.app/haku-inc/issue/FOR-33/t532-costruisci-almanacco-e-albo-doro). Etichette Linear: si, ready-for-agent.
