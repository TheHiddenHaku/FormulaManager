---
id: m5-schermata-tui-del-mercato-piloti-textual
titolo: "M5 - Schermata TUI del Mercato piloti (Textual)"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-14
scadenza:
linear: FOR-48
---

## Contesto
Importata da Linear FOR-48: progetto "Stagione e carriera", stato Linear "Done", creata 2026-06-14. Issue madre Linear: FOR-30 (slug t5-2-1-implementa-mercato-piloti).

## Obiettivo
**Issue madre:** <issue id="08ed669f-8d3a-4716-8bcf-e8572625c6d9" href="https://linear.app/haku-inc/issue/FOR-30/t521-implementa-mercato-piloti">FOR-30</issue> — T5.2.1 Mercato piloti
**Layer:** tui · **Tracer bullet:** no
**Dipendenze (sub-issue):** M3

## Scope

Guscio TUI sopra il motore (ADR 0002): la schermata mostra il pool dei Contratti in scadenza, gli attributi dei piloti SEMPRE come Stime (riuso KnowledgeState.estimate_for su driver_subject(driver_id) + format_estimate, mai valori esatti), l'offerta rivale visibile, i controlli per controfferta (ingaggio + durata 1-3) e il log mosse AI consultabile. Le controfferte insostenibili mostrano il motivo strutturato dal risultato del motore (M3). Nessuna logica di dominio nella schermata: solo chiamate a fm_engine.market. Pattern coerente con screens/preseason.py e screens/development.py (push_screen + callback *on**_closed che riporta la Career aggiornata); registrazione/apertura da [grid.py](<http://grid.py>) (NON da [app.py](<http://app.py>): le schermate hub sono pushate da [grid.py](<http://grid.py>)). Testabile con i test TUI (Docker).

## Deliverable verificabile

* src/fm_tui/screens/market.py con la schermata Textual: pool, Stime piloti, offerta rivale, controfferta, log mosse AI
* Gli attributi pilota sono mostrati come Stime (intervallo da format_estimate), mai valori esatti (verificato in test TUI)
* Una controfferta insostenibile mostra il motivo esplicito senza crash
* tests/tui/test_market_screen.py: rendering del pool, interazione di controfferta, blocco con motivo, log consultabile

## File da toccare (path reali)

* `src/fm_tui/screens/market.py`
* `tests/tui/test_market_screen.py`

## Definition of Done

- [ ] .venv/bin/python -m pytest tests/tui/test_market_screen.py verde (Docker)
- [ ] ruff check . e ruff format --check . verdi
- [ ] tests/engine/test_pure_imports.py verde: nessuna logica di dominio nella schermata, solo chiamate a fm_engine.market
- [ ] Le Stime usano l'infrastruttura esistente fm_engine.info.estimates (estimate_for/format_estimate/driver_subject), non un formatter nuovo
- [ ] Le stringhe UI sono in italiano; identificatori, nomi di file e moduli in inglese

## Default da documentare (scelte dell'implementatore, tuning rimandato a <issue id="12469ed4-27a3-4673-9fb9-74dd07fc3952" href="https://linear.app/haku-inc/issue/FOR-34/t541-esegui-beta-giocabile-e-review-di-gioco">FOR-34</issue>)

* Layout della schermata (tabella pool + pannello negoziazione + pannello log): scegliere uno schema coerente con le schermate esistenti e documentarlo
* Quante tornate di interazione esporre nella UI: allineare al default di M3
* Etichette UI italiane per fasi/azioni (Apri Mercato, Controfferta, Rifiutata: Cassa insufficiente, ecc.): defaultare e documentare

## Riferimenti

* Issue madre: <issue id="08ed669f-8d3a-4716-8bcf-e8572625c6d9" href="https://linear.app/haku-inc/issue/FOR-30/t521-implementa-mercato-piloti">FOR-30</issue>
* CONTEXT.md (Mappa dei nomi nel codice), docs/adr/0001 (Checkpoint), docs/adr/0002 (motore puro)
* Vincoli: `tests/engine/test_pure_imports.py` verde; pytest + ruff verdi prima del commit

## Note
Origine: Linear FOR-48 (https://linear.app/haku-inc/issue/FOR-48/m5-schermata-tui-del-mercato-piloti-textual). Etichette Linear: si, ready-for-agent.
