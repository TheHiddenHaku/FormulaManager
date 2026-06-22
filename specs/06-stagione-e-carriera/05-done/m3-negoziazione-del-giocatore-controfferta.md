---
id: m3-negoziazione-del-giocatore-controfferta
titolo: "M3 - Negoziazione del giocatore: controfferta ingaggio+durata con vincolo Cassa (engine puro)"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-14
scadenza:
linear: FOR-46
---

## Contesto
Importata da Linear FOR-46: progetto "Stagione e carriera", stato Linear "Done", creata 2026-06-14. Issue madre Linear: FOR-30 (slug t5-2-1-implementa-mercato-piloti).

## Obiettivo
**Issue madre:** <issue id="08ed669f-8d3a-4716-8bcf-e8572625c6d9" href="https://linear.app/haku-inc/issue/FOR-30/t521-implementa-mercato-piloti">FOR-30</issue> — T5.2.1 Mercato piloti
**Layer:** engine · **Tracer bullet:** no
**Dipendenze (sub-issue):** M2

## Scope

Logica pura della negoziazione lato giocatore, motore puro. Il giocatore rilancia su un pilota del pool (proprio pilota in scadenza o un libero) alzando ingaggio e/o durata (1-3 anni). Le controfferte insostenibili rispetto alla Cassa del giocatore sono RIFIUTATE con MOTIVO STRUTTURATO (enum/dataclass, non stringa libera), riusando il concetto di vincolo Cassa dell'economia esistente (TeamLedger.allowed_spending_usd / il salary_instalment dell'economia, SpendingBlocked), NON una formula ad hoc divergente. La logica decide se il pilota accetta confrontando la controfferta con la migliore offerta rivale (esito deterministico dati gli input). Nessuna UI: funzioni pure che dato MarketState + controfferta ritornano nuovo MarketState o un rifiuto motivato; aggiornano il log mosse.

## Deliverable verificabile

* src/fm_engine/market/negotiation.py con funzione di controfferta (driver, salary, duration) che ritorna un esito strutturato: accettata / rifiutata-dal-pilota / bloccata-Cassa, con motivo tipizzato
* Vincolo Cassa: una controfferta non sostenibile e' bloccata con motivo esplicito (testato), usando la stessa nozione di vincolo dell'economia esistente
* Confronto con la migliore offerta rivale per decidere se il pilota resta
* Test pytest engine-only: rilancio vincente tiene il pilota, rilancio perdente lo perde, controfferta insostenibile bloccata con motivo, durata fuori range 1-3 rifiutata, determinismo dell'esito

## File da toccare (path reali)

* `src/fm_engine/market/negotiation.py`
* `src/fm_engine/market/models.py`
* `tests/engine/test_market_negotiation.py`

## Definition of Done

- [ ] .venv/bin/python -m pytest tests/engine/test_market_negotiation.py verde
- [ ] ruff check . e ruff format --check . verdi
- [ ] tests/engine/test_pure_imports.py verde
- [ ] Il motivo del rifiuto e' un valore strutturato e testabile (enum/dataclass), non una stringa libera
- [ ] La sostenibilita' Cassa usa la nozione di vincolo dell'economia esistente (allowed_spending_usd / salary instalment), coerente con fm_engine.economy, non una formula nuova divergente

## Default da documentare (scelte dell'implementatore, tuning rimandato a <issue id="12469ed4-27a3-4673-9fb9-74dd07fc3952" href="https://linear.app/haku-inc/issue/FOR-34/t541-esegui-beta-giocabile-e-review-di-gioco">FOR-34</issue>)

* Soglia di accettazione del pilota (di quanto la controfferta deve battere l'offerta rivale; a parita' vince l'incumbent?): defaultare e documentare
* Numero di tornate di controfferta consentite (es. una sola): defaultare e documentare
* Come la sostenibilita' considera l'ingaggio annuale vs la durata pluriennale rispetto alla Cassa corrente (es. controllo sulla rata stagionale): scegliere e documentare
* Peso di fattori oltre l'ingaggio nella decisione del pilota (Prestigio della squadra del giocatore): default documentato

## Riferimenti

* Issue madre: <issue id="08ed669f-8d3a-4716-8bcf-e8572625c6d9" href="https://linear.app/haku-inc/issue/FOR-30/t521-implementa-mercato-piloti">FOR-30</issue>
* CONTEXT.md (Mappa dei nomi nel codice), docs/adr/0001 (Checkpoint), docs/adr/0002 (motore puro)
* Vincoli: `tests/engine/test_pure_imports.py` verde; pytest + ruff verdi prima del commit

## Note
Origine: Linear FOR-46 (https://linear.app/haku-inc/issue/FOR-46/m3-negoziazione-del-giocatore-controfferta-ingaggiodurata-con-vincolo). Etichette Linear: si, ready-for-agent.
