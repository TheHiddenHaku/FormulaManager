---
id: m4-persistenza-del-mercato-ai-checkpoint-market
titolo: "M4 - Persistenza del Mercato ai Checkpoint: market_state jsonb + round-trip roster"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-14
scadenza:
linear: FOR-47
---

## Contesto
Importata da Linear FOR-47: progetto "Stagione e carriera", stato Linear "Done", creata 2026-06-14. Issue madre Linear: FOR-30 (slug t5-2-1-implementa-mercato-piloti).

## Obiettivo
**Issue madre:** <issue id="08ed669f-8d3a-4716-8bcf-e8572625c6d9" href="https://linear.app/haku-inc/issue/FOR-30/t521-implementa-mercato-piloti">FOR-30</issue> — T5.2.1 Mercato piloti
**Layer:** persistence · **Tracer bullet:** no
**Dipendenze (sub-issue):** M1, M3

## Scope

Rendere il Mercato Checkpoint-safe seguendo i due pattern reali del repo. (A) Stato transitorio della fase (MarketState in corso: pool, offerte, log mosse AI, negoziazione pendente, richieste salariali transitorie dei liberi) serializzato in una NUOVA colonna jsonb market_state su careers, con la convenzione standard (NULL=default, save in [checkpoint.py](<http://checkpoint.py>):save_career come Jsonb(...) o None, load in load_career; nuovo modulo fm_persistence/market.py con market_state_payload/market_state_from_payload sul modello di [preseason.py](<http://preseason.py>)); estendere Career con campo market: MarketState = field(default_factory). (B) Verificare che le MUTAZIONI del roster prodotte dal mercato (Contratti nuovi/rimossi, piloti che cambiano squadra) round-trippino via il percorso esistente _insert_world/world_from_rows: aggiungere test di round-trip su un World con Contratti mutati. (C) GESTIRE IL LANDMINE: world_from_rows deriva player_set_up dalla presenza di Contratti del giocatore ([mapping.py](<http://mapping.py>) L352); aggiungere un test che dimostra che un World con i 2 Contratti del giocatore (post-mercato) round-trippa mantenendo is_set_up e gli Attributi vettura. Risolvere la richiesta salariale dei liberi NEL payload market_state (transitorio), senza nuova colonna su drivers. Niente test contro matilde: Postgres effimero in Docker.

## Deliverable verificabile

* Migrazione supabase/migrations/<timestamp>_careers_market_state.sql che AGGIUNGE la colonna market_state jsonb su careers con COMMENT in italiano (NON una nuova tabella)
* src/fm_persistence/market.py con market_state_payload / market_state_from_payload (None=default, sul modello di [preseason.py](<http://preseason.py>))
* [checkpoint.py](<http://checkpoint.py>):save_career e load_career estesi per market_state (stesso pattern di season_state/preseason_state); Career esteso con campo market
* Test persistence (Docker) di round-trip: MarketState in corso salvato e ricaricato identico; World con Contratti mutati dal mercato round-trippa via world_from_rows
* Test che un World del giocatore con 2 Contratti post-mercato round-trippa mantenendo player_slot.is_set_up e gli Attributi vettura (copre il landmine player_set_up)

## File da toccare (path reali)

* `supabase/migrations/<timestamp>_careers_market_state.sql`
* `src/fm_persistence/market.py`
* `src/fm_persistence/checkpoint.py`
* `src/fm_engine/career.py`
* `tests/persistence/test_market_state.py`

## Definition of Done

- [ ] .venv/bin/python -m pytest tests/persistence/test_market_state.py verde (Postgres effimero in Docker)
- [ ] ruff check . e ruff format --check . verdi
- [ ] Stato di partenza del Mercato => colonna market_state NULL (coerenza con season_state/preseason_state); Carriere salvate prima della migrazione continuano a caricarsi (colonna nullable)
- [ ] Round-trip strutturalmente identico per MarketState e per i Contratti mutati
- [ ] Nessuna nuova tabella normalizzata per il mercato; le mutazioni roster usano _insert_world/world_from_rows esistenti
- [ ] La richiesta salariale dei liberi vive nel payload market_state, non in una nuova colonna drivers (nessun cambio di forma del roster persistito)

## Default da documentare (scelte dell'implementatore, tuning rimandato a <issue id="12469ed4-27a3-4673-9fb9-74dd07fc3952" href="https://linear.app/haku-inc/issue/FOR-34/t541-esegui-beta-giocabile-e-review-di-gioco">FOR-34</issue>)

* Granularita' del log mosse AI nel payload (tutte le mosse vs ultime N): defaultare a 'tutte' e documentare
* Persistenza del MarketState: defaultare a 'persistito mentre la fase e' aperta', NULL altrimenti (la fase e' a fine stagione, non a meta' gara)
* Documentare che la richiesta salariale dei liberi e' transitoria nel payload e non diventa colonna su drivers

## Coordinamento file condivisi

Tocca `src/fm_engine/career.py` (campo market) e `checkpoint.py` (save/load) condivisi con S1/S2. Rebase sul shape gia' esteso.

## Riferimenti

* Issue madre: <issue id="08ed669f-8d3a-4716-8bcf-e8572625c6d9" href="https://linear.app/haku-inc/issue/FOR-30/t521-implementa-mercato-piloti">FOR-30</issue>
* CONTEXT.md (Mappa dei nomi nel codice), docs/adr/0001 (Checkpoint), docs/adr/0002 (motore puro)
* Vincoli: `tests/engine/test_pure_imports.py` verde; pytest + ruff verdi prima del commit

## Note
Origine: Linear FOR-47 (https://linear.app/haku-inc/issue/FOR-47/m4-persistenza-del-mercato-ai-checkpoint-market-state-jsonb-round-trip). Etichette Linear: si, ready-for-agent.
