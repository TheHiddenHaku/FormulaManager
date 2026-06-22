---
id: t2-1-1-implementa-modello-passo-e-gara-base
titolo: "T2.1.1 Implementa modello passo e gara base"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-8
---

## Contesto
Importata da Linear FOR-8: progetto "Motore di gara", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T2.1.1 [ ] Implementa modello passo e gara base

**Dipendenze**: T1.2.1.

**Wave**: 1.

**Scope**: costruire il cuore del motore di gara come riduttore puro `step(stato, ordini) -> (stato', eventi)` con Tick = giro: gara asciutta senza pit stop, tempo sul giro derivato dagli Attributi vettura pesati dal circuito più Attributi pilota più varianza, sorpassi e duelli, distacchi cumulati, classifica finale con punti 2026. È la fondazione su cui si innestano gomme, Sfiga, neutralizzazioni e meteo.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Lo scenario è coperto dalle issue del progetto Weekend interattivo, che consumano gli eventi tipizzati per Telecronaca e schermata di gara.

**Deliverable verificabile**:

* Esiste la funzione pura `step(stato, ordini) -> (stato', eventi)` nel pacchetto motore, senza import TUI/DB, con Tick = giro: sorpassi e duelli si risolvono dentro al giro. Verificabile via import headless e pytest.
* Una gara completa a 22 vetture è deterministica a parità di seed: due run con stesso seed e stessi ordini producono stati ed eventi identici (test di determinismo).
* Il tempo sul giro è funzione degli Attributi vettura pesati dal profilo circuito (dai dati statici), degli Attributi pilota (Passo gara in primis) e di una varianza stocastica.
* Sorpassi e duelli usano l'attributo Duelli; la firma di `step` accetta già gli Ordini previsti dal MVP — Aggressività, Ordine di scuderia, Istruzione sui duelli — con effetti cablati sul comportamento in duello e sul passo.
* I distacchi cumulati per giro sono tracciati nello stato; a bandiera a scacchi viene prodotta la classifica finale con punti 2026: 25-18-15-12-10-8-6-4-2-1, nessun punto per il giro veloce.
* Gli eventi sono tipizzati e serializzabili (sorpasso, giro veloce, bandiera a scacchi, ...): dataclass/enum con payload strutturato, mai testo libero (ADR 0003).
* Unit test pytest su classifica e attribuzione punti; smoke test che simula 1000 gare senza errori.

**File da toccare**:

* `src/engine/` (NEW DIR)
* `src/engine/__init__.py` (NEW)
* `src/engine/state.py` (NEW)
* `src/engine/events.py` (NEW)
* `src/engine/laptime.py` (NEW)
* `src/engine/race.py` (NEW)
* `src/engine/points.py` (NEW)
* `tests/engine/` (NEW DIR)
* `tests/engine/test_race_base.py` (NEW)
* `tests/engine/test_determinism.py` (NEW)
* `tests/engine/test_points.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: l'API `step` è importabile dal pacchetto motore senza dipendenze TUI/DB
- [ ] Popolata: lo stato di gara contiene 22 vetture con distacchi, posizioni ed eventi per ogni Tick
- [ ] Cliccabile: (previsto [N/A]: task puro-motore, nessun elemento interattivo)
- [ ] URL canonica: (previsto [N/A]: nessuna route; il path canonico del modulo è `src/engine/race.py`)
- [ ] Stati UI: (previsto [N/A]: nessuna UI; gli stati osservabili sono gli eventi tipizzati)
- [ ] Aggiornata: lo stato restituito da `step` riflette sempre l'ultimo Tick simulato, nessuna cache nascosta
- [ ] Compatibile wireframe: (previsto [N/A]: task puro-motore, nessuna schermata)

**Cosa NON fare**:

* Niente Mescole, Degrado o pit stop (T2.2.1).
* Niente Guasti, Errori, Incidenti o Abbandoni (T2.2.2).
* Niente testo di Telecronaca: il motore emette solo eventi tipizzati (ADR 0003).
* Niente import Textual o psycopg nel pacchetto motore (ADR 0002).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 16 (base), 25.
* `CONTEXT.md` (Tick, Ordine, Aggressività, Ordine di scuderia, Istruzione sui duelli, Attributo vettura, Attributo pilota).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md`.
* T1.2.1 (<issue id="65439eab-9551-410e-af4f-df9810144497" href="https://linear.app/haku-inc/issue/FOR-4/t121-implementa-modulo-mondo-generazione-griglia">FOR-4</issue>): dati statici di Griglia e Calendario consumati dal motore.

## Note
Origine: Linear FOR-8 (https://linear.app/haku-inc/issue/FOR-8/t211-implementa-modello-passo-e-gara-base). Etichette Linear: si, ready-for-agent.
Dipendenze cross-progetto su Linear (non risolte come slug locali): t1-2-1-implementa-modulo-mondo-generazione-griglia (FOR-4).
