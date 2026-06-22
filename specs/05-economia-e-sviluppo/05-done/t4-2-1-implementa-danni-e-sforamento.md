---
id: t4-2-1-implementa-danni-e-sforamento
titolo: "T4.2.1 Implementa Danni e Sforamento"
stato: done
priorita: media
dipendenze: [t4-1-1-implementa-registro-cassa-e-cap]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-23
---

## Contesto
Importata da Linear FOR-23: progetto "Economia e sviluppo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T4.2.1 [ ] Implementa Danni e Sforamento

**Dipendenze**: T4.1.1, T2.2.2.

**Wave**: 2.

**Scope**: trasformare gli eventi danno del motore di gara (Incidenti, Guasti di T2.2.2) in costi di riparazione che pesano sulla Cassa E consumano Cap, come nella F1 reale. Se il Cap residuo non basta, la riparazione avviene comunque — la vettura corre sempre — e lo Sforamento (Cap negativo) viene registrato; a fine stagione la penalità riduce il Cap dell'anno successivo in misura proporzionale allo Sforamento.

**Scenario utente**:

> In gara il pilota del giocatore ha un Incidente. Chiuso il weekend, il giocatore
> apre la schermata finanze e vede il movimento "Danni" con causale dell'evento e
> importo proporzionale alla sua entità: la Cassa scende e il Cap residuo si erode.
> Edge case: se il danno supera il Cap residuo, la riparazione passa comunque e il
> widget dei saldi mostra lo Sforamento; al rollover di stagione il giocatore vede
> il Cap del nuovo anno ridotto dalla penalità.

**Deliverable verificabile**:

* Gli eventi danno tipizzati di T2.2.2 (Incidenti, Guasti, con entità nel payload) generano costi di riparazione proporzionali all'entità, registrati con causale Danni su Cassa e Cap nel registro di T4.1.1, verificabile via pytest headless.
* Caso limite danno > Cap residuo: la riparazione viene comunque applicata (mai vetture ferme per Cap) e lo Sforamento viene tracciato come Cap negativo, verificabile via pytest.
* Al rollover di stagione lo Sforamento si traduce in una riduzione proporzionale del Cap dell'anno successivo, verificabile via pytest sul passaggio di stagione (incluso il caso senza Sforamento: nessuna penalità).
* La schermata finanze mostra i movimenti Danni e lo stato di Sforamento quando presente, verificabile con test Pilot.
* Lo stato di Sforamento sopravvive al round-trip di persistenza a Checkpoint, verificabile via pytest su Postgres effimero Docker.

**File da toccare**:

* `src/engine/economy/damages.py` (NEW)
* `src/engine/economy/ledger.py`
* `src/persistence/economy.py`
* `src/tui/screens/finances.py`
* `src/tui/widgets/balance_bar.py`
* `tests/engine/economy/test_damages.py` (NEW)
* `tests/engine/economy/test_overspend_rollover.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: i movimenti Danni compaiono nella schermata finanze di T4.1.1 senza nuove rotte
- [ ] Popolata: ogni movimento Danni porta causale dell'evento, importo e data di gioco reali
- [ ] Cliccabile: (previsto [N/A]: nessun nuovo controllo interattivo; la navigazione dello storico è di T4.1.1)
- [ ] URL canonica: (previsto [N/A]: app TUI senza URL; nessuna nuova schermata)
- [ ] Stati UI: lo Sforamento è segnalato in modo esplicito nel widget dei saldi quando il Cap è negativo
- [ ] Aggiornata: Cassa e Cap residuo riflettono il danno appena registrato senza riavvio
- [ ] Compatibile wireframe: (previsto [N/A]: nessun wireframe formale per il MVP TUI)

**Cosa NON fare**:

* Niente riparazioni gratuite: ogni evento danno ha un costo.
* Niente vettura menomata persistente: il danno è puramente economico, la vettura corre sempre al GP successivo.
* Niente Misura d'emergenza né fallimento: è T4.2.2.
* Niente modifica all'estrazione degli eventi di T2.2.2: qui solo il calcolo economico dal payload.
* Niente scritture su DB fuori dai Checkpoint (ADR 0001).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 31, 32.
* `CONTEXT.md` § Economia (Danni, Sforamento, Cassa, Cap) e § Gara (Incidente, Guasto).
* `docs/adr/0001-supabase-self-hosted-su-vps-con-salvataggi-a-checkpoint.md`.
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* T4.1.1 (<issue id="5b4a287a-4f3d-4fe2-a70a-8b11ae00634c" href="https://linear.app/haku-inc/issue/FOR-15/t411-implementa-registro-cassa-e-cap">FOR-15</issue>, registro Cassa e Cap), T2.2.2 (<issue id="2500443d-2a43-4d48-9e53-07f7bd8100c9" href="https://linear.app/haku-inc/issue/FOR-11/t222-implementa-sfiga-guasti-errori-incidenti">FOR-11</issue>, eventi danno con entità nel payload).

## Note
Origine: Linear FOR-23 (https://linear.app/haku-inc/issue/FOR-23/t421-implementa-danni-e-sforamento). Etichette Linear: si, ready-for-agent.
Dipendenze cross-progetto su Linear (non risolte come slug locali): t2-2-2-implementa-sfiga-guasti-errori-incidenti (FOR-11).
