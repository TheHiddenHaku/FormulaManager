-- Pre-season phase and estimate knowledge on the career root (T5.1.2).
--
-- Two JSON documents on the careers row, written and read atomically with
-- the rest of the career state (ADR 0001):
--   - knowledge_state: how much the player knows each subject (car or
--     driver), i.e. how tight the estimate margins are. Grows with
--     Knowledge programmes, practice and races.
--   - preseason_state: the Test pre-season phase (days run and the
--     programmes assigned to the player drivers).
-- NULL means the starting state (no knowledge gained, pre-season not
-- started): existing saves keep loading unchanged.

alter table careers add column knowledge_state jsonb;
alter table careers add column preseason_state jsonb;

comment on column careers.knowledge_state is 'Conoscenza degli attributi (T5.1.2), serializzata da fm_persistence.estimates: livello per soggetto (vettura o pilota) da cui il margine delle Stime. NULL = nessuna conoscenza accumulata.';
comment on column careers.preseason_state is 'Stato della fase Test pre-season (T5.1.2), serializzato da fm_persistence.preseason: giorni svolti e Programmi assegnati. NULL = fase non iniziata.';
