---
id: correggi-l-ordine-di-pit-dalla-finestra-di
titolo: "Correggi l'Ordine di pit dalla finestra di undercut"
stato: done
priorita: media
dipendenze: []
etichette: [si]
creata: 2026-06-13
scadenza:
linear: FOR-42
---

## Contesto
Importata da Linear FOR-42: progetto "Motore di gara", stato Linear "Done", creata 2026-06-13.

## Obiettivo
### <issue id="292edee3-5b82-4dd0-84ed-33601e56b34c" href="https://linear.app/haku-inc/issue/FOR-42/finestra-undercut-non-funziona">FOR-42</issue> [ ] Correggi l'Ordine di pit dalla finestra di undercut

**Tipo**: bug (correzione).
**Dipendenze**: nessuna (la finestra di undercut e l'Ordine di pit esistono gia').
**Wave**: nuovo (correzione fuori dal piano di Wave).

**Scope**: l'Ordine di pit impartito dalla finestra di undercut (il pannello che si apre in Auto-pausa quando scatta una finestra di undercut che coinvolge un pilota del giocatore) deve far rientrare il pilota ai box per il cambio Mescola, esattamente come l'Ordine di pit dato dal flusso manuale. Oggi quel comando non ha effetto e il pilota resta in pista: la correzione chiude il buco tra la decisione presa nel pannello e l'esecuzione del pit nel motore.

**Scenario utente**:
Durante un GP un pilota del giocatore entra in una finestra di undercut: la simulazione va in Auto-pausa e si apre il pannello con la descrizione dell'evento, la scelta del pilota da richiamare e della Mescola. Il giocatore seleziona pilota e Mescola e conferma con "Ordina il pit". La gara riprende, ma il pilota non rientra: resta in pista come se nessun Ordine fosse stato dato. Se invece il giocatore impartisce lo stesso Ordine di pit dal flusso manuale a gara in corso (l'utente riferisce il tasto "o"), il pit viene eseguito e il pilota rientra. Atteso: l'Ordine confermato dalla finestra di undercut produce il rientro al Tick successivo, identico al flusso manuale.

**Deliverable verificabile**:

* Confermando "Ordina il pit" dalla finestra di undercut (Auto-pausa), il pilota selezionato rientra ai box e monta la Mescola scelta al pit successivo, verificabile in gara e via test.
* Esiste un test di regressione (pytest, motore headless o test TUI) che parte da una finestra di undercut su un pilota del giocatore, simula la conferma di un Ordine di pit dal pannello e verifica che il PitOrder risultante venga eseguito (il pilota cambia Mescola).
* Il flusso manuale dell'Ordine di pit continua a funzionare invariato (nessuna regressione).

**File da toccare**:

* `src/fm_tui/screens/race.py` (PitOrderPanel in Auto-pausa, callback on_close, coda `_pending_pits`, `_take_orders`)
* `tests/tui/test_race.py` (NEW test di regressione) oppure `tests/engine/...` a seconda di dove si riproduce il difetto

(stima, da rivedere in implementazione: la causa va confermata prima di scegliere il punto di intervento)

**Definition of Done**:

- [ ] Raggiungibile: la finestra di undercut si apre in Auto-pausa quando l'evento coinvolge un pilota del giocatore
- [ ] Popolata: il pannello mostra pilota coinvolto, Mescola e descrizione dell'evento
- [ ] Cliccabile: la conferma "Ordina il pit" da tastiera produce il rientro
- [ ] URL canonica: N/A (pannello modale dentro la schermata gara)
- [ ] Stati UI: nessun pilota del giocatore in pista (pannello non si apre), Ordine confermato, ripresa senza Ordini
- [ ] Aggiornata: l'Ordine confermato entra in coda e si applica al Tick successivo
- [ ] Compatibile wireframe: layout del pannello invariato

(la DoD si compila in chiusura del task)

**Cosa NON fare**:

* Niente refactor del rilevamento della finestra di undercut nel motore (`UndercutWindow` in `events.py`).
* Niente modifica al cooldown dell'Auto-pausa sull'undercut (<issue id="b4590e46-f1db-4294-9e23-53c9e8e91a8f" href="https://linear.app/haku-inc/issue/FOR-40/t324-tara-la-finestra-di-undercut-niente-auto-pausa-a-raffica">FOR-40</issue>).
* Niente modifica alla strategia di pit delle AI (<issue id="6a5084b8-c579-4982-9b96-6b8d473840f0" href="https://linear.app/haku-inc/issue/FOR-39/t253-porta-la-strategia-pit-delle-squadre-ai-nel-motore-di-gara">FOR-39</issue>).
* Niente nuove feature sul pannello: solo far funzionare l'Ordine gia' previsto.

**Note operative**:
Lead da verificare, non causa accertata: il pannello dell'Auto-pausa e il pannello manuale sono lo stesso `PitOrderPanel`; la differenza sta nel percorso `on_close` e nella coda `_pending_pits` quando l'apertura nasce da una finestra di undercut. Confermare se l'Ordine entra in coda e perche' non si traduce in PitOrder al Tick successivo, prima di scegliere il fix. Da chiarire in triage: il tasto del flusso manuale che "funziona" e' "o" (pannello Ordini pilota, che gestisce solo Aggressivita' e Istruzioni sui duelli) o "b" (Ordine di pit)? L'utente riferisce "o", ma l'Ordine di pit manuale e' sul tasto "b".

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>)
* `CONTEXT.md` (Ordine di pit, finestra di undercut, Auto-pausa, Mescola, Tick)
* `docs/adr/0002` (Textual come TUI con motore di gioco puro)
* `src/fm_tui/screens/race.py` (PitOrderPanel, `_open_pit_panel`, `_take_orders`)
* Issue correlate: <issue id="d68b9134-2f8f-4c3c-b71c-6318e11d4bb3" href="https://linear.app/haku-inc/issue/FOR-38/t323-implementa-finestra-di-undercut-come-evento-chiave">FOR-38</issue> (Auto-pausa sulla finestra di undercut), <issue id="6007b508-9796-4725-9374-9e6bb2d82267" href="https://linear.app/haku-inc/issue/FOR-18/t321-implementa-auto-pausa-e-ordine-pit">FOR-18</issue> (pannello Ordine di pit), <issue id="a75e7026-4c2a-421e-b168-b4ae6458b468" href="https://linear.app/haku-inc/issue/FOR-19/t322-implementa-ordini-pilota-aggressivita-scuderia-duelli">FOR-19</issue> (passaggio al pannello Ordini pilota), <issue id="b4590e46-f1db-4294-9e23-53c9e8e91a8f" href="https://linear.app/haku-inc/issue/FOR-40/t324-tara-la-finestra-di-undercut-niente-auto-pausa-a-raffica">FOR-40</issue> (cooldown undercut)

## Note
Origine: Linear FOR-42 (https://linear.app/haku-inc/issue/FOR-42/correggi-lordine-di-pit-dalla-finestra-di-undercut). Etichette Linear: si.
