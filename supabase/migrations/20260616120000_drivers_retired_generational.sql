-- Ricambio generazionale del parco piloti (FOR-31, T5.2.2).
--
-- Il flag drivers.retired distingue i piloti ritirati di carriera (usciti
-- dal parco attivo a fine stagione) dai piloti in attivita'. I ritirati
-- restano nel roster come storia della Carriera ma non vengono piu'
-- selezionati dai Contratti ne' entrano nel pool del Mercato piloti.
--
-- La colonna esiste gia' nello schema iniziale (20260612004743): questa
-- migration la rende idempotente (add column if not exists) cosi' che lo
-- schema sia esplicito sulla dipendenza FOR-31 anche se applicata a un DB
-- creato prima che il motore valorizzasse il flag. Aggiunge inoltre un
-- indice parziale sui piloti attivi: le query del parco attivo (generazione
-- dei Giovani, popolamento del pool) filtrano su retired = false.

alter table drivers add column if not exists retired boolean not null default false;

comment on column drivers.retired is 'Ritiro di carriera (FOR-31): true se il pilota e'' uscito dal parco attivo a fine stagione. I ritirati restano nel roster come storia ma non sono piu'' ingaggiabili.';

create index if not exists drivers_active on drivers (career_id) where not retired;
