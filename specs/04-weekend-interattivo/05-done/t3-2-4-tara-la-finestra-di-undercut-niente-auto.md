---
id: t3-2-4-tara-la-finestra-di-undercut-niente-auto
titolo: "T3.2.4 Tara la finestra di undercut: niente auto-pausa a raffica"
stato: done
priorita: media
dipendenze: []
etichette: [si]
creata: 2026-06-12
scadenza:
linear: FOR-40
---

## Contesto
Importata da Linear FOR-40: progetto "Weekend interattivo", stato Linear "Done", creata 2026-06-12.

## Obiettivo
### T3.2.4 [ ] Tara la finestra di undercut: niente auto-pausa a raffica

**Dipendenze**: T3.2.3, T2.5.3.
**Wave**: taratura (emersa nel playtest del primo weekend giocato).

**Scope**: nel playtest il pannello della finestra di undercut compariva quasi a ogni giro, costringendo a "Riprendi senza ordini" in continuazione. Cause: l'anti-spam attuale e' per coppia (attaccante, rivale) con isteresi solo sul distacco (`UNDERCUT_GAP_HYSTERESIS_SECONDS`), ma in traffico le posizioni cambiano a ogni giro, le coppie adiacenti si rimescolano e ogni coppia nuova e' un'emissione nuova; inoltre le soglie sono permissive (eta' gomme attaccante >= 5 giri, degrado rivale >= 0.45s) e con T2.5.3 assente tutti i rivali avevano gomme vecchissime, quindi la finestra era permanente. La finestra deve comparire solo quando fermarsi e' strategicamente sensato, non ogni volta che si e' vicini a qualcuno.

**Scenario utente**: il manager guarda la gara senza interruzioni continue; quando il suo pilota entra davvero nella finestra utile (rivale davanti su gomme a fine vita, sosta che ripaga la perdita pit), l'Auto-pausa scatta una volta, il manager decide, e per parecchi giri non viene ridisturbato per lo stesso pilota a condizioni simili.

**Deliverable verificabile**:

* Cooldown per attaccante: dopo un'emissione (o un'Auto-pausa rifiutata), nessuna nuova finestra per lo stesso pilota per almeno N giri (costante nominata, indicativamente 5-8), anche se la coppia cambia.
* Condizione di convenienza reale: la finestra si apre solo se la sosta ripaga, stimando dal modello esistente che il guadagno della gomma fresca sui giri residui superi la perdita pit (riuso di perdita media pit e curve di Degrado, niente modelli nuovi).
* Soglie riviste con l'AI che pitta (T2.5.3): in una gara interattiva tipica con seed fisso le Auto-pause da undercut per il giocatore sono poche unita' (asserzione di sanita' nel test, range largo ma non decine).
* Monitoraggio della frequenza dell'evento nell'harness di bilanciamento con asserzione di range (il follow-up gia' segnalato in <issue id="d68b9134-2f8f-4c3c-b71c-6318e11d4bb3" href="https://linear.app/haku-inc/issue/FOR-38/t323-implementa-finestra-di-undercut-come-evento-chiave">FOR-38</issue>).
* Test motore con seed fisso su cooldown e convenienza; test Pilot che in una gara trafficata non apre il pannello a ogni giro.

**Cosa NON fare**:

* Niente rimozione dell'evento o dell'innesco: va tarato, non spento.
* Niente suggerimento automatico della strategia al giocatore oltre alla descrizione della finestra.
* Niente modifica al comportamento degli altri inneschi di Auto-pausa.

**Riferimenti**:

* <issue id="d68b9134-2f8f-4c3c-b71c-6318e11d4bb3" href="https://linear.app/haku-inc/issue/FOR-38/t323-implementa-finestra-di-undercut-come-evento-chiave">FOR-38</issue> (implementazione della finestra, costanti `UNDERCUT_*` in `src/fm_engine/race.py`).
* <issue id="6a5084b8-c579-4982-9b96-6b8d473840f0" href="https://linear.app/haku-inc/issue/FOR-39/t253-porta-la-strategia-pit-delle-squadre-ai-nel-motore-di-gara">FOR-39</issue> / T2.5.3 (strategia pit AI: prerequisito per tarare su gare realistiche).
* `CONTEXT.md` (Finestra di undercut, Evento chiave, Degrado).

## Note
Origine: Linear FOR-40 (https://linear.app/haku-inc/issue/FOR-40/t324-tara-la-finestra-di-undercut-niente-auto-pausa-a-raffica). Etichette Linear: si.
Dipendenze cross-progetto su Linear (non risolte come slug locali): t2-5-3-porta-la-strategia-pit-delle-squadre-ai (FOR-39).
