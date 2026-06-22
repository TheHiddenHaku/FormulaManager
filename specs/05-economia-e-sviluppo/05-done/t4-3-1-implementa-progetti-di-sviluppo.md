---
id: t4-3-1-implementa-progetti-di-sviluppo
titolo: "T4.3.1 Implementa Progetti di sviluppo"
stato: done
priorita: media
dipendenze: [t4-1-1-implementa-registro-cassa-e-cap]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-25
---

## Contesto
Importata da Linear FOR-25: progetto "Economia e sviluppo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T4.3.1 [ ] Implementa Progetti di sviluppo

**Dipendenze**: T4.1.1.

**Wave**: 3.

**Scope**: permettere al giocatore di investire nello sviluppo in-season della vettura: un Progetto punta un Attributo vettura, ha un costo che esce dal Cap, una durata in giorni di calendario reali e un esito con varianza — può deludere o superare le attese. Massimo 2 Progetti paralleli. La schermata sviluppo mostra i Progetti in corso con data di consegna stimata; la consegna genera una Notizia e applica l'effetto sugli attributi. Vincolo: chi è Cliente di un Motorista NON può sviluppare la Potenza motore.

**Scenario utente**:

> Dalle schermate gestionali il giocatore apre la schermata sviluppo. Vede i due slot
> Progetto e ne avvia uno sul Carico aerodinamico, scegliendo l'investimento: il costo
> esce dal Cap (e dalla Cassa) e compare la data di consegna stimata, in tempo per il
> GP di Monza. Tra un GP e l'altro il Progetto avanza con il calendario e la schermata
> ne mostra l'avanzamento. Alla consegna il giocatore legge la Notizia con l'esito:
> stavolta il reparto ha superato le attese, e la Stima dell'attributo si aggiorna.
> Edge case: con 2 Progetti già attivi, l'avvio di un terzo è rifiutato con messaggio
> chiaro; se la squadra è Cliente di un Motorista, la Potenza motore non è selezionabile
> e la schermata spiega il perché.

**Deliverable verificabile**:

* Il pacchetto motore espone un'API Progetti (avvio su un Attributo vettura con investimento dal Cap, durata in giorni di calendario, avanzamento col tempo di gioco, consegna con esito), senza import TUI/DB, verificabile via pytest headless.
* Il vincolo di massimo 2 Progetti paralleli è applicato dal motore: il terzo avvio viene rifiutato, verificabile via pytest.
* L'esito ha varianza con distribuzione testata: su un campione ampio esistono esiti sotto e sopra le attese, con effetto medio coerente con l'investimento, verificabile via pytest statistico con seed.
* Il vincolo Cliente è applicato dal motore: una squadra Cliente di un Motorista non può avviare Progetti su Potenza motore, verificabile via pytest.
* La consegna genera una Notizia e applica l'effetto sull'Attributo vettura (con aggiornamento della Stima visibile al giocatore), verificabile via pytest.
* La schermata sviluppo è navigabile da tastiera: elenco Progetti in corso con data di consegna stimata, avvio di un nuovo Progetto, verificabile con test Pilot; i Progetti sopravvivono al round-trip di persistenza a Checkpoint su Postgres effimero Docker.

**File da toccare**:

* `src/engine/development/` (NEW DIR)
* `src/engine/development/__init__.py` (NEW)
* `src/engine/development/projects.py` (NEW)
* `src/engine/economy/ledger.py`
* `src/persistence/development.py` (NEW)
* `supabase/migrations/XXXX_development_projects.sql` (NEW)
* `src/tui/screens/development.py` (NEW)
* `tests/engine/development/test_projects.py` (NEW)
* `tests/persistence/test_development_roundtrip.py` (NEW)
* `tests/tui/test_development_screen.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: la schermata sviluppo si apre dalle schermate gestionali con binding dedicato
- [ ] Popolata: Progetti, costi, date di consegna ed esiti sono dati reali del motore, mai placeholder
- [ ] Cliccabile: avvio Progetto e navigazione tra gli slot interamente da tastiera
- [ ] URL canonica: (previsto [N/A]: app TUI senza URL; la schermata ha nome e binding canonici stabili)
- [ ] Stati UI: empty state senza Progetti attivi, rifiuto del terzo Progetto, vincolo Cliente spiegato a schermo
- [ ] Aggiornata: l'avanzamento riflette il calendario di gioco a ogni passaggio tra GP senza riavvio
- [ ] Compatibile wireframe: (previsto [N/A]: nessun wireframe formale per il MVP TUI)

**Cosa NON fare**:

* Niente albero tecnologico (post-MVP).
* Niente AI di spesa per le squadre rivali: è T4.3.2.
* Niente Progetti invernali né carry-over di fine stagione: qui solo lo sviluppo in-season.
* Niente scritture su DB fuori dai Checkpoint (ADR 0001).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 35.
* `CONTEXT.md` § Economia (Progetto, Cap, Motorista, Cliente), § Vettura (Attributo vettura, Potenza motore), § Stagione (Notizia) e § Informazione (Stima).
* `docs/adr/0001-supabase-self-hosted-su-vps-con-salvataggi-a-checkpoint.md`.
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* T4.1.1 (<issue id="5b4a287a-4f3d-4fe2-a70a-8b11ae00634c" href="https://linear.app/haku-inc/issue/FOR-15/t411-implementa-registro-cassa-e-cap">FOR-15</issue>, registro Cassa e Cap: la spesa Progetto passa dal registro).

## Note
Origine: Linear FOR-25 (https://linear.app/haku-inc/issue/FOR-25/t431-implementa-progetti-di-sviluppo). Etichette Linear: si, ready-for-agent.
