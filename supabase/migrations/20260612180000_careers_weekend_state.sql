-- Weekend state on the career root (FOR-21).
--
-- The in-progress GP weekend survives the Checkpoint: phase, practice
-- programme effects, starting grid and final classification are
-- serialized as a single JSON document on the careers row, written and
-- read atomically with the rest of the career state (ADR 0001). NULL
-- means no weekend in progress: existing saves keep loading unchanged.

alter table careers add column weekend_state jsonb;

comment on column careers.weekend_state is 'Stato del weekend di gara in corso (FOR-21), serializzato da fm_persistence.weekend: fase, effetti dei Programmi, griglia di partenza e classifica finale con i punti. NULL fuori dal weekend.';
