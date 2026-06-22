---
id: t2-1-2-implementa-qualifiche-q1-q2-q3
titolo: "T2.1.2 Implementa qualifiche Q1/Q2/Q3"
stato: done
priorita: media
dipendenze: [t2-1-1-implementa-modello-passo-e-gara-base]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-9
---

## Contesto
Importata da Linear FOR-9: progetto "Motore di gara", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T2.1.2 [ ] Implementa qualifiche Q1/Q2/Q3

**Dipendenze**: T2.1.1.

**Wave**: 1.

**Scope**: simulare la sessione di Qualifiche nel formato 2026 — Q1 (22 vetture, 6 eliminate), Q2 (16 vetture, 6 eliminate), Q3 (10 vetture per la pole) — con tempo del giro secco derivato dall'attributo Giro secco, dagli Attributi vettura e dalla varianza. Produce la Classifica tempi di sessione e la griglia di partenza consumata dalla gara.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Lo scenario è coperto dalle issue del progetto Weekend interattivo, che mostrano Qualifiche e Classifica tempi in Telecronaca.

**Deliverable verificabile**:

* Esiste nel pacchetto motore una simulazione di Qualifiche con formato 2026 esatto: Q1 22 → 16, Q2 16 → 10, Q3 assegna la pole; eliminazioni 6+6 verificate da pytest.
* Il tempo del giro secco è funzione dell'attributo pilota Giro secco, degli Attributi vettura pesati dal circuito e di una varianza; deterministico a parità di seed.
* Ogni segmento produce una Classifica tempi di sessione (tempi sempre esatti) ed eventi tipizzati (tempo segnato, eliminazione, pole), mai testo libero.
* L'output è una griglia di partenza nel formato consumato dallo stato di gara di T2.1.1, verificabile con un test di integrazione qualifiche → gara.
* Test pytest su eliminazioni, ordine di griglia (Q3 davanti, poi eliminati Q2 per tempo, poi eliminati Q1) e determinismo.

**File da toccare**:

* `src/engine/qualifying.py` (NEW)
* `src/engine/state.py`
* `src/engine/events.py`
* `tests/engine/test_qualifying.py` (NEW)
* `tests/engine/test_grid_to_race.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: l'API di Qualifiche è importabile dal pacchetto motore senza dipendenze TUI/DB
- [ ] Popolata: la sessione produce Classifica tempi completa per Q1/Q2/Q3 e griglia a 22 posizioni
- [ ] Cliccabile: (previsto [N/A]: task puro-motore, nessun elemento interattivo)
- [ ] URL canonica: (previsto [N/A]: nessuna route; il path canonico del modulo è `src/engine/qualifying.py`)
- [ ] Stati UI: (previsto [N/A]: nessuna UI; gli stati osservabili sono gli eventi tipizzati)
- [ ] Aggiornata: la Classifica tempi riflette sempre l'ultimo giro completato nel segmento, nessuna cache
- [ ] Compatibile wireframe: (previsto [N/A]: task puro-motore, nessuna schermata)

**Cosa NON fare**:

* Niente Mescole dedicate alla qualifica né consumo set gomme (T2.2.1 / post-MVP).
* Niente meteo in qualifica (T2.3.2).
* Niente formato Sprint (post-MVP).
* Niente testo di Telecronaca né UI (ADR 0003, ADR 0002).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 14, 15.
* `CONTEXT.md` (Qualifiche, Giro secco, Classifica tempi, Formato weekend).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md`.
* T2.1.1 (modello passo e stato di gara che consuma la griglia).

## Note
Origine: Linear FOR-9 (https://linear.app/haku-inc/issue/FOR-9/t212-implementa-qualifiche-q1q2q3). Etichette Linear: si, ready-for-agent.
