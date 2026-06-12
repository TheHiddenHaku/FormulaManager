# Graph Report - .  (2026-06-12)

## Corpus Check
- Corpus is ~27,781 words - fits in a single context window. You may not need a graph.

## Summary
- 532 nodes · 1123 edges · 28 communities (16 shown, 12 thin omitted)
- Extraction: 71% EXTRACTED · 29% INFERRED · 0% AMBIGUOUS · INFERRED: 329 edges (avg confidence: 0.61)
- Token cost: 75,186 input · 5,200 output

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

## God Nodes (most connected - your core abstractions)
1. `Career` - 44 edges
2. `TeamSetup` - 37 edges
3. `Grid` - 34 edges
4. `Driver` - 32 edges
5. `World` - 31 edges
6. `apply_team_setup()` - 29 edges
7. `generate()` - 23 edges
8. `WorldConfig` - 23 edges
9. `Contract` - 22 edges
10. `save_career()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `world()` --calls--> `generate()`  [INFERRED]
  tests/persistence/test_round_trip.py → src/fm_engine/world/generation.py
- `AGENTS.md - Regole operative (mirror di CLAUDE.md)` --semantically_similar_to--> `CLAUDE.md - Regole operative Formula Manager`  [INFERRED] [semantically similar]
  AGENTS.md → CLAUDE.md
- `Template task canonico` --conceptually_related_to--> `CLAUDE.md - Regole operative Formula Manager`  [AMBIGUOUS]
  specs/templates/task-template.md → CLAUDE.md
- `Career` --uses--> `Career`  [INFERRED]
  tests/tui/test_career_management.py → src/fm_engine/career.py
- `FormulaManagerApp` --uses--> `Career`  [INFERRED]
  tests/tui/test_career_management.py → src/fm_engine/career.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Architettura a tre pacchetti (motore puro / persistenza / guscio TUI)** — readme_fm_engine, readme_fm_persistence, readme_fm_tui [EXTRACTED 1.00]
- **Flusso di persistenza a Checkpoint della Carriera** — context_checkpoint, adr_0001_supabase_self_hosted_su_vps_con_salvataggi_a_checkpoint_checkpoint_persistence, readme_fm_persistence, supabase_readme_fm_database_url, supabase_readme_career_isolation [INFERRED 0.85]
- **Loop di gara interattiva in tempo simulato** — context_tick, context_evento_chiave, context_auto_pausa, context_telecronaca [INFERRED 0.85]

## Communities (28 total, 12 thin omitted)

### Community 0 - "World Models & Generation"
Cohesion: 0.08
Nodes (60): PlayerSlot, Random, Contract, Driver, EngineSupplier, Team, World, WorldConfig (+52 more)

### Community 1 - "Checkpoint Persistence"
Cohesion: 0.05
Nodes (61): Cursor, DataTable, Exception, Career, Modello di Carriera: la partita del giocatore (CONTEXT.md, sezione Stagione).  D, La partita del giocatore: nome, Mondo e metadati di Checkpoint.      Possono esi, True se la Carriera non ha ancora un Checkpoint su database., CareerNotFoundError (+53 more)

### Community 2 - "Career TUI Screens"
Cohesion: 0.05
Nodes (29): CareerSummary, Screen, CareerList, DeleteConfirmation, Schermata elenco Carriere: il punto d'ingresso del gioco (FOR-6).  Mostra le Car, Elenco delle Carriere salvate, con crea/apri/elimina., Ricarica l'elenco ogni volta che la schermata torna attiva., Invio o click su una voce: apre quella Carriera. (+21 more)

### Community 3 - "Team Setup Wizard UI"
Cohesion: 0.07
Nodes (24): OptionHighlighted, RowSelected, _millions(), Wizard di Setup squadra: piloti, motore, Filosofia telaio (FOR-7).  Parte subito, Mostra il passo richiesto, nasconde gli altri, aggiorna i binding., Mostra nel Footer solo i binding sensati per il passo corrente., Avanza di un passo, validando il vincolo dei 2 piloti., Torna al passo precedente; dal primo passo esce dal wizard.          Edge accett (+16 more)

### Community 4 - "TUI App & Pilot Tests"
Cohesion: 0.06
Nodes (41): App, list_careers(), Elenca le Carriere salvate con i metadati di Checkpoint.      Ordinate dal Check, FormulaManagerApp, main(), Shell TUI di Formula Manager (FOR-6).  L'app apre sull'elenco delle Carriere e d, La shell di gioco: stack di schermate sopra l'elenco Carriere., Entry point del comando fm.      Verifica la raggiungibilita' del database prima (+33 more)

### Community 5 - "Team Setup Engine Logic"
Cohesion: 0.13
Nodes (38): apply_team_setup(), baseline_car_attribute(), _check_invariants(), _clamp(), initial_car_attributes(), Setup squadra: applicazione pura delle scelte del wizard (FOR-7).  apply_team_se, Gli Attributi vettura iniziali del giocatore per le scelte date.      Baseline n, Applica le scelte del Setup squadra e ritorna il Mondo nuovo.      Valida le sce (+30 more)

### Community 6 - "Row Mapping Layer"
Cohesion: 0.11
Nodes (36): Any, contract_from_row(), contract_params(), driver_from_row(), driver_params(), engine_supplier_from_row(), engine_supplier_params(), id_from_uuid() (+28 more)

### Community 7 - "World Generation Tests"
Cohesion: 0.06
Nodes (10): generate(), Genera il Mondo completo di inizio Carriera in modo deterministico.      Due chi, Property test e test di determinismo per fm_engine.world.generate.  Le proprieta, test_custom_config_respected(), test_different_seeds_different_worlds(), test_same_seed_same_world(), test_same_seed_with_explicit_config(), Mondo generato con lo slot del giocatore gia' nominato (T1.3.1). (+2 more)

### Community 8 - "Architecture Docs & ADRs"
Cohesion: 0.11
Nodes (26): Persistenza a Checkpoint (stato in memoria, scritture atomiche), ADR 0001 - Supabase self-hosted su VPS con salvataggi a checkpoint, Supabase self-hosted su matilde via Tailscale, ADR 0002 - Textual come TUI con motore di gioco puro, Principio del motore puro (engine senza textual/psycopg), Textual come framework TUI (pin >=8,<9), Telecronaca a template parametrici (niente LLM nel loop), AGENTS.md - Regole operative (mirror di CLAUDE.md) (+18 more)

### Community 9 - "Wizard Pilot Tests"
Cohesion: 0.26
Nodes (16): FormulaManagerApp, _complete_wizard(), _create_career(), _error_text(), Test Pilot del wizard di Setup squadra (FOR-7).  Coprono il flusso completo: avv, Dall'elenco vuoto: crea una Carriera e arriva al wizard., Nel passo piloti: seleziona le prime due righe del roster., Dal passo piloti alla conferma: 2 piloti, Cliente, telaio veloce. (+8 more)

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

## Ambiguous Edges - Review These
- `CLAUDE.md - Regole operative Formula Manager` → `Template task canonico`  [AMBIGUOUS]
  specs/templates/task-template.md · relation: conceptually_related_to

## Knowledge Gaps
- **10 isolated node(s):** `play.sh script`, `Connection`, `Path`, `ADR 0003 - Telecronaca a template parametrici senza LLM`, `fm_engine - Motore di gioco Python puro` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `CLAUDE.md - Regole operative Formula Manager` and `Template task canonico`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `generate()` connect `World Generation Tests` to `World Models & Generation`, `Checkpoint Persistence`, `Career TUI Screens`, `TUI App & Pilot Tests`, `Team Setup Engine Logic`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Why does `Career` connect `Checkpoint Persistence` to `World Models & Generation`, `Career TUI Screens`, `Team Setup Wizard UI`, `TUI App & Pilot Tests`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Why does `TeamSetup` connect `Team Setup Wizard UI` to `World Models & Generation`, `Checkpoint Persistence`, `Career TUI Screens`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `Career` (e.g. with `Cursor` and `DataTable`) actually correct?**
  _`Career` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `TeamSetup` (e.g. with `.action_create()` and `Career`) actually correct?**
  _`TeamSetup` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `Grid` (e.g. with `CareerSummary` and `OptionHighlighted`) actually correct?**
  _`Grid` has 22 INFERRED edges - model-reasoned connections that need verification._