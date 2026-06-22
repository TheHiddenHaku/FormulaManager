---
id: t2-4-1-costruisci-harness-di-bilanciamento
titolo: "T2.4.1 Costruisci harness di bilanciamento"
stato: done
priorita: media
dipendenze: [t2-2-1-implementa-mescole-degrado-e-pit-stop, t2-2-2-implementa-sfiga-guasti-errori-incidenti, t2-3-2-implementa-meteo-e-crossover, t2-1-1-implementa-modello-passo-e-gara-base, t2-3-1-implementa-safety-car-e-vsc, t2-1-2-implementa-qualifiche-q1-q2-q3]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-14
---

## Contesto
Importata da Linear FOR-14: progetto "Motore di gara", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T2.4.1 [ ] Costruisci harness di bilanciamento

**Dipendenze**: T2.1.1, T2.1.2, T2.2.1, T2.2.2, T2.3.1, T2.3.2.

**Wave**: 4.

**Scope**: costruire una CLI headless che simula N stagioni complete con seed e produce un report statistico del comportamento del motore (Abbandoni per gara, frequenza Safety car e pioggia, spread punti, correlazione attributi-risultati, distribuzione strategie), con asserzioni pytest sui range come test di sanità permanente. È la rete di sicurezza che impedisce al bilanciamento di degenerare in silenzio.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Lo scenario è coperto dalle issue del progetto Weekend interattivo, che beneficiano di un motore bilanciato; l'harness è uno strumento per sviluppatori.

**Deliverable verificabile**:

* Esiste un comando headless documentato (es. `python -m engine.balance --seasons N --seed S`) che simula N stagioni complete — Qualifiche e gare dei 24 GP del Calendario — senza import TUI né DB, eseguibile da terminale.
* Il comando produce un report statistico leggibile (stdout o file) con almeno: media Abbandoni per gara; frequenza SC/VSC e pioggia per circuito; spread punti tra prima e ultima squadra; correlazione Attributi (vettura e pilota) verso risultati; distribuzione delle strategie (numero soste, Mescole usate).
* A parità di seed il report è identico tra due run (test di determinismo end-to-end).
* Esiste una suite pytest di asserzioni sui range attesi (es. Abbandoni/gara in 3-5, SC più frequente a Monaco/Baku, correlazione attributi-risultati positiva, strategie 1-2 soste dominanti sull'asciutto) che fallisce se il bilanciamento degenera; eseguita come test di sanità permanente nella suite del progetto.
* L'uso del comando è documentato (README di progetto o docstring del modulo).

**File da toccare**:

* `src/engine/balance/` (NEW DIR)
* `src/engine/balance/__init__.py` (NEW)
* `src/engine/balance/__main__.py` (NEW)
* `src/engine/balance/simulate.py` (NEW)
* `src/engine/balance/report.py` (NEW)
* `tests/engine/test_balance_sanity.py` (NEW)
* `README.md`

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il comando è lanciabile da terminale sul repo senza setup oltre alle dipendenze Python
- [ ] Popolata: il report contiene tutte le metriche elencate nei deliverable per N stagioni
- [ ] Cliccabile: (previsto [N/A]: CLI headless per sviluppatori, nessun elemento interattivo)
- [ ] URL canonica: (previsto [N/A]: nessuna route; l'entry point canonico è `python -m engine.balance`)
- [ ] Stati UI: (previsto [N/A]: nessuna UI; output testuale del report)
- [ ] Aggiornata: ogni run risimula da zero con il seed dato, nessun risultato cachato
- [ ] Compatibile wireframe: (previsto [N/A]: strumento sviluppatore, nessuna schermata di gioco)

**Cosa NON fare**:

* Niente tuning automatico dei parametri di bilanciamento: l'harness misura, non corregge.
* Niente persistenza dei report su DB: nessuna scrittura Supabase, il motore resta puro (ADR 0001 non coinvolto).
* Niente UI Textual né integrazione con la Telecronaca.
* Niente nuove meccaniche di gioco: solo orchestrazione e misura di quelle esistenti.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — sezione Testing Decisions.
* `CONTEXT.md` (Abbandono, Safety car, Mescola, Attributo vettura, Attributo pilota, Calendario, Griglia).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* T2.1.1, T2.1.2, T2.2.1, T2.2.2, T2.3.1, T2.3.2 (tutti i moduli del motore misurati dall'harness).

## Note
Origine: Linear FOR-14 (https://linear.app/haku-inc/issue/FOR-14/t241-costruisci-harness-di-bilanciamento). Etichette Linear: si, ready-for-agent.
