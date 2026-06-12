-- Baseline schema of Formula Manager (FOR-35).
--
-- Replaces the two Italian-named migrations of 2026-06-11 (schema_radice,
-- nazionalita_e_colori) with a single English-named baseline: same
-- constraints and semantics, identifiers translated per CONTEXT.md
-- ("Mappa dei nomi nel codice"). The nationality and livery color columns
-- are folded in.
--
-- Two table families:
--   1. Global static data, outside careers: circuits, points_tables, race_prizes.
--      Populated by supabase/seed.sql, shared by all careers.
--   2. Career state: careers (root) and every table with a career_id FK
--      ON DELETE CASCADE. Deleting a careers row removes the whole game.
--
-- Conventions:
--   - English snake_case naming; the Italian domain glossary lives in CONTEXT.md.
--   - Team, driver and engine supplier names are editable text columns, not enums.
--   - Closed sets (weekend format, session kind, transaction kind) use CHECK on
--     text, not Postgres enums: adding a value does not require ALTER TYPE.
--   - Every career-state table has UNIQUE (career_id, id): intra-career FKs are
--     composite on (career_id, <fk>) so rows cannot reference another career.
--   - Amounts are numeric USD (*_usd columns). Car and driver attributes are on
--     a 0-100 scale. No RLS: single-player on a private Tailscale network.

-- ---------------------------------------------------------------------------
-- Global static data
-- ---------------------------------------------------------------------------

create table circuits (
    id uuid primary key default gen_random_uuid(),
    code text not null unique,
    name text not null,
    country text not null,
    locality text not null,
    length_metres integer not null check (length_metres > 0),
    race_laps smallint not null check (race_laps > 0),
    -- 2026 calendar: the calendar repeats every season with the year advancing,
    -- so round and 2026 date live here and not in the careers.
    calendar_order smallint not null unique check (calendar_order between 1 and 24),
    race_date_2026 date not null,
    -- Weekend format of the GP in the real 2026 calendar. The MVP plays everything
    -- in standard format, but the flag exists from day one (see grands_prix.weekend_format).
    weekend_format_2026 text not null default 'standard'
        check (weekend_format_2026 in ('standard', 'sprint')),
    -- Weights over the 6 car attributes (0.00-1.00): how much each attribute
    -- counts on the lap at this circuit. Starting values, tunable.
    engine_power_weight numeric(3,2) not null check (engine_power_weight between 0 and 1),
    downforce_weight numeric(3,2) not null check (downforce_weight between 0 and 1),
    aero_efficiency_weight numeric(3,2) not null check (aero_efficiency_weight between 0 and 1),
    mechanical_grip_weight numeric(3,2) not null check (mechanical_grip_weight between 0 and 1),
    tyre_management_weight numeric(3,2) not null check (tyre_management_weight between 0 and 1),
    reliability_weight numeric(3,2) not null check (reliability_weight between 0 and 1),
    -- Tyre severity: how hard the tarmac is on degradation, scale 1 (gentle) - 5 (severe).
    tyre_severity smallint not null check (tyre_severity between 1 and 5),
    -- Probability that the race sees at least one safety car (0.00-1.00). Tunable.
    safety_car_probability numeric(3,2) not null check (safety_car_probability between 0 and 1),
    -- Weekend weather profile and race rain probability (0.00-1.00). Tunable.
    weather_profile text not null check (weather_profile in ('dry', 'variable', 'wet')),
    rain_probability numeric(3,2) not null check (rain_probability between 0 and 1),
    -- The 3 dry compounds nominated for the GP (C1-C5 range, hardest to softest).
    -- Intermediate and wet are always available and are not nominated.
    hard_compound text not null check (hard_compound in ('C1', 'C2', 'C3', 'C4', 'C5')),
    medium_compound text not null check (medium_compound in ('C1', 'C2', 'C3', 'C4', 'C5')),
    soft_compound text not null check (soft_compound in ('C1', 'C2', 'C3', 'C4', 'C5')),
    check (hard_compound < medium_compound and medium_compound < soft_compound)
);

comment on table circuits is 'Dato statico globale: i 24 circuiti del Calendario 2026 (annuncio originale 2025, inclusi Bahrain e Jeddah). Pesi, severita'' e probabilita'' sono parametri di partenza tarabili.';
comment on column circuits.race_date_2026 is 'Data reale della gara nella stagione 2026; le stagioni successive traslano l''anno mantenendo il giorno.';

-- Points tables: rows of (table code, position, points). The code separates the
-- 2026 race table (25-18-15-12-10-8-6-4-2-1, no fastest lap point) from future
-- tables (e.g. sprint) without requiring migrations.
create table points_tables (
    code text not null,
    position smallint not null check (position >= 1),
    points smallint not null check (points >= 0),
    primary key (code, position)
);

comment on table points_tables is 'Dato statico globale: punti per posizione. code = ''race_2026'' per la gara standard, ''sprint_2026'' per la sprint (post-MVP).';

-- Race prizes: income collected after each grand prix based on finishing position.
-- Starting amounts, tunable; the code allows alternative prize tables.
create table race_prizes (
    code text not null,
    position smallint not null check (position >= 1),
    amount_usd numeric(12,2) not null check (amount_usd >= 0),
    primary key (code, position)
);

comment on table race_prizes is 'Dato statico globale: Premio gara per posizione di arrivo. Importi di partenza tarabili.';

-- ---------------------------------------------------------------------------
-- Career root
-- ---------------------------------------------------------------------------

create table careers (
    id uuid primary key default gen_random_uuid(),
    -- Career name, editable by the player.
    name text not null,
    created_at timestamptz not null default now(),
    -- Checkpoint metadata (T1.2.2): updated on every transactional save.
    last_checkpoint_at timestamptz
);

comment on table careers is 'Radice multi-Carriera: ogni riga e'' una partita indipendente. La cancellazione elimina in cascata tutto lo stato della Carriera.';

-- ---------------------------------------------------------------------------
-- Career registries
-- ---------------------------------------------------------------------------

create table engine_suppliers (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    -- Fictional name, editable via Studio.
    name text not null,
    -- Engine power (0-100) supplied to customers and to the owning team, if any.
    engine_power numeric(5,2) not null default 50 check (engine_power between 0 and 100),
    -- Annual fee paid by each customer team. Tunable starting value.
    customer_fee_usd numeric(12,2) not null default 15000000 check (customer_fee_usd >= 0),
    unique (career_id, id)
);

comment on table engine_suppliers is 'I 3-4 produttori di motori del mondo di gioco, per Carriera. La Potenza motore di un Cliente e'' quella del suo Motorista.';

create table teams (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    -- Fictional name, editable via Studio.
    name text not null,
    -- True for the player team (only one per career, see index below).
    is_player boolean not null default false,
    -- Prestige (0-100): scales the annual sponsor and the appeal on the driver market.
    prestige numeric(5,2) not null default 50 check (prestige between 0 and 100),
    -- Cash: available money. Can go negative (insolvency, emergency measure).
    cash_usd numeric(14,2) not null default 0,
    -- Chassis philosophy: skews towards fast circuits (aero efficiency) or
    -- technical/slow ones (downforce and mechanical grip). Renegotiable every winter.
    chassis_philosophy text not null default 'balanced'
        check (chassis_philosophy in ('fast', 'balanced', 'technical')),
    -- NULL = the team builds its own engine; set = customer team
    -- (composite FK on (career_id, engine_supplier_id) declared at the end).
    engine_supplier_id uuid,
    -- Current car attributes (0-100). For a customer team the effective engine
    -- power is the supplier's: this column matters for own-engine teams.
    engine_power numeric(5,2) not null default 50 check (engine_power between 0 and 100),
    downforce numeric(5,2) not null default 50 check (downforce between 0 and 100),
    aero_efficiency numeric(5,2) not null default 50 check (aero_efficiency between 0 and 100),
    mechanical_grip numeric(5,2) not null default 50 check (mechanical_grip between 0 and 100),
    tyre_management numeric(5,2) not null default 50 check (tyre_management between 0 and 100),
    reliability numeric(5,2) not null default 50 check (reliability between 0 and 100),
    -- Livery colors: hex #rrggbb or color name. Chosen by the player at
    -- creation; NULL for the AI teams.
    primary_color text,
    secondary_color text,
    unique (career_id, id),
    foreign key (career_id, engine_supplier_id) references engine_suppliers (career_id, id)
);

comment on table teams is 'La Griglia: 11 squadre per Carriera (10 AI + giocatore), con Attributi vettura correnti e stato economico.';
comment on column teams.primary_color is 'Colore primario della livrea: esadecimale #rrggbb o nome colore. Scelto dal giocatore alla creazione; NULL per le squadre AI.';
comment on column teams.secondary_color is 'Colore secondario della livrea: esadecimale #rrggbb o nome colore. Scelto dal giocatore alla creazione; NULL per le squadre AI.';

-- At most one player team per career.
create unique index teams_player_unique on teams (career_id) where is_player;

create table drivers (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    -- Fictional name, editable via Studio.
    name text not null,
    -- Lowercase ISO 3166-1 alpha-2 code (e.g. 'it', 'gb'). Empty string when unknown.
    nationality text not null default '',
    age smallint not null check (age between 16 and 60),
    -- The 6 visible driver attributes (0-100).
    one_lap_pace numeric(5,2) not null default 50 check (one_lap_pace between 0 and 100),
    race_pace numeric(5,2) not null default 50 check (race_pace between 0 and 100),
    duels numeric(5,2) not null default 50 check (duels between 0 and 100),
    tyre_management numeric(5,2) not null default 50 check (tyre_management between 0 and 100),
    wet_weather numeric(5,2) not null default 50 check (wet_weather between 0 and 100),
    consistency numeric(5,2) not null default 50 check (consistency between 0 and 100),
    -- Potential: hidden attribute, growth or decline margin. Never shown.
    potential numeric(5,2) not null default 50 check (potential between 0 and 100),
    -- Career retirement: the driver left the scene at the end of a season.
    retired boolean not null default false,
    unique (career_id, id)
);

comment on table drivers is 'Il roster piloti della Carriera: i 22 titolari piu'' Giovani generati e ritirati. L''appartenenza a una squadra passa dai contratti.';
comment on column drivers.nationality is 'Codice ISO 3166-1 alpha-2 minuscolo (es. ''it'', ''gb''). Stringa vuota se non nota.';

create table contracts (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    team_id uuid not null,
    driver_id uuid not null,
    -- Year of the first season covered by the contract.
    start_season integer not null check (start_season >= 2026),
    duration_seasons smallint not null check (duration_seasons between 1 and 3),
    -- Annual salary: weighs on cash only, excluded from the cap.
    salary_usd numeric(12,2) not null check (salary_usd >= 0),
    unique (career_id, id),
    foreign key (career_id, team_id) references teams (career_id, id),
    foreign key (career_id, driver_id) references drivers (career_id, id)
);

comment on table contracts is 'Contratti squadra-pilota: durata 1-3 stagioni, stipendio fuori Cap. I contratti in scadenza alimentano il Mercato piloti.';

create index contracts_team on contracts (career_id, team_id);
create index contracts_driver on contracts (career_id, driver_id);

-- ---------------------------------------------------------------------------
-- Sporting structure: seasons, grands prix, sessions, results
-- ---------------------------------------------------------------------------

create table seasons (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    year integer not null check (year >= 2026),
    -- Cap: seasonal spending ceiling, identical for every team ($215M like the
    -- real 2026 F1). Individual reductions from overspend are recorded as
    -- financial transactions of kind 'overspend'.
    cap_usd numeric(14,2) not null default 215000000 check (cap_usd > 0),
    status text not null default 'in_progress' check (status in ('in_progress', 'completed')),
    unique (career_id, year),
    unique (career_id, id)
);

comment on table seasons is 'Le stagioni di una Carriera: il Calendario 2026 si ripete ogni anno con l''anno che avanza.';

create table grands_prix (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    season_id uuid not null,
    circuit_id uuid not null references circuits (id),
    round smallint not null check (round between 1 and 24),
    -- Race date in the season calendar (year shifted from race_date_2026).
    race_date date not null,
    -- Weekend format: the MVP only has 'standard' (practice, Q1/Q2/Q3, race);
    -- the 'sprint' flag is in the schema from day one to avoid future migrations.
    weekend_format text not null default 'standard'
        check (weekend_format in ('standard', 'sprint')),
    status text not null default 'scheduled'
        check (status in ('scheduled', 'in_progress', 'completed')),
    unique (career_id, id),
    unique (career_id, season_id, round),
    foreign key (career_id, season_id) references seasons (career_id, id)
);

comment on table grands_prix is 'I Gran Premi di una stagione di Carriera, istanziati dal Calendario statico dei circuiti.';

create table sessions (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    grand_prix_id uuid not null,
    -- Standard format kinds: practice, q1, q2, q3, race.
    -- sprint_qualifying and sprint are modelled but post-MVP.
    kind text not null check (kind in ('practice', 'q1', 'q2', 'q3', 'sprint_qualifying', 'sprint', 'race')),
    -- Progressive number for repeatable kinds (e.g. multiple practice sessions).
    number smallint not null default 1 check (number >= 1),
    status text not null default 'scheduled'
        check (status in ('scheduled', 'in_progress', 'completed')),
    unique (career_id, id),
    unique (career_id, grand_prix_id, kind, number),
    foreign key (career_id, grand_prix_id) references grands_prix (career_id, id)
);

comment on table sessions is 'Le sessioni di un Gran Premio. Fine sessione e pre-gara sono i punti di Checkpoint.';

create table results (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    session_id uuid not null,
    driver_id uuid not null,
    team_id uuid not null,
    -- Final position in the timesheet or finishing order. NULL when the driver
    -- is not classified (early DNF, did not start).
    position smallint check (position between 1 and 22),
    best_time_ms integer check (best_time_ms > 0),
    laps_completed smallint not null default 0 check (laps_completed >= 0),
    status text not null default 'classified'
        check (status in ('classified', 'dnf', 'did_not_start')),
    -- Points awarded to the driver in this session (race only, sprint post-MVP).
    points smallint not null default 0 check (points >= 0),
    unique (career_id, id),
    unique (career_id, session_id, driver_id),
    foreign key (career_id, session_id) references sessions (career_id, id),
    foreign key (career_id, driver_id) references drivers (career_id, id),
    foreign key (career_id, team_id) references teams (career_id, id)
);

comment on table results is 'Risultato di un pilota in una sessione: posizione, miglior tempo, giri, eventuale Abbandono, punti.';

create index results_driver on results (career_id, driver_id);
create index results_team on results (career_id, team_id);

-- ---------------------------------------------------------------------------
-- Economy and development
-- ---------------------------------------------------------------------------

create table financial_transactions (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    team_id uuid not null,
    season_id uuid not null,
    -- Set for transactions tied to a GP (race prize, in-weekend damage).
    grand_prix_id uuid,
    kind text not null check (kind in (
        'race_prize',          -- post-GP income based on finishing position
        'annual_sponsor',      -- guaranteed income at season start, scales with prestige
        'constructors_pool',   -- end-of-season income, constructors standings
        'one_off_sponsor',     -- extra-race event
        'stopgap_sponsor',     -- emergency measure with prestige malus
        'loan',                -- emergency measure: payout
        'interest',            -- emergency measure: cost of the loan
        'salary',              -- driver salaries, outside the cap
        'engine_fee',          -- annual customer fee to the engine supplier
        'development_project', -- cost of a project, from the cap
        'damage',              -- repairs after a crash or failure: cash and cap
        'overspend',           -- reduction of next season's cap
        'other'
    )),
    -- Positive = income, negative = expense.
    amount_usd numeric(14,2) not null,
    -- True when the transaction consumes (or reduces) the cap, besides moving cash.
    counts_against_cap boolean not null default false,
    description text,
    -- Date in the game calendar when the transaction happens.
    game_date date not null,
    recorded_at timestamptz not null default now(),
    unique (career_id, id),
    foreign key (career_id, team_id) references teams (career_id, id),
    foreign key (career_id, season_id) references seasons (career_id, id),
    foreign key (career_id, grand_prix_id) references grands_prix (career_id, id)
);

comment on table financial_transactions is 'Registro transazionale dell''economia: ogni movimento di Cassa o Cap e'' una riga. Cassa e Cap residuo si ricostruiscono per somma.';

create index financial_transactions_team on financial_transactions (career_id, team_id);
create index financial_transactions_season on financial_transactions (career_id, season_id);

create table development_projects (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    team_id uuid not null,
    season_id uuid not null,
    -- The car attribute targeted by the project.
    attribute text not null check (attribute in (
        'engine_power', 'downforce', 'aero_efficiency',
        'mechanical_grip', 'tyre_management', 'reliability'
    )),
    -- True for winter projects (decided between one season and the next).
    winter boolean not null default false,
    -- Cost charged against the cap.
    cost_usd numeric(12,2) not null check (cost_usd > 0),
    start_date date not null,
    duration_days smallint not null check (duration_days > 0),
    status text not null default 'in_progress'
        check (status in ('in_progress', 'completed', 'cancelled')),
    -- Delta applied to the attribute on completion (outcome with variance,
    -- negative for a flop). NULL while the project is in progress.
    outcome numeric(5,2),
    unique (career_id, id),
    foreign key (career_id, team_id) references teams (career_id, id),
    foreign key (career_id, season_id) references seasons (career_id, id)
);

comment on table development_projects is 'Progetti di sviluppo: costo dal Cap, durata in giorni di calendario, esito con varianza. Il limite di 2 Progetti paralleli per squadra e'' regola di gioco, non vincolo DB.';

create index development_projects_team on development_projects (career_id, team_id);
