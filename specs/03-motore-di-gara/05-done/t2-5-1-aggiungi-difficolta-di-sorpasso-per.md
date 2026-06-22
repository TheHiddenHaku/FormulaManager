---
id: t2-5-1-aggiungi-difficolta-di-sorpasso-per
titolo: "T2.5.1 Aggiungi difficolta' di sorpasso per circuito"
stato: done
priorita: media
dipendenze: []
etichette: [si]
creata: 2026-06-12
scadenza:
linear: FOR-36
---

## Contesto
Importata da Linear FOR-36: progetto "Motore di gara", stato Linear "Done", creata 2026-06-12.

## Obiettivo
### T2.5.1 [ ] Aggiungi difficolta' di sorpasso per circuito

**Dipendenze**: T2.1.1, T2.4.1.

**Wave**: 1 (follow-up realismo; indipendente da T2.5.2).

**Scope**: dare a ogni circuito un peso di difficolta' di sorpasso (scala 1-5: Monza facile, Monaco quasi impossibile) che modula la risoluzione dei duelli, e smorzare il ping-pong tra vetture di passo simile con una isteresi (chi viene sorpassato non ritenta il giro dopo a parita' di condizioni). Oggi Monaco produce ~130 sorpassi a gara come un circuito qualsiasi: la posizione in pista vale troppo poco e la qualifica non pesa.

**Scenario utente**: nessuno (task puro-motore, abilitatore). L'effetto visibile arriva con la Telecronaca e la schermata gara del progetto Weekend interattivo: a Monaco il treno di vetture resta treno, e la pole vale una gara.

**Contesto**: emerso dal collaudo manuale del batch T2.x (gara a Monaco, seed 42: ~130 sorpassi in 78 giri, vincitore partito decimo senza difficolta'; ping-pong visibile ai giri 26-28 tra coppie di vetture di passo identico). Il modello duelli vive in `src/fm_engine/race.py` (`_resolve_duels`, `_duel_success_probability`); i dati statici in `src/fm_engine/circuits.py` con mirror SQL in `supabase/seed.sql`.

**Deliverable verificabile**:

* La tabella SQL `circuits` e la dataclass `Circuit` hanno una colonna `overtaking_difficulty` (smallint 1-5, CHECK) valorizzata per tutti i 24 circuiti del Calendario, con Monaco al massimo e Monza/Spa/Jeddah bassi; i due mirror (Python e seed.sql) restano allineati, verificabile dai test sui dati statici.
* La probabilita' di successo del sorpasso e' modulata dalla difficolta' del circuito: a Monaco un attacco a parita' di passo e' raro; test comparativo a parita' di seed tra circuito facile e difficile.
* Isteresi nei duelli: due vetture con passo quasi identico non si scambiano la posizione a giri alterni; test che misura gli scambi ripetuti tra la stessa coppia.
* L'harness di bilanciamento (T2.4.1) riporta i sorpassi medi per gara per circuito; test di sanita' permanente: sorpassi a Monaco molto sotto la media del Calendario, Monza sopra.
* Su gare simulate a Monaco la correlazione tra posizione di partenza e posizione finale cresce rispetto a oggi (la qualifica conta), verificabile con test statistico.
* Determinismo invariato: stesso seed, stessa gara (i test di determinismo esistenti restano verdi).

**File da toccare**:

* `supabase/migrations/` (NEW: migrazione colonna overtaking_difficulty)
* `supabase/seed.sql`
* `src/fm_engine/circuits.py`
* `src/fm_engine/race.py`
* `src/fm_engine/balance/simulate.py`
* `src/fm_engine/balance/report.py`
* `tests/engine/test_race_base.py`
* `tests/engine/test_balance_sanity.py`
* `tests/engine/test_circuits.py`
* `tests/engine/test_overtaking_difficulty.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: la modulazione e' attiva importando il motore, senza dipendenze TUI/DB
- [ ] Popolata: tutti i 24 circuiti hanno overtaking_difficulty valorizzata in entrambi i mirror
- [ ] Cliccabile: (previsto [N/A]: task puro-motore, nessun elemento interattivo)
- [ ] URL canonica: (previsto [N/A]: nessuna route; il path canonico resta `src/fm_engine/race.py`)
- [ ] Stati UI: (previsto [N/A]: nessuna UI; gli stati osservabili sono gli eventi tipizzati)
- [ ] Aggiornata: la difficolta' agisce a ogni Tick sulla risoluzione duelli corrente
- [ ] Compatibile wireframe: (previsto [N/A]: task puro-motore, nessuna schermata)

**Cosa NON fare**:

* Niente DRS o meccaniche nuove: solo modulazione dei duelli esistenti.
* Niente ritocchi alle altre probabilita' (Sfiga, trigger SC/VSC) in questa issue.
* Niente tempi sul giro: e' T2.5.2.

**Riferimenti**:

* `CONTEXT.md` (Duelli, Tick, Ordine, Qualifiche).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* T2.1.1 (<issue id="516e2b13-c63d-4694-9785-3f343432b6ce" href="https://linear.app/haku-inc/issue/FOR-8/t211-implementa-modello-passo-e-gara-base">FOR-8</issue>, modello duelli), T2.4.1 (<issue id="79a770f8-d669-468a-9671-f86b4f32b1ca" href="https://linear.app/haku-inc/issue/FOR-14/t241-costruisci-harness-di-bilanciamento">FOR-14</issue>, harness che misura).
* Collaudo manuale che ha originato la issue: commento finale su <issue id="79a770f8-d669-468a-9671-f86b4f32b1ca" href="https://linear.app/haku-inc/issue/FOR-14/t241-costruisci-harness-di-bilanciamento">FOR-14</issue>.

## Note
Origine: Linear FOR-36 (https://linear.app/haku-inc/issue/FOR-36/t251-aggiungi-difficolta-di-sorpasso-per-circuito). Etichette Linear: si.
