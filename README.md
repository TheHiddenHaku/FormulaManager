# Formula Manager

Gioco manageriale di motorsport single-player su terminale (TUI), ispirato alla Formula 1 con nomi di fantasia. Il giocatore gestisce una squadra in una Carriera pluristagionale.

Il progetto e' diviso in tre pacchetti (vedi `docs/adr/0002`):

- `fm_engine`: il motore di gioco, Python puro, senza dipendenze da TUI o database.
- `fm_persistence`: la persistenza a Checkpoint delle Carriere su Postgres (psycopg, vedi `docs/adr/0001`). Si configura con la sola variabile d'ambiente `FM_DATABASE_URL` (come costruirla: `supabase/README.md`).
- `fm_tui`: il guscio TUI costruito con Textual.

## Installazione

Richiede Python >= 3.12.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

In alternativa con uv:

```sh
uv venv .venv
uv pip install -e ".[dev]"
```

## Avvio

La via rapida e' lo script che prepara tutto da solo (venv al primo avvio, credenziali recuperate via SSH da matilde, lancio del gioco):

```sh
scripts/play.sh
```

In alternativa, a mano: serve `FM_DATABASE_URL` puntata al Postgres di matilde (vedi `supabase/README.md` per come ottenerla), poi:

```sh
fm
```

Si apre l'elenco delle Carriere: alla creazione di una nuova Carriera parte il wizard di Setup squadra e si atterra sulla griglia. `q` esce.

## Test e lint

```sh
pytest
ruff check .
```
