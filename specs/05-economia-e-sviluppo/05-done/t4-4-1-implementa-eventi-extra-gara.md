---
id: t4-4-1-implementa-eventi-extra-gara
titolo: "T4.4.1 Implementa Eventi extra-gara"
stato: done
priorita: media
dipendenze: [t4-3-1-implementa-progetti-di-sviluppo]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-27
---

## Contesto
Importata da Linear FOR-27: progetto "Economia e sviluppo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T4.4.1 [ ] Implementa Eventi extra-gara

**Dipendenze**: T4.3.1.

**Wave**: 4.

**Scope**: dare vita agli intervalli tra i GP con un pool di Eventi extra-gara estratti con frequenza bassa (al massimo uno per intervallo): sponsor una tantum, intoppo che ritarda un Progetto, reparto ispirato che lo accelera, guaio in fabbrica di un rivale. Ogni evento produce una Notizia in stile rassegna stampa ed effetti meccanici secchi su Cassa o Progetti, senza scelte da parte del giocatore.

**Scenario utente**:

> Tra due Gran Premi il giocatore avanza il calendario e legge la Notizia "Lo sponsor
> TecnoX versa un bonus": aprendo la schermata finanze vede l'entrata una tantum con
> causale e la Cassa salita nel widget persistente. In un altro intervallo la Notizia
> annuncia un intoppo in galleria del vento: la data di consegna del suo Progetto
> slitta, e la schermata sviluppo lo riflette. Edge case: nella maggior parte degli
> intervalli non succede nulla — nessuna Notizia forzata, il silenzio è normale.

**Deliverable verificabile**:

* Esiste nel motore un pool iniziale di almeno 10 Eventi extra-gara con pesi di estrazione, che copre i quattro tipi: sponsor una tantum (entrata in Cassa), Progetto ritardato, Progetto accelerato, guaio in fabbrica di un rivale; verificabile via pytest headless.
* L'estrazione avviene tra un GP e l'altro con al massimo un evento per intervallo e frequenza bassa configurabile; verificabile via pytest statistico su una stagione simulata (la maggioranza degli intervalli resta senza evento).
* Ogni evento estratto produce una Notizia in stile rassegna stampa (template parametrici, ADR 0003) e applica il suo effetto meccanico secco su Cassa (movimento con causale nel registro) o su Progetti (consegna anticipata/posticipata), verificabile via pytest sugli effetti.
* Gli eventi che toccano la Cassa o i Progetti del giocatore sono visibili nelle schermate finanze e sviluppo esistenti; la Notizia è leggibile in TUI, verificabile con test Pilot.
* Nessun evento richiede una scelta del giocatore: il pool contiene solo eventi a effetto automatico, verificabile via review del pool e test.

**File da toccare**:

* `src/engine/events_extra/` (NEW DIR)
* `src/engine/events_extra/__init__.py` (NEW)
* `src/engine/events_extra/pool.py` (NEW)
* `src/engine/events_extra/draw.py` (NEW)
* `src/engine/economy/ledger.py`
* `src/engine/development/projects.py`
* `src/tui/screens/news.py` (NEW)
* `tests/engine/events_extra/test_pool.py` (NEW)
* `tests/engine/events_extra/test_draw_frequency.py` (NEW)
* `tests/tui/test_news.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: la Notizia è leggibile nell'avanzamento tra i GP senza passaggi nascosti
- [ ] Popolata: ogni Notizia porta testo reale dal template e l'effetto meccanico è davvero applicato, mai placeholder
- [ ] Cliccabile: le Notizie dell'intervallo sono scorribili da tastiera
- [ ] URL canonica: (previsto [N/A]: app TUI senza URL; la vista Notizie ha nome e binding canonici stabili)
- [ ] Stati UI: intervallo senza eventi = nessuna Notizia forzata; empty state coerente
- [ ] Aggiornata: Cassa e Progetti riflettono l'effetto dell'evento appena estratto senza riavvio
- [ ] Compatibile wireframe: (previsto [N/A]: nessun wireframe formale per il MVP TUI)

**Cosa NON fare**:

* Niente eventi con decisione del giocatore (post-MVP): solo effetti automatici.
* Niente eventi in-gara: quelli sono gli Eventi chiave del motore di gara.
* Niente testo generato da LLM: solo template parametrici (ADR 0003).
* Niente più di un evento per intervallo tra GP.
* Niente scritture su DB fuori dai Checkpoint (ADR 0001).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 37.
* `CONTEXT.md` § Stagione (Evento extra-gara, Notizia) ed § Economia (Cassa, Progetto).
* `docs/adr/0001-supabase-self-hosted-su-vps-con-salvataggi-a-checkpoint.md`.
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md`.
* T4.3.1 (<issue id="ff7559c5-d130-4a0e-8001-250e78f21f34" href="https://linear.app/haku-inc/issue/FOR-25/t431-implementa-progetti-di-sviluppo">FOR-25</issue>, Progetti di sviluppo: bersaglio degli eventi ritardo/accelerazione).

## Note
Origine: Linear FOR-27 (https://linear.app/haku-inc/issue/FOR-27/t441-implementa-eventi-extra-gara). Etichette Linear: si, ready-for-agent.
