---
id: m2-offerte-ai-guidate-dal-prestigio-e-convergenza
titolo: "M2 - Offerte AI guidate dal Prestigio e convergenza garantita (2 piloti/squadra)"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-14
scadenza:
linear: FOR-45
---

## Contesto
Importata da Linear FOR-45: progetto "Stagione e carriera", stato Linear "Done", creata 2026-06-14. Issue madre Linear: FOR-30 (slug t5-2-1-implementa-mercato-piloti).

## Obiettivo
**Issue madre:** <issue id="08ed669f-8d3a-4716-8bcf-e8572625c6d9" href="https://linear.app/haku-inc/issue/FOR-30/t521-implementa-mercato-piloti">FOR-30</issue> — T5.2.1 Mercato piloti
**Layer:** engine · **Tracer bullet:** no
**Dipendenze (sub-issue):** M1

## Scope

Logica delle offerte delle squadre AI sul pool e garanzia di convergenza, motore puro testabile headless con seed (random.Random). Le AI fanno offerte (ingaggio + durata 1-3) sui piloti del pool: il Prestigio piu' alto attrae i piloti migliori (attrattivita' = funzione del prestige della squadra e della qualita' del pilota), entro il vincolo di Cassa (cash_usd persistito). NOTA VINCOLANTE: l'AI delle offerte si basa su prestige+cash_usd (persistiti), NON su SpendingPersonality (non persistita, azzerata dopo reload); la logica salariale e' nuova (fm_engine.ai.spending riguarda i Progetti, non gli stipendi) ma riusa il concetto di vincolo Cassa. La risoluzione e' deterministica dato il seed e DEVE convergere: alla chiusura ogni squadra ha esattamente 2 piloti, nessun sedile vuoto, tramite un fallback di assegnazione forzata dai liberi rimanenti. Ogni mossa AI entra nel log. SCOPE BOUNDED (rischio sessione): la slice consegna esattamente generazione offerte + loop di risoluzione + fallback di convergenza + i due test (economics, convergence); non aggiunge negoziazione del giocatore (M3) ne UI.

## Deliverable verificabile

* src/fm_engine/market/ai_offers.py con generazione offerte AI parametrizzata da prestige e vincolata da cash_usd
* Funzione di risoluzione del mercato AI che ritorna un MarketState avanzato con offerte assegnate, log popolato e invariante 2 piloti/squadra garantito via fallback dai liberi
* test_market_economics.py: su >=100 seed, correlazione statistica prestige->qualita' media dei piloti aggiudicati (squadre a prestige alto vincono in media piloti con attributi medi piu' alti); nessuna offerta AI supera cash_usd della squadra
* test_market_convergence.py: su >=100 seed, alla chiusura OGNI squadra ha esattamente 2 piloti e nessun sedile resta vuoto; nessun pilota assegnato a due squadre
* Determinismo verificato: stesso seed -> stesso MarketState finale

## File da toccare (path reali)

* `src/fm_engine/market/ai_offers.py`
* `src/fm_engine/market/pool.py`
* `src/fm_engine/market/models.py`
* `tests/engine/test_market_convergence.py`
* `tests/engine/test_market_economics.py`

## Definition of Done

- [ ] .venv/bin/python -m pytest tests/engine/test_market_convergence.py tests/engine/test_market_economics.py verde
- [ ] ruff check . e ruff format --check . verdi
- [ ] tests/engine/test_pure_imports.py verde
- [ ] Invariante di convergenza dimostrato su un numero alto di seed (>=100), non su un singolo caso
- [ ] Nessuna offerta usa SpendingPersonality (verificabile: la risoluzione funziona anche con personalita' azzerata, cioe' su un World ricaricato)
- [ ] Tutti i coefficienti (peso del Prestigio, formula di credibilita' offerta, soglia di accettazione AI, dimensionamento ingaggio) sono costanti nominate e documentate

## Default da documentare (scelte dell'implementatore, tuning rimandato a <issue id="12469ed4-27a3-4673-9fb9-74dd07fc3952" href="https://linear.app/haku-inc/issue/FOR-34/t541-esegui-beta-giocabile-e-review-di-gioco">FOR-34</issue>)

* Peso del Prestigio nell'attrattivita' e nell'aggiudicazione: costante iniziale ragionevole, tuning a <issue id="12469ed4-27a3-4673-9fb9-74dd07fc3952" href="https://linear.app/haku-inc/issue/FOR-34/t541-esegui-beta-giocabile-e-review-di-gioco">FOR-34</issue>
* Formula di ingaggio offerto dall'AI (funzione di attributi pilota e Cassa): defaultare e documentare
* Politica di durata AI (1-3 anni): default deterministico documentato
* Meccanismo di fallback per garantire 2 piloti/squadra (es. assegnazione greedy dei liberi residui ai sedili vuoti per ordine di Prestigio): scegliere e documentare
* Se l'AI valuta i piloti a valori veri o a Stime: defaultare a 'valori veri internamente' (le Stime sono solo cio' che il giocatore VEDE) e documentare
* Documentare esplicitamente che, essendo SpendingPersonality non persistita, l'AI delle offerte usa prestige+cash_usd

## Riferimenti

* Issue madre: <issue id="08ed669f-8d3a-4716-8bcf-e8572625c6d9" href="https://linear.app/haku-inc/issue/FOR-30/t521-implementa-mercato-piloti">FOR-30</issue>
* CONTEXT.md (Mappa dei nomi nel codice), docs/adr/0001 (Checkpoint), docs/adr/0002 (motore puro)
* Vincoli: `tests/engine/test_pure_imports.py` verde; pytest + ruff verdi prima del commit

## Note
Origine: Linear FOR-45 (https://linear.app/haku-inc/issue/FOR-45/m2-offerte-ai-guidate-dal-prestigio-e-convergenza-garantita-2). Etichette Linear: si, ready-for-agent.
