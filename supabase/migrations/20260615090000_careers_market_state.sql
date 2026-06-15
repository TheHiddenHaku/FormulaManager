-- Market phase state on the career root (T5.2.1, sub-issue M4).
--
-- One JSON document on the careers row, written and read atomically with
-- the rest of the career state (ADR 0001): the driver Market phase while it
-- is open (end of season), i.e. the pool of expiring contracts, the free
-- agents and their transient salary demands, the vacant seats, the signings
-- and the AI move log. The roster mutations the Market produces (new and
-- removed contracts) ride the existing contracts table, not this column.
-- NULL means the starting state (Market closed): existing saves keep loading
-- unchanged.

alter table careers add column market_state jsonb;

comment on column careers.market_state is 'Stato della fase di Mercato piloti (T5.2.1), serializzato da fm_persistence.market: pool dei Contratti in scadenza, liberi e richieste salariali transitorie, sedili vacanti, firme e log mosse. NULL = fase chiusa (stato di partenza). Le mutazioni del roster usano la tabella contracts.';
