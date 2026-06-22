---
id: t3-2-3-implementa-finestra-di-undercut-come
titolo: "T3.2.3 Implementa finestra di undercut come Evento chiave"
stato: done
priorita: media
dipendenze: []
etichette: [si]
creata: 2026-06-12
scadenza:
linear: FOR-38
---

## Contesto
Importata da Linear FOR-38: progetto "Weekend interattivo", stato Linear "Done", creata 2026-06-12.

## Obiettivo
### T3.2.3 [ ] Implementa finestra di undercut come Evento chiave

**Dipendenze**: T3.2.1.
**Wave**: follow-up (gap emerso in <issue id="6007b508-9796-4725-9374-9e6bb2d82267" href="https://linear.app/haku-inc/issue/FOR-18/t321-implementa-auto-pausa-e-ordine-pit">FOR-18</issue>).

**Scope**: la issue <issue id="6007b508-9796-4725-9374-9e6bb2d82267" href="https://linear.app/haku-inc/issue/FOR-18/t321-implementa-auto-pausa-e-ordine-pit">FOR-18</issue> prevedeva la "finestra di undercut" tra gli inneschi dell'Auto-pausa, ma il motore non ha alcun tipo di evento corrispondente e il vincolo di quella issue vietava di crearne di nuovi: oggi quell'innesco non esiste. Questo task introduce nel motore puro un evento che segnala l'apertura di una finestra di undercut (un rivale in range di pit potrebbe guadagnare la posizione fermandosi, o viceversa il proprio pilota puo' guadagnarla sul rivale davanti), emesso da `step()` al momento giusto e con anti-spam (una emissione per finestra, non una per giro), con relativi template di Telecronaca e innesco di Auto-pausa nella schermata gara.

**Scenario utente**: gara al giro 18, il pilota del manager e' a 2 secondi dal rivale davanti con gomme piu' fresche in arrivo dal pit: il motore emette l'evento di finestra di undercut, la simulazione va in Auto-pausa e il pannello di decisione propone l'ordine di pit con la scelta della Mescola. Il manager ordina il box e guadagna la posizione all'uscita. Edge case: la stessa finestra non ri-scatena l'Auto-pausa al giro successivo se le condizioni restano invariate.

**Deliverable verificabile**:

* Nuovo tipo evento nel motore (es. `UndercutWindow`) emesso da `step()` quando un rivale in range di pit puo' guadagnare posizione fermandosi, calcolato dai modelli esistenti (perdita pit, Degrado, distacchi); deterministico a parita' di seed.
* Anti-spam: una emissione per apertura di finestra, niente ripetizione a ogni giro a condizioni invariate (isteresi o registro della finestra attiva).
* Famiglia di template di Telecronaca per il nuovo evento (il test di copertura impone template per ogni tipo evento).
* L'evento innesca l'Auto-pausa nella schermata gara quando riguarda i piloti del giocatore, con pannello pit contestuale, esattamente una volta per evento.
* Test unitari sul motore con seed fisso (emissione, anti-spam, determinismo) e test Pilot sull'innesco di Auto-pausa.

**Cosa NON fare**:

* Niente strategia AI automatica del pit per il giocatore: l'evento informa, la decisione resta al manager.
* Niente modifica al comportamento degli altri Eventi chiave o del pannello di <issue id="6007b508-9796-4725-9374-9e6bb2d82267" href="https://linear.app/haku-inc/issue/FOR-18/t321-implementa-auto-pausa-e-ordine-pit">FOR-18</issue> oltre al nuovo innesco.
* Niente persistenza dell'evento.

**Riferimenti**:

* <issue id="6007b508-9796-4725-9374-9e6bb2d82267" href="https://linear.app/haku-inc/issue/FOR-18/t321-implementa-auto-pausa-e-ordine-pit">FOR-18</issue> (Auto-pausa e ordine pit: pattern degli inneschi nella RaceScreen).
* `CONTEXT.md` (Evento chiave, Ordine, Mescola, Degrado).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md`.

## Note
Origine: Linear FOR-38 (https://linear.app/haku-inc/issue/FOR-38/t323-implementa-finestra-di-undercut-come-evento-chiave). Etichette Linear: si.
