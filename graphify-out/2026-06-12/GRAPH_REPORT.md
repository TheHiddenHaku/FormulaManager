# Graph Report - FormulaManager  (2026-06-12)

## Corpus Check
- 92 files · ~49,730 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1235 nodes · 3323 edges · 84 communities (60 shown, 24 thin omitted)
- Extraction: 62% EXTRACTED · 38% INFERRED · 0% AMBIGUOUS · INFERRED: 1247 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b9a9e0b8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_World Models & Generation|World Models & Generation]]
- [[_COMMUNITY_Checkpoint Persistence|Checkpoint Persistence]]
- [[_COMMUNITY_Career TUI Screens|Career TUI Screens]]
- [[_COMMUNITY_Team Setup Wizard UI|Team Setup Wizard UI]]
- [[_COMMUNITY_TUI App & Pilot Tests|TUI App & Pilot Tests]]
- [[_COMMUNITY_Team Setup Engine Logic|Team Setup Engine Logic]]
- [[_COMMUNITY_Row Mapping Layer|Row Mapping Layer]]
- [[_COMMUNITY_World Generation Tests|World Generation Tests]]
- [[_COMMUNITY_Architecture Docs & ADRs|Architecture Docs & ADRs]]
- [[_COMMUNITY_Wizard Pilot Tests|Wizard Pilot Tests]]
- [[_COMMUNITY_Postgres Connection Config|Postgres Connection Config]]
- [[_COMMUNITY_Ephemeral Docker Postgres|Ephemeral Docker Postgres]]
- [[_COMMUNITY_Pure Engine Import Guard|Pure Engine Import Guard]]
- [[_COMMUNITY_Engine Placeholder Tests|Engine Placeholder Tests]]
- [[_COMMUNITY_Persistence Test Fixtures|Persistence Test Fixtures]]
- [[_COMMUNITY_DB Reset Script|DB Reset Script]]
- [[_COMMUNITY_TUI Test Fixtures|TUI Test Fixtures]]
- [[_COMMUNITY_Economy Cassa & Cap|Economy: Cassa & Cap]]
- [[_COMMUNITY_Race Auto-pause Events|Race Auto-pause Events]]
- [[_COMMUNITY_Timing & Attribute Estimates|Timing & Attribute Estimates]]
- [[_COMMUNITY_Engine Package Init|Engine Package Init]]
- [[_COMMUNITY_TUI Package Init|TUI Package Init]]
- [[_COMMUNITY_TUI Screens Init|TUI Screens Init]]
- [[_COMMUNITY_Play Launcher Script|Play Launcher Script]]
- [[_COMMUNITY_TUI Widgets Init|TUI Widgets Init]]
- [[_COMMUNITY_World Package Init|World Package Init]]
- [[_COMMUNITY_Nationalities Data|Nationalities Data]]
- [[_COMMUNITY_Telecronaca ADR|Telecronaca ADR]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]

## God Nodes (most connected - your core abstractions)
1. `step()` - 69 edges
2. `Circuit` - 66 edges
3. `circuit_by_code()` - 62 edges
4. `RaceEntry` - 55 edges
5. `Driver` - 54 edges
6. `Aggression` - 51 edges
7. `DriverOrders` - 51 edges
8. `Compound` - 46 edges
9. `Career` - 44 edges
10. `_LapRun` - 43 edges

## Surprising Connections (you probably didn't know these)
- `result()` --calls--> `simulate()`  [INFERRED]
  tests/engine/test_balance_sanity.py → src/fm_engine/balance/simulate.py
- `world()` --calls--> `generate()`  [INFERRED]
  tests/persistence/test_round_trip.py → src/fm_engine/world/generation.py
- `Template task canonico` --conceptually_related_to--> `CLAUDE.md - Regole operative Formula Manager`  [AMBIGUOUS]
  specs/templates/task-template.md → CLAUDE.md
- `AGENTS.md - Regole operative (mirror di CLAUDE.md)` --semantically_similar_to--> `CLAUDE.md - Regole operative Formula Manager`  [INFERRED] [semantically similar]
  AGENTS.md → CLAUDE.md
- `Configurazione linear-sync (team FOR)` --conceptually_related_to--> `CLAUDE.md - Regole operative Formula Manager`  [INFERRED]
  .linear-sync.yaml → CLAUDE.md

## Import Cycles
- 1-file cycle: `src/fm_engine/balance/simulate.py -> src/fm_engine/balance/simulate.py`
- 1-file cycle: `src/fm_engine/pitstop.py -> src/fm_engine/pitstop.py`
- 1-file cycle: `src/fm_engine/race.py -> src/fm_engine/race.py`
- 1-file cycle: `src/fm_engine/tyres.py -> src/fm_engine/tyres.py`
- 1-file cycle: `src/fm_engine/weather.py -> src/fm_engine/weather.py`
- 1-file cycle: `src/fm_engine/laptime.py -> src/fm_engine/laptime.py`
- 1-file cycle: `src/fm_engine/neutralization.py -> src/fm_engine/neutralization.py`
- 1-file cycle: `src/fm_engine/commentary/narrator.py -> src/fm_engine/commentary/narrator.py`
- 1-file cycle: `src/fm_engine/misfortune.py -> src/fm_engine/misfortune.py`

## Hyperedges (group relationships)
- **Architettura a tre pacchetti (motore puro / persistenza / guscio TUI)** — readme_fm_engine, readme_fm_persistence, readme_fm_tui [EXTRACTED 1.00]
- **Flusso di persistenza a Checkpoint della Carriera** — context_checkpoint, adr_0001_supabase_self_hosted_su_vps_con_salvataggi_a_checkpoint_checkpoint_persistence, readme_fm_persistence, supabase_readme_fm_database_url, supabase_readme_career_isolation [INFERRED 0.85]
- **Loop di gara interattiva in tempo simulato** — context_tick, context_evento_chiave, context_auto_pausa, context_telecronaca [INFERRED 0.85]

## Communities (84 total, 24 thin omitted)

### Community 0 - "World Models & Generation"
Cohesion: 0.18
Nodes (31): Contract, Driver, EngineSupplier, Team, World, WorldConfig, Contract, Driver (+23 more)

### Community 2 - "Career TUI Screens"
Cohesion: 0.16
Nodes (8): DataTable, Grid, Schermata griglia: le 11 squadre e i 22 piloti della Carriera (FOR-6).  Due tabe, Torna all'elenco delle Carriere., La griglia di partenza della Carriera, ad attributi a Stime., Career, ComposeResult, Driver

### Community 3 - "Team Setup Wizard UI"
Cohesion: 0.07
Nodes (19): _millions(), Wizard di Setup squadra: piloti, motore, Filosofia telaio (FOR-7).  Parte subito, Mostra il passo richiesto, nasconde gli altri, aggiorna i binding., Mostra nel Footer solo i binding sensati per il passo corrente., Avanza di un passo, validando il vincolo dei 2 piloti., Torna al passo precedente; dal primo passo esce dal wizard.          Edge accett, Invio (o click) su una riga del roster: stessa logica dello spazio., Invio su un'opzione: adotta la scelta e avanza. (+11 more)

### Community 4 - "TUI App & Pilot Tests"
Cohesion: 0.06
Nodes (49): App, FormulaManagerApp, main(), Shell TUI di Formula Manager (FOR-6).  L'app apre sull'elenco delle Carriere e d, La shell di gioco: stack di schermate sopra l'elenco Carriere., Entry point del comando fm.      Verifica la raggiungibilita' del database prima, Career, FormulaManagerApp (+41 more)

### Community 5 - "Team Setup Engine Logic"
Cohesion: 0.22
Nodes (26): apply_team_setup(), Applica le scelte del Setup squadra e ritorna il Mondo nuovo.      Valida le sce, _choices(), _contracted_ids(), _free_agent_ids(), Unit test del Setup squadra puro (FOR-7, fm_engine.world.team_setup).  Coprono l, Gli id dei primi piloti contrattualizzati nelle squadre AI., test_ai_team_losing_a_driver_receives_a_free_agent() (+18 more)

### Community 6 - "Row Mapping Layer"
Cohesion: 0.13
Nodes (32): Any, contract_from_row(), contract_params(), driver_from_row(), driver_params(), engine_supplier_from_row(), engine_supplier_params(), id_from_uuid() (+24 more)

### Community 7 - "World Generation Tests"
Cohesion: 0.13
Nodes (29): Random, WorldConfig, _amount_in_range(), _assign_supply_deals(), _draw_age(), _draw_driver_name(), generate(), _generate_contracts() (+21 more)

### Community 8 - "Architecture Docs & ADRs"
Cohesion: 0.33
Nodes (7): Persistenza a Checkpoint (stato in memoria, scritture atomiche), Carriera (Career), Checkpoint, Mappa dei nomi nel codice (dominio -> identificatore), fm_persistence - Persistenza a Checkpoint su Postgres, Isolamento tra Carriere (FK composite su career_id), Baseline schema inglese 20260612004743 (FOR-35)

### Community 9 - "Wizard Pilot Tests"
Cohesion: 0.11
Nodes (24): narrate(), Una riga di Telecronaca in italiano per ogni evento ricevuto.      Funzione pura, Test della Telecronaca a template (FOR-16, ADR 0003).  Quattro garanzie: copertu, Ogni famiglia ha varianti distinte e piu' della finestra anti-ripetizione., Il factory dei campioni va aggiornato quando nasce un tipo evento., Ogni variante formatta senza errori e senza segnaposto residui., Stessa sequenza di eventi e stesso seed: testo identico., Seed diverso, scelta diversa delle varianti (sequenza lunga). (+16 more)

### Community 10 - "Postgres Connection Config"
Cohesion: 0.19
Nodes (11): connect(), database_url(), Configurazione della connessione Postgres via FM_DATABASE_URL.  FM_DATABASE_URL, Ritorna l'URL Postgres da FM_DATABASE_URL.      Solleva RuntimeError se la varia, Apre una connessione Postgres all'URL di FM_DATABASE_URL.      Autocommit disatt, Persistenza a Checkpoint delle Carriere su Postgres (ADR 0001, FOR-5).  L'API pu, Test della configurazione via FM_DATABASE_URL (senza database)., test_empty_env_var_equals_missing() (+3 more)

### Community 11 - "Ephemeral Docker Postgres"
Cohesion: 0.24
Nodes (10): _apply_sql(), ephemeral_database_url(), _free_port(), Path, Postgres effimero in Docker, condiviso dai test che toccano il database.  Fixtur, Chiede al sistema una porta TCP libera su localhost., Attende che il Postgres del container accetti connessioni TCP., Esegue un file SQL multi-statement via psycopg (niente psql). (+2 more)

### Community 12 - "Pure Engine Import Guard"
Cohesion: 0.36
Nodes (6): _declared_imports(), Test di architettura: fm_engine resta Python puro (ADR 0002).  Due verifiche com, Raccoglie le radici dei moduli importati in un file Python., _root(), test_static_no_forbidden_import(), Path

### Community 14 - "Persistence Test Fixtures"
Cohesion: 0.50
Nodes (3): conn(), Fixture dei test di persistenza (FOR-5).  Il Postgres effimero Docker vive in te, Connessione psycopg al Postgres effimero, una per test.      A fine test cancell

### Community 16 - "TUI Test Fixtures"
Cohesion: 0.50
Nodes (3): db_env(), Fixture dei test Pilot della TUI (FOR-6).  I test Pilot che toccano il database, FM_DATABASE_URL puntata al Postgres effimero, Carriere pulite a fine test.

### Community 17 - "Economy: Cassa & Cap"
Cohesion: 1.00
Nodes (3): Cap (tetto di spesa stagionale), Cassa, Economia a registro append-only (financial_transactions)

### Community 28 - "Community 28"
Cohesion: 0.06
Nodes (149): AccidentSeverity, _average_car_score(), build_grid(), _build_plans(), _category_of(), _lap_orders(), _planned_stop_count(), RaceRecord (+141 more)

### Community 29 - "Community 29"
Cohesion: 0.14
Nodes (19): CarFailure, _car_failure(), _chequered_flag(), CommentaryContext, _dnf(), _lap_only(), _overtake(), _pit_entry() (+11 more)

### Community 30 - "Community 30"
Cohesion: 0.12
Nodes (17): _dnf_counts(), Statistica degli Abbandoni: range realistico e sfortuna onesta (FOR-11)., Su 1000 gare la media degli Abbandoni cade in 3-5 (deliverable)., Sfortuna onesta: il conteggio DNF di una gara non dipende dalla precedente., test_average_dnf_per_race_in_realistic_range(), test_no_hidden_anti_streak_corrector(), Integrazione qualifiche -> gara: la griglia alimenta start_race (FOR-9)., test_full_weekend_qualifying_then_race() (+9 more)

### Community 31 - "Community 31"
Cohesion: 0.08
Nodes (20): main(), Entry point CLI dell'harness: python -m fm_engine.balance (FOR-14)., Aggregates, _pearson(), Aggregati e report leggibile dell'harness di bilanciamento (FOR-14)., Le metriche aggregate su cui ragiona il report e la sanita' pytest., Calcola le metriche aggregate dal risultato della simulazione., Il report statistico leggibile, identico a parita' di seed. (+12 more)

### Community 32 - "Community 32"
Cohesion: 0.13
Nodes (24): Una pioggia forzata fa scattare l'Evento chiave di Crossover., test_crossover_event_fires_when_the_optimal_tyre_changes(), _race_until_safety_car(), Safety car: compattamento, sconto pit, ripartenza (FOR-12)., La prima gara a Monaco che vede una Safety car, fermata al deploy., A parita' di seed, la finestra di ripartenza produce piu' Sfiga., test_pit_under_safety_car_is_discounted(), test_restart_opens_a_risk_window() (+16 more)

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (35): entry_factory(), Costruisce una griglia sintetica di RaceEntry, riproducibile dal seed., Simula una gara completa e raccoglie tutti gli eventi emessi., run_race(), Determinismo del motore di gara (FOR-8).  Stesso seed e stessi Ordini: stati ed, test_different_seeds_differ(), test_same_seed_same_race(), test_same_seed_same_race_with_orders() (+27 more)

### Community 34 - "Community 34"
Cohesion: 0.40
Nodes (5): Il Push alza misurabilmente il rischio di Errori e Incidenti (FOR-11)., Errori e Incidenti totali su N gare con la stessa Aggressivita' per tutti., A parita' di seed di partenza, tutto il campo in Push sbaglia di piu'., _risk_events(), test_push_raises_error_and_accident_risk()

### Community 35 - "Community 35"
Cohesion: 0.19
Nodes (17): after_lap(), degradation_step_seconds(), management_factor(), nominated_compounds(), random_dry_compound(), Modello gomme: Mescole, nomina per GP e Degrado (FOR-10).  Gamma stagionale C1 (, Le 3 Mescole da asciutto nominate per il GP, dai dati statici., Quanto l'asfalto del circuito accelera il Degrado (severita' 1-5). (+9 more)

### Community 36 - "Community 36"
Cohesion: 0.10
Nodes (20): Altri attributi ricorrenti, Attributi pilota, Attributi vettura, Economia, Entita', Example dialogue, Flagged ambiguities, Formula Manager (+12 more)

### Community 37 - "Community 37"
Cohesion: 0.20
Nodes (14): _entry(), _overtake_count(), _pearson(), Difficolta' di sorpasso per circuito e isteresi dei duelli (FOR-36).  Tre propri, Griglia invertita: a Monza il passo riordina, a Monaco la pole regge., Una iscritta con vettura neutra: conta solo il passo del pilota., Griglia al contrario: in pole il piu' lento, in fondo il piu' veloce., A parita' di seed Monaco (difficolta' 5) sorpassa molto meno di Monza (1). (+6 more)

### Community 38 - "Community 38"
Cohesion: 0.12
Nodes (26): Slick regina sull'asciutto, Intermedia in mezzo, Bagnato nel diluvio., test_condition_curves_cross_over(), test_slick_gets_slower_as_the_track_gets_wetter(), test_wet_error_multiplier_grows_with_wetness_and_wrong_tyre(), Crossover, RainStopped, La pioggia cessa: la pista inizia ad asciugarsi, Evento chiave., Il Crossover: cambia la categoria di gomma piu' veloce (CONTEXT.md).      Catego (+18 more)

### Community 39 - "Community 39"
Cohesion: 0.06
Nodes (60): Tempi sul giro fisicamente plausibili per circuito (FOR-37).  Il tempo di pole s, Una griglia di vetture e piloti forti: la pole sfiora il riferimento., Per ogni circuito la pole simulata sta attorno al riferimento., Il collaudo che ha originato la issue: 59.5s a Monaco e' impossibile., _strong_grid(), test_monaco_pole_never_below_seventy_seconds(), test_pole_times_fall_in_the_plausibility_window(), _qualifier() (+52 more)

### Community 40 - "Community 40"
Cohesion: 0.18
Nodes (4): DeleteConfirmation, Conferma di eliminazione di una Carriera: dismiss True = elimina., ComposeResult, Pressed

### Community 41 - "Community 41"
Cohesion: 0.29
Nodes (5): Schermata elenco Carriere: il punto d'ingresso del gioco (FOR-6).  Mostra le Car, Invio o click su una voce: apre quella Carriera., Carica la Carriera dal database e apre la griglia., OptionSelected, UUID

### Community 42 - "Community 42"
Cohesion: 0.10
Nodes (31): load_career(), Ricostruisce per intero una Carriera salvata.      Il Mondo ricostruito e' la pr, Scrive l'intera Carriera (Mondo + stato) in una transazione atomica.      Carrie, save_career(), _count(), Round-trip dei Checkpoint su Postgres effimero Docker (FOR-5).  save_career segu, I colori della livrea scelti alla creazione sopravvivono al round-trip., Due save consecutivi: load ritorna l'ultimo stato, senza duplicati. (+23 more)

### Community 43 - "Community 43"
Cohesion: 0.25
Nodes (8): persistable_projection(), Il Mondo come lo schema sa rappresentarlo.      Normalizza ai valori canonici i, Test unitari della mappatura id interni <-> uuid (senza database)., test_internal_id_out_of_range_raises(), test_persistable_projection_idempotent(), test_projection_leaves_persisted_fields_intact(), test_uuid_deterministic_per_career_and_kind(), test_uuid_distinct_across_careers_kinds_and_ids()

### Community 44 - "Community 44"
Cohesion: 0.16
Nodes (18): Career, La partita del giocatore: nome, Mondo e metadati di Checkpoint.      Possono esi, True se la Carriera non ha ancora un Checkpoint su database., OptionHighlighted, Il Setup squadra (FOR-7) sopravvive al round-trip: vettura e Contratti.      Lo, test_round_trip_after_team_setup(), RowSelected, Career (+10 more)

### Community 45 - "Community 45"
Cohesion: 0.13
Nodes (17): Cursor, Exception, Modello di Carriera: la partita del giocatore (CONTEXT.md, sezione Stagione).  D, CareerNotFoundError, CareerSummary, delete_career(), _insert_world(), list_careers() (+9 more)

### Community 46 - "Community 46"
Cohesion: 0.11
Nodes (23): Fixture comuni dei test del motore di gara (FOR-8).  Griglie sintetiche riproduc, Crossover: curve di prestazione per condizioni e soste emergenti (FOR-13)., Sfiga: probabilita', Abbandoni e payload degli eventi (FOR-11)., test_damage_amounts_have_a_payload_entity(), test_disabled_config_means_sterile_race(), test_duel_contact_probability_modulation(), test_error_probability_modulation(), test_failure_probability_is_inverse_of_reliability() (+15 more)

### Community 47 - "Community 47"
Cohesion: 0.13
Nodes (10): NewCareer, Flusso di nuova Carriera: nome, identita' squadra, colori (FOR-6).  Il giocatore, Torna all'elenco delle Carriere senza creare nulla., Genera il Mondo, salva il Checkpoint di creazione, avvia il wizard., Il colore dal campo indicato, None se lasciato vuoto., Modulo di creazione di una nuova Carriera., Invio in un campo equivale alla conferma del modulo., ComposeResult (+2 more)

### Community 48 - "Community 48"
Cohesion: 0.22
Nodes (6): CareerSummary, Screen, CareerList, Elenco delle Carriere salvate, con crea/apri/elimina., Ricarica l'elenco ogni volta che la schermata torna attiva., Rilegge le Carriere dal database e aggiorna elenco ed empty state.

### Community 49 - "Community 49"
Cohesion: 0.13
Nodes (16): Pit stop, eventi box e undercut emergente dai distacchi (FOR-10)., Chi anticipa la sosta guadagna sul rivale rimasto fuori su gomme vecchie., Chi rientra dai box cede la posizione senza che serva un sorpasso., Attive dal meteo (FOR-13): sull'asciutto le paga la curva, non una regola., Gara a 2 alla pari: il pilota 2 anticipa la sosta di 6 giri.      Misura il guad, test_only_nominated_compounds_are_available(), test_pit_order_changes_tyres_and_emits_events(), test_pit_rejoin_is_not_a_duel() (+8 more)

### Community 50 - "Community 50"
Cohesion: 0.19
Nodes (14): World, baseline_car_attribute(), _check_invariants(), _clamp(), initial_car_attributes(), Setup squadra: applicazione pura delle scelte del wizard (FOR-7).  apply_team_se, Gli Attributi vettura iniziali del giocatore per le scelte date.      Baseline n, Validazioni esplicite delle scelte, con errori chiari. (+6 more)

### Community 51 - "Community 51"
Cohesion: 0.32
Nodes (11): _chequered_flag(), Obbligo bi-mescola in gara asciutta: penalita' in classifica (FOR-10)., Nessuna sosta: tutti penalizzati di 30s in classifica., Sostare senza cambiare tipo di Mescola non soddisfa l'obbligo., Il furbo che salta la sosta vince in pista ma perde in classifica., _run_with_pit_plan(), test_penalty_can_flip_the_classification(), test_same_compound_stop_does_not_clear_the_rule() (+3 more)

### Community 52 - "Community 52"
Cohesion: 0.28
Nodes (8): _rainy_race(), Meteo: previsione, evoluzione in-sessione, transizioni (FOR-13)., La prima gara che vede pioggia: stati per giro ed eventi raccolti., Transizione completa: asciutto -> bagnato -> asciugatura progressiva., Se la pista si bagna, l'obbligo bi-mescola decade., test_forecast_is_deterministic_and_profile_driven(), test_rain_arrives_wets_the_track_and_dries_after(), test_wet_race_disables_bi_compound_penalty()

### Community 53 - "Community 53"
Cohesion: 0.19
Nodes (13): BiCompoundPenalty, _accident(), _bi_compound_penalty(), _crossover(), _driver_error(), _format_seconds(), _join_names(), _pit_exit() (+5 more)

### Community 54 - "Community 54"
Cohesion: 0.25
Nodes (8): _fastest_lap(), _format_lap_time(), _pole_position(), _qualifying_time_set(), Un tempo sul giro in stile cronometraggio: 1:23.456., FastestLap, PolePosition, QualifyingTimeSet

### Community 55 - "Community 55"
Cohesion: 0.27
Nodes (7): Punti 2026: tabella e attribuzione per posizione (FOR-8)., test_no_points_below_tenth_place(), test_points_for_scoring_positions(), test_position_must_be_one_based(), points_for_position(), Tabella punti 2026 (FOR-8).  Punti gara reali 2026: 25-18-15-12-10-8-6-4-2-1, ne, I punti 2026 per la posizione finale data (1-based); 0 oltre il decimo.

### Community 56 - "Community 56"
Cohesion: 0.27
Nodes (9): _neutralization_laps(), Distribuzione delle Safety car per circuito e determinismo (FOR-12)., In quante gare su N e' uscita almeno una Safety car., Monaco e Baku (profilo alto) vedono piu' SC di Barcellona (profilo basso)., Stesso seed, stessa sequenza di neutralizzazioni (giri e tipi)., La sequenza (tipo, giro) delle neutralizzazioni di una gara., _safety_car_races(), test_high_probability_circuits_see_more_safety_cars() (+1 more)

### Community 57 - "Community 57"
Cohesion: 0.20
Nodes (9): Configurazione linear-sync (team FOR), Edge case, Esempio minimo compilato, Header, Note operative, Open question, Sezioni opzionali, Template task canonico (+1 more)

### Community 58 - "Community 58"
Cohesion: 0.20
Nodes (10): Cosa NON fare, Definition of Done, Deliverable verificabile, Dipendenze, File da toccare, Riferimenti, Scenario utente, Scope (+2 more)

### Community 59 - "Community 59"
Cohesion: 0.22
Nodes (8): Architettura, CLAUDE.md, Comandi canonici, Commit e PR, Database, Disciplina, graphify, Lingua

### Community 60 - "Community 60"
Cohesion: 0.10
Nodes (25): Chi monta l'Intermedia al Crossover guadagna su chi resta su slick., test_crossover_stop_pays_off_in_the_rain(), _entry(), Gara base: classifica, punti, duelli e Ordini (FOR-8)., Il Push paga sul passo puro; il conto del Degrado e' un'altra voce., Una iscritta con tutti gli attributi al livello dato: duelli mirati., test_hold_positions_freezes_teammates(), test_no_risk_instruction_blocks_attacks() (+17 more)

### Community 62 - "Community 62"
Cohesion: 0.62
Nodes (7): ADR 0001 - Supabase self-hosted su VPS con salvataggi a checkpoint, ADR 0002 - Textual come TUI con motore di gioco puro, AGENTS.md - Regole operative (mirror di CLAUDE.md), CLAUDE.md - Regole operative Formula Manager, CONTEXT.md - Glossario di dominio e mappa dei nomi, README.md - Panoramica Formula Manager, supabase/README.md - Schema, migrazioni e procedure DB

### Community 63 - "Community 63"
Cohesion: 0.29
Nodes (7): Principio del motore puro (engine senza textual/psycopg), Textual come framework TUI (pin >=8,<9), Telecronaca a template parametrici (niente LLM nel loop), Telecronaca, Tick (unita' di simulazione), fm_engine - Motore di gioco Python puro, fm_tui - Guscio TUI Textual

### Community 64 - "Community 64"
Cohesion: 0.18
Nodes (6): Calendario 2026: sanita' dei dati statici dei circuiti (FOR-8).  Replica in pyte, Nessun giro di F1 sta sotto il minuto o sopra i due (FOR-37)., Monaco al massimo della scala, Monza/Spa/Jeddah bassi (FOR-36)., test_base_lap_seconds_are_physically_plausible(), test_circuit_by_code_lookup(), test_overtaking_difficulty_follows_the_known_profiles()

### Community 65 - "Community 65"
Cohesion: 0.50
Nodes (4): CarDamage, _car_damage(), _format_usd(), Un importo in dollari con separatore delle migliaia: 120.000.

### Community 66 - "Community 66"
Cohesion: 0.29
Nodes (6): Applicare migrazioni e seed, Contenuto, Reset del DB (distruttivo), Scelte di modellazione, Studio, Supabase: schema e migrazioni

### Community 67 - "Community 67"
Cohesion: 0.33
Nodes (5): Avvio, Formula Manager, Harness di bilanciamento, Installazione, Test e lint

### Community 68 - "Community 68"
Cohesion: 0.33
Nodes (6): 1. Conteggio circuiti (atteso: 24), 2. Seed punti e premi (atteso: race_2026 10 posizioni 101 punti, sprint_2026 8 posizioni 36 punti, premi 22 posizioni), 3. Integrita' FK: ogni tabella di stato cascata dalla Carriera (atteso: 10 righe, tutte CASCADE), 4. Tabelle con colonna career_id (atteso: le stesse 10 tabelle), 5. Cascade alla cancellazione di una Carriera (atteso: 10 righe, tutte con residui = 0), Query di verifica

### Community 70 - "Community 70"
Cohesion: 0.40
Nodes (4): Consequences, Considered Options, Nota di attuazione (2026-06-12), Supabase self-hosted su VPS (via Tailscale) con salvataggi a checkpoint

### Community 71 - "Community 71"
Cohesion: 0.50
Nodes (4): Supabase self-hosted su matilde via Tailscale, Come ottenere FM_DATABASE_URL, FM_DATABASE_URL (unica variabile di connessione), Tunnel SSH per la CLI Supabase

### Community 78 - "Community 78"
Cohesion: 0.50
Nodes (3): _race_started(), Il nome del circuito, o il codice stesso se sconosciuto., RaceStarted

### Community 79 - "Community 79"
Cohesion: 0.50
Nodes (4): _params(), I parametri di formattazione per l'evento dato., Tutte le varianti della famiglia dell'evento, gia' renderizzate.      Esposta pe, render_variants()

### Community 80 - "Community 80"
Cohesion: 0.50
Nodes (4): _rain_intensity_label(), _rain_started(), L'aggettivo per l'intensita' di pioggia, scala 0-1., RainStarted

## Ambiguous Edges - Review These
- `Template task canonico` → `CLAUDE.md - Regole operative Formula Manager`  [AMBIGUOUS]
  specs/templates/task-template.md · relation: conceptually_related_to

## Knowledge Gaps
- **83 isolated node(s):** `play.sh script`, `RaceStarted`, `TeamOrderSwap`, `FastestLap`, `CarFailure` (+78 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Template task canonico` and `CLAUDE.md - Regole operative Formula Manager`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Driver` connect `World Models & Generation` to `Career TUI Screens`, `Team Setup Wizard UI`, `Community 37`, `Row Mapping Layer`, `Community 39`, `World Generation Tests`, `Community 44`, `Community 28`, `Community 61`?**
  _High betweenness centrality (0.218) - this node is a cross-community bridge._
- **Why does `Grid` connect `Career TUI Screens` to `World Models & Generation`, `Team Setup Wizard UI`, `TUI App & Pilot Tests`, `Community 40`, `Community 41`, `Community 44`, `Community 48`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `Career` connect `Community 44` to `World Models & Generation`, `Career TUI Screens`, `Team Setup Wizard UI`, `TUI App & Pilot Tests`, `Community 42`, `Community 45`, `Community 47`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 61 inferred relationships involving `Circuit` (e.g. with `AccidentSeverity` and `RaceRecord`) actually correct?**
  _`Circuit` has 61 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `RaceEntry` (e.g. with `RaceRecord` and `SimulationResult`) actually correct?**
  _`RaceEntry` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `Driver` (e.g. with `Any` and `DataTable`) actually correct?**
  _`Driver` has 50 INFERRED edges - model-reasoned connections that need verification._