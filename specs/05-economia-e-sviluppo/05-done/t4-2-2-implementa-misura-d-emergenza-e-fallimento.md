---
id: t4-2-2-implementa-misura-d-emergenza-e-fallimento
titolo: "T4.2.2 Implementa Misura d'emergenza e fallimento"
stato: done
priorita: media
dipendenze: [t4-1-2-implementa-entrate-e-stipendi]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-24
---

## Contesto
Importata da Linear FOR-24: progetto "Economia e sviluppo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T4.2.2 [ ] Implementa Misura d'emergenza e fallimento

**Dipendenze**: T4.1.2.

**Wave**: 2.

**Scope**: dare conseguenze reali all'insolvenza: con Cassa insufficiente le spese facoltative si bloccano (Progetti sospesi); se gli stipendi non sono coperti scatta UNA sola Misura d'emergenza per stagione — prestito con interessi oppure sponsor-tampone con malus Prestigio, a scelta del giocatore; insolvenza protratta per N gare consecutive significa fallimento e fine della Carriera con schermata dedicata.

**Scenario utente**:

> La Cassa del giocatore non copre la scadenza stipendi. Il gioco apre la schermata
> Misura d'emergenza con due opzioni: prestito con interessi, con piano di rientro a
> rate sulle gare successive, oppure sponsor-tampone, denaro subito in cambio di un
> malus al Prestigio. Il giocatore sceglie il prestito e vede il piano di rientro con
> rate e date di gioco; la Cassa torna a coprire gli stipendi e il movimento compare
> nello storico con causale. Finché la squadra non è sana, le spese facoltative
> restano bloccate e i Progetti sospesi, con messaggio chiaro al tentativo di spesa.
> Edge case: seconda insolvenza nella stessa stagione → nessuna nuova Misura
> disponibile: parte il conto alla rovescia del fallimento, visibile a ogni gara;
> dopo N gare consecutive di insolvenza appare la schermata di fine Carriera con il
> riepilogo, da cui si torna solo all'elenco delle Carriere.

**Deliverable verificabile**:

* Il motore espone stati economici espliciti (sana / bloccata / emergenza / fallita) con transizioni deterministiche interrogabili via API, senza import TUI/DB, verificabile via pytest headless.
* Con Cassa insufficiente le spese facoltative vengono rifiutate e i Progetti in corso risultano sospesi, verificabile via pytest.
* La Misura d'emergenza è attivabile UNA sola volta per stagione, nelle due varianti (prestito con interessi e piano di rientro; sponsor-tampone con malus Prestigio), con tutti gli effetti registrati nel registro con causale, verificabile via pytest.
* L'insolvenza protratta per N gare consecutive (N configurabile) porta al fallimento: la Carriera termina e non è più giocabile, verificabile via pytest su sequenze di insolvenza (insolvenza → Misura → rientro; insolvenza → seconda insolvenza → conto alla rovescia → fallimento).
* La schermata di scelta della Misura e la schermata di fine Carriera sono raggiungibili e testate con Pilot; lo stato economico sopravvive al round-trip di persistenza a Checkpoint su Postgres effimero Docker.

**File da toccare**:

* `src/engine/economy/solvency.py` (NEW)
* `src/engine/economy/emergency.py` (NEW)
* `src/engine/economy/ledger.py`
* `src/persistence/economy.py`
* `src/tui/screens/emergency_measure.py` (NEW)
* `src/tui/screens/game_over.py` (NEW)
* `tests/engine/economy/test_solvency.py` (NEW)
* `tests/engine/economy/test_emergency.py` (NEW)
* `tests/tui/test_emergency_and_game_over.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: la schermata Misura d'emergenza si apre da sola all'insolvenza sugli stipendi; la schermata di fine Carriera al fallimento
- [ ] Popolata: opzioni con importi, interessi, rate e malus reali calcolati dal motore, mai placeholder
- [ ] Cliccabile: la scelta tra prestito e sponsor-tampone è navigabile e confermabile da tastiera
- [ ] URL canonica: (previsto [N/A]: app TUI senza URL; le due schermate hanno nomi canonici stabili)
- [ ] Stati UI: stato economico visibile (bloccata/emergenza), conto alla rovescia del fallimento, messaggio di rifiuto per spese bloccate
- [ ] Aggiornata: saldi e stato economico si aggiornano subito dopo la scelta della Misura
- [ ] Compatibile wireframe: (previsto [N/A]: nessun wireframe formale per il MVP TUI)

**Cosa NON fare**:

* Niente bailout infiniti: una sola Misura d'emergenza per stagione, senza eccezioni.
* Niente vendita squadra.
* Niente calcolo di Danni e Sforamento: è T4.2.1.
* Niente scritture su DB fuori dai Checkpoint (ADR 0001).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 33.
* `CONTEXT.md` § Economia (Misura d'emergenza, Cassa, Progetto) e § Stagione (Prestigio, Carriera, Checkpoint).
* `docs/adr/0001-supabase-self-hosted-su-vps-con-salvataggi-a-checkpoint.md`.
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* T4.1.2 (<issue id="9ee2219c-746d-4ae0-a0e2-fe6f4a71e498" href="https://linear.app/haku-inc/issue/FOR-22/t412-implementa-entrate-e-stipendi">FOR-22</issue>, entrate e stipendi: la scadenza stipendi che innesca l'insolvenza).

## Note
Origine: Linear FOR-24 (https://linear.app/haku-inc/issue/FOR-24/t422-implementa-misura-demergenza-e-fallimento). Etichette Linear: si, ready-for-agent.
