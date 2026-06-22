---
id: t3-1-2-costruisci-schermata-gara-cronaca-e
titolo: "T3.1.2 Costruisci schermata gara: cronaca e monitor live"
stato: done
priorita: media
dipendenze: [t3-1-1-implementa-telecronaca-a-template]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-17
---

## Contesto
Importata da Linear FOR-17: progetto "Weekend interattivo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T3.1.2 [ ] Costruisci schermata gara: cronaca e monitor live

**Dipendenze**: T3.1.1.
**Wave**: 1.

**Scope**: schermata Textual della Gara interattiva: un RichLog mostra la Telecronaca in streaming mentre una DataTable presenta il monitor tempi live (posizione, pilota, distacco, Mescola, età gomme) aggiornato per cella; un worker asyncio avanza il motore Tick dopo Tick con velocità regolabile (1x/2x/4x/skip-to-event) e pausa/riprendi. È la finestra principale del giocatore sulla simulazione.

**Scenario utente**: il manager avvia la gara e atterra nella schermata gara: da un lato la Telecronaca scorre riga dopo riga, dall'altro il monitor con la Classifica tempi live mostra posizione, pilota, distacco, Mescola montata ed età gomme di ogni vettura. Dopo qualche giro preme il tasto velocità e passa a 4x: la cronaca accelera senza scatti e la tabella continua ad aggiornarsi. Al giro 30 mette pausa: la simulazione si congela e la tabella resta consultabile. Riprende a 1x, poi usa skip-to-event per saltare al prossimo accadimento rilevante. Alla bandiera a scacchi la Telecronaca annuncia il vincitore e la schermata mostra l'ordine d'arrivo. Edge case: se restano in pista pochissime vetture per gli Abbandoni, la gara prosegue e si chiude regolarmente.

**Deliverable verificabile**:

* Esiste la schermata `RaceScreen` (Textual) con cui una gara intera è guardabile dal via alla bandiera a scacchi senza freeze della UI, verificabile lanciando l'app.
* Il RichLog riceve la Telecronaca di T3.1.1 in streaming, riga per riga, in ordine di Tick.
* La DataTable dei tempi live mostra per ogni vettura posizione, pilota, distacco, Mescola ed età gomme; gli aggiornamenti avvengono per cella con throttling del refresh (nessun ridisegno completo a ogni Tick).
* Controlli funzionanti: velocità 1x/2x/4x, skip-to-event, pausa/riprendi; il worker asyncio che avanza il motore non blocca mai l'event loop di Textual.
* Test Pilot che avvia una gara breve, cambia velocità, mette pausa, riprende e verifica l'arrivo alla bandiera a scacchi con risultato visibile.

**File da toccare**:

* `src/formula_manager/tui/screens/race.py` (NEW)
* `src/formula_manager/tui/widgets/commentary_log.py` (NEW)
* `src/formula_manager/tui/widgets/live_timing_table.py` (NEW)
* `src/formula_manager/tui/workers/race_worker.py` (NEW)
* `tests/tui/test_race_screen.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: la schermata gara si apre dal flusso di avvio gara
- [ ] Popolata: cronaca e monitor tempi mostrano dati reali del motore, mai placeholder
- [ ] Cliccabile: velocità, pausa/riprendi e skip-to-event rispondono ai binding
- [ ] URL canonica: la schermata è registrata nell'app Textual con nome stabile (`race`)
- [ ] Stati UI: in corso (1x/2x/4x), pausa, skip-to-event, bandiera a scacchi con risultato
- [ ] Aggiornata: tabella e cronaca riflettono lo stato del motore a ogni Tick
- [ ] Compatibile wireframe (previsto [N/A]: nessun wireframe formale; layout cronaca+monitor come da PRD)

**Cosa NON fare**:

* Niente Ordini né pannelli decisione: Auto-pausa e ordine pit sono T3.2.1, gli altri Ordini T3.2.2.
* Niente Programmi di prove libere (T3.3.1) né macchina a stati del weekend (T3.3.2).
* Niente scritture su DB durante la gara: i Checkpoint restano fuori da questo task (ADR 0001).
* Niente modifica ai template di Telecronaca (T3.1.1): qui si consuma solo l'output.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 16, 26, 27).
* `CONTEXT.md` (Gara interattiva, Telecronaca, Tick, Mescola, Classifica tempi, Abbandono).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md`.
* T3.1.1 (Telecronaca a template, sorgente delle righe di cronaca).

## Note
Origine: Linear FOR-17 (https://linear.app/haku-inc/issue/FOR-17/t312-costruisci-schermata-gara-cronaca-e-monitor-live). Etichette Linear: si, ready-for-agent.
