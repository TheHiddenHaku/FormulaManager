-- Season state on the career root (T5.1.1).
--
-- The multi-season clock and standings survive the Checkpoint: current
-- year, game date and the results of the grands prix played so far are
-- serialized as a single JSON document on the careers row, written and
-- read atomically with the rest of the career state (ADR 0001). NULL
-- means the starting state (2026, before the first GP, empty standings):
-- existing saves keep loading unchanged.

alter table careers add column season_state jsonb;

comment on column careers.season_state is 'Stato di stagione della Carriera (T5.1.1), serializzato da fm_persistence.season: anno corrente, data di gioco e risultati dei GP disputati (da cui le classifiche piloti e costruttori). NULL = stato di partenza (2026, prima del primo GP).';
