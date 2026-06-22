---
id: t2-5-2-rendi-realistici-i-tempi-sul-giro-per
titolo: "T2.5.2 Rendi realistici i tempi sul giro per circuito"
stato: done
priorita: media
dipendenze: []
etichette: [si]
creata: 2026-06-12
scadenza:
linear: FOR-37
---

## Contesto
Importata da Linear FOR-37: progetto "Motore di gara", stato Linear "Done", creata 2026-06-12.

## Obiettivo
### T2.5.2 [ ] Rendi realistici i tempi sul giro per circuito

**Dipendenze**: T2.1.1.

**Wave**: 1 (follow-up realismo; indipendente da T2.5.1).

**Scope**: sostituire la velocita' media di riferimento globale (`BASE_AVERAGE_SPEED_KMH = 205` in `src/fm_engine/laptime.py`) con un tempo base per circuito nei dati statici, cosi' che i tempi sul giro siano fisicamente plausibili. Oggi il motore produce 59.5s in qualifica a Monaco, dove il giro reale sta sopra il minuto e dieci: fisicamente impossibile. I distacchi relativi e il bilanciamento non dipendono dalla base additiva, quindi l'impatto sul gameplay e' nullo: e' credibilita' della simulazione.

**Scenario utente**: nessuno (task puro-motore, abilitatore). I tempi sono pero' mostrati al giocatore nella Classifica tempi (sempre esatti, CONTEXT.md) dal progetto Weekend interattivo: devono essere credibili prima che la Telecronaca li racconti.

**Contesto**: emerso dal collaudo manuale del batch T2.x (Q3 a Monaco con pole a 59.48s, seed 42). Il modello del tempo vive in `src/fm_engine/laptime.py`; i dati statici in `src/fm_engine/circuits.py` con mirror SQL in `supabase/seed.sql`.

**Deliverable verificabile**:

* La tabella SQL `circuits` e la dataclass `Circuit` hanno una colonna `base_lap_seconds` (numeric, CHECK > 0) valorizzata per i 24 circuiti con tempi di riferimento realistici della stagione base (Monaco ~74s, Monza ~85s, Spa ~107s, Jeddah ~91s, ...); i due mirror restano allineati.
* `laptime.base_lap_seconds` legge il valore dal circuito; la costante globale `BASE_AVERAGE_SPEED_KMH` sparisce dal modulo.
* Test pytest: per ogni circuito il tempo di pole simulato (vettura e pilota forti, seed fissi) cade in una finestra plausibile attorno al riferimento (es. -2s / +6s); Monaco mai sotto i 70 secondi.
* I test di sanita' dell'harness (T2.4.1) non cambiano esito: distacchi, DNF, correlazioni e strategie sono invariati per costruzione (la base e' additiva e uguale per tutte le vetture sullo stesso circuito).
* Determinismo invariato a parita' di seed.

**File da toccare**:

* `supabase/migrations/` (NEW: migrazione colonna base_lap_seconds)
* `supabase/seed.sql`
* `src/fm_engine/circuits.py`
* `src/fm_engine/laptime.py`
* `tests/engine/test_circuits.py`
* `tests/engine/test_lap_times_realism.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il tempo base e' letto dai dati statici importando il motore, senza dipendenze TUI/DB
- [ ] Popolata: tutti i 24 circuiti hanno base_lap_seconds valorizzata in entrambi i mirror
- [ ] Cliccabile: (previsto [N/A]: task puro-motore, nessun elemento interattivo)
- [ ] URL canonica: (previsto [N/A]: nessuna route; il path canonico resta `src/fm_engine/laptime.py`)
- [ ] Stati UI: (previsto [N/A]: nessuna UI; i tempi finiscono nella Classifica tempi via eventi e stato)
- [ ] Aggiornata: il tempo base entra nel calcolo di ogni Tick, nessun valore cacheato
- [ ] Compatibile wireframe: (previsto [N/A]: task puro-motore, nessuna schermata)

**Cosa NON fare**:

* Niente ritocchi al modello di prestazione (pesi attributi, varianza, quota vettura/pilota): cambia solo la base additiva.
* Niente settori o microtempi: il Tick resta il giro.
* Niente difficolta' di sorpasso: e' T2.5.1.

**Riferimenti**:

* `CONTEXT.md` (Classifica tempi, Tick).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* T2.1.1 (<issue id="516e2b13-c63d-4694-9785-3f343432b6ce" href="https://linear.app/haku-inc/issue/FOR-8/t211-implementa-modello-passo-e-gara-base">FOR-8</issue>, modello del tempo sul giro), T2.4.1 (<issue id="79a770f8-d669-468a-9671-f86b4f32b1ca" href="https://linear.app/haku-inc/issue/FOR-14/t241-costruisci-harness-di-bilanciamento">FOR-14</issue>, sanita' che deve restare verde).
* Collaudo manuale che ha originato la issue: commento finale su <issue id="79a770f8-d669-468a-9671-f86b4f32b1ca" href="https://linear.app/haku-inc/issue/FOR-14/t241-costruisci-harness-di-bilanciamento">FOR-14</issue>.

## Note
Origine: Linear FOR-37 (https://linear.app/haku-inc/issue/FOR-37/t252-rendi-realistici-i-tempi-sul-giro-per-circuito). Etichette Linear: si.
