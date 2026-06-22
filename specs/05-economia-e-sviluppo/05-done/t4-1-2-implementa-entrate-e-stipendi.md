---
id: t4-1-2-implementa-entrate-e-stipendi
titolo: "T4.1.2 Implementa entrate e stipendi"
stato: done
priorita: media
dipendenze: [t4-1-1-implementa-registro-cassa-e-cap]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-22
---

## Contesto
Importata da Linear FOR-22: progetto "Economia e sviluppo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T4.1.2 [ ] Implementa entrate e stipendi

**Dipendenze**: T4.1.1, T3.3.2.

**Wave**: 1.

**Scope**: collegare il registro economico ai flussi automatici della stagione: Premio gara accreditato dopo ogni Gran Premio in base al piazzamento, Sponsor annuale a inizio stagione proporzionale al Prestigio, Montepremi costruttori a fine stagione secondo la classifica costruttori, e addebito periodico degli stipendi piloti che pesa SOLO sulla Cassa — gli stipendi sono esclusi dal Cap, per fedeltà alle regole F1 2026.

**Scenario utente**:

> Il giocatore chiude un Gran Premio con un podio. Tornato alle schermate gestionali,
> apre la schermata finanze e in cima allo storico vede il movimento "Premio gara"
> con la causale del GP e l'importo legato al piazzamento; la Cassa nel widget
> persistente è salita di conseguenza. Edge case: alla scadenza periodica degli
> stipendi vede l'addebito "Stipendi piloti" che riduce la Cassa ma lascia
> invariato il Cap residuo.

**Deliverable verificabile**:

* Il motore accredita il Premio gara dopo ogni GP in base al piazzamento, con causale dedicata nel registro di T4.1.1, verificabile via pytest headless.
* Lo Sponsor annuale viene accreditato a inizio stagione con importo proporzionale al Prestigio della squadra, verificabile via pytest su Prestigi diversi (importi monotòni crescenti).
* Il Montepremi costruttori viene accreditato a fine stagione secondo la classifica costruttori finale, verificabile via pytest.
* Gli stipendi piloti vengono addebitati periodicamente SOLO dalla Cassa: nessun movimento stipendi consuma Cap, verificabile via pytest con asserzione esplicita sull'invarianza del Cap residuo.
* Test su un anno economico simulato: una stagione completa produce un registro coerente con tutte le entrate e tutti gli addebiti stipendi, ciascuno con causale, e saldi finali corretti.

**File da toccare**:

* `src/engine/economy/income.py` (NEW)
* `src/engine/economy/salaries.py` (NEW)
* `src/engine/economy/ledger.py`
* `src/persistence/economy.py`
* `tests/engine/economy/test_income.py` (NEW)
* `tests/engine/economy/test_salaries.py` (NEW)
* `tests/engine/economy/test_season_economy_year.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: i movimenti automatici compaiono nella schermata finanze di T4.1.1 senza nuove rotte
- [ ] Popolata: ogni entrata e ogni addebito stipendi ha causale, importo e data di gioco reali, mai placeholder
- [ ] Cliccabile: (previsto [N/A]: nessun nuovo controllo interattivo; la navigazione dello storico è di T4.1.1)
- [ ] URL canonica: (previsto [N/A]: app TUI senza URL; nessuna nuova schermata)
- [ ] Stati UI: l'addebito stipendi è distinguibile a colpo d'occhio dalle entrate nello storico
- [ ] Aggiornata: Cassa e Cap residuo nel widget persistente riflettono l'ultimo accredito/addebito senza riavvio
- [ ] Compatibile wireframe: (previsto [N/A]: nessun wireframe formale per il MVP TUI)

**Cosa NON fare**:

* Niente sponsor a obiettivi (post-MVP).
* Niente Misura d'emergenza né gestione insolvenza: è T4.2.2.
* Niente Danni né Sforamento: è T4.2.1.
* Niente scritture su DB fuori dai Checkpoint (ADR 0001).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 29, 30, 34.
* `CONTEXT.md` § Economia (Cassa, Cap, Premio gara, Sponsor annuale, Montepremi costruttori) e § Stagione (Prestigio, Contratto, Checkpoint).
* `docs/adr/0001-supabase-self-hosted-su-vps-con-salvataggi-a-checkpoint.md`.
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* T4.1.1 (<issue id="5b4a287a-4f3d-4fe2-a70a-8b11ae00634c" href="https://linear.app/haku-inc/issue/FOR-15/t411-implementa-registro-cassa-e-cap">FOR-15</issue>, registro Cassa e Cap), T3.3.2 (<issue id="e1ad9fe0-2247-4d86-85ba-67282ab0d9ea" href="https://linear.app/haku-inc/issue/FOR-21/t332-completa-flusso-weekend-end-to-end">FOR-21</issue>).

## Note
Origine: Linear FOR-22 (https://linear.app/haku-inc/issue/FOR-22/t412-implementa-entrate-e-stipendi). Etichette Linear: si, ready-for-agent.
Dipendenze cross-progetto su Linear (non risolte come slug locali): t3-3-2-completa-flusso-weekend-end-to-end (FOR-21).
