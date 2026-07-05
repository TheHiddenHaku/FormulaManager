# Formula Manager

Gioco manageriale di motorsport single-player su terminale (TUI), ispirato alla Formula 1 con nomi di fantasia. Il giocatore gestisce una squadra in una Carriera pluristagionale.

Il progetto e' diviso in tre pacchetti (vedi `docs/adr/0002`):

- `fm_engine`: il motore di gioco, Python puro, senza dipendenze da TUI o database.
- `fm_persistence`: la persistenza a Checkpoint delle Carriere su un database SQLite locale (`sqlite3` della stdlib, vedi `docs/adr/0004`). Si configura con la sola variabile d'ambiente `FM_DB_PATH` (percorso del file; dettagli in `docs/database.md`).
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

La via rapida e' lo script che prepara tutto da solo (venv al primo avvio, database SQLite creato al primo avvio, lancio del gioco):

```sh
scripts/play.sh
```

In alternativa, a mano (il database SQLite si crea da solo al primo avvio; `FM_DB_PATH` per cambiarne il percorso, vedi `docs/database.md`):

```sh
fm
```

Si apre l'elenco delle Carriere: alla creazione di una nuova Carriera parte il wizard di Setup squadra e si atterra sulla griglia. `q` esce.

## Harness di bilanciamento

CLI headless per sviluppatori: simula N stagioni complete (Qualifiche e gara dei 24 GP del Calendario, con gomme, sfiga, neutralizzazioni e meteo) e stampa un report statistico del comportamento del motore. Nessun database coinvolto, deterministico a parita' di seed.

```sh
python -m fm_engine.balance --seasons 5 --seed 2026
```

Il report copre: media Abbandoni per gara, frequenza Safety car / VSC / pioggia per circuito, spread punti tra prima e ultima squadra, correlazione attributi-risultati, distribuzione delle strategie (numero soste, Mescole usate). Le asserzioni sui range attesi vivono in `tests/engine/test_balance_sanity.py` e girano con la suite: se il bilanciamento degenera, la suite diventa rossa.

## Test e lint

```sh
pytest
ruff check .
```
