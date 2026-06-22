---
id: t5-1-1-implementa-calendario-e-classifiche
titolo: "T5.1.1 Implementa calendario e classifiche"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-28
---

## Contesto
Importata da Linear FOR-28: progetto "Stagione e carriera", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T5.1.1 [ ] Implementa calendario e classifiche

**Dipendenze**: T3.3.2, T1.1.2.
**Wave**: 1.

**Scope**: far avanzare il tempo della Carriera sui giorni reali del Calendario 2026 (24 GP con date e pause vere, inclusa la pausa estiva) e tenere classifiche piloti e costruttori sempre coerenti dopo ogni gara. A fine stagione l'anno avanza (2026 → 2027) replicando lo stesso Calendario: il ciclo stagione completo diventa giocabile in sequenza.

**Scenario utente**:
Il giocatore chiude un GP e atterra sulla schermata di fine gara. Da lì apre le classifiche: vede la classifica piloti e quella costruttori aggiornate con i punti appena incassati. Torna al calendario: il prossimo GP è evidenziato con la data reale e il conto dei giorni mancanti. Avanza i giorni fino al weekend successivo; durante la pausa estiva il conto giorni mostra chiaramente lo stacco lungo. Dopo l'ultimo GP della stagione la classifica finale viene congelata e l'anno avanza al 2027 con lo stesso Calendario di 24 GP. Edge case: prima del primo GP le classifiche mostrano tutti a 0 punti con un ordine stabile, non un errore né una vista vuota.

**Deliverable verificabile**:

* Esiste il Calendario 2026 con 24 GP, date reali e pause (inclusa la pausa estiva), caricato da seed in `supabase/`, verificabile via query e via schermata calendario.
* Il motore espone l'avanzamento del tempo a giorni di calendario: avanzando si arriva esattamente al GP successivo, verificabile via test pytest headless.
* Le classifiche piloti e costruttori si aggiornano dopo ogni gara con punteggio e tie-break corretti (a parità di punti contano i piazzamenti migliori), verificabile via test pytest con casi di parità.
* A fine stagione l'anno avanza 2026 → 2027 replicando il Calendario, con classifiche azzerate e stato Carriera preservato, verificabile via test.
* Ogni avanzamento di calendario produce un Checkpoint (scrittura transazionale via psycopg), verificabile su Postgres effimero Docker.
* Le schermate calendario e classifiche sono navigabili da tastiera, verificabili via test Pilot.

**File da toccare**:

* `engine/season/__init__.py` (NEW DIR)
* `engine/season/calendar.py` (NEW)
* `engine/season/clock.py` (NEW)
* `engine/season/standings.py` (NEW)
* `tui/screens/calendar.py` (NEW)
* `tui/screens/standings.py` (NEW)
* `persistence/repositories/season.py` (NEW)
* `supabase/migrations/<timestamp>_season_calendar_standings.sql` (NEW)
* `supabase/seed/calendar_2026.sql` (NEW)
* `tests/engine/test_calendar.py` (NEW)
* `tests/engine/test_standings.py` (NEW)
* `tests/tui/test_calendar_standings_screens.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: calendario e classifiche raggiungibili dal flusso post-gara e dal menu della Carriera
- [ ] Popolata: 24 GP con date e pause reali; classifiche con tutti i 22 piloti e le 11 squadre della Griglia
- [ ] Cliccabile: navigazione completa da tastiera (avanza giorni, apri classifiche, torna al calendario)
- [ ] URL canonica: ogni schermata ha un id/binding canonico e stabile nell'app Textual
- [ ] Stati UI: pre-primo GP (tutti a 0 punti), pausa estiva, fine stagione con passaggio d'anno
- [ ] Aggiornata: classifiche ricalcolate subito dopo ogni gara; Checkpoint a ogni avanzamento
- [ ] Compatibile wireframe: layout coerente con le schermate TUI esistenti

**Cosa NON fare**:

* Niente Mercato piloti né fase inverno (sono T5.2.x e T5.3.1).
* Niente variazioni di calendario tra stagioni (post-MVP): il 2027 replica il 2026.
* Niente Formato weekend Sprint (post-MVP).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 38, 39)
* `CONTEXT.md` (Calendario, Carriera, Checkpoint, Griglia)
* `docs/adr/0001` (persistenza: scritture solo a Checkpoint)
* `docs/adr/0002` (Textual + motore puro)
* Task a monte: T3.3.2, T1.1.2

## Note
Origine: Linear FOR-28 (https://linear.app/haku-inc/issue/FOR-28/t511-implementa-calendario-e-classifiche). Etichette Linear: si, ready-for-agent.
Dipendenze cross-progetto su Linear (non risolte come slug locali): t3-3-2-completa-flusso-weekend-end-to-end (FOR-21), t1-1-2-crea-schema-db-multi-carriera-e-seed-dati (FOR-3).
