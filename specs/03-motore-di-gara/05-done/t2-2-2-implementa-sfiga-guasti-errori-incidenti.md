---
id: t2-2-2-implementa-sfiga-guasti-errori-incidenti
titolo: "T2.2.2 Implementa Sfiga: Guasti, Errori, Incidenti"
stato: done
priorita: media
dipendenze: [t2-1-1-implementa-modello-passo-e-gara-base]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-11
---

## Contesto
Importata da Linear FOR-11: progetto "Motore di gara", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T2.2.2 [ ] Implementa Sfiga: Guasti, Errori, Incidenti

**Dipendenze**: T2.1.1.

**Wave**: 2.

**Scope**: aggiungere al motore l'estrazione per giro degli eventi negativi: Guasto (in funzione inversa dell'Affidabilità), Errore pilota (in funzione della Costanza, aggravato da Push e duelli), Incidente (contatti in duello e alla partenza), con conseguenti Abbandoni (DNF) ed eventi danno con entità destinati al progetto Economia. Per decisione di design non esiste alcun correttivo nascosto anti-strisce: la sfortuna è onesta.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Lo scenario è coperto dalle issue del progetto Weekend interattivo (Guasti e Incidenti come Eventi chiave in Telecronaca) e dal progetto Economia (Danni su Cassa e Cap).

**Deliverable verificabile**:

* A ogni Tick il motore estrae: Guasti in funzione inversa dell'Affidabilità della vettura; Errori pilota in funzione della Costanza, aggravati da Aggressività Push e duelli in corso; Incidenti da contatti in duello e alla partenza.
* Gli esiti includono l'Abbandono (DNF): la vettura esce dalla sessione e dalla classifica, con evento tipizzato.
* Su 1000 gare simulate la media degli Abbandoni per gara cade in un range realistico di 3-5, con parametri configurabili; verificabile con test statistico pytest.
* Il rischio di Errore e Incidente cresce misurabilmente con Aggressività Push rispetto a Conserva (test comparativo a parità di seed di partenza).
* Ogni evento è tipizzato con causa visibile (guasto specifico, errore in frenata, contatto, ...) e gli eventi danno portano nel payload l'entità del danno, pronta per il calcolo di Danni su Cassa e Cap nel progetto Economia.
* Nessun correttivo nascosto anti-strisce: le estrazioni sono indipendenti tra giri e gare; la decisione è documentata nel codice e verificata da un test sull'indipendenza delle estrazioni.

**File da toccare**:

* `src/engine/misfortune.py` (NEW)
* `src/engine/race.py`
* `src/engine/state.py`
* `src/engine/events.py`
* `tests/engine/test_misfortune.py` (NEW)
* `tests/engine/test_dnf_rates.py` (NEW)
* `tests/engine/test_push_risk.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il modulo Sfiga è importabile dal pacchetto motore senza dipendenze TUI/DB
- [ ] Popolata: gli eventi Guasto/Errore/Incidente portano causa ed entità danno nel payload
- [ ] Cliccabile: (previsto [N/A]: task puro-motore, nessun elemento interattivo)
- [ ] URL canonica: (previsto [N/A]: nessuna route; il path canonico del modulo è `src/engine/misfortune.py`)
- [ ] Stati UI: (previsto [N/A]: nessuna UI; gli stati osservabili sono gli eventi tipizzati)
- [ ] Aggiornata: lo stato Abbandono di una vettura è effettivo dal Tick in cui viene estratto
- [ ] Compatibile wireframe: (previsto [N/A]: task puro-motore, nessuna schermata)

**Cosa NON fare**:

* Niente infortuni pilota (post-MVP).
* Niente Safety car né VSC: qui solo gli Incidenti, il trigger di neutralizzazione è T2.3.1.
* Niente calcolo economico dei Danni su Cassa e Cap (progetto Economia): solo l'entità nel payload.
* Niente correttivi nascosti anti-strisce di sfortuna (decisione di design esplicita).
* Niente testo di Telecronaca né UI (ADR 0003, ADR 0002).

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) — user story 24.
* `CONTEXT.md` (Guasto, Errore, Incidente, Abbandono, Affidabilità, Costanza, Aggressività, Danni).
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md`.
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md`.
* T2.1.1 (riduttore `step` e modello duelli su cui si innestano le estrazioni).

## Note
Origine: Linear FOR-11 (https://linear.app/haku-inc/issue/FOR-11/t222-implementa-sfiga-guasti-errori-incidenti). Etichette Linear: si, ready-for-agent.
