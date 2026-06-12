-- Difficolta' di sorpasso per circuito (FOR-36).
--
-- Scala 1 (sorpassare e' facile: Monza, Spa) - 5 (quasi impossibile:
-- Monaco). Modula la probabilita' di successo dei duelli nel motore di
-- gara. Mirror Python: src/fm_engine/circuits.py.

alter table circuits
    add column overtaking_difficulty smallint;

update circuits
set overtaking_difficulty = v.difficulty
from (values
    ('albert_park', 3),
    ('shanghai', 2),
    ('suzuka', 4),
    ('sakhir', 2),
    ('jeddah', 2),
    ('miami', 3),
    ('montreal', 2),
    ('monaco', 5),
    ('barcellona', 4),
    ('spielberg', 2),
    ('silverstone', 2),
    ('spa', 1),
    ('hungaroring', 4),
    ('zandvoort', 4),
    ('monza', 1),
    ('madring', 3),
    ('baku', 2),
    ('marina_bay', 4),
    ('austin', 2),
    ('citta_del_messico', 3),
    ('interlagos', 2),
    ('las_vegas', 1),
    ('lusail', 3),
    ('yas_marina', 3)
) as v(code, difficulty)
where circuits.code = v.code;

alter table circuits
    alter column overtaking_difficulty set not null;

alter table circuits
    add constraint circuits_overtaking_difficulty_check
    check (overtaking_difficulty between 1 and 5);

comment on column circuits.overtaking_difficulty is
    'Difficolta'' di sorpasso in pista, scala 1 (facile: Monza) - 5 (quasi impossibile: Monaco). Modula la risoluzione dei duelli; valore di partenza tarabile.';
