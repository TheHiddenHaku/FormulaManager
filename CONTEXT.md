# Formula Manager

Gioco manageriale di motorsport single-player su terminale (TUI), ispirato alla Formula 1 con nomi di fantasia. Il giocatore gestisce una squadra in una Carriera pluristagionale; ogni stagione è modellata sul calendario F1 2026 reale.

## Language

### Gara

**Gara interattiva**:
La sessione di gara scorre in tempo simulato con velocità regolabile; il manager può mettere in pausa in qualsiasi momento per impartire ordini.
_Avoid_: simulazione batch, replay

**Auto-pausa**:
Interruzione automatica della simulazione quando si verifica un Evento chiave, in attesa di una decisione del manager.

**Evento chiave**:
Accadimento di gara che richiede (o merita) una decisione del manager: safety car, pioggia in arrivo, finestra di undercut, guasto, incidente, crossover gomme.

**Mescola**:
Uno dei tipi di pneumatico. Gamma stagionale C1-C5 più Intermedia e Bagnato; ogni GP ne nomina 3 da asciutto (Soft/Medium/Hard relative). In gara asciutta vige l'obbligo di usare almeno 2 mescole diverse.

**Degrado**:
La perdita di prestazione di un set di gomme con i giri, modulata da mescola, circuito, Gestione gomme (vettura e pilota) e Aggressività.

**Crossover**:
Il momento in cui il cambio tipo di gomma (slick ↔ intermedia ↔ bagnato) diventa conveniente per il variare delle condizioni. È un Evento chiave.

**Guasto**:
Cedimento meccanico estratto giro per giro in funzione dell'Affidabilità. Può causare un Abbandono.

**Errore**:
Sbavatura di un pilota estratta giro per giro in funzione della Costanza, aggravata da Push, pioggia e duelli.

**Incidente**:
Contatto o uscita che può coinvolgere una o più vetture; può causare Abbandoni e innescare Safety car o VSC.

**Abbandono**:
L'uscita definitiva di una vettura dalla sessione (DNF).
_Avoid_: ritiro (riservato al Ritiro di carriera)

**Safety car**:
Neutralizzazione piena: il gruppo si compatta, pit stop a costo ridotto, ripartenza ad alto rischio. Probabilità influenzata dal circuito.

**VSC**:
Neutralizzazione leggera: distacchi congelati, pit stop scontato, nessun compattamento.

**Telecronaca**:
Il flusso testuale leggibile che racconta le sessioni in tempo simulato. È l'output primario della simulazione verso il giocatore.

**Tick**:
L'unità atomica di avanzamento della simulazione di gara: un giro completo per ogni vettura. Sorpassi, pit stop ed eventi casuali si risolvono dentro al giro.
_Avoid_: settore, frame, step temporale

**Ordine**:
Istruzione impartita dal manager a un pilota durante la gara. Gli Ordini del MVP sono: pit stop con scelta mescola, Aggressività, Ordine di scuderia, Istruzione sui duelli.
_Avoid_: comando, azione

**Aggressività**:
Livello di spinta richiesto a un pilota (Push / Normale / Conserva). Influenza passo, degrado gomme e rischio di errori.

**Ordine di scuderia**:
Ordine che regola i rapporti tra i due piloti della stessa squadra: scambio posizioni, congelamento posizioni, divieto di attacco al compagno.
_Avoid_: team order (in italiano nel progetto)

**Istruzione sui duelli**:
Ordine che regola il comportamento di un pilota nei confronti diretti con vetture avversarie: difendi duro / non rischiare. Distinta dall'Aggressività, che riguarda il passo.

### Vettura

**Attributo vettura**:
Uno dei 6 assi che definiscono la competitività di una vettura: Potenza motore, Carico aerodinamico, Efficienza aerodinamica, Meccanica, Gestione gomme, Affidabilità. I circuiti pesano gli attributi, gli sviluppi li migliorano.
_Avoid_: statistica, caratteristica, parametro

**Potenza motore**:
Attributo vettura: prestazione del propulsore in accelerazione e allungo.

**Carico aerodinamico**:
Attributo vettura: aderenza generata nelle curve medio-veloci. In tensione con l'Efficienza aerodinamica.

**Efficienza aerodinamica**:
Attributo vettura: bassa resistenza all'avanzamento, determina la velocità di punta. In tensione con il Carico aerodinamico.
_Avoid_: drag (come termine di gioco)

**Meccanica**:
Attributo vettura: trazione e comportamento nelle curve lente e sui cordoli.
_Avoid_: telaio (riservato alla scelta di filosofia in fase di setup squadra)

**Gestione gomme**:
Attributo vettura: quanto la vettura preserva gli pneumatici dal degrado.

**Affidabilità**:
Attributo vettura: probabilità inversa di guasti meccanici in sessione.

**Filosofia telaio**:
Scelta di progetto, presa alla creazione della squadra e rinegoziabile ogni inverno, che sbilancia la vettura verso i circuiti veloci (Efficienza aerodinamica) oppure tecnici/lenti (Carico aerodinamico e Meccanica).

### Pilota

**Attributo pilota**:
Uno dei 6 assi visibili che definiscono un pilota: Giro secco, Passo gara, Duelli, Gestione gomme (pilota), Bagnato, Costanza. Ognuno ha un momento riconoscibile in cui agisce in telecronaca.

**Potenziale**:
Attributo nascosto di un pilota: margine di crescita (o declino) nel corso della Carriera. Si rivela indirettamente con le prestazioni.

**Ritiro (carriera)**:
Uscita di scena di un pilota anziano a fine stagione. Possibile, non obbligatorio; il posto viene preso da un Giovane generato.
_Avoid_: ritiro (in gara) — usare "Abbandono" per il DNF

**Giovane**:
Pilota generato proceduralmente che entra nel roster per rimpiazzare i ritiri di carriera.
_Avoid_: regen, rookie

### Stagione

**Carriera**:
La partita del giocatore: una sequenza aperta di stagioni con la stessa squadra. I piloti invecchiano tra una stagione e l'altra. Possono esistere più Carriere parallele e indipendenti.
_Avoid_: salvataggio, partita singola

**Checkpoint**:
Punto di salvataggio transazionale: fine di ogni sessione e pre-gara. Lo stato vive in memoria durante il gioco; ricaricare un Checkpoint ri-estrae gli eventi casuali (reroll consentito, per scelta di design).
_Avoid_: autosave, snapshot

**Test pre-season**:
I giorni di prova prima del primo GP della stagione: per ogni giorno e pilota si assegna un Programma. Stringono le Stime e riducono i rischi di inizio stagione.

**Evento extra-gara**:
Accadimento casuale tra un GP e l'altro, estratto da un pool leggero (al più uno per intervallo): sponsor una tantum, progetto ritardato o accelerato, guaio in fabbrica di un rivale. Produce una Notizia.

**Notizia**:
La voce in stile rassegna stampa con cui un Evento extra-gara viene comunicato al giocatore.

**Prestigio**:
La reputazione di una squadra, costruita dai risultati. Scala lo Sponsor annuale e l'appetibilità della squadra sul Mercato piloti.

**Contratto**:
Accordo tra squadra e pilota con durata (1-3 stagioni) e stipendio. I contratti in scadenza alimentano il Mercato piloti.

**Mercato piloti**:
La finestra di fine stagione in cui squadre AI e giocatore ingaggiano i piloti con Contratto in scadenza e i Giovani.

**Carry-over**:
La regola per cui la vettura della stagione successiva eredita una quota degli attributi attuali, con regressione verso la media di griglia, più i frutti dei Progetti invernali.

**Progetto invernale**:
Investimento di sviluppo deciso tra la fine di una stagione e l'inizio della successiva, incluse le scelte rinegoziabili di motore e filosofia telaio.

### Informazione

**Stima**:
Il valore di un attributo (vettura o pilota) come appare al giocatore: un intervallo con margine di incertezza, non un numero esatto. Test, prove libere e gare disputate stringono il margine.
_Avoid_: valore approssimato, rating visibile

**Classifica tempi**:
I tempi sul giro di ogni vettura in ogni sessione. Sono sempre esatti e visibili per tutti: il cronometro non mente mai.
_Avoid_: timesheet

**Tempo sporco**:
Un tempo esatto di una vettura rivale il cui contesto (carburante, programma, mescola) non è noto al giocatore: vero ma non direttamente confrontabile. Interpretarlo è parte del gioco.

**Programma**:
L'attività assegnata a un pilota in un giorno di test o in uno slot di prove libere. Nei test: Sviluppo, Conoscenza, Affidabilità. Nelle libere: Setup, Gomme, Focus qualifica, Passo gara, Strategia. Produce effetti validi per il weekend (libere) o per la stagione (test).
_Avoid_: piano di lavoro, task

### Economia

**Cassa**:
Il denaro effettivamente disponibile alla squadra. Alimentata da Premi gara, Sponsor annuale e Montepremi costruttori; consumata da spese e stipendi.
_Avoid_: budget (ambiguo col Cap)

**Cap**:
Il tetto di spesa stagionale identico per tutte le squadre ($215M, come il budget cap F1 2026). Si spende fino al minore tra Cassa e Cap residuo. Gli stipendi piloti sono esclusi dal Cap e pesano solo sulla Cassa.
_Avoid_: budget cap (abbreviare in Cap), tetto

**Premio gara**:
Entrata incassata dopo ogni Gran Premio in base al piazzamento.

**Sponsor annuale**:
Entrata garantita a inizio stagione, proporzionale al prestigio della squadra (classifica costruttori della stagione precedente).

**Montepremi costruttori**:
Entrata di fine stagione distribuita secondo la classifica costruttori finale.

**Danni**:
Il costo di riparazione dopo un Incidente o un Guasto: pesa sulla Cassa E consuma Cap, come nella F1 reale.

**Sforamento**:
Cap negativo causato da Danni obbligatori (la vettura corre sempre). Si sconta con una riduzione del Cap della stagione successiva.

**Misura d'emergenza**:
L'unico salvagente economico per stagione quando la Cassa non copre gli stipendi: prestito con interessi o sponsor-tampone con malus prestigio. Insolvenza protratta per N gare = fallimento e fine Carriera.

**Motorista**:
Produttore di motori del mondo di gioco (3-4, con nomi editabili). Una squadra produce in proprio oppure è Cliente di un Motorista: in quel caso la sua Potenza motore è quella del fornitore, condivisa con gli altri Clienti.

**Cliente**:
Squadra che acquista il motore da un Motorista: canone più basso, ma nessun controllo sullo sviluppo della Potenza motore.

**Progetto**:
Investimento di sviluppo in-season su un attributo: ha un costo (dal Cap), una durata in giorni di calendario e un esito con varianza. Massimo 2 Progetti paralleli.
_Avoid_: upgrade, ricerca

**Griglia**:
Le 11 squadre (10 AI + la squadra del giocatore) e i 22 piloti che disputano la stagione. Replica la dimensione della griglia F1 2026 reale.

**Calendario**:
I 24 Gran Premi della stagione 2026 come da annuncio originale (inclusi Bahrain e Jeddah, poi cancellati nella realtà), con date e pause reali.

**Formato weekend**:
La struttura delle sessioni di un Gran Premio. Nel MVP esiste solo il formato Standard (prove libere, Q1/Q2/Q3, gara); il formato Sprint è previsto dal modello ma post-MVP.

**Qualifiche**:
Q1 (22 vetture, 6 eliminate) → Q2 (16 vetture, 6 eliminate) → Q3 (10 vetture), come nella F1 2026 reale.

## Flagged ambiguities

- **"Budget"** è bandito: si dice **Cassa** (quanto hai) o **Cap** (quanto puoi spendere). Sono vincoli diversi e si vince/perde su entrambi.
- **"Ritiro"** da solo è ambiguo: in gara si dice **Abbandono** (DNF), a fine carriera **Ritiro (carriera)**.
- **"Telaio"** indica solo la **Filosofia telaio**; l'attributo vettura corrispondente si chiama **Meccanica**.
- I **tempi sul giro sono sempre esatti** (Classifica tempi); l'incertezza esiste solo nelle **Stime** degli attributi. Un tempo rivale può essere **sporco** (contesto ignoto), mai falso.

## Example dialogue

> **Dev:** Quando arriva la safety car, la simulazione continua?
> **Esperto:** No: la safety car è un Evento chiave, quindi scatta l'Auto-pausa e la Telecronaca si ferma finché il manager non decide se rientrare ai box.
>
> **Dev:** Nei test vedo il livello vero della mia vettura?
> **Esperto:** Vedi i tempi esatti di tutti — il cronometro non mente — ma gli attributi restano Stime: i Programmi di Conoscenza stringono il margine, e i tempi dei rivali sono sporchi finché non li interpreti.
>
> **Dev:** Il mio pilota ha sbattuto: quanto mi costa?
> **Esperto:** Due volte: i Danni escono dalla Cassa e consumano Cap. Se il Cap residuo non basta, la riparazione avviene comunque e lo Sforamento ti riduce il Cap dell'anno prossimo.

## Mappa dei nomi nel codice

Il codice si scrive in inglese: identificatori, moduli, file, commenti inline e schema SQL. L'italiano resta per la documentazione, i testi mostrati al giocatore, le docstring discorsive e il glossario di dominio qui sopra. Questa tabella e' la mappa vincolante tra termine di dominio e identificatore inglese: ogni identificatore nuovo deve rispettarla. Lessico motorsport in inglese britannico (tyre, non tire).

### Entita'

| Termine di dominio | Identificatore |
| --- | --- |
| Mondo | `World` |
| Squadra | `Team` |
| Slot del giocatore | `PlayerSlot` |
| Pilota | `Driver` |
| Motorista | `EngineSupplier` |
| Contratto | `Contract` |
| Personalita' di spesa | `SpendingPersonality` |
| Configurazione del Mondo | `WorldConfig` |
| Carriera | `Career` |
| Riepilogo di Carriera | `CareerSummary` |
| Carriera non trovata (errore) | `CareerNotFoundError` |
| Circuito | `Circuit` |
| Calendario | `CALENDAR_2026` |
| Iscritta alla gara (pilota + squadra + vettura) | `RaceEntry` |
| Attributi vettura di una iscritta | `CarAttributes` |
| Stato di gara | `RaceState` |
| Stato in gara di una vettura | `CarRaceState` |
| Ordini (del manager, per Tick) | `Orders` |
| Aggressivita' | `Aggression` (valori: `push`, `normal`, `conserve`) |
| Ordine di scuderia | `TeamOrder` (valori: `swap_positions`, `hold_positions`, `no_attack`) |
| Istruzione sui duelli | `DuelInstruction` (valori: `standard`, `defend_hard`, `no_risk`) |
| Sorpasso (evento) | `Overtake` |
| Giro veloce (evento) | `FastestLap` |
| Bandiera a scacchi (evento) | `ChequeredFlag` |
| Riga di classifica finale | `ClassifiedResult` |

### Attributi pilota

| Termine di dominio | Identificatore |
| --- | --- |
| Giro secco | `one_lap_pace` |
| Passo gara | `race_pace` |
| Duelli | `duels` |
| Gestione gomme (pilota) | `tyre_management` |
| Bagnato | `wet_weather` |
| Costanza | `consistency` |
| Potenziale | `potential` |

### Attributi vettura

| Termine di dominio | Identificatore |
| --- | --- |
| Potenza motore | `engine_power` |
| Carico aerodinamico | `downforce` |
| Efficienza aerodinamica | `aero_efficiency` |
| Meccanica | `mechanical_grip` |
| Gestione gomme (vettura) | `tyre_management` |
| Affidabilita' | `reliability` |
| Filosofia telaio | `chassis_philosophy` (valori: `fast`, `balanced`, `technical`) |

### Personalita' di spesa

| Termine di dominio | Identificatore |
| --- | --- |
| Profilo aggressiva / equilibrata / prudente | `aggressive` / `balanced` / `cautious` |
| Propensione alla spesa | `spending_propensity` |
| Tolleranza al rischio | `risk_tolerance` |

### Altri attributi ricorrenti

| Termine di dominio | Identificatore |
| --- | --- |
| nome | `name` |
| eta' | `age` |
| nazionalita' | `nationality` |
| ritirato (carriera) | `retired` |
| squadra del giocatore (flag) | `is_player` |
| Prestigio | `prestige` |
| Cassa | `cash_usd` |
| stipendio | `salary_usd` |
| ingaggio richiesto | `salary_demand_usd` |
| canone Cliente | `customer_fee_usd` |
| stagione di inizio | `start_season` |
| durata in stagioni | `duration_seasons` |
| Formato weekend | `weekend_format` (valori: `standard`, `sprint`) |
| Severita' gomme | `tyre_severity` |
| probabilita' Safety car | `safety_car_probability` |
| profilo meteo | `weather_profile` (valori: `dry`, `variable`, `wet`) |
| rilevante per il Cap | `counts_against_cap` |
| data di gioco | `game_date` |
| data della gara | `race_date` |
| giri completati | `laps_completed` |
| posizione | `position` |
| punti | `points` |
| importo | `amount_usd` |
| codice | `code` |
| colori livrea | `primary_color`, `secondary_color` |
| creata il | `created_at` |
| data ultimo Checkpoint | `last_checkpoint_at` |

### Tabelle SQL

| Termine di dominio | Tabella |
| --- | --- |
| Carriere | `careers` |
| Squadre | `teams` |
| Piloti | `drivers` |
| Motoristi | `engine_suppliers` |
| Contratti | `contracts` |
| Circuiti | `circuits` |
| Stagioni | `seasons` |
| Gran Premi | `grands_prix` |
| Sessioni | `sessions` |
| Risultati | `results` |
| Transazioni economiche | `financial_transactions` |
| Progetti di sviluppo | `development_projects` |
| Tabelle punti | `points_tables` |
| Premi gara | `race_prizes` |

La colonna `career_id` resta invariata in tutte le tabelle di stato.

### Moduli e pacchetti

| Area | Modulo |
| --- | --- |
| Motore di gioco | `fm_engine` |
| Mondo (modelli, generazione, nazionalita') | `fm_engine.world` (`models`, `generation`, `nationalities`) |
| Carriera | `fm_engine.career` |
| Motore di gara (circuiti, eventi, stato, tempi, punti, riduttore) | `fm_engine` (`circuits`, `events`, `state`, `laptime`, `points`, `race`) |
| Persistenza (connessione, mappatura, checkpoint) | `fm_persistence` (`connection`, `mapping`, `checkpoint`) |
| TUI (schermate, widget) | `fm_tui` (`screens`, `widgets`) |

### Funzioni e simboli canonici

| Operazione | Identificatore |
| --- | --- |
| Generazione del Mondo | `fm_engine.world.generate` |
| Salvataggio Carriera | `save_career` |
| Caricamento Carriera | `load_career` |
| Elenco Carriere | `list_careers` |
| Eliminazione Carriera | `delete_career` |
| Connessione al database | `connect` |
| URL del database | `database_url` |
| Variabile d'ambiente canonica | `ENV_VAR` (il valore resta `FM_DATABASE_URL`) |
| Partenza della gara | `start_race` |
| Avanzamento di un Tick | `step` |
| Punti per posizione (2026) | `points_for_position` |
| Circuito dal codice | `circuit_by_code` |

### Schermate Textual (nomi canonici)

`career_list`, `new_career`, `grid`, `delete_confirmation`. I testi mostrati al giocatore restano in italiano.
