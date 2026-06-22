---
id: t1-2-1-implementa-modulo-mondo-generazione-griglia
titolo: "T1.2.1 Implementa modulo Mondo: generazione griglia"
stato: done
priorita: media
dipendenze: [t1-1-1-imposta-scaffolding-repo-e-pacchetti]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-4
---

## Contesto
Importata da Linear FOR-4: progetto "Fondamenta", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T1.2.1 [ ] Implementa modulo Mondo: generazione griglia

**Dipendenze**: T1.1.1.
**Wave**: 2.

**Scope**: implementare nel motore puro la funzione `genera(seed, config)` che produce il Mondo di inizio Carriera: la Griglia (10 squadre AI + slot giocatore), i 22 piloti, i Motoristi con i rapporti di fornitura, i Contratti iniziali e le personalità di spesa AI. È il cuore deterministico su cui la TUI (T1.3.1) costruisce la nuova Carriera.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Lo scenario è coperto da T1.3.1.

**Deliverable verificabile**:

* Modulo in `fm_engine` esporta `genera(seed, config)` che ritorna il Mondo completo: 10 squadre AI + slot giocatore, 22 piloti con i 6 Attributi pilota più età, nazionalità pesate sui vivai reali e Potenziale nascosto, 3-4 Motoristi (squadre produttrici e Clienti), Contratti iniziali 1-3 anni, personalità di spesa per ogni squadra AI.
* Property test pytest: sempre 22 piloti; ogni squadra esattamente 2 piloti; ogni squadra ha un motore (produzione propria oppure Cliente di un Motorista); 3-4 Motoristi; ogni attributo nei range di config; durate Contratto in 1-3 anni.
* Determinismo: due chiamate con lo stesso seed producono Mondi identici; seed diversi producono Mondi diversi (test dedicato).
* Il Potenziale è modellato come attributo nascosto, distinto dai 6 Attributi pilota che la TUI mostrerà come Stime.
* Il modulo non importa `textual` né `psycopg` (motore puro, ADR 0002).

**File da toccare**:

* `src/fm_engine/mondo/__init__.py` (NEW DIR)
* `src/fm_engine/mondo/modelli.py` (NEW: Squadra, Pilota, Motorista, Contratto)
* `src/fm_engine/mondo/generazione.py` (NEW: `genera(seed, config)`)
* `src/fm_engine/mondo/nazionalita.py` (NEW: pesi dei vivai reali)
* `tests/engine/mondo/test_generazione.py` (NEW DIR)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile (previsto [N/A]: task puro motore, nessuna UI)
- [ ] Popolata: il Mondo generato contiene Griglia, piloti, Motoristi, Contratti e personalità di spesa completi
- [ ] Cliccabile (previsto [N/A]: nessuna interazione UI)
- [ ] URL canonica (previsto [N/A]: nessuna route; API canonica `fm_engine.mondo.genera`)
- [ ] Stati UI (previsto [N/A]: nessuna UI)
- [ ] Aggiornata (previsto [N/A]: nessun dato mostrato; il Mondo è consumato da T1.3.1)
- [ ] Compatibile wireframe (previsto [N/A]: nessuna UI)

**Cosa NON fare**:

* Niente persistenza (è T1.2.2).
* Niente UI (è T1.3.1).
* Niente Giovani, Mercato piloti o invecchiamento (post-Fondamenta).
* Niente simulazione di sessioni né economia runtime.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (story 6, 41 base).
* `CONTEXT.md` (Griglia, Attributo pilota, Potenziale, Motorista, Cliente, Contratto, Stima).
* `docs/adr/0002` (Textual + motore puro).
* T1.1.1 (scaffolding repo).

## Note
Origine: Linear FOR-4 (https://linear.app/haku-inc/issue/FOR-4/t121-implementa-modulo-mondo-generazione-griglia). Etichette Linear: si, ready-for-agent.
