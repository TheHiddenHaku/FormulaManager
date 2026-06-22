---
id: checkpoint-carriera-crash-tabelle-archivio
titolo: "Checkpoint Carriera in crash: tabelle Archivio mancanti su matilde"
stato: review
priorita: urgente
dipendenze: []
etichette: [bug, persistenza, database]
creata: 2026-06-22
scadenza:
---

## Contesto
Durante una partita di prova: creata una Carriera, completato il team setup,
premuto Ctrl+S per salvare l'inizio della Carriera. Il salvataggio va in crash
con:

```
UndefinedTable: relation "archive_principal_events" does not exist
LINE 1: delete from archive_principal_events where career_id = $1
```

La Carriera era stata gia' salvata una prima volta (la riga radice esiste, con
created_at e last_checkpoint_at distinti): e' il secondo Checkpoint a fallire,
non il primo.

Causa: in `save_career` il percorso di Checkpoint successivo (id valorizzato)
esegue un ciclo di delete su `_STATE_TABLES`
(src/fm_persistence/checkpoint.py:183-186). `_STATE_TABLES` include
`history.ARCHIVE_TABLES`, cioe' le sei tabelle `archive_*`
(src/fm_persistence/history.py:40). Quelle tabelle nascono dalla migrazione
`supabase/migrations/20260616140000_career_archive_tables.sql`, presente nel
repo ma mai applicata allo schema del DB di gioco su matilde. Il primo
salvataggio (percorso di insert) non tocca le tabelle Archivio perche'
`insert_archive` su un Archivio vuoto e' un no-op, quindi passa; il secondo
(Ctrl+S, percorso di update) cancella da tutte le tabelle di stato senza
condizioni e muore sulla prima mancante (`archive_principal_events`).

Non e' un bug del motore ne' del codice di persistenza: il codice e' coerente
con le migrazioni del repo (e i test su Postgres effimero le applicano tutte). E'
lo schema remoto di matilde a essere indietro.

## Obiettivo
Il giocatore puo' fare Checkpoint (Ctrl+S) di una Carriera, anche ripetuto, senza
crash. Lo schema di matilde torna allineato alle migrazioni del repo.

## Criteri di accettazione
- [x] La migrazione `20260616140000_career_archive_tables.sql` risulta applicata
      allo schema di matilde: le sei tabelle `archive_*` esistono.
- [x] Verificato che non manchino altre migrazioni su matilde: lo stato delle
      migrazioni applicate coincide con il contenuto di `supabase/migrations/`.
- [ ] Nuova Carriera, team setup completato, due Ctrl+S consecutivi: entrambi i
      salvataggi vanno a buon fine, nessun UndefinedTable.
- [ ] Il caricamento della Carriera salvata ricostruisce l'Archivio (vuoto) senza
      errori.

## Dipendenze
Nessuna.

## Note
- Punto del crash: src/fm_persistence/checkpoint.py:183-186 (ciclo di delete),
  tabella `archive_principal_events`. Elenco tabelle: `ARCHIVE_TABLES` in
  src/fm_persistence/history.py:40.
- Procedura per applicare la migrazione a matilde: supabase/README.md (tunnel SSH
  piu' CLI). Vincolo CLAUDE.md: vietato `supabase start` e qualunque stack locale,
  il DB di gioco e' il self-hosted su matilde; mai test o esperimenti contro quel
  DB.
- Il fix vero e' operativo (applicare la migrazione pendente), non una modifica di
  codice. La disciplina "un test che prima fallisce e poi passa" non si applica in
  modo diretto: i test su Postgres effimero applicano gia' tutte le migrazioni e
  passano, ed e' proprio per questo che il difetto non e' emerso in CI.
- Da capire perche' la migrazione non e' arrivata su matilde (push mancato?
  reset_db.sh non rilanciato dopo l'aggiunta delle tabelle Archivio?) per evitare
  che ricapiti con le prossime migrazioni. Una difesa preventiva (preflight che
  rileva migrazioni pendenti su matilde e da' un errore chiaro invece di crashare
  a meta' Checkpoint) e' fuori dallo scope di questa issue.
- Riproduzione osservata con seed 8323511264827380807, ma il problema e'
  indipendente dal seed.

## Esito
2026-06-22: applicate a matilde le migrazioni pendenti con
`supabase db push` attraverso il tunnel SSH (procedura supabase/README.md).
Su matilde mancavano tre migrazioni, non solo l'Archivio:
`20260616120000_drivers_retired_generational` (la colonna `retired` esisteva
gia', migrazione idempotente, NOTICE skip), `20260616130000_winter_transition_carryover`
e `20260616140000_career_archive_tables`. Dopo il push tutte e 11 le migrazioni
risultano allineate (Local = Remote) e le sei tabelle `archive_*` esistono sul
DB (verificato via information_schema). Restano da spuntare i due criteri di
verifica in gioco (doppio Ctrl+S e load della Carriera): vanno fatti
nell'applicazione, perche' CLAUDE.md vieta test ed esperimenti contro matilde.
Causa radice del difetto: dopo l'aggiunta delle tabelle Archivio nessuno aveva
fatto `db push` verso matilde, che e' rimasto indietro rispetto al repo. Vedi la
regola aggiunta in CLAUDE.md (sezione Database) per non ripetere l'errore.
