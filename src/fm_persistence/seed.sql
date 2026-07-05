-- Seed dei dati statici globali di Formula Manager, dialetto SQLite.
--
-- Contiene SOLO dati statici, condivisi da tutte le Carriere: i 24 circuiti del
-- Calendario 2026, le tabelle punti e i Premi gara. Nessun dato di Carriera:
-- squadre, piloti, motoristi e contratti vengono creati alla creazione di una
-- nuova Carriera dal codice di gioco.
--
-- Calendario 2026 come da annuncio originale del 2025: INCLUDE Bahrain e Jeddah
-- (poi cancellati nella realta'), con date e pause reali. I 6 GP sprint del 2026
-- reale (Cina, Miami, Canada, Gran Bretagna, Paesi Bassi, Singapore) sono marcati
-- in weekend_format_2026: il MVP li gioca comunque in formato standard.
--
-- Pesi sui 6 Attributi vettura (0.00-1.00), tempo base sul giro, severita' gomme
-- (1-5), difficolta' di sorpasso (1-5), probabilita' Safety car e pioggia
-- (0.00-1.00), profilo meteo e mescole nominate sono valori di partenza da tarare.
--
-- circuits.id: nello schema Postgres era una uuid generata dal DB e il seed la
-- ometteva. In SQLite l'id lo scrive chi inserisce, quindi qui l'id coincide col
-- code (chiave naturale gia' unica). Il runtime non interroga questa tabella:
-- il motore tiene i propri dati statici (fm_engine.circuits).
--
-- Idempotente: insert or ignore salta le righe gia' presenti (per chiave unica).

insert or ignore into circuits (
    id, code, name, country, locality,
    length_metres, race_laps, calendar_order, race_date_2026, weekend_format_2026,
    base_lap_seconds,
    engine_power_weight, downforce_weight, aero_efficiency_weight,
    mechanical_grip_weight, tyre_management_weight, reliability_weight,
    tyre_severity, overtaking_difficulty, safety_car_probability, weather_profile,
    rain_probability,
    hard_compound, medium_compound, soft_compound
) values
    ('albert_park', 'albert_park', 'Albert Park Circuit', 'Australia', 'Melbourne',
     5278, 58, 1, '2026-03-08', 'standard', 80.0,
     0.70, 0.75, 0.65, 0.75, 0.65, 0.60,
     3, 3, 0.40, 'variable', 0.25, 'C3', 'C4', 'C5'),
    ('shanghai', 'shanghai', 'Shanghai International Circuit', 'Cina', 'Shanghai',
     5451, 56, 2, '2026-03-15', 'sprint', 95.0,
     0.75, 0.75, 0.70, 0.65, 0.80, 0.60,
     4, 2, 0.30, 'variable', 0.30, 'C2', 'C3', 'C4'),
    ('suzuka', 'suzuka', 'Suzuka International Racing Course', 'Giappone', 'Suzuka',
     5807, 53, 3, '2026-03-29', 'standard', 92.0,
     0.70, 0.90, 0.75, 0.70, 0.80, 0.65,
     4, 4, 0.25, 'variable', 0.30, 'C1', 'C2', 'C3'),
    ('sakhir', 'sakhir', 'Bahrain International Circuit', 'Bahrein', 'Sakhir',
     5412, 57, 4, '2026-04-12', 'standard', 93.0,
     0.80, 0.65, 0.70, 0.75, 0.85, 0.75,
     4, 2, 0.30, 'dry', 0.05, 'C1', 'C2', 'C3'),
    ('jeddah', 'jeddah', 'Jeddah Corniche Circuit', 'Arabia Saudita', 'Jeddah',
     6174, 50, 5, '2026-04-19', 'standard', 91.0,
     0.85, 0.70, 0.85, 0.65, 0.60, 0.70,
     2, 2, 0.60, 'dry', 0.05, 'C2', 'C3', 'C4'),
    ('miami', 'miami', 'Miami International Autodrome', 'Stati Uniti', 'Miami',
     5412, 57, 6, '2026-05-03', 'sprint', 91.0,
     0.80, 0.70, 0.75, 0.70, 0.75, 0.70,
     3, 3, 0.45, 'variable', 0.30, 'C2', 'C3', 'C4'),
    ('montreal', 'montreal', 'Circuit Gilles Villeneuve', 'Canada', 'Montreal',
     4361, 70, 7, '2026-05-24', 'sprint', 76.0,
     0.85, 0.60, 0.75, 0.80, 0.70, 0.75,
     3, 2, 0.50, 'variable', 0.35, 'C3', 'C4', 'C5'),
    ('monaco', 'monaco', 'Circuit de Monaco', 'Monaco', 'Monte Carlo',
     3337, 78, 8, '2026-06-07', 'standard', 74.0,
     0.40, 0.90, 0.40, 0.95, 0.55, 0.70,
     1, 5, 0.65, 'variable', 0.20, 'C3', 'C4', 'C5'),
    ('barcellona', 'barcellona', 'Circuit de Barcelona-Catalunya', 'Spagna', 'Montmelo',
     4657, 66, 9, '2026-06-14', 'standard', 77.0,
     0.65, 0.85, 0.70, 0.70, 0.85, 0.60,
     4, 4, 0.20, 'dry', 0.10, 'C1', 'C2', 'C3'),
    ('spielberg', 'spielberg', 'Red Bull Ring', 'Austria', 'Spielberg',
     4318, 71, 10, '2026-06-28', 'standard', 68.0,
     0.80, 0.65, 0.70, 0.75, 0.70, 0.70,
     3, 2, 0.35, 'variable', 0.30, 'C3', 'C4', 'C5'),
    ('silverstone', 'silverstone', 'Silverstone Circuit', 'Gran Bretagna', 'Silverstone',
     5891, 52, 11, '2026-07-05', 'sprint', 90.0,
     0.75, 0.90, 0.75, 0.65, 0.85, 0.65,
     5, 2, 0.30, 'variable', 0.35, 'C1', 'C2', 'C3'),
    ('spa', 'spa', 'Circuit de Spa-Francorchamps', 'Belgio', 'Stavelot',
     7004, 44, 12, '2026-07-19', 'standard', 107.0,
     0.85, 0.75, 0.85, 0.65, 0.75, 0.70,
     4, 1, 0.45, 'wet', 0.45, 'C2', 'C3', 'C4'),
    ('hungaroring', 'hungaroring', 'Hungaroring', 'Ungheria', 'Mogyorod',
     4381, 70, 13, '2026-07-26', 'standard', 80.0,
     0.55, 0.90, 0.50, 0.85, 0.75, 0.70,
     3, 4, 0.30, 'dry', 0.20, 'C3', 'C4', 'C5'),
    ('zandvoort', 'zandvoort', 'Circuit Zandvoort', 'Paesi Bassi', 'Zandvoort',
     4259, 72, 14, '2026-08-23', 'sprint', 75.0,
     0.60, 0.90, 0.60, 0.80, 0.75, 0.65,
     3, 4, 0.40, 'wet', 0.40, 'C2', 'C3', 'C4'),
    ('monza', 'monza', 'Autodromo Nazionale di Monza', 'Italia', 'Monza',
     5793, 53, 15, '2026-09-06', 'standard', 85.0,
     0.95, 0.45, 0.95, 0.60, 0.60, 0.75,
     2, 1, 0.30, 'dry', 0.15, 'C3', 'C4', 'C5'),
    ('madring', 'madring', 'Madring', 'Spagna', 'Madrid',
     5474, 57, 16, '2026-09-13', 'standard', 95.0,
     0.70, 0.75, 0.70, 0.80, 0.70, 0.65,
     3, 3, 0.50, 'dry', 0.15, 'C2', 'C3', 'C4'),
    ('baku', 'baku', 'Baku City Circuit', 'Azerbaigian', 'Baku',
     6003, 51, 17, '2026-09-27', 'standard', 105.0,
     0.90, 0.60, 0.85, 0.75, 0.60, 0.70,
     2, 2, 0.60, 'dry', 0.10, 'C3', 'C4', 'C5'),
    ('marina_bay', 'marina_bay', 'Marina Bay Street Circuit', 'Singapore', 'Singapore',
     4940, 62, 18, '2026-10-11', 'sprint', 97.0,
     0.55, 0.90, 0.50, 0.90, 0.70, 0.85,
     3, 4, 0.70, 'wet', 0.40, 'C3', 'C4', 'C5'),
    ('austin', 'austin', 'Circuit of the Americas', 'Stati Uniti', 'Austin',
     5513, 56, 19, '2026-10-25', 'standard', 96.0,
     0.75, 0.80, 0.70, 0.75, 0.80, 0.65,
     4, 2, 0.35, 'variable', 0.20, 'C2', 'C3', 'C4'),
    ('citta_del_messico', 'citta_del_messico', 'Autodromo Hermanos Rodriguez', 'Messico', 'Citta del Messico',
     4304, 71, 20, '2026-11-01', 'standard', 81.0,
     0.70, 0.85, 0.55, 0.75, 0.70, 0.85,
     2, 3, 0.40, 'variable', 0.25, 'C3', 'C4', 'C5'),
    ('interlagos', 'interlagos', 'Autodromo Jose Carlos Pace', 'Brasile', 'San Paolo',
     4309, 71, 21, '2026-11-08', 'standard', 75.0,
     0.75, 0.75, 0.70, 0.75, 0.75, 0.70,
     3, 2, 0.45, 'wet', 0.45, 'C2', 'C3', 'C4'),
    ('las_vegas', 'las_vegas', 'Las Vegas Strip Circuit', 'Stati Uniti', 'Las Vegas',
     6201, 50, 22, '2026-11-21', 'standard', 95.0,
     0.90, 0.50, 0.90, 0.70, 0.65, 0.65,
     2, 1, 0.50, 'dry', 0.05, 'C3', 'C4', 'C5'),
    ('lusail', 'lusail', 'Lusail International Circuit', 'Qatar', 'Lusail',
     5419, 57, 23, '2026-11-29', 'standard', 86.0,
     0.70, 0.85, 0.70, 0.65, 0.90, 0.75,
     5, 3, 0.35, 'dry', 0.05, 'C1', 'C2', 'C3'),
    ('yas_marina', 'yas_marina', 'Yas Marina Circuit', 'Emirati Arabi Uniti', 'Abu Dhabi',
     5281, 58, 24, '2026-12-06', 'standard', 88.0,
     0.75, 0.70, 0.70, 0.75, 0.70, 0.65,
     2, 3, 0.35, 'dry', 0.05, 'C3', 'C4', 'C5');

-- Tabella punti gara 2026 reale: 25-18-15-12-10-8-6-4-2-1, senza punto giro veloce.
insert or ignore into points_tables (code, position, points) values
    ('race_2026', 1, 25),
    ('race_2026', 2, 18),
    ('race_2026', 3, 15),
    ('race_2026', 4, 12),
    ('race_2026', 5, 10),
    ('race_2026', 6, 8),
    ('race_2026', 7, 6),
    ('race_2026', 8, 4),
    ('race_2026', 9, 2),
    ('race_2026', 10, 1);

-- Tabella punti sprint 2026 reale (8-7-6-5-4-3-2-1): post-MVP, gia' in seed cosi'
-- non serve una migrazione quando la sprint verra' abilitata.
insert or ignore into points_tables (code, position, points) values
    ('sprint_2026', 1, 8),
    ('sprint_2026', 2, 7),
    ('sprint_2026', 3, 6),
    ('sprint_2026', 4, 5),
    ('sprint_2026', 5, 4),
    ('sprint_2026', 6, 3),
    ('sprint_2026', 7, 2),
    ('sprint_2026', 8, 1);

-- Premio gara per posizione di arrivo (tutte e 22 le vetture incassano qualcosa).
-- Importi di partenza tarabili: una top team fa circa 5M a GP, una di meta'
-- gruppo circa 1M, contro un Cap stagionale di 215M.
insert or ignore into race_prizes (code, position, amount_usd) values
    ('race_2026', 1, 3000000),
    ('race_2026', 2, 2500000),
    ('race_2026', 3, 2100000),
    ('race_2026', 4, 1800000),
    ('race_2026', 5, 1500000),
    ('race_2026', 6, 1250000),
    ('race_2026', 7, 1050000),
    ('race_2026', 8, 900000),
    ('race_2026', 9, 750000),
    ('race_2026', 10, 650000),
    ('race_2026', 11, 550000),
    ('race_2026', 12, 480000),
    ('race_2026', 13, 420000),
    ('race_2026', 14, 370000),
    ('race_2026', 15, 330000),
    ('race_2026', 16, 300000),
    ('race_2026', 17, 270000),
    ('race_2026', 18, 240000),
    ('race_2026', 19, 210000),
    ('race_2026', 20, 180000),
    ('race_2026', 21, 150000),
    ('race_2026', 22, 120000);
