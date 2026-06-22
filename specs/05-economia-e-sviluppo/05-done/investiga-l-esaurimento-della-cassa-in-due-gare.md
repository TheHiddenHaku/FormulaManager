---
id: investiga-l-esaurimento-della-cassa-in-due-gare
titolo: "Investiga l'esaurimento della Cassa in due gare"
stato: done
priorita: media
dipendenze: []
etichette: [si]
creata: 2026-06-13
scadenza:
linear: FOR-43
---

## Contesto
Importata da Linear FOR-43: progetto "Economia e sviluppo", stato Linear "Done", creata 2026-06-13.

## Obiettivo
### [ ] Investiga l'esaurimento della Cassa in due gare

**Stima**: 2-3h (diagnosi piu' eventuale taratura).

**Dipendenze**: nessuna. Tocca codice gia' esistente dell'economia (registro <issue id="5b4a287a-4f3d-4fe2-a70a-8b11ae00634c" href="https://linear.app/haku-inc/issue/FOR-15/t411-implementa-registro-cassa-e-cap">FOR-15</issue>, entrate e stipendi <issue id="9ee2219c-746d-4ae0-a0e2-fe6f4a71e498" href="https://linear.app/haku-inc/issue/FOR-22/t412-implementa-entrate-e-stipendi">FOR-22</issue>, Danni <issue id="0319329b-1365-434e-a692-264431382c68" href="https://linear.app/haku-inc/issue/FOR-23/t421-implementa-danni-e-sforamento">FOR-23</issue>, solvibilita' <issue id="018cfdb8-bbe7-4676-8b98-967b08566ad9" href="https://linear.app/haku-inc/issue/FOR-24/t422-implementa-misura-demergenza-e-fallimento">FOR-24</issue>).

**Wave**: nuova (bug emerso in playtest, fuori dal piano di fase).

**Scope**: capire perche' una Carriera reale esaurisce la Cassa dopo due soli Gran Premi e stabilire se e' un difetto (entrate mancanti, addebiti sovradimensionati, sviluppi non implementati) o un comportamento corretto ma mal tarato. Produce una diagnosi con i numeri alla mano e, se serve, una taratura dei parametri o un fix mirato.

**Scenario utente**:

> Alessio crea una squadra, conferma il setup e parte la stagione con la sola entrata dello Sponsor annuale in Cassa. Gioca il primo GP, poi il secondo. Alla schermata Finanze vede la Cassa gia' a zero o in negativo dopo due gare, con spese facoltative bloccate e Progetti sospesi. Si aspetta che, pur dovendo rispettare i vincoli di spesa, due gare non possano bastare a prosciugare la Cassa: il vincolo economico deve mordere nell'arco della stagione, non subito.

**Contesto tecnico** (osservazioni di partenza, da verificare in diagnosi):

* La Cassa iniziale e' solo lo Sponsor annuale: con Prestigio di partenza 50, annual_sponsor_usd(50) vale 50.000.000 USD (src/fm_engine/economy/income.py:48, src/fm_tui/screens/team_setup.py:483). Nessun'altra dotazione di partenza alimenta la Cassa.
* Il Montepremi costruttori arriva solo a fine stagione (credit_constructors_pool), quindi non aiuta nelle prime gare.
* Per gara entrano i Premi gara (credit_race_prizes, da 3.000.000 per P1 a 120.000 per P22, per vettura) ed escono: rata stipendi (charge_salary_instalments, stipendio annuale diviso per 24 GP, fuori Cap) e riparazioni Danni (charge_damage_repairs, REPAIR_COST_RATIO 1.0, addebito forzoso su Cassa e Cap).
* Ipotesi da confermare sui dati della Carriera attiva: stipendi piloti generati troppo alti rispetto alla Cassa iniziale, entita' Danni sovradimensionata, assenza di una dotazione di Cassa di partenza separata dallo Sponsor, oppure entrate di gara troppo basse.

**Deliverable verificabile**:

* Esiste una diagnosi scritta (commento sull'issue o nota nel repo) che riporta, per la Carriera attiva, il dettaglio dei movimenti delle prime due gare: entrate (Sponsor, Premi gara) e uscite (stipendi, Danni, eventuali Progetti), con il saldo Cassa risultante gara per gara.
* La diagnosi stabilisce la causa: parametro mal tarato (quale, valore attuale, valore proposto), entrata mancante, oppure comportamento corretto da accettare e documentare.
* Se e' un difetto: la taratura o il fix e' applicato e un test di bilanciamento dimostra che una stagione tipo non prosciuga la Cassa in due gare (vedi src/fm_engine/balance/simulate.py).
* I numeri tarati restano allineati tra motore e seed dove serve (es. RACE_PRIZES_2026 e la tabella race_prizes in supabase/seed.sql, come da nota in [income.py](<http://income.py>)).

**File da toccare** (stima, da rivedere in diagnosi):

* src/fm_engine/economy/income.py (entrate: Sponsor, Premi gara, parametri di taratura)
* src/fm_engine/economy/salaries.py (rata stipendi per gara)
* src/fm_engine/economy/damages.py (REPAIR_COST_RATIO, costo riparazioni)
* src/fm_engine/economy/solvency.py (regolamento post-gara, soglia insolvenza)
* src/fm_engine/world/generation.py (generazione stipendi dei Contratti, se la causa e' a monte)
* src/fm_engine/balance/simulate.py (simulazione di stagione per validare la taratura)
* supabase/seed.sql (solo se cambiano i numeri mirrorati delle entrate)

**Test**:

* Balance: una simulazione di stagione completa (vedi _simulate_season_spending in [simulate.py](<http://simulate.py>)) mostra che la Cassa di una squadra tipo resta positiva oltre la seconda gara e che il vincolo economico morde nell'arco della stagione, non alle prime due gare.
* Unit: i parametri tarati (entrate, costo Danni, rata stipendi) producono i valori attesi ai bordi.
* Manual: rigiocare due GP su una Carriera nuova e verificare alla schermata Finanze che la Cassa non vada a zero, salvo scelte di spesa volontarie del giocatore.

**Definition of Done**:

- [ ] Raggiungibile: N/A (diagnosi e taratura, nessuna nuova route)
- [ ] Popolata: N/A
- [ ] Cliccabile: N/A
- [ ] URL canonica: N/A
- [ ] Stati UI: la schermata Finanze riflette correttamente i saldi dopo il fix
- [ ] Aggiornata: i saldi mostrati derivano live dal registro
- [ ] Compatibile wireframe: N/A

**Cosa NON fare**:

* Niente test o esperimenti contro il DB di matilde: la lettura della Carriera attiva per diagnosi e' ammessa, ma simulazioni e tuning vanno su dati locali o sintetici (CLAUDE.md, sezione Database).
* Niente riscrittura del modello economico (registro, doppio vincolo Cassa/Cap): solo taratura dei parametri o fix mirati.
* Niente nuove fonti di entrata non previste dal modello (CONTEXT.md, Economia) senza prima validarle con Alessio.
* Niente refactor fuori scope dei moduli economy.

**Open question**:

* RICHIEDE INPUT ALESSIO se la causa e' una scelta di design (es. introdurre una dotazione di Cassa di partenza oltre lo Sponsor annuale) anziche' una semplice taratura dei parametri esistenti.

**Riferimenti**:

* CONTEXT.md, sezione Economia (Cassa, Cap, Premio gara, Sponsor annuale, Montepremi costruttori, Danni, Sforamento, Misura d'emergenza).
* src/fm_engine/economy/ledger.py (registro, Cassa, Cap, doppio vincolo di spesa).
* src/fm_engine/economy/income.py, [salaries.py](<http://salaries.py>), [damages.py](<http://damages.py>), [solvency.py](<http://solvency.py>) (entrate, stipendi, Danni, solvibilita').
* src/fm_tui/screens/team_setup.py:483 (accredito Sponsor annuale di partenza).
* src/fm_tui/screens/weekend.py:233 (_collect_race_economy), :259 (_settle_and_close_race): flusso economico di fine gara.
* src/fm_tui/screens/finances.py (schermata Finanze).
* src/fm_engine/balance/simulate.py (simulazione di bilanciamento).
* Issue correlate: <issue id="5b4a287a-4f3d-4fe2-a70a-8b11ae00634c" href="https://linear.app/haku-inc/issue/FOR-15/t411-implementa-registro-cassa-e-cap">FOR-15</issue>, <issue id="9ee2219c-746d-4ae0-a0e2-fe6f4a71e498" href="https://linear.app/haku-inc/issue/FOR-22/t412-implementa-entrate-e-stipendi">FOR-22</issue>, <issue id="0319329b-1365-434e-a692-264431382c68" href="https://linear.app/haku-inc/issue/FOR-23/t421-implementa-danni-e-sforamento">FOR-23</issue>, <issue id="018cfdb8-bbe7-4676-8b98-967b08566ad9" href="https://linear.app/haku-inc/issue/FOR-24/t422-implementa-misura-demergenza-e-fallimento">FOR-24</issue> (impianto economico).

## Note
Origine: Linear FOR-43 (https://linear.app/haku-inc/issue/FOR-43/investiga-lesaurimento-della-cassa-in-due-gare). Etichette Linear: si.
