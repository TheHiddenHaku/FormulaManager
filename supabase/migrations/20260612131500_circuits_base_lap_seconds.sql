-- Tempo base sul giro per circuito (FOR-37).
--
-- Riferimento realistico del giro di gara della stagione base, in
-- secondi: sostituisce la velocita' media globale del modello del tempo
-- (BASE_AVERAGE_SPEED_KMH). La base e' additiva e uguale per tutte le
-- vetture sullo stesso circuito: distacchi e bilanciamento invariati.
-- Mirror Python: src/fm_engine/circuits.py.

alter table circuits
    add column base_lap_seconds numeric(5,2);

update circuits
set base_lap_seconds = v.base_lap
from (values
    ('albert_park', 80.0),
    ('shanghai', 95.0),
    ('suzuka', 92.0),
    ('sakhir', 93.0),
    ('jeddah', 91.0),
    ('miami', 91.0),
    ('montreal', 76.0),
    ('monaco', 74.0),
    ('barcellona', 77.0),
    ('spielberg', 68.0),
    ('silverstone', 90.0),
    ('spa', 107.0),
    ('hungaroring', 80.0),
    ('zandvoort', 75.0),
    ('monza', 85.0),
    ('madring', 95.0),
    ('baku', 105.0),
    ('marina_bay', 97.0),
    ('austin', 96.0),
    ('citta_del_messico', 81.0),
    ('interlagos', 75.0),
    ('las_vegas', 95.0),
    ('lusail', 86.0),
    ('yas_marina', 88.0)
) as v(code, base_lap)
where circuits.code = v.code;

alter table circuits
    alter column base_lap_seconds set not null;

alter table circuits
    add constraint circuits_base_lap_seconds_check
    check (base_lap_seconds > 0);

comment on column circuits.base_lap_seconds is
    'Tempo base sul giro in secondi: riferimento realistico del giro di gara della stagione base. Base additiva del modello del tempo, uguale per tutte le vetture; valore di partenza tarabile.';
