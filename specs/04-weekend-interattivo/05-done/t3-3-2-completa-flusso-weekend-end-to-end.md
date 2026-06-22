---
id: t3-3-2-completa-flusso-weekend-end-to-end
titolo: "T3.3.2 Completa flusso weekend end-to-end"
stato: done
priorita: media
dipendenze: [t3-3-1-costruisci-prove-libere-con-programmi, t3-2-2-implementa-ordini-pilota-aggressivit]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-21
---

## Contesto
Importata da Linear FOR-21: progetto "Weekend interattivo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T3.3.2 [ ] Completa flusso weekend end-to-end

**Dipendenze**: T3.2.2, T3.3.1, T2.1.2, T1.2.2.
**Wave**: 3.

**Scope**: macchina a stati del weekend con Formato weekend Standard: FP1 → FP2 → FP3 → Qualifiche (Q1/Q2/Q3 con schermata tempi) → Gara → schermata risultato con punti; Checkpoint transazionale a fine di ogni sessione; il flag del Formato weekend è rispettato (solo Standard nel MVP). Chiude il loop: un Gran Premio intero giocabile e persistito.

**Scenario utente**: il manager inizia il GP dal venerdì e gioca FP1, FP2 e FP3 con i Programmi. Sabato le Qualifiche: la schermata tempi mostra Q1 con le 22 vetture e le 6 eliminate, poi Q2 con altre 6 eliminate, infine Q3 con la pole; la griglia di partenza è il risultato. Domenica la Gara interattiva con Auto-pausa e Ordini, poi la schermata risultato con l'ordine d'arrivo e i punti di piloti e costruttori. Chiude l'app dopo le qualifiche: alla riapertura la Carriera riprende dal Checkpoint, con la griglia salvata, e gioca direttamente la gara. Edge case: se la scrittura del Checkpoint fallisce, l'errore è mostrato e il salvataggio è ritentabile senza perdere la sessione appena conclusa.

**Deliverable verificabile**:

* Macchina a stati del weekend Standard nel motore che concatena FP1 → FP2 → FP3 → Q1/Q2/Q3 → Gara → risultato, senza salti né stati irraggiungibili (test unitari sul motore headless).
* Schermata Qualifiche con Classifica tempi per Q1 (22 vetture, 6 eliminate), Q2 (16 vetture, 6 eliminate), Q3 (10 vetture) e griglia di partenza risultante.
* Schermata risultato post-gara con ordine d'arrivo e punti piloti/costruttori assegnati.
* Checkpoint scritto su Supabase a fine di ogni sessione (e pre-gara, come da CONTEXT.md); chiusura e riapertura dell'app a metà weekend riprende dalla sessione giusta, verificabile con test su Postgres effimero Docker.
* Il Formato weekend è letto dal flag e nel MVP esiste solo Standard (test che rifiuta formati sconosciuti).
* Test Pilot end-to-end che gioca un weekend completo e verifica il risultato persistito.

**File da toccare**:

* `src/formula_manager/engine/weekend/state_machine.py` (NEW)
* `src/formula_manager/engine/weekend/qualifying.py` (NEW)
* `src/formula_manager/tui/screens/weekend.py` (NEW)
* `src/formula_manager/tui/screens/qualifying.py` (NEW)
* `src/formula_manager/tui/screens/race_result.py` (NEW)
* `src/formula_manager/persistence/checkpoints.py`
* `tests/engine/test_weekend_state_machine.py` (NEW)
* `tests/persistence/test_weekend_checkpoints.py` (NEW)
* `tests/tui/test_weekend_e2e.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il weekend si avvia dalla Carriera e ogni sessione è raggiungibile in sequenza
- [ ] Popolata: schermate qualifiche e risultato con dati reali del motore (tempi, eliminazioni, punti)
- [ ] Cliccabile: avanzamento tra le sessioni e conferme da tastiera in ogni passaggio
- [ ] URL canonica: ogni schermata del weekend è registrata nell'app Textual con nome stabile
- [ ] Stati UI: sessione in corso, fine sessione con Checkpoint, errore di salvataggio ritentabile, ripresa da metà weekend
- [ ] Aggiornata: alla riapertura dell'app lo stato riflette l'ultimo Checkpoint scritto
- [ ] Compatibile wireframe (previsto [N/A]: nessun wireframe formale; flusso come da PRD)

**Cosa NON fare**:

* Niente weekend Sprint (post-MVP: il modello prevede solo il flag del Formato weekend).
* Niente avanzamento calendario tra un GP e l'altro (T5.1.1).
* Niente economia post-GP (Premi gara, Danni in Cassa/Cap) oltre all'assegnazione dei punti.
* Niente scritture su DB durante le sessioni: solo a Checkpoint (ADR 0001).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 14, 16, 25, 44).
* `CONTEXT.md` (Formato weekend, Qualifiche, Checkpoint, Carriera, Classifica tempi).
* `docs/adr/0001-supabase-self-hosted-su-vps-con-salvataggi-a-checkpoint.md`.
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* T2.1.2 e T1.2.2 (motore e persistenza su cui poggia il flusso), T3.2.2 (gara completa con Ordini), T3.3.1 (prove libere).

## Note
Origine: Linear FOR-21 (https://linear.app/haku-inc/issue/FOR-21/t332-completa-flusso-weekend-end-to-end). Etichette Linear: si, ready-for-agent.
Dipendenze cross-progetto su Linear (non risolte come slug locali): t1-2-2-implementa-persistenza-a-checkpoint (FOR-5), t2-1-2-implementa-qualifiche-q1-q2-q3 (FOR-9).
