---
id: t1-1-1-imposta-scaffolding-repo-e-pacchetti
titolo: "T1.1.1 Imposta scaffolding repo e pacchetti"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-2
---

## Contesto
Importata da Linear FOR-2: progetto "Fondamenta", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T1.1.1 [ ] Imposta scaffolding repo e pacchetti

**Dipendenze**: nessuna.
**Wave**: 1.

**Scope**: mettere in piedi il repo greenfield con due pacchetti separati — motore di gioco in Python puro (nessun import TUI/DB, come da ADR 0002) e TUI Textual (>=8,<9) — più tooling pytest e lint, e un entry point `fm` che apre una TUI placeholder con Footer e binding visibili. È la base su cui atterrano tutti i task successivi.

**Scenario utente**: il giocatore lancia `fm` da terminale. Vede una schermata placeholder con il nome del gioco e un Footer con le scorciatoie disponibili. Preme `q` ed esce pulitamente. Nessun altro contenuto: serve solo a provare che l'applicazione si avvia e risponde alla tastiera.

**Deliverable verificabile**:

* `pyproject.toml` definisce il progetto con i due pacchetti (`fm_engine` motore puro, `fm_tui` Textual) e il vincolo `textual>=8,<9`; installabile con `pip install -e .`.
* Comando `fm` (script entry point) avvia l'app Textual placeholder con Footer e binding `q` visibile; `q` chiude l'app.
* `pytest` verde: test segnaposto del motore più smoke test Pilot (l'app si avvia, `q` la chiude).
* Test di architettura: `fm_engine` non importa `textual` né `psycopg`, verificabile via test sugli import.
* Lint configurato (es. ruff) e passante sull'intero repo.

**File da toccare**:

* `pyproject.toml` (NEW)
* `.gitignore` (NEW)
* `README.md` (NEW)
* `src/fm_engine/__init__.py` (NEW DIR)
* `src/fm_tui/__init__.py` (NEW DIR)
* `src/fm_tui/app.py` (NEW)
* `tests/engine/test_segnaposto.py` (NEW DIR)
* `tests/engine/test_import_puri.py` (NEW)
* `tests/tui/test_smoke.py` (NEW DIR)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il comando `fm` apre la schermata placeholder
- [ ] Popolata: la schermata mostra titolo e Footer con i binding
- [ ] Cliccabile: il binding `q` esce dall'app (interazione da tastiera)
- [ ] URL canonica (previsto [N/A]: TUI senza routing; l'entry point canonico è il comando `fm`)
- [ ] Stati UI (previsto [N/A]: schermata statica senza dati, nessun loading/empty/error)
- [ ] Aggiornata (previsto [N/A]: nessun dato dinamico nella placeholder)
- [ ] Compatibile wireframe (previsto [N/A]: nessun wireframe previsto per la placeholder)

**Cosa NON fare**:

* Nessuna logica di gioco (niente Mondo, Gara, economia).
* Nessuna connessione DB né dipendenza psycopg/Supabase.
* Nessuna schermata reale (l'elenco Carriere è T1.3.1).
* Niente CI remota: solo tooling locale.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (story 45).
* `CONTEXT.md` (glossario canonico).
* `docs/adr/0002` (Textual + motore puro).

## Note
Origine: Linear FOR-2 (https://linear.app/haku-inc/issue/FOR-2/t111-imposta-scaffolding-repo-e-pacchetti). Etichette Linear: si, ready-for-agent.
