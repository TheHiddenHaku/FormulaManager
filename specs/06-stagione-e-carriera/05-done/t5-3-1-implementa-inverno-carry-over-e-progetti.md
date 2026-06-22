---
id: t5-3-1-implementa-inverno-carry-over-e-progetti
titolo: "T5.3.1 Implementa Inverno: Carry-over e Progetti invernali"
stato: done
priorita: media
dipendenze: [t5-2-1-implementa-mercato-piloti]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-32
---

## Contesto
Importata da Linear FOR-32: progetto "Stagione e carriera", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T5.3.1 [ ] Implementa Inverno: Carry-over e Progetti invernali

**Dipendenze**: T5.2.1, T4.3.1.
**Wave**: 3.

**Scope**: la fase inverno tra le stagioni: la vettura nuova eredita una quota degli attributi con regressione verso la media di griglia (Carry-over), si decidono i Progetti invernali con budget dedicato, si rinegoziano le scelte di fondo (motore in proprio vs Cliente di un Motorista, Filosofia telaio) e l'economia fa rollover (nuovo Cap, eventuale penalità da Sforamento, Sponsor annuale).

**Scenario utente**:
Il giocatore chiude la stagione 4° in classifica costruttori. Si apre la fase inverno: vede la proiezione Carry-over della vettura 2027 (attributi ereditati con regressione verso la media di griglia), il nuovo Cap con l'eventuale penalità da Sforamento e lo Sponsor annuale proporzionale al Prestigio. Distribuisce il budget sui Progetti invernali, cambia Motorista (da Cliente del fornitore debole a Cliente di quello forte) e conferma la Filosofia telaio. Avvia il 2027: la griglia è rimescolata, i dominatori dell'anno prima sono rientrati verso il gruppo. Edge case: se non decide nulla, l'inverno applica comunque Carry-over e rollover con default espliciti e dichiarati.

**Deliverable verificabile**:

* Esiste il Carry-over: la vettura nuova eredita una quota degli attributi con regressione verso la media di griglia, verificabile via test pytest con valori noti.
* La regressione comprime i distacchi: simulazione headless multi-stagione mostra che nessuna squadra domina per sempre (spread di griglia che non diverge), verificata da test dedicato.
* Esistono i Progetti invernali con budget dedicato, scelti in una schermata navigabile da tastiera, verificabili via Pilot.
* Le scelte di fondo sono rinegoziabili in inverno: motore in proprio vs Cliente di un Motorista e Filosofia telaio, con effetti applicati alla stagione nuova, verificabili via test.
* Il rollover economico applica nuovo Cap, eventuale penalità da Sforamento e Sponsor annuale legato al Prestigio, verificabile via test su casi limite (Sforamento zero e Sforamento pesante).
* La transizione di stagione è completa e senza perdita dati: Checkpoint transazionale, verificabile su Postgres effimero Docker.

**File da toccare**:

* `engine/winter/__init__.py` (NEW DIR)
* `engine/winter/carryover.py` (NEW)
* `engine/winter/projects.py` (NEW)
* `engine/winter/renegotiation.py` (NEW)
* `engine/economy/rollover.py` (NEW)
* `tui/screens/winter.py` (NEW)
* `persistence/repositories/season_transition.py` (NEW)
* `supabase/migrations/<timestamp>_winter_carryover.sql` (NEW)
* `tests/engine/test_carryover_regression.py` (NEW)
* `tests/engine/test_economy_rollover.py` (NEW)
* `tests/tui/test_winter_screen.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: la fase inverno si apre nel flusso di fine stagione, dopo il Mercato piloti
- [ ] Popolata: proiezione Carry-over, budget, Progetti invernali, opzioni Motorista e Filosofia telaio
- [ ] Cliccabile: tutte le decisioni invernali prendibili da tastiera
- [ ] URL canonica: schermata inverno con id/binding canonico nell'app Textual
- [ ] Stati UI: nessuno Sforamento, Sforamento con penalità, scelte lasciate a default
- [ ] Aggiornata: attributi, Cap e Cassa della stagione nuova coerenti con le scelte; Checkpoint a fine fase
- [ ] Compatibile wireframe: layout coerente con le schermate TUI esistenti

**Cosa NON fare**:

* Niente cambi di regolamento tra stagioni (post-MVP).
* Niente modifiche al Mercato piloti (è T5.2.1) né al ricambio generazionale (è T5.2.2).
* Niente Progetti in-season: qui si trattano solo i Progetti invernali.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 42)
* `CONTEXT.md` (Carry-over, Progetto invernale, Motorista, Cliente, Filosofia telaio, Cap, Sforamento, Sponsor annuale, Prestigio)
* `docs/adr/0001` (persistenza: scritture solo a Checkpoint)
* `docs/adr/0002` (Textual + motore puro)
* Task a monte: T5.2.1, T4.3.1

## Note
Origine: Linear FOR-32 (https://linear.app/haku-inc/issue/FOR-32/t531-implementa-inverno-carry-over-e-progetti-invernali). Etichette Linear: si, ready-for-agent.
Dipendenze cross-progetto su Linear (non risolte come slug locali): t4-3-1-implementa-progetti-di-sviluppo (FOR-25).
