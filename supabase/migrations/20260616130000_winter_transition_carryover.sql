-- Fase inverno tra le stagioni: Carry-over, Progetti invernali, rollover (FOR-32).
--
-- La transizione di stagione (fm_engine.winter.advance_winter) NON introduce
-- nuovo stato persistente: i suoi effetti viaggiano sulle tabelle gia'
-- esistenti, scritti dal Checkpoint a granularita' di Carriera intera
-- (ADR 0001) in un'unica transazione (save_career), cosi' o si salva tutta
-- la stagione nuova o niente:
--
-- - Carry-over della vettura (attributi regrediti verso la media di griglia)
--   e Progetti invernali: aggiornano teams (squadra del giocatore e AI), le
--   stesse colonne degli Attributi vettura del Setup squadra.
-- - Rinegoziazione delle scelte di fondo (motore proprio vs Cliente, Filosofia
--   telaio): aggiornano teams.engine_supplier_id, teams.engine_power e
--   teams.chassis_philosophy della squadra del giocatore.
-- - Rollover economico (nuovo Cap con penalita' da Sforamento, Cassa riportata,
--   Sponsor annuale): la riga della stagione nuova in seasons (cap_usd) e i
--   movimenti in financial_transactions.
-- - Le mutazioni del roster del Mercato piloti (FOR-30) restano in contracts.
--
-- Questa migration e' di sola documentazione: rende esplicito nello schema il
-- ruolo della transizione di stagione e i vincoli usati dal Carry-over, senza
-- alterare struttura ne' dati. Idempotente per costruzione (solo COMMENT).

comment on column teams.engine_power is 'Potenza motore (Attributo vettura). Per i Clienti e'' la copia della Potenza del Motorista fornitore. Il Carry-over (FOR-32) la fa regredire verso la media di griglia tra una stagione e l''altra; la rinegoziazione del motore (Cliente vs proprio) puo'' reimpostarla.';

comment on column teams.chassis_philosophy is 'Filosofia telaio (FOR-7): fast / balanced / technical. Scelta alla creazione della squadra e rinegoziabile ogni inverno (FOR-32): cambia i delta su efficienza/carico/meccanica della stagione nuova.';

comment on column seasons.cap_usd is 'Cap stagionale ($215M di partenza). Il rollover invernale (FOR-32) imposta il Cap della stagione nuova: pieno senza Sforamento, ridotto della penalita'' proporzionale (mai sotto il pavimento) in caso di Sforamento.';
