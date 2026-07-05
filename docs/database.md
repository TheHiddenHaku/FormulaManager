# Database di gioco (SQLite locale)

Il database di gioco di Formula Manager e' un singolo file SQLite locale. Nessun servizio remoto, niente Docker, niente rete: il gioco parte e salva offline. La decisione e i suoi motivi sono in [ADR 0004](adr/0004-sqlite-locale-come-database-di-gioco.md); qui stanno le procedure operative.

## Percorso del file

Il percorso e' l'unica cosa configurabile, con la variabile d'ambiente `FM_DB_PATH`. In assenza si usa il default sotto la home dell'utente:

```
~/.local/share/formulamanager/formulamanager.db
```

Per usare un percorso diverso (per esempio per tenere piu' partite separate o per un database usa-e-getta):

```sh
export FM_DB_PATH="/percorso/scelto/formulamanager.db"
```

Nel codice la variabile e' `ENV_VAR` e il percorso risolto e' `fm_persistence.database_path()`. `FM_DB_PATH` e' l'unica variabile letta dal layer di persistenza (`src/fm_persistence`).

## Bootstrap al primo avvio

Al primo avvio (file assente o database senza tabelle) `fm_persistence.connect()`:

1. crea la cartella contenitrice se manca;
2. apre il file con `sqlite3` della standard library e attiva `PRAGMA foreign_keys = ON` (impostazione per connessione, non nello schema);
3. applica `src/fm_persistence/schema.sql` (schema baseline) e `src/fm_persistence/seed.sql` (dati statici: circuiti, tabelle punti, Premi gara).

Schema e seed sono package data di `fm_persistence`: non serve applicarli a mano ne' tenere allineato alcuno stack esterno. Non ci sono migrazioni incrementali; lo schema porta `PRAGMA user_version = 1` come aggancio per eventuali migrazioni future.

## Reset

Per ripartire da zero basta cancellare il file: al primo avvio successivo il gioco lo ricrea vuoto con schema e seed. Lo script fa questo, con conferma perche' e' distruttivo:

```sh
scripts/reset_db.sh        # chiede conferma, poi cancella il file (e i suoi -wal/-shm)
scripts/reset_db.sh --yes  # salta la conferma
```

Rispetta `FM_DB_PATH`: cancella il database puntato dalla variabile, o il default se non impostata.

## Ispezione manuale

Il file e' un database SQLite qualsiasi: si ispeziona e si edita con un client SQLite (per esempio la CLI `sqlite3` o un editor grafico). L'editing a mano dei dati (nomi di squadre, piloti, motoristi) si fa tra una sessione e l'altra; il gioco rilegge lo stato al load successivo.

```sh
sqlite3 "${FM_DB_PATH:-$HOME/.local/share/formulamanager/formulamanager.db}"
```

## Test

I test che toccano la persistenza usano un file SQLite temporaneo con schema e seed applicati (fixture `game_db_path` in `tests/conftest.py`): girano senza Docker e senza rete.
