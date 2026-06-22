---
id: t5-1-2-implementa-test-pre-season-e-stime
titolo: "T5.1.2 Implementa Test pre-season e Stime"
stato: done
priorita: media
dipendenze: [t5-1-1-implementa-calendario-e-classifiche]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-29
---

## Contesto
Importata da Linear FOR-29: progetto "Stagione e carriera", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T5.1.2 [ ] Implementa Test pre-season e Stime

**Dipendenze**: T5.1.1, T1.3.2, T2.1.1.
**Wave**: 2.

**Scope**: introdurre la fase Test pre-season a inizio stagione (~6 giorni) con un Programma per giorno e pilota (Sviluppo / Conoscenza / Affidabilità) e rendere attivo il sistema delle Stime ovunque (griglia, mercato): i Programmi di Conoscenza stringono le Stime sugli attributi propri, e i margini si stringono anche con prove libere e gare disputate.

**Scenario utente**:
A inizio stagione il giocatore entra nella fase Test pre-season. Per ciascuno dei ~6 giorni assegna un Programma a ogni pilota: dedica i primi due giorni alla Conoscenza, poi Sviluppo e Affidabilità. A fine giornata legge la Classifica tempi: i tempi sono esatti per tutti, ma il rivale più veloce gira con carburante e programma ignoti — un Tempo sporco da interpretare, non un verdetto. Aprendo la scheda della propria vettura vede le Stime con margini visibilmente più stretti dopo i giorni di Conoscenza. A fine fase legge il report pre-stagione e si fa un'idea di chi è davvero forte prima del primo GP. Edge case: se dedica 0 giorni alla Conoscenza, le Stime restano larghe e il report lo segnala esplicitamente.

**Deliverable verificabile**:

* Esiste la fase Test pre-season (~6 giorni) tra l'inizio stagione e il primo GP: per ogni giorno e pilota si assegna un Programma (Sviluppo / Conoscenza / Affidabilità), verificabile via schermata dedicata e test Pilot.
* I Programmi di Conoscenza stringono le Stime sugli attributi propri in modo misurabile (margine post < margine pre), verificabile via test pytest sul motore headless.
* La Classifica tempi dei test mostra tempi esatti di tutte le vetture, ma il contesto delle AI (carburante, programma) resta nascosto: Tempi sporchi, verificabile via schermata e test.
* Il sistema Stime è attivo ovunque (griglia, mercato) e i margini si stringono anche con prove libere e gare, verificabile via test di convergenza su più weekend simulati.
* Esiste il report finale pre-stagione navigabile da tastiera, verificabile via Pilot.
* Test pytest dedicati coprono la convergenza delle Stime (margine monotono non crescente, mai negativo, valore vero sempre dentro l'intervallo).

**File da toccare**:

* `engine/preseason/__init__.py` (NEW DIR)
* `engine/preseason/programs.py` (NEW)
* `engine/preseason/timesheets.py` (NEW)
* `engine/info/estimates.py` (NEW)
* `tui/screens/preseason.py` (NEW)
* `tui/screens/preseason_report.py` (NEW)
* `persistence/repositories/estimates.py` (NEW)
* `supabase/migrations/<timestamp>_preseason_estimates.sql` (NEW)
* `tests/engine/test_preseason_programs.py` (NEW)
* `tests/engine/test_estimates_convergence.py` (NEW)
* `tests/tui/test_preseason_screens.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: la fase Test pre-season si apre automaticamente a inizio stagione, prima del primo GP
- [ ] Popolata: ~6 giorni × 2 piloti con Programmi assegnabili; Classifica tempi completa di tutta la Griglia
- [ ] Cliccabile: assegnazione Programmi, lettura tempi e report interamente da tastiera
- [ ] URL canonica: schermate test e report con id/binding canonici nell'app Textual
- [ ] Stati UI: giorno non ancora assegnato, fase completata, caso "0 giorni di Conoscenza" con Stime larghe segnalate
- [ ] Aggiornata: Stime e Classifica tempi aggiornate a fine giornata; Checkpoint a fine fase
- [ ] Compatibile wireframe: layout coerente con le schermate TUI esistenti

**Cosa NON fare**:

* Niente Telecronaca live dei test: l'esito arriva come Classifica tempi e report (deciso nel grill).
* Niente modifiche ai Programmi delle prove libere (Setup, Gomme, Focus qualifica, Passo gara, Strategia): qui solo i Programmi dei test.
* Niente scouting o acquisto di informazioni sui rivali (post-MVP): le Stime si stringono solo giocando.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 7, 8, 9)
* `CONTEXT.md` (Test pre-season, Programma, Stima, Classifica tempi, Tempo sporco, Checkpoint)
* `docs/adr/0001` (persistenza: scritture solo a Checkpoint)
* `docs/adr/0002` (Textual + motore puro)
* `docs/adr/0003` (telecronaca a template: per i test si usa il report, non la telecronaca)
* Task a monte: T5.1.1, T1.3.2, T2.1.1

## Note
Origine: Linear FOR-29 (https://linear.app/haku-inc/issue/FOR-29/t512-implementa-test-pre-season-e-stime). Etichette Linear: si, ready-for-agent.
Dipendenze cross-progetto su Linear (non risolte come slug locali): t1-3-2-costruisci-wizard-setup-squadra (FOR-7), t2-1-1-implementa-modello-passo-e-gara-base (FOR-8).
