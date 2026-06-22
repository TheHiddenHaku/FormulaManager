---
id: t2-2-1-implementa-mescole-degrado-e-pit-stop
titolo: "T2.2.1 Implementa Mescole, Degrado e pit stop"
stato: done
priorita: media
dipendenze: [t2-1-1-implementa-modello-passo-e-gara-base]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-10
---

## Contesto
Importata da Linear FOR-10: progetto "Motore di gara", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T2.2.1 [ ] Implementa Mescole, Degrado e pit stop

**Dipendenze**: T2.1.1.

**Wave**: 2.

**Scope**: introdurre nel motore il modello gomme: gamma stagionale C1-C5 con 3 Mescole nominate per GP (Soft/Medium/Hard relative, scelte dalla severità del circuito), offset di passo e curva di Degrado per Mescola modulati da Gestione gomme (vettura e pilota) e Aggressività, pit stop con tempo medio più varianza, obbligo bi-mescola in gara asciutta. L'undercut deve emergere dai distacchi, non da regole ad hoc.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Lo scenario è coperto dalle issue del progetto Weekend interattivo, dove il manager impartisce l'Ordine di pit stop con scelta Mescola.

**Deliverable verificabile**:

* Per ogni GP il motore nomina 3 Mescole da asciutto dalla gamma C1-C5 in base alla severità del circuito (dai dati statici), verificabile con test sui 24 GP del Calendario.
* Ogni Mescola ha un offset di passo e una curva di Degrado; il Degrado è monotono crescente coi giri e modulato da Gestione gomme (vettura e pilota) e Aggressività; test pytest su monotonia e ordinamento Soft più veloce ma più fragile.
* `step` accetta l'Ordine di pit stop con scelta Mescola; il pit costa tempo medio più varianza ed emette eventi tipizzati (ingresso box, cambio gomme, rientro).
* L'obbligo bi-mescola in gara asciutta è impossibile da violare o penalizzato (scelta documentata nel codice e coperta da test).
* Su simulazioni ripetute emergono strategie a 1-2 soste dalle sole curve di Degrado (test statistico su N gare).
* Test sull'undercut: a parità di passo, chi anticipa la sosta guadagna sul rivale rimasto fuori con gomme degradate; il vantaggio è misurabile dai distacchi.
* I tipi Intermedia e Bagnato esistono nel modello dati ma restano inattivi (li attiva T2.3.2).

**File da toccare**:

* `src/engine/tyres.py` (NEW)
* `src/engine/pitstop.py` (NEW)
* `src/engine/laptime.py`
* `src/engine/race.py`
* `src/engine/state.py`
* `src/engine/events.py`
* `tests/engine/test_tyres_degradation.py` (NEW)
* `tests/engine/test_pitstop_undercut.py` (NEW)
* `tests/engine/test_bimescola.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il modello gomme è importabile dal pacchetto motore senza dipendenze TUI/DB
- [ ] Popolata: lo stato di gara traccia per ogni vettura Mescola montata, età del set e Degrado corrente
- [ ] Cliccabile: (previsto [N/A]: task puro-motore, nessun elemento interattivo)
- [ ] URL canonica: (previsto [N/A]: nessuna route; il path canonico del modulo è `src/engine/tyres.py`)
- [ ] Stati UI: (previsto [N/A]: nessuna UI; gli stati osservabili sono gli eventi tipizzati di pit e gomme)
- [ ] Aggiornata: il Degrado è ricalcolato a ogni Tick, nessun valore stantio
- [ ] Compatibile wireframe: (previsto [N/A]: task puro-motore, nessuna schermata)

**Cosa NON fare**:

* Niente meteo né Crossover slick/Intermedia/Bagnato (T2.3.2): qui si predispone solo il modello dati.
* Niente gestione di set limitati per weekend (post-MVP).
* Niente sconto pit sotto Safety car o VSC (T2.3.1).
* Niente testo di Telecronaca né UI (ADR 0003, ADR 0002).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 11, 18 (lato motore).
* `CONTEXT.md` (Mescola, Degrado, Gestione gomme, Aggressività, Ordine, Tick).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md`.
* T2.1.1 (riduttore `step`, distacchi cumulati da cui emerge l'undercut).

## Note
Origine: Linear FOR-10 (https://linear.app/haku-inc/issue/FOR-10/t221-implementa-mescole-degrado-e-pit-stop). Etichette Linear: si, ready-for-agent.
