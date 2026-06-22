---
id: t3-3-1-costruisci-prove-libere-con-programmi
titolo: "T3.3.1 Costruisci prove libere con Programmi"
stato: done
priorita: media
dipendenze: [t3-1-2-costruisci-schermata-gara-cronaca-e]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-20
---

## Contesto
Importata da Linear FOR-20: progetto "Weekend interattivo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T3.3.1 [ ] Costruisci prove libere con Programmi

**Dipendenze**: T3.1.2.
**Wave**: 3.

**Scope**: schermata delle prove libere: per ogni sessione il manager assegna a ciascun pilota uno slot con scelta del Programma (Setup, Gomme, Focus qualifica, Passo gara, Strategia); scheda circuito con caratteristiche, Mescole nominate e previsione meteo; report di fine sessione con gli effetti ottenuti (percentuale di setup, curve di Degrado rivelate, bonus) e Classifica tempi della sessione.

**Scenario utente**: venerdì, FP1. Il manager apre la schermata libere: in alto la scheda circuito con le caratteristiche della pista, le 3 Mescole nominate del GP e la previsione meteo del weekend. Assegna al primo pilota il Programma Setup e al secondo Gomme, poi lancia la sessione. A fine sessione il report mostra la percentuale di setup raggiunta, le curve di Degrado rivelate per le Mescole provate e i bonus validi per il weekend; sotto, la Classifica tempi della sessione con i tempi esatti di tutti. In FP2 cambia i Programmi e vede gli effetti cumularsi. Edge case: se lancia la sessione senza assegnare un Programma a un pilota, la schermata chiede conferma e applica un Programma di default, segnalandolo nel report.

**Deliverable verificabile**:

* Schermata libere con uno slot per pilota per sessione e scelta tra i 5 Programmi (Setup, Gomme, Focus qualifica, Passo gara, Strategia).
* Scheda circuito visibile in schermata: caratteristiche, Mescole nominate del GP, previsione meteo.
* Gli effetti dei Programmi sono misurabili nel weekend: la percentuale di setup incide sulla prestazione, le curve di Degrado rivelate arricchiscono le informazioni mostrate, i bonus si applicano alle sessioni successive; verificato da test sul motore con seed fisso.
* Report di fine sessione leggibile con effetti ottenuti e Classifica tempi della sessione.
* Test sui bonus applicati e test Pilot sul flusso assegna Programma → sessione → report.

**File da toccare**:

* `src/formula_manager/tui/screens/practice.py` (NEW)
* `src/formula_manager/tui/widgets/circuit_card.py` (NEW)
* `src/formula_manager/tui/widgets/session_report.py` (NEW)
* `src/formula_manager/engine/weekend/practice.py` (NEW)
* `tests/engine/test_practice_programs.py` (NEW)
* `tests/tui/test_practice_screen.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: la schermata libere si apre per ogni sessione di prove del weekend
- [ ] Popolata: scheda circuito, slot Programmi, report e Classifica tempi con dati reali del motore
- [ ] Cliccabile: scelta del Programma per pilota e lancio sessione da tastiera
- [ ] URL canonica: la schermata è registrata nell'app Textual con nome stabile (`practice`)
- [ ] Stati UI: assegnazione Programmi, sessione in corso, report fine sessione, conferma su slot vuoto
- [ ] Aggiornata: gli effetti dei Programmi si riflettono nelle sessioni successive del weekend
- [ ] Compatibile wireframe (previsto [N/A]: nessun wireframe formale; layout come da PRD)

**Cosa NON fare**:

* Niente minigioco di setup iterativo (escluso per decisione presa nel grill).
* Niente Tempi sporchi dei rivali (T5.1.2).
* Niente Qualifiche, gara o macchina a stati del weekend (T3.3.2).
* Niente Programmi dei Test pre-season (flusso distinto, fuori scope).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 10, 11, 13).
* `CONTEXT.md` (Programma, Mescola, Degrado, Stima, Classifica tempi, Formato weekend).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* T3.1.2 (pattern schermata + worker che avanza il motore).

## Note
Origine: Linear FOR-20 (https://linear.app/haku-inc/issue/FOR-20/t331-costruisci-prove-libere-con-programmi). Etichette Linear: si, ready-for-agent.
