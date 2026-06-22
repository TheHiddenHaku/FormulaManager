---
id: m1-modelli-del-mercato-piloti-e-apertura-fase
titolo: "M1 - Modelli del Mercato piloti e apertura fase + pool Contratti in scadenza (tracer)"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-14
scadenza:
linear: FOR-44
---

## Contesto
Importata da Linear FOR-44: progetto "Stagione e carriera", stato Linear "Done", creata 2026-06-14. Issue madre Linear: FOR-30 (slug t5-2-1-implementa-mercato-piloti).

## Obiettivo
**Issue madre:** <issue id="08ed669f-8d3a-4716-8bcf-e8572625c6d9" href="https://linear.app/haku-inc/issue/FOR-30/t521-implementa-mercato-piloti">FOR-30</issue> — T5.2.1 Mercato piloti
**Layer:** engine · **Tracer bullet:** si
**Dipendenze (sub-issue):** nessuna (puo partire subito)
**A monte (gia merged):** <issue id="9ee2219c-746d-4ae0-a0e2-fe6f4a71e498" href="https://linear.app/haku-inc/issue/FOR-22/t412-implementa-entrate-e-stipendi">FOR-22</issue>, <issue id="ff7559c5-d130-4a0e-8001-250e78f21f34" href="https://linear.app/haku-inc/issue/FOR-25/t431-implementa-progetti-di-sviluppo">FOR-25</issue>, <issue id="1ab3c88c-4a6a-43b8-a341-f97127aa7007" href="https://linear.app/haku-inc/issue/FOR-28/t511-implementa-calendario-e-classifiche">FOR-28</issue> (merged)

## Scope

Tracer-bullet del sottosistema, motore puro (ADR 0002). Definisce le dataclass frozen: MarketState (fase, pool dei Contratti in scadenza, sedili vacanti squadra->slot, log mosse AI come tupla di record tipizzati, eventuali richieste salariali transitorie dei liberi), e i record di supporto (es. ExpiringContract/SeatToFill, AiMove tipizzato). Definisce la funzione open_market(world, concluded_year) -> MarketState che popola il pool: tutti i Contratti la cui ultima stagione coperta (start_season + duration_seasons - 1) coincide con concluded_year entrano nel pool; i piloti liberi (world.drivers_without_contract) entrano come disponibili. Nessuna logica di offerta/negoziazione/convergenza: solo modelli, selezione del pool e query di sola lettura (pool, sedili vacanti per squadra, conteggio piloti per squadra). MarketState ha uno stato di partenza canonico (default()) coerente con la convenzione degli altri *State, cosi' M4 puo' applicare NULL=default in persistenza.

## Deliverable verificabile

* MarketState e modelli correlati come dataclass frozen in src/fm_engine/market/models.py (incluso il record tipizzato del log mosse AI)
* open_market(world, concluded_year) -> MarketState in src/fm_engine/market/pool.py che popola pool dei Contratti in scadenza e piloti liberi
* Formula di scadenza derivata e testata come costante/funzione nominata: last_covered_season(contract) == start_season + duration_seasons - 1
* Test pytest engine-only (senza DB/TUI): Contratti in scadenza identificati, Contratti pluriennali ancora validi esclusi, piloti liberi inclusi, sedili vacanti calcolati per squadra
* tests/engine/test_pure_imports.py resta verde

## File da toccare (path reali)

* `src/fm_engine/market/__init__.py`
* `src/fm_engine/market/models.py`
* `src/fm_engine/market/pool.py`
* `tests/engine/test_market_pool.py`

## Definition of Done

- [ ] .venv/bin/python -m pytest tests/engine/test_market_pool.py verde
- [ ] ruff check . e ruff format --check . verdi
- [ ] tests/engine/test_pure_imports.py verde (nessun import textual/psycopg in src/fm_engine/market/)
- [ ] La scadenza di un Contratto e' una funzione/costante nominata e testata, non magia inline
- [ ] MarketState() default e' lo stato a fase non aperta, coerente con la convenzione XState() (per NULL=default in M4)

## Default da documentare (scelte dell'implementatore, tuning rimandato a <issue id="12469ed4-27a3-4673-9fb9-74dd07fc3952" href="https://linear.app/haku-inc/issue/FOR-34/t541-esegui-beta-giocabile-e-review-di-gioco">FOR-34</issue>)

* Definizione operativa di 'Contratto in scadenza' (ultima stagione coperta == anno concluso): documentare la formula last_covered_season come funzione nominata
* Se i piloti liberi entrino nel pool da subito o solo dopo la prima tornata di offerte AI: defaultare a 'da subito' e documentare
* Struttura del log mosse AI (record tipizzato con squadra, pilota, tipo mossa, importo, durata): definirla come dataclass frozen e documentarla; sara' anche la forma serializzata in M4

## Coordinamento file condivisi

Il pool dei liberi deve usare il filtro `active_drivers` introdotto da FOR-31e; finche' FOR-31e non e' a terra, assumere il filtro come default documentato (escludere i piloti con flag `retired`).

## Riferimenti

* Issue madre: <issue id="08ed669f-8d3a-4716-8bcf-e8572625c6d9" href="https://linear.app/haku-inc/issue/FOR-30/t521-implementa-mercato-piloti">FOR-30</issue>
* CONTEXT.md (Mappa dei nomi nel codice), docs/adr/0001 (Checkpoint), docs/adr/0002 (motore puro)
* Vincoli: `tests/engine/test_pure_imports.py` verde; pytest + ruff verdi prima del commit

## Note
Origine: Linear FOR-44 (https://linear.app/haku-inc/issue/FOR-44/m1-modelli-del-mercato-piloti-e-apertura-fase-pool-contratti-in). Etichette Linear: si, ready-for-agent.
