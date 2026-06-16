-- Archivio permanente della Carriera: Almanacco e Albo d'oro (T5.3.2).
--
-- Lo storico vive in tabelle relazionali dedicate, NON in una colonna
-- jsonb: per ogni GP disputato la griglia di partenza, l'ordine d'arrivo
-- e gli eventi principali; per ogni stagione conclusa le classifiche
-- finali e i Titoli. Le tabelle sono scritte SOLO nel flusso di save_career
-- (Checkpoint a granularita' di Carriera intera, ADR 0001): delete e
-- reinsert dell'intero archivio in transazione, mai scritture incrementali
-- fuori Checkpoint. Indici dedicati su (career_id, year) per query
-- efficienti dell'Almanacco su Carriere lunghe (10+ stagioni).
--
-- "Mai cancellato ne' sovrascritto dai cambi di stagione" e' garantito a
-- monte dal modello (l'archivio in memoria accumula): qui il rewrite
-- riscrive sempre l'intero archivio accumulato, quindi le stagioni passate
-- restano presenti a ogni Checkpoint.

-- Una riga per stagione archiviata. I Titoli (campioni piloti e
-- costruttori) sono NULL finche' la stagione e' in corso.
create table archive_seasons (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    year integer not null,
    -- Driver id del campione piloti; NULL se la stagione non e' conclusa.
    driver_champion_id integer,
    -- Team id del campione costruttori; NULL se la stagione non e' conclusa.
    constructor_champion_id integer,
    unique (career_id, year),
    unique (career_id, id)
);

comment on table archive_seasons is 'Albo d''oro per stagione archiviata (T5.3.2): anno e Titoli piloti e costruttori. Mai cancellata dai cambi di stagione: l''archivio accumula.';

create index archive_seasons_career_year on archive_seasons (career_id, year);

-- Le righe di classifica finale di ogni stagione, piloti e costruttori.
-- scope distingue le due classifiche; entity_id e' il driver_id o il
-- team_id a seconda dello scope.
create table archive_standings (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    year integer not null,
    scope text not null check (scope in ('driver', 'constructor')),
    position integer not null check (position >= 1),
    entity_id integer not null,
    points integer not null check (points >= 0),
    wins integer not null check (wins >= 0),
    unique (career_id, id),
    unique (career_id, year, scope, position)
);

comment on table archive_standings is 'Classifiche finali archiviate di ogni stagione (T5.3.2), piloti e costruttori (scope). entity_id e'' il driver_id o il team_id.';

create index archive_standings_career_year on archive_standings (career_id, year);

-- Una riga per GP disputato e archiviato (voce di Almanacco).
create table archive_grands_prix (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    year integer not null,
    round integer not null check (round >= 1),
    circuit_code text not null,
    unique (career_id, id),
    unique (career_id, year, round)
);

comment on table archive_grands_prix is 'Voce di Almanacco di un GP disputato (T5.3.2): stagione, round e circuito. Griglia, arrivo ed eventi nelle tabelle figlie.';

create index archive_grands_prix_career_year on archive_grands_prix (career_id, year);

-- La griglia di partenza di un GP archiviato, in ordine di pole
-- (grid_position 1 = pole). Una riga per pilota schierato.
create table archive_starting_grid (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    year integer not null,
    round integer not null,
    grid_position integer not null check (grid_position >= 1),
    driver_id integer not null,
    unique (career_id, id),
    unique (career_id, year, round, grid_position)
);

comment on table archive_starting_grid is 'Griglia di partenza archiviata di un GP (T5.3.2), in ordine di pole (grid_position 1 = pole).';

create index archive_starting_grid_career_year_round
    on archive_starting_grid (career_id, year, round);

-- L'ordine d'arrivo completo di un GP archiviato, coi punti 2026.
create table archive_results (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
    year integer not null,
    round integer not null,
    position integer not null check (position >= 1),
    driver_id integer not null,
    team_id integer not null,
    points integer not null check (points >= 0),
    total_time_seconds double precision not null,
    gap_to_winner_seconds double precision not null,
    penalty_seconds double precision not null default 0,
    unique (career_id, id),
    unique (career_id, year, round, position)
);

comment on table archive_results is 'Ordine d''arrivo archiviato di un GP (T5.3.2): posizione, pilota, squadra, punti 2026 e tempi.';

create index archive_results_career_year_round on archive_results (career_id, year, round);

-- Gli eventi principali di un GP archiviato (ADR 0003: niente Telecronaca
-- integrale, solo Safety car e Abbandoni). ordinal conserva l'ordine.
create table archive_principal_events (
    id uuid primary key default gen_random_uuid(),
    career_id uuid not null references careers (id) on delete cascade,
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

comment on table archive_principal_events is 'Eventi principali archiviati di un GP (T5.3.2): Safety car e Abbandoni (ADR 0003, niente Telecronaca integrale).';

create index archive_principal_events_career_year_round
    on archive_principal_events (career_id, year, round);
