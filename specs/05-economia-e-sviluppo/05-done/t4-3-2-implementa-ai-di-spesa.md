---
id: t4-3-2-implementa-ai-di-spesa
titolo: "T4.3.2 Implementa AI di spesa"
stato: done
priorita: media
dipendenze: [t4-3-1-implementa-progetti-di-sviluppo]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-26
---

## Contesto
Importata da Linear FOR-26: progetto "Economia e sviluppo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T4.3.2 [ ] Implementa AI di spesa

**Dipendenze**: T4.3.1.

**Wave**: 3.

**Scope**: far vivere l'economia alle 10 squadre AI della Griglia: gestiscono Cassa, Cap e Progetti con le stesse regole del giocatore, guidate dalla personalità di spesa generata dal Mondo (aggressiva/conservativa, focus aero/motore/affidabilità); i Motoristi produttori sviluppano la Potenza motore condivisa con tutte le squadre Clienti.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Gli effetti si osservano nelle classifiche e nelle prestazioni delle squadre rivali; lo scenario è coperto da T4.3.1 (Progetti di sviluppo) e dalle schermate di classifica del progetto Weekend interattivo.

**Deliverable verificabile**:

* Esiste un modulo motore di decisione di spesa AI che usa esclusivamente le stesse API economiche e di Progetto del giocatore (registro di T4.1.1, Progetti di T4.3.1: stessi costi, stessi vincoli min(Cassa, Cap residuo), max 2 Progetti paralleli), senza import TUI/DB, verificabile via pytest headless.
* Le decisioni sono parametrizzate dalla personalità di spesa generata dal Mondo: profilo aggressivo/conservativo e focus aero/motore/affidabilità producono allocazioni distinguibili tra squadre, verificabile via pytest comparativo a parità di seed.
* I Motoristi produttori avviano sviluppi di Potenza motore i cui frutti si applicano alla Potenza condivisa con tutte le squadre Clienti, verificabile via pytest.
* Su una stagione simulata le AI spendono in modo differenziato e plausibile: nessuna AI resta a spesa zero, nessuna è costantemente al Cap, verificabile con asserzioni pytest sui range.
* L'harness di bilanciamento (T2.4.1) è esteso con metriche di spesa AI: spesa totale per squadra, distribuzione per Attributo vettura, numero di Progetti completati, eventuali Sforamenti; il report le include e le asserzioni di sanità le coprono.

**File da toccare**:

* `src/engine/ai/` (NEW DIR)
* `src/engine/ai/__init__.py` (NEW)
* `src/engine/ai/spending.py` (NEW)
* `src/engine/development/projects.py`
* `src/engine/balance/simulate.py`
* `src/engine/balance/report.py`
* `tests/engine/ai/test_spending.py` (NEW)
* `tests/engine/test_balance_sanity.py`

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: (previsto [N/A]: task puro-motore senza UI; il modulo è importabile dal pacchetto motore)
- [ ] Popolata: (previsto [N/A]: nessuna schermata; i dati osservabili sono le metriche di spesa nell'harness)
- [ ] Cliccabile: (previsto [N/A]: task puro-motore, nessun elemento interattivo)
- [ ] URL canonica: (previsto [N/A]: nessuna route; il path canonico del modulo è `src/engine/ai/spending.py`)
- [ ] Stati UI: (previsto [N/A]: nessuna UI; gli stati osservabili sono le decisioni di spesa tipizzate)
- [ ] Aggiornata: le decisioni AI avanzano con il calendario di gioco tra un GP e l'altro senza intervento del giocatore
- [ ] Compatibile wireframe: (previsto [N/A]: task puro-motore, nessuna schermata)

**Cosa NON fare**:

* Niente cheating: le AI non vedono i numeri veri del giocatore (solo Classifica tempi e informazioni pubbliche) né godono di sconti su costi, vincoli o regole.
* Niente regole economiche speciali: stessi vincoli del giocatore, inclusi Misura d'emergenza e Sforamento.
* Niente UI dedicata alla spesa AI.
* Niente tuning automatico del bilanciamento: l'harness misura, non corregge (come da T2.4.1).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 36.
* `CONTEXT.md` § Economia (Cassa, Cap, Progetto, Motorista, Cliente, Griglia) e § Informazione (Classifica tempi).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* T4.3.1 (<issue id="ff7559c5-d130-4a0e-8001-250e78f21f34" href="https://linear.app/haku-inc/issue/FOR-25/t431-implementa-progetti-di-sviluppo">FOR-25</issue>, Progetti di sviluppo: API riusata dalle AI), T2.4.1 (<issue id="79a770f8-d669-468a-9671-f86b4f32b1ca" href="https://linear.app/haku-inc/issue/FOR-14/t241-costruisci-harness-di-bilanciamento">FOR-14</issue>, harness di bilanciamento da estendere).

## Note
Origine: Linear FOR-26 (https://linear.app/haku-inc/issue/FOR-26/t432-implementa-ai-di-spesa). Etichette Linear: si, ready-for-agent.
