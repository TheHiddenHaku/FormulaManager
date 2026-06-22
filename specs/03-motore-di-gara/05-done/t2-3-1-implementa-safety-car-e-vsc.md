---
id: t2-3-1-implementa-safety-car-e-vsc
titolo: "T2.3.1 Implementa Safety car e VSC"
stato: done
priorita: media
dipendenze: [t2-2-2-implementa-sfiga-guasti-errori-incidenti]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-12
---

## Contesto
Importata da Linear FOR-12: progetto "Motore di gara", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T2.3.1 [ ] Implementa Safety car e VSC

**Dipendenze**: T2.2.2.

**Wave**: 3.

**Scope**: aggiungere le neutralizzazioni di gara: trigger di Safety car e VSC dalla gravità dell'Incidente con probabilità per circuito (dal seed dei dati statici); la Safety car compatta il gruppo e sconta il pit stop, il VSC congela i distacchi e sconta meno; durata variabile e ripartenza con rischio duelli aumentato. Gli eventi sono marcati come Evento chiave per l'Auto-pausa del progetto Weekend interattivo.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Lo scenario è coperto dalle issue del progetto Weekend interattivo, dove la Safety car scatta l'Auto-pausa e il manager decide se rientrare ai box.

**Deliverable verificabile**:

* Il trigger SC/VSC dipende dalla gravità dell'Incidente (da T2.2.2) e dalla probabilità per circuito letta dai dati statici; su N gare simulate la distribuzione delle SC per circuito è coerente col profilo: Monaco e Baku alte (test statistico).
* Sotto Safety car il gruppo si compatta (distacchi azzerati dietro la SC) e il pit stop costa meno; sotto VSC i distacchi sono congelati e lo sconto pit è minore; comportamenti distinti coperti da test.
* La durata della neutralizzazione è variabile e deterministica a parità di seed.
* Alla ripartenza il rischio di Errori e Incidenti in duello è aumentato per una finestra di giri (test comparativo).
* Il vantaggio del pit sotto SC rispetto al regime verde è misurabile dai distacchi (test dedicato).
* Gli eventi SC/VSC (ingresso, ripartenza) sono tipizzati e marcati come Evento chiave, con flag consumabile dall'Auto-pausa del progetto Weekend interattivo.
* Test deterministici: stesso seed, stessa sequenza di neutralizzazioni.

**File da toccare**:

* `src/engine/neutralization.py` (NEW)
* `src/engine/race.py`
* `src/engine/pitstop.py`
* `src/engine/state.py`
* `src/engine/events.py`
* `tests/engine/test_safety_car.py` (NEW)
* `tests/engine/test_vsc.py` (NEW)
* `tests/engine/test_sc_distribution.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il modulo neutralizzazioni è importabile dal pacchetto motore senza dipendenze TUI/DB
- [ ] Popolata: lo stato di gara espone regime corrente (verde/SC/VSC), durata residua e distacchi coerenti
- [ ] Cliccabile: (previsto [N/A]: task puro-motore, nessun elemento interattivo)
- [ ] URL canonica: (previsto [N/A]: nessuna route; il path canonico del modulo è `src/engine/neutralization.py`)
- [ ] Stati UI: (previsto [N/A]: nessuna UI; gli stati osservabili sono gli eventi tipizzati con flag Evento chiave)
- [ ] Aggiornata: il regime di gara è aggiornato a ogni Tick, distacchi coerenti col regime in corso
- [ ] Compatibile wireframe: (previsto [N/A]: task puro-motore, nessuna schermata)

**Cosa NON fare**:

* Niente bandiere rosse (fuori MVP).
* Niente UI né implementazione dell'Auto-pausa: solo il flag Evento chiave negli eventi (progetto Weekend interattivo).
* Niente modifiche all'estrazione di Guasti/Errori/Incidenti di T2.2.2 oltre all'aggancio del trigger e al moltiplicatore di ripartenza.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 17 (lato motore), 22.
* `CONTEXT.md` (Safety car, VSC, Evento chiave, Auto-pausa, Incidente, Tick).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md`.
* T2.2.2 (gravità Incidente che alimenta il trigger).

## Note
Origine: Linear FOR-12 (https://linear.app/haku-inc/issue/FOR-12/t231-implementa-safety-car-e-vsc). Etichette Linear: si, ready-for-agent.
