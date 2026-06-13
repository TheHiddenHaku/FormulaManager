-- Stato di solvibilita' della squadra del giocatore (FOR-24).
--
-- Documento JSON con la storia di solvibilita': Misura d'emergenza usata
-- o in attesa, conto alla rovescia del fallimento, piano di rientro del
-- prestito, malus Prestigio accumulato. NULL = squadra sana senza storia
-- (Checkpoint precedenti a FOR-24 inclusi).

alter table careers add column solvency_state jsonb;

comment on column careers.solvency_state is 'Stato di solvibilita'' del giocatore (FOR-24): Misura d''emergenza, rate del prestito, conto alla rovescia del fallimento, malus Prestigio. NULL = squadra sana.';
