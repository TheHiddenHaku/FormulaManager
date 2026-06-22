---
id: t2-5-3-porta-la-strategia-pit-delle-squadre-ai
titolo: "T2.5.3 Porta la strategia pit delle squadre AI nel motore di gara"
stato: done
priorita: media
dipendenze: []
etichette: [si]
creata: 2026-06-12
scadenza:
linear: FOR-39
---

## Contesto
Importata da Linear FOR-39: progetto "Motore di gara", stato Linear "Done", creata 2026-06-12.

## Obiettivo
### T2.5.3 [ ] Porta la strategia pit delle squadre AI nel motore di gara

**Dipendenze**: T2.2.1, T3.1.2.
**Wave**: bugfix (emerso nel playtest del primo weekend giocato).

**Scope**: nella Gara interattiva le squadre AI non si fermano MAI ai box. La strategia pit (conteggio soste ottimale, piani per pilota, ordini di pit al giro giusto: `_planned_stop_count`, `_StrategyPlan`, `_lap_orders`) vive solo nell'harness di bilanciamento (`src/fm_engine/balance/simulate.py`) e la RaceScreen avanza `step()` passando solo gli ordini del giocatore. Risultato osservato nel playtest: a fine gara tutti i rivali hanno gomme con 58 giri di eta', subiscono in blocco la penalita' di 30 secondi per obbligo bi-mescola violato, e il giocatore che monta gomme fresche a 15 giri dalla fine rimonta da P17/P18 alla doppietta. Va estratta la strategia in un modulo del motore riusabile (es. `fm_engine/strategy.py`) consumato sia dall'harness sia dal flusso di gara interattiva.

**Scenario utente**: il manager guarda la gara: attorno al giro delle soste i rivali entrano ai box scaglionati, montano la seconda mescola e la Telecronaca racconta i pit; a bandiera nessuna pioggia di penalita' bi-mescola; una rimonta dalla coda con gomme fresche guadagna posizioni plausibili, non venti.

**Deliverable verificabile**:

* Modulo del motore (Python puro) che genera i piani strategici delle AI e gli ordini di pit per giro, estratto dall'harness senza duplicazione: l'harness lo importa da li'.
* La RaceScreen (e quindi il flusso weekend) inietta gli ordini AI a ogni Tick insieme a quelli del giocatore; i piloti del giocatore restano esclusi dai piani AI (decide il manager).
* In una gara interattiva completa le AI rispettano l'obbligo bi-mescola: zero penalita' da mancata seconda mescola in condizioni asciutte normali (test con seed fisso).
* I pit delle AI compaiono in Telecronaca e aggiornano il monitor (gia' garantito dagli eventi esistenti).
* Test motore con seed fisso sui piani generati e test Pilot che verifica almeno una sosta AI in una gara breve.
* L'harness di bilanciamento produce gli stessi risultati di prima a parita' di seed (o differenze giustificate dal refactor, da motivare).

**Cosa NON fare**:

* Niente strategia AI per i piloti del giocatore: la decisione resta al manager.
* Niente nuovi modelli di strategia (undercut AI, reazioni alla SC oltre quanto gia' fa l'harness): solo estrazione e cablaggio di cio' che esiste.
* Niente modifiche al regolamento bi-mescola.

**Riferimenti**:

* `src/fm_engine/balance/simulate.py` (la strategia da estrarre).
* `src/fm_tui/screens/race.py` (il loop che oggi passa solo gli ordini del giocatore).
* `CONTEXT.md` (Ordine, Mescola, Degrado).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.

## Note
Origine: Linear FOR-39 (https://linear.app/haku-inc/issue/FOR-39/t253-porta-la-strategia-pit-delle-squadre-ai-nel-motore-di-gara). Etichette Linear: si.
