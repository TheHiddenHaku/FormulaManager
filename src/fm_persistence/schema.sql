-- Schema di gioco di Formula Manager in dialetto SQLite.
--
-- Baseline unica che collassa le 11 migrazioni Postgres originali
-- (dallo schema iniziale del 2026-06-12 alle tabelle di archivio): stesso schema,
-- stessi vincoli, tradotto al dialetto SQLite del database di gioco locale
-- (vedi ADR 0004). Traduzione dei tipi:
--   uuid             -> text (gli id li scrive l'applicazione, niente gen_random_uuid())
--   timestamptz      -> text ISO 8601 (niente now(): li scrive l'applicazione)
--   date             -> text ISO 8601
--   numeric(p,s)     -> real
--   double precision -> real
--   boolean          -> integer 0/1 (con check)
--   jsonb            -> text (documenti JSON serializzati dall'applicazione)
--   smallint/integer -> integer
-- Vincoli check, unique e foreign key con on delete cascade conservati.
--
-- PRAGMA foreign_keys = ON e' un'impostazione per connessione e vive nel codice
-- (fm_persistence.connection), non qui.
--
-- Due famiglie di tabelle:
--   1. Dati statici globali, fuori dalle Carriere: circuits, points_tables,
--      race_prizes. Popolati da seed.sql, condivisi da tutte le Carriere.
--   2. Stato di Carriera: careers (radice) e ogni tabella con FK career_id
--      on delete cascade. Cancellare una riga di careers rimuove l'intera partita.

pragma user_version = 1;

-- ---------------------------------------------------------------------------
-- Dati statici globali
-- ---------------------------------------------------------------------------

-- I 24 circuiti del Calendario 2026. Pesi, severita' e probabilita' sono
-- parametri di partenza tarabili.
create table circuits (
    id text primary key,
    code text not null unique,
    name text not null,
    country text not null,
    locality text not null,
    length_metres integer not null check (length_metres > 0),
    race_laps integer not null check (race_laps > 0),
    -- Il calendario si ripete ogni stagione con l'anno che avanza: round e data
    -- 2026 vivono qui e non nelle Carriere.
    calendar_order integer not null unique check (calendar_order between 1 and 24),
    race_date_2026 text not null,
    weekend_format_2026 text not null default 'standard'
        check (weekend_format_2026 in ('standard', 'sprint')),
    -- Tempo base sul giro in secondi: base additiva del modello del tempo,
    -- uguale per tutte le vetture sullo stesso circuito. Tarabile.
    base_lap_seconds real not null check (base_lap_seconds > 0),
    -- Pesi sui 6 Attributi vettura (0.00-1.00): quanto ogni attributo conta sul
    -- giro in questo circuito.
    engine_power_weight real not null check (engine_power_weight between 0 and 1),
    downforce_weight real not null check (downforce_weight between 0 and 1),
    aero_efficiency_weight real not null check (aero_efficiency_weight between 0 and 1),
    mechanical_grip_weight real not null check (mechanical_grip_weight between 0 and 1),
    tyre_management_weight real not null check (tyre_management_weight between 0 and 1),
    reliability_weight real not null check (reliability_weight between 0 and 1),
    -- Severita' gomme: quanto l'asfalto e' aggressivo sul degrado, 1 (dolce) - 5 (severa).
    tyre_severity integer not null check (tyre_severity between 1 and 5),
    -- Difficolta' di sorpasso: 1 (facile: Monza) - 5 (quasi impossibile: Monaco).
    overtaking_difficulty integer not null check (overtaking_difficulty between 1 and 5),
    -- Probabilita' che la gara veda almeno una Safety car (0.00-1.00).
    safety_car_probability real not null check (safety_car_probability between 0 and 1),
    weather_profile text not null check (weather_profile in ('dry', 'variable', 'wet')),
    rain_probability real not null check (rain_probability between 0 and 1),
    -- Le 3 mescole a secco nominate per il GP (C1-C5, dalla piu' dura alla piu' morbida).
    hard_compound text not null check (hard_compound in ('C1', 'C2', 'C3', 'C4', 'C5')),
    medium_compound text not null check (medium_compound in ('C1', 'C2', 'C3', 'C4', 'C5')),
    soft_compound text not null check (soft_compound in ('C1', 'C2', 'C3', 'C4', 'C5')),
    check (hard_compound < medium_compound and medium_compound < soft_compound)
);

-- Punti per posizione. code = 'race_2026' per la gara standard, 'sprint_2026'
-- per la sprint (post-MVP).
create table points_tables (
    code text not null,
    position integer not null check (position >= 1),
    points integer not null check (points >= 0),
    primary key (code, position)
);

-- Premio gara per posizione di arrivo. Importi di partenza tarabili.
create table race_prizes (
    code text not null,
    position integer not null check (position >= 1),
    amount_usd real not null check (amount_usd >= 0),
    primary key (code, position)
);

-- ---------------------------------------------------------------------------
-- Radice di Carriera
-- ---------------------------------------------------------------------------

-- Radice multi-Carriera: ogni riga e' una partita indipendente. La cancellazione
-- elimina in cascata tutto lo stato della Carriera.
create table careers (
    id text primary key,
    name text not null,
    created_at text not null,
    -- Metadati di Checkpoint: aggiornati a ogni salvataggio transazionale.
    last_checkpoint_at text,
    -- Documenti JSON di stato serializzati dall'applicazione (ADR 0001), scritti e
    -- letti atomicamente con il resto dello stato di Carriera. NULL = stato di partenza.
    weekend_state text,    -- weekend di gara in corso (fase, Programmi, griglia, classifica)
    solvency_state text,   -- solvibilita' del giocatore (Misura d'emergenza, prestito, malus)
    season_state text,     -- anno corrente, data di gioco, risultati dei GP disputati
    knowledge_state text,  -- conoscenza degli attributi (margine delle Stime)
    preseason_state text,  -- fase Test pre-season (giorni svolti, Programmi)
    market_state text      -- fase di Mercato piloti (scadenze, liberi, firme, log mosse)
);

-- ---------------------------------------------------------------------------
-- Registri di Carriera
-- ---------------------------------------------------------------------------

-- I 3-4 produttori di motori del mondo di gioco, per Carriera. La Potenza motore
-- di un Cliente e' quella del suo Motorista.
create table engine_suppliers (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    name text not null,
    engine_power real not null default 50 check (engine_power between 0 and 100),
    customer_fee_usd real not null default 15000000 check (customer_fee_usd >= 0),
    unique (career_id, id)
);

-- La Griglia: 11 squadre per Carriera (10 AI + giocatore), con Attributi vettura
-- correnti e stato economico.
create table teams (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    name text not null,
    is_player integer not null default 0 check (is_player in (0, 1)),
    prestige real not null default 50 check (prestige between 0 and 100),
    -- Cassa: puo' andare negativa (insolvenza, Misura d'emergenza).
    cash_usd real not null default 0,
    chassis_philosophy text not null default 'balanced'
        check (chassis_philosophy in ('fast', 'balanced', 'technical')),
    -- NULL = la squadra costruisce il proprio motore; valorizzato = squadra Cliente.
    engine_supplier_id text,
    engine_power real not null default 50 check (engine_power between 0 and 100),
    downforce real not null default 50 check (downforce between 0 and 100),
    aero_efficiency real not null default 50 check (aero_efficiency between 0 and 100),
    mechanical_grip real not null default 50 check (mechanical_grip between 0 and 100),
    tyre_management real not null default 50 check (tyre_management between 0 and 100),
    reliability real not null default 50 check (reliability between 0 and 100),
    -- Colori livrea: esadecimale #rrggbb o nome colore. NULL per le squadre AI.
    primary_color text,
    secondary_color text,
    unique (career_id, id),
    foreign key (career_id, engine_supplier_id) references engine_suppliers (career_id, id)
);

-- Al massimo una squadra del giocatore per Carriera.
create unique index teams_player_unique on teams (career_id) where is_player = 1;

-- Il roster piloti della Carriera: i 22 titolari piu' Giovani generati e ritirati.
create table drivers (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    name text not null,
    -- Codice ISO 3166-1 alpha-2 minuscolo (es. 'it', 'gb'). Stringa vuota se non nota.
    nationality text not null default '',
    age integer not null check (age between 16 and 60),
    one_lap_pace real not null default 50 check (one_lap_pace between 0 and 100),
    race_pace real not null default 50 check (race_pace between 0 and 100),
    duels real not null default 50 check (duels between 0 and 100),
    tyre_management real not null default 50 check (tyre_management between 0 and 100),
    wet_weather real not null default 50 check (wet_weather between 0 and 100),
    consistency real not null default 50 check (consistency between 0 and 100),
    -- Potenziale: attributo nascosto, margine di crescita o declino. Mai mostrato.
    potential real not null default 50 check (potential between 0 and 100),
    -- Ritiro di carriera: true se uscito dal parco attivo a fine stagione.
    retired integer not null default 0 check (retired in (0, 1)),
    unique (career_id, id)
);

-- Indice parziale sui piloti attivi (generazione Giovani, pool del Mercato).
create index drivers_active on drivers (career_id) where retired = 0;

-- Contratti squadra-pilota: durata 1-3 stagioni, stipendio fuori Cap.
create table contracts (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    team_id text not null,
    driver_id text not null,
    start_season integer not null check (start_season >= 2026),
    duration_seasons integer not null check (duration_seasons between 1 and 3),
    salary_usd real not null check (salary_usd >= 0),
    unique (career_id, id),
    foreign key (career_id, team_id) references teams (career_id, id),
    foreign key (career_id, driver_id) references drivers (career_id, id)
);

create index contracts_team on contracts (career_id, team_id);
create index contracts_driver on contracts (career_id, driver_id);

-- ---------------------------------------------------------------------------
-- Struttura sportiva: stagioni, Gran Premi, sessioni, risultati
-- ---------------------------------------------------------------------------

-- Le stagioni di una Carriera: il Calendario 2026 si ripete ogni anno.
create table seasons (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    year integer not null check (year >= 2026),
    -- Cap stagionale ($215M di partenza). Il rollover invernale imposta il Cap
    -- della stagione nuova, ridotto della penalita' in caso di Sforamento.
    cap_usd real not null default 215000000 check (cap_usd > 0),
    status text not null default 'in_progress' check (status in ('in_progress', 'completed')),
    unique (career_id, year),
    unique (career_id, id)
);

-- I Gran Premi di una stagione, istanziati dal Calendario statico dei circuiti.
create table grands_prix (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    season_id text not null,
    circuit_id text not null references circuits (id),
    round integer not null check (round between 1 and 24),
    race_date text not null,
    weekend_format text not null default 'standard'
        check (weekend_format in ('standard', 'sprint')),
    status text not null default 'scheduled'
        check (status in ('scheduled', 'in_progress', 'completed')),
    unique (career_id, id),
    unique (career_id, season_id, round),
    foreign key (career_id, season_id) references seasons (career_id, id)
);

-- Le sessioni di un Gran Premio. Fine sessione e pre-gara sono i punti di Checkpoint.
create table sessions (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    grand_prix_id text not null,
    kind text not null check (kind in ('practice', 'q1', 'q2', 'q3', 'sprint_qualifying', 'sprint', 'race')),
    -- Numero progressivo per i tipi ripetibili (es. piu' sessioni di prove).
    number integer not null default 1 check (number >= 1),
    status text not null default 'scheduled'
        check (status in ('scheduled', 'in_progress', 'completed')),
    unique (career_id, id),
    unique (career_id, grand_prix_id, kind, number),
    foreign key (career_id, grand_prix_id) references grands_prix (career_id, id)
);

-- Risultato di un pilota in una sessione: posizione, miglior tempo, giri, Abbandono, punti.
create table results (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    session_id text not null,
    driver_id text not null,
    team_id text not null,
    -- NULL quando il pilota non e' classificato (DNF, mancata partenza).
    position integer check (position between 1 and 22),
    best_time_ms integer check (best_time_ms > 0),
    laps_completed integer not null default 0 check (laps_completed >= 0),
    status text not null default 'classified'
        check (status in ('classified', 'dnf', 'did_not_start')),
    points integer not null default 0 check (points >= 0),
    unique (career_id, id),
    unique (career_id, session_id, driver_id),
    foreign key (career_id, session_id) references sessions (career_id, id),
    foreign key (career_id, driver_id) references drivers (career_id, id),
    foreign key (career_id, team_id) references teams (career_id, id)
);

create index results_driver on results (career_id, driver_id);
create index results_team on results (career_id, team_id);

-- ---------------------------------------------------------------------------
-- Economia e sviluppo
-- ---------------------------------------------------------------------------

-- Registro transazionale dell'economia: ogni movimento di Cassa o Cap e' una riga.
-- Cassa e Cap residuo si ricostruiscono per somma.
create table financial_transactions (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    team_id text not null,
    season_id text not null,
    -- Valorizzato per le transazioni legate a un GP (Premio gara, danni in weekend).
    grand_prix_id text,
    kind text not null check (kind in (
        'race_prize', 'annual_sponsor', 'constructors_pool', 'one_off_sponsor',
        'stopgap_sponsor', 'loan', 'interest', 'salary', 'engine_fee',
        'development_project', 'damage', 'overspend', 'other'
    )),
    -- Positivo = entrata, negativo = uscita.
    amount_usd real not null,
    -- true quando la transazione consuma (o riduce) il Cap, oltre a muovere Cassa.
    counts_against_cap integer not null default 0 check (counts_against_cap in (0, 1)),
    description text,
    -- Data nel calendario di gioco in cui avviene la transazione.
    game_date text not null,
    recorded_at text not null,
    unique (career_id, id),
    foreign key (career_id, team_id) references teams (career_id, id),
    foreign key (career_id, season_id) references seasons (career_id, id),
    foreign key (career_id, grand_prix_id) references grands_prix (career_id, id)
);

create index financial_transactions_team on financial_transactions (career_id, team_id);
create index financial_transactions_season on financial_transactions (career_id, season_id);

-- Progetti di sviluppo: costo dal Cap, durata in giorni di calendario, esito con
-- varianza. Il limite di 2 Progetti paralleli per squadra e' regola di gioco, non vincolo DB.
create table development_projects (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    team_id text not null,
    season_id text not null,
    attribute text not null check (attribute in (
        'engine_power', 'downforce', 'aero_efficiency',
        'mechanical_grip', 'tyre_management', 'reliability'
    )),
    -- true per i Progetti invernali (decisi tra una stagione e la successiva).
    winter integer not null default 0 check (winter in (0, 1)),
    cost_usd real not null check (cost_usd > 0),
    start_date text not null,
    duration_days integer not null check (duration_days > 0),
    status text not null default 'in_progress'
        check (status in ('in_progress', 'completed', 'cancelled')),
    -- Delta applicato all'attributo al completamento (negativo per un flop). NULL in corso.
    outcome real,
    unique (career_id, id),
    foreign key (career_id, team_id) references teams (career_id, id),
    foreign key (career_id, season_id) references seasons (career_id, id)
);

create index development_projects_team on development_projects (career_id, team_id);

-- ---------------------------------------------------------------------------
-- Archivio permanente della Carriera: Almanacco e Albo d'oro
-- ---------------------------------------------------------------------------
-- Scritte SOLO nel flusso di save_career (delete e reinsert dell'intero archivio
-- in transazione, ADR 0001). driver_id, team_id ed entity_id sono identificatori
-- interi dell'archivio, non FK alle tabelle di stato.

-- Una riga per stagione archiviata. I Titoli sono NULL finche' la stagione e' in corso.
create table archive_seasons (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    year integer not null,
    driver_champion_id integer,
    constructor_champion_id integer,
    unique (career_id, year),
    unique (career_id, id)
);

create index archive_seasons_career_year on archive_seasons (career_id, year);

-- Le righe di classifica finale di ogni stagione, piloti e costruttori. scope
-- distingue le due classifiche; entity_id e' il driver_id o il team_id.
create table archive_standings (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    year integer not null,
    scope text not null check (scope in ('driver', 'constructor')),
    position integer not null check (position >= 1),
    entity_id integer not null,
    points integer not null check (points >= 0),
    wins integer not null check (wins >= 0),
    unique (career_id, id),
    unique (career_id, year, scope, position)
);

create index archive_standings_career_year on archive_standings (career_id, year);

-- Una riga per GP disputato e archiviato (voce di Almanacco).
create table archive_grands_prix (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    year integer not null,
    round integer not null check (round >= 1),
    circuit_code text not null,
    unique (career_id, id),
    unique (career_id, year, round)
);

create index archive_grands_prix_career_year on archive_grands_prix (career_id, year);

-- La griglia di partenza di un GP archiviato, in ordine di pole (grid_position 1 = pole).
create table archive_starting_grid (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    year integer not null,
    round integer not null,
    grid_position integer not null check (grid_position >= 1),
    driver_id integer not null,
    unique (career_id, id),
    unique (career_id, year, round, grid_position)
);

create index archive_starting_grid_career_year_round
    on archive_starting_grid (career_id, year, round);

-- L'ordine d'arrivo completo di un GP archiviato, coi punti 2026.
create table archive_results (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    year integer not null,
    round integer not null,
    position integer not null check (position >= 1),
    driver_id integer not null,
    team_id integer not null,
    points integer not null check (points >= 0),
    total_time_seconds real not null,
    gap_to_winner_seconds real not null,
    penalty_seconds real not null default 0,
    unique (career_id, id),
    unique (career_id, year, round, position)
);

create index archive_results_career_year_round on archive_results (career_id, year, round);

-- Gli eventi principali di un GP archiviato (ADR 0003: solo Safety car e Abbandoni).
-- ordinal conserva l'ordine.
create table archive_principal_events (
    id text primary key,
    career_id text not null references careers (id) on delete cascade,
    year integer not null,
    round integer not null,
    ordinal integer not null check (ordinal >= 1),
    kind text not null check (kind in ('safety_car', 'dnf')),
    lap integer not null check (lap >= 0),
    driver_id integer,
    detail text not null,
    unique (career_id, id),
    unique (career_id, year, round, ordinal)
);

create index archive_principal_events_career_year_round
    on archive_principal_events (career_id, year, round);
