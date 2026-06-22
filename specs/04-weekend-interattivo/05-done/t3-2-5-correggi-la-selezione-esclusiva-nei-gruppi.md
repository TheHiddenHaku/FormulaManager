---
id: t3-2-5-correggi-la-selezione-esclusiva-nei-gruppi
titolo: "T3.2.5 Correggi la selezione esclusiva nei gruppi del pannello Ordini pilota"
stato: done
priorita: media
dipendenze: []
etichette: [si]
creata: 2026-06-12
scadenza:
linear: FOR-41
---

## Contesto
Importata da Linear FOR-41: progetto "Weekend interattivo", stato Linear "Done", creata 2026-06-12.

## Obiettivo
### T3.2.5 [ ] Correggi la selezione esclusiva nei gruppi del pannello Ordini pilota

**Dipendenze**: T3.2.2.
**Wave**: bugfix (emerso nel playtest del primo weekend giocato).

**Scope**: nel pannello Ordini pilota (`DriverOrdersPanel` in `src/fm_tui/screens/race.py`) puo' capitare che due RadioButton dello stesso gruppo risultino selezionati insieme: nel playtest, scegliendo Aggressivita' Push per un pilota, anche Normale restava marcato. Sospetto principale: `on_radio_set_changed` al cambio pilota ricarica gli Ordini correnti impostando `RadioButton.value = True` a livello programmatico (righe ~310-313); l'impostazione programmatica del value dentro un RadioSet di Textual non sgancia in modo affidabile il bottone gia' premuto (race tra il toggle del compose iniziale e quello del reload), lasciando due pallini accesi. Da riprodurre con un test Pilot e correggere con un meccanismo di selezione robusto (es. spegnere esplicitamente il bottone premuto prima di accendere il nuovo, o pilotare la selezione via RadioSet invece che sul singolo bottone).

**Scenario utente**: il manager apre il pannello Ordini, cambia pilota, sceglie Push: nel gruppo Aggressivita' risulta selezionato SOLO Push, e la conferma applica Push. Cambiando pilota avanti e indietro la selezione mostrata coincide sempre con lo stato reale degli Ordini del pilota visualizzato.

**Deliverable verificabile**:

* In ogni RadioSet del pannello (pilota, Aggressivita', Ordine di scuderia, Istruzione sui duelli) al massimo un bottone risulta premuto in qualsiasi momento, anche dopo cambi pilota ripetuti.
* `_decision()` ritorna sempre il valore effettivamente evidenziato dall'utente, mai quello vecchio.
* Test Pilot di regressione: apri pannello, cambia pilota, seleziona Push, verifica che Normale non sia premuto e che la conferma produca Push; ripeti col secondo pilota.
* Stessa verifica difensiva sul `PitOrderPanel` (usa lo stesso pattern con il preset della Mescola di default).

**Cosa NON fare**:

* Niente redesign del pannello: solo la correttezza della selezione.
* Niente upgrade di Textual se non indispensabile; se il fix richiede una versione nuova, segnalarlo prima.

**Riferimenti**:

* <issue id="a75e7026-4c2a-421e-b168-b4ae6458b468" href="https://linear.app/haku-inc/issue/FOR-19/t322-implementa-ordini-pilota-aggressivita-scuderia-duelli">FOR-19</issue> / T3.2.2 (pannello Ordini pilota).
* `src/fm_tui/screens/race.py` (`DriverOrdersPanel.on_radio_set_changed`, `_decision`).
* `tests/tui/test_race.py` (test Pilot esistenti del pannello).

## Note
Origine: Linear FOR-41 (https://linear.app/haku-inc/issue/FOR-41/t325-correggi-la-selezione-esclusiva-nei-gruppi-del-pannello-ordini). Etichette Linear: si.
