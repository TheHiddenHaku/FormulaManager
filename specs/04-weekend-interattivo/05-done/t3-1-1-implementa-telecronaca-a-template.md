---
id: t3-1-1-implementa-telecronaca-a-template
titolo: "T3.1.1 Implementa Telecronaca a template"
stato: done
priorita: media
dipendenze: []
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-16
---

## Contesto
Importata da Linear FOR-16: progetto "Weekend interattivo", stato Linear "Done", creata 2026-06-11.

## Obiettivo
### T3.1.1 [ ] Implementa Telecronaca a template

**Dipendenze**: T2.1.1, T2.2.1, T2.2.2, T2.3.1, T2.3.2.
**Wave**: 1.

**Scope**: modulo del motore (Python puro, zero import TUI/DB) che trasforma gli eventi di simulazione in Telecronaca testuale in italiano: libreria di template parametrici con molte varianti per ogni tipo di evento (sorpassi, pit stop, Guasti, Safety car/VSC, meteo, bandiere), tono da cronaca radiofonica, regole anti-ripetizione, output deterministico dato un RNG. È l'output primario della simulazione verso il giocatore.

**Scenario utente**: nessuno (task backend invisibile, abilitatore). Lo scenario è coperto da T3.1.2.

**Deliverable verificabile**:

* Esiste il modulo `commentary` del motore che espone una funzione pura `eventi + RNG → righe di Telecronaca in italiano`, senza alcun import da TUI o persistenza.
* Ogni tipo di evento esistente del motore (sorpasso, pit stop, Guasto, Errore, Incidente, Abbandono, Safety car, VSC, meteo/Crossover, bandiere) ha una famiglia di template parametrici con più varianti, in tono cronaca radiofonica.
* Test di copertura che enumera TUTTI i tipi evento del motore e fallisce se anche un solo tipo non ha template associato (la copertura non può regredire in silenzio).
* Golden test: stessa sequenza di eventi + stesso seed RNG → stesso testo identico, verificabile via pytest.
* Test anti-ripetizione: la stessa variante di template non compare mai in righe ravvicinate (finestra definita nel test), verificabile via pytest.

**File da toccare**:

* `src/formula_manager/engine/commentary/` (NEW DIR)
* `src/formula_manager/engine/commentary/__init__.py` (NEW)
* `src/formula_manager/engine/commentary/templates_it.py` (NEW)
* `src/formula_manager/engine/commentary/renderer.py` (NEW)
* `tests/engine/test_commentary_coverage.py` (NEW)
* `tests/engine/test_commentary_golden.py` (NEW)
* `tests/engine/test_commentary_antirepeat.py` (NEW)

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile (previsto [N/A]: task puro-motore, nessuna schermata)
- [ ] Popolata (previsto [N/A]: task puro-motore, nessuna UI da popolare)
- [ ] Cliccabile (previsto [N/A]: task puro-motore, nessuna interazione)
- [ ] URL canonica (previsto [N/A]: task puro-motore, nessuna schermata/route)
- [ ] Stati UI (previsto [N/A]: task puro-motore, nessuno stato UI)
- [ ] Aggiornata: il testo generato riflette fedelmente gli eventi del motore (golden test e test di copertura verdi)
- [ ] Compatibile wireframe (previsto [N/A]: task puro-motore, nessun layout)

**Cosa NON fare**:

* Niente LLM né generazione di testo esterna: solo template parametrici deterministici (ADR 0003).
* Niente UI/widget Textual: il consumo della Telecronaca a schermo è T3.1.2.
* Niente persistenza della Telecronaca su DB.
* Niente lingue oltre l'italiano.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (user story 26).
* `CONTEXT.md` (Telecronaca, Tick, Evento chiave, Mescola, Guasto, Abbandono, Safety car, VSC, Crossover).
* `docs/adr/0003-telecronaca-a-template-parametrici-senza-llm.md`.
* `docs/adr/0002-textual-come-tui-con-motore-di-gioco-puro.md` (vincolo motore puro).
* T2.2.x / T2.3.x (eventi del motore di gara da coprire).

## Note
Origine: Linear FOR-16 (https://linear.app/haku-inc/issue/FOR-16/t311-implementa-telecronaca-a-template). Etichette Linear: si, ready-for-agent.
Dipendenze cross-progetto su Linear (non risolte come slug locali): t2-2-2-implementa-sfiga-guasti-errori-incidenti (FOR-11), t2-3-2-implementa-meteo-e-crossover (FOR-13), t2-1-1-implementa-modello-passo-e-gara-base (FOR-8), t2-3-1-implementa-safety-car-e-vsc (FOR-12), t2-2-1-implementa-mescole-degrado-e-pit-stop (FOR-10).
