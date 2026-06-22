---
id: t3-2-2-implementa-ordini-pilota-aggressivit
titolo: "T3.2.2 Implementa ordini pilota: Aggressività, scuderia, duelli"
stato: done
priorita: media
dipendenze: [t3-2-1-implementa-auto-pausa-e-ordine-pit]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-19
---

## Contesto
Importata da Linear FOR-19: progetto "Weekend interattivo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T3.2.2 [ ] Implementa ordini pilota: Aggressività, scuderia, duelli

**Dipendenze**: T3.2.1.
**Wave**: 2.

**Scope**: pannello Ordini per ciascun pilota, accessibile in pausa (manuale o Auto-pausa): Aggressività (Push/Normale/Conserva), Ordini di scuderia (scambio posizioni, congelamento posizioni, divieto di attacco al compagno), Istruzioni sui duelli (difendi duro / non rischiare); ogni Ordine produce conferma e feedback in Telecronaca e si riflette negli input del motore.

**Scenario utente**: il manager mette pausa al giro 12 e apre il pannello Ordini del primo pilota: imposta l'Aggressività su Push e l'Istruzione sui duelli su "difendi duro". Conferma e riprende: in Telecronaca compare la conferma via radio e nei giri successivi il pilota guadagna passo al prezzo di più Degrado e maggiore rischio di Errore. Quando i due piloti si ritrovano vicini in pista, pausa di nuovo e impone l'Ordine di scuderia "congelamento posizioni": nessuno dei due attacca l'altro. Lo stato corrente degli Ordini di entrambi i piloti resta sempre visibile nella schermata gara. Edge case: se un pilota è in Abbandono, il suo pannello Ordini è disabilitato con motivo visibile.

**Deliverable verificabile**:

* Pannello Ordini per pilota accessibile in qualsiasi pausa con i tre gruppi: Aggressività (Push/Normale/Conserva), Ordine di scuderia (scambio, congelamento, divieto di attacco al compagno), Istruzione sui duelli (difendi duro / non rischiare).
* Gli Ordini confluiscono negli input del motore e producono effetti misurabili su passo, Degrado e rischio di Errore, verificati da test unitari sul motore con seed fisso.
* Ogni Ordine confermato produce una riga di feedback in Telecronaca.
* Lo stato corrente degli Ordini di entrambi i piloti è sempre visibile nella schermata gara.
* Test Pilot sul flusso pausa → pannello → Ordine → ripresa; test unitari sugli effetti dei tre gruppi di Ordini.

**File da toccare**:

* `src/formula_manager/tui/widgets/orders_panel.py` (NEW)
* `src/formula_manager/tui/screens/race.py`
* `src/formula_manager/engine/race/orders.py`
* `tests/tui/test_orders_panel.py` (NEW)
* `tests/engine/test_driver_orders_effects.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il pannello Ordini si apre da qualsiasi pausa per ciascun pilota
- [ ] Popolata: il pannello mostra lo stato reale corrente degli Ordini del pilota selezionato
- [ ] Cliccabile: ogni Ordine è selezionabile e confermabile da tastiera, con feedback immediato
- [ ] URL canonica (previsto [N/A]: pannello modale dentro la schermata gara, nessuna route propria)
- [ ] Stati UI: pannello per pilota, conferma impartita, stato Ordini sempre visibile, pilota in Abbandono disabilitato
- [ ] Aggiornata: gli effetti degli Ordini sono osservabili nei giri successivi (passo/Degrado/rischio)
- [ ] Compatibile wireframe (previsto [N/A]: nessun wireframe formale; pannello come da PRD)

**Cosa NON fare**:

* Niente gestione energia 2026 (post-MVP).
* Niente Ordini oltre i quattro del MVP (il pit con scelta Mescola è già T3.2.1).
* Niente modifica al flusso di Auto-pausa o al pannello decisione di T3.2.1.
* Niente nuovi tipi di Evento chiave nel motore.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 19, 20, 21).
* `CONTEXT.md` (Ordine, Aggressività, Ordine di scuderia, Istruzione sui duelli, Degrado, Errore, Abbandono).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md` (feedback degli Ordini in cronaca).
* T3.2.1 (Auto-pausa e pause da cui si accede al pannello).

## Note
Origine: Linear FOR-19 (https://linear.app/haku-inc/issue/FOR-19/t322-implementa-ordini-pilota-aggressivita-scuderia-duelli). Etichette Linear: si, ready-for-agent.
