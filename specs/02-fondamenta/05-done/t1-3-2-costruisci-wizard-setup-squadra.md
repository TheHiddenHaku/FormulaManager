---
id: t1-3-2-costruisci-wizard-setup-squadra
titolo: "T1.3.2 Costruisci wizard Setup squadra"
stato: done
priorita: media
dipendenze: [migra-codice-e-schema-a-naming-inglese, t1-3-1-costruisci-tui-shell-e-gestione-carriere]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-7
---

## Contesto
Importata da Linear FOR-7: progetto "Fondamenta", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T1.3.2 [ ] Costruisci wizard Setup squadra

**Dipendenze**: T1.3.1.
**Wave**: 3.

**Scope**: costruire il wizard post-creazione della Carriera con cui il giocatore compone la sua squadra: 2 piloti dal roster con Stime e ingaggio richiesto, motore interno oppure Cliente di un Motorista, Filosofia telaio (veloce vs tecnico) con effetto sugli attributi vettura iniziali. Le scelte si persistono al Checkpoint e si chiude con il riepilogo squadra.

**Scenario utente**: dopo la creazione della Carriera, il giocatore entra nel wizard di Setup squadra. Passo 1: sceglie 2 piloti dal roster, ognuno con Stime sui 6 Attributi pilota, età e ingaggio richiesto. Passo 2: sceglie tra motore interno (costo alto, sviluppo libero) ed essere Cliente di un Motorista (canone più basso, Potenza motore condivisa con il fornitore). Passo 3: sceglie la Filosofia telaio (veloce vs tecnico) e vede l'effetto sugli attributi vettura iniziali, mostrati come Stime. Riepilogo finale della squadra; conferma e salvataggio al Checkpoint. Naviga tutto da tastiera e può tornare al passo precedente. Edge case: non può confermare il passo piloti con meno di 2 piloti selezionati.

**Deliverable verificabile**:

* Wizard in 3 passi interamente navigabile da tastiera, con binding visibili e ritorno al passo precedente.
* Passo piloti: roster con Stime sui 6 Attributi pilota, età e ingaggio richiesto; selezione di esattamente 2 piloti, vincolo verificato.
* Passo motore: scelta interno vs Cliente con le differenze mostrate (costo alto e sviluppo libero vs canone e Potenza motore condivisa).
* Passo Filosofia telaio: la scelta veloce/tecnico si riflette negli attributi vettura iniziali (Efficienza aerodinamica vs Carico aerodinamico e Meccanica).
* Riepilogo finale della squadra; alla conferma le scelte sono persistite al Checkpoint e ricaricabili.
* Unit test motore sull'applicazione delle scelte agli attributi vettura; test Pilot sul flusso completo del wizard.

**File da toccare**:

* `src/fm_engine/mondo/setup_squadra.py` (NEW: applicazione di scelte piloti, motore, Filosofia telaio)
* `src/fm_tui/schermate/setup_squadra.py` (NEW)
* `src/fm_tui/schermate/nuova_carriera.py` (aggancio del wizard al flusso di creazione)
* `tests/engine/mondo/test_setup_squadra.py` (NEW)
* `tests/tui/test_setup_squadra.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: il wizard parte automaticamente dopo la creazione della Carriera
- [ ] Popolata: roster con Stime e ingaggi, opzioni motore e Filosofia telaio con effetti mostrati
- [ ] Cliccabile: wizard interamente navigabile da tastiera, avanti e indietro tra i passi
- [ ] URL canonica (previsto [N/A]: TUI senza routing; i passi del wizard hanno nomi canonici)
- [ ] Stati UI: conferma bloccata con meno di 2 piloti; riepilogo prima del salvataggio
- [ ] Aggiornata: le scelte si riflettono subito nel riepilogo e persistono al Checkpoint
- [ ] Compatibile wireframe (previsto [N/A]: nessun wireframe; il riferimento di layout è il PRD)

**Cosa NON fare**:

* Niente stipendi ricorrenti (è T4.1.2).
* Niente Mercato piloti né Contratti negoziabili: il roster iniziale viene dal Mondo generato.
* Niente rinegoziazione invernale di motore o Filosofia telaio (post-Fondamenta).
* Niente economia runtime (Cassa/Cap) oltre ai costi mostrati nel wizard.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (story 3, 4, 5).
* `CONTEXT.md` (Stima, Motorista, Cliente, Filosofia telaio, Attributo pilota, Attributo vettura, Checkpoint).
* `docs/adr/0001` (persistenza), `docs/adr/0002` (Textual + motore puro).
* T1.2.1 (Mondo e roster), T1.3.1 (shell TUI e flusso nuova Carriera).

## Note
Origine: Linear FOR-7 (https://linear.app/haku-inc/issue/FOR-7/t132-costruisci-wizard-setup-squadra). Etichette Linear: si, ready-for-agent.
