---
id: t2-3-2-implementa-meteo-e-crossover
titolo: "T2.3.2 Implementa meteo e Crossover"
stato: done
priorita: media
dipendenze: [t2-2-1-implementa-mescole-degrado-e-pit-stop, t2-2-2-implementa-sfiga-guasti-errori-incidenti]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-13
---

## Contesto
Importata da Linear FOR-13: progetto "Motore di gara", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T2.3.2 [ ] Implementa meteo e Crossover

**Dipendenze**: T2.2.1, T2.2.2.

**Wave**: 3.

**Scope**: introdurre il meteo nel motore: previsione probabilistica per sessione dal profilo meteo del circuito, evoluzione della pioggia in-sessione (arrivo, intensità, cessazione), prestazioni per tipo gomma in funzione delle condizioni con punto di Crossover, attivazione dell'attributo pilota Bagnato sul passo, Errori amplificati su pista bagnata. Gli eventi pioggia e Crossover sono marcati come Evento chiave per l'Auto-pausa.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Lo scenario è coperto dalle issue del progetto Weekend interattivo, dove pioggia in arrivo e Crossover scattano l'Auto-pausa per la decisione gomme.

**Deliverable verificabile**:

* Esiste una previsione probabilistica per sessione generata dal profilo meteo del circuito (dai dati statici), deterministica a parità di seed.
* Lo stato pista evolve in-sessione: arrivo pioggia, variazione di intensità, cessazione e asciugatura progressiva, con eventi tipizzati.
* I tipi Intermedia e Bagnato predisposti da T2.2.1 sono attivi: ogni tipo gomma ha una prestazione funzione delle condizioni, con punto di Crossover emergente; slick su pista bagnata significa lentezza più rischio Errore amplificato (test che lo dimostra dai tempi e dalle estrazioni).
* L'attributo pilota Bagnato agisce sul passo in condizioni di pioggia: su N gare bagnate gli specialisti del Bagnato sono visibili nei risultati (test statistico).
* Gli Errori (estrazione di T2.2.2) sono amplificati su pista bagnata, ulteriormente con gomma sbagliata (test comparativo).
* Gli eventi pioggia e Crossover sono tipizzati e marcati come Evento chiave con flag per l'Auto-pausa.
* Test pytest sulle transizioni asciutto → bagnato → asciutto, incluse soste per Crossover che emergono nelle simulazioni.

**File da toccare**:

* `src/engine/weather.py` (NEW)
* `src/engine/tyres.py`
* `src/engine/laptime.py`
* `src/engine/misfortune.py`
* `src/engine/race.py`
* `src/engine/state.py`
* `src/engine/events.py`
* `tests/engine/test_weather.py` (NEW)
* `tests/engine/test_crossover.py` (NEW)
* `tests/engine/test_wet_specialists.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il modulo meteo è importabile dal pacchetto motore senza dipendenze TUI/DB
- [ ] Popolata: lo stato di sessione espone previsione, condizioni pista correnti e tipo gomma per vettura
- [ ] Cliccabile: (previsto [N/A]: task puro-motore, nessun elemento interattivo)
- [ ] URL canonica: (previsto [N/A]: nessuna route; il path canonico del modulo è `src/engine/weather.py`)
- [ ] Stati UI: (previsto [N/A]: nessuna UI; gli stati osservabili sono gli eventi tipizzati con flag Evento chiave)
- [ ] Aggiornata: le condizioni pista sono ricalcolate a ogni Tick, prestazione gomme coerente con le condizioni correnti
- [ ] Compatibile wireframe: (previsto [N/A]: task puro-motore, nessuna schermata)

**Cosa NON fare**:

* Niente radar meteo grafico né UI: solo eventi e stato (progetto Weekend interattivo).
* Niente bandiere rosse per pioggia estrema (fuori MVP).
* Niente modifica alle curve di Degrado da asciutto di T2.2.1 oltre all'innesto dei tipi Intermedia/Bagnato.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 12 (lato motore), 23.
* `CONTEXT.md` (Crossover, Mescola, Bagnato, Errore, Evento chiave, Auto-pausa).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md`.
* T2.2.1 (tipi Intermedia/Bagnato predisposti), T2.2.2 (estrazione Errori da amplificare).

## Note
Origine: Linear FOR-13 (https://linear.app/haku-inc/issue/FOR-13/t232-implementa-meteo-e-crossover). Etichette Linear: si, ready-for-agent.
