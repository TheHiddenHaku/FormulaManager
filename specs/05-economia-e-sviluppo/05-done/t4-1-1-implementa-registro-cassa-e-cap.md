---
id: t4-1-1-implementa-registro-cassa-e-cap
titolo: "T4.1.1 Implementa registro Cassa e Cap"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-15
---

## Contesto
Importata da Linear FOR-15: progetto "Economia e sviluppo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T4.1.1 [ ] Implementa registro Cassa e Cap

**Dipendenze**: T1.2.2, T1.3.1.

**Wave**: 1.

**Scope**: introdurre nel motore il registro transazionale dell'economia di squadra: ogni movimento ha causale, importo e timestamp di gioco. Vige il doppio vincolo: la spesa consentita è min(Cassa, Cap residuo), con Cap stagionale fisso a $215M. I saldi sono sempre visibili in TUI tramite widget persistente e lo stato economico è persistito a Checkpoint.

**Scenario utente**:

> Il giocatore, dalla schermata principale della Carriera, apre la schermata finanze.
> Vede tre cose: la Cassa, il Cap residuo della stagione e lo storico dei movimenti,
> ognuno con causale, importo e data di gioco. Il widget con Cassa e Cap residuo
> resta visibile anche nelle altre schermate gestionali. Se tenta una spesa superiore
> al minimo tra Cassa e Cap residuo, la spesa viene rifiutata con un messaggio chiaro
> che indica quale dei due vincoli ha bloccato. Dalla schermata finanze torna alla
> schermata principale con il binding di back. Edge case: a inizio Carriera, senza
> movimenti, lo storico mostra un empty state ("Nessun movimento registrato").

**Deliverable verificabile**:

* Il pacchetto motore espone un'API di registro (registrazione movimento con causale/importo/timestamp di gioco, interrogazione di Cassa, Cap residuo e storico) senza alcun import TUI/DB, verificabile via pytest headless.
* La spesa consentita è `min(Cassa, Cap residuo $215M)`: i tentativi oltre il limite vengono rifiutati dal motore, verificabile via pytest sui casi Cassa < Cap residuo, Cap residuo < Cassa e importo esattamente al limite.
* La schermata finanze TUI mostra Cassa, Cap residuo e storico movimenti; un widget persistente con i due saldi è visibile nelle schermate gestionali, verificabile con test Pilot.
* Round-trip di persistenza a Checkpoint: il registro viene salvato via psycopg e ricaricato identico, verificabile via pytest su Postgres effimero Docker.

**File da toccare**:

* `src/engine/economy/__init__.py` (NEW DIR)
* `src/engine/economy/ledger.py` (NEW)
* `src/tui/screens/finances.py` (NEW)
* `src/tui/widgets/balance_bar.py` (NEW)
* `src/persistence/economy.py` (NEW)
* `supabase/migrations/XXXX_economy_ledger.sql` (NEW)
* `tests/engine/economy/test_ledger.py` (NEW)
* `tests/persistence/test_economy_roundtrip.py` (NEW)
* `tests/tui/test_finances_screen.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: la schermata finanze si apre dalla schermata principale con binding dedicato
- [ ] Popolata: Cassa, Cap residuo e storico mostrano dati reali del motore, mai placeholder
- [ ] Cliccabile: storico movimenti navigabile da tastiera (scroll/selezione)
- [ ] URL canonica: (previsto [N/A]: app TUI senza URL; la schermata ha nome e binding canonici stabili)
- [ ] Stati UI: empty state per registro vuoto e messaggio di rifiuto per spesa oltre il vincolo
- [ ] Aggiornata: saldi e storico riflettono l'ultimo movimento registrato senza riavvio
- [ ] Compatibile wireframe: (previsto [N/A]: nessun wireframe formale per il MVP TUI; layout da convenzioni di progetto)

**Cosa NON fare**:

* Niente entrate automatiche (Premio gara, Sponsor annuale, Montepremi costruttori) né stipendi: è T4.1.2.
* Niente Danni né Sforamento: è T4.2.1.
* Niente Progetti di sviluppo: è T4.3.1.
* Niente scritture su DB fuori dai Checkpoint (ADR 0001).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 28.
* `CONTEXT.md` § Economia (Cassa, Cap) e § Stagione (Checkpoint).
* `docs/adr/0001-supabase-self-hosted-su-vps-con-salvataggi-a-checkpoint.md`.
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* T1.2.2 (<issue id="13aef04f-fb4a-4c6a-b364-b1513438015b" href="https://linear.app/haku-inc/issue/FOR-5/t122-implementa-persistenza-a-checkpoint">FOR-5</issue>), T1.3.1 (<issue id="d71eab6d-ba5c-4432-86ad-0de590e6ed14" href="https://linear.app/haku-inc/issue/FOR-6/t131-costruisci-tui-shell-e-gestione-carriere">FOR-6</issue>).

## Note
Origine: Linear FOR-15 (https://linear.app/haku-inc/issue/FOR-15/t411-implementa-registro-cassa-e-cap). Etichette Linear: si, ready-for-agent.
Dipendenze cross-progetto su Linear (non risolte come slug locali): t1-3-1-costruisci-tui-shell-e-gestione-carriere (FOR-6), t1-2-2-implementa-persistenza-a-checkpoint (FOR-5).
