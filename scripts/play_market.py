"""Harness manuale del Mercato piloti su un Postgres effimero (mai matilde).

Avvia un Postgres usa-e-getta in Docker (NON uno stack Supabase, NON
matilde), applica schema e seed come fanno i test, semina una Carriera di
fine stagione 2027 (squadra pronta, piloti in scadenza, ultimo GP gia'
concluso) e lancia la TUI puntata su quel database. Cosi' si puo' provare a
mano l'intero Mercato:

  1. apri la Carriera "Mercato 2027" dalla lista;
  2. dalla Griglia premi m: il Mercato si apre e hai due sedili liberi;
  3. scegli un pilota dal pool, scrivi un ingaggio annuale, premi o (o il
     bottone Controfferta): offerta alta -> firma, offerta bassa -> rifiuto
     con l'offerta rivale da battere;
  4. Esc per tornare alla Griglia, poi g: la stagione avanza al 2028
     applicando le firme e si apre la pre-season, che mostra gia' la tua
     nuova coppia di piloti (c'e' il pilota appena ingaggiato);
  5. q per uscire: il container effimero viene rimosso.

Uso: scripts/play_market.sh (prepara il venv) oppure
     .venv/bin/python scripts/play_market.py
"""

import os
import shutil
import socket
import subprocess
import time
import uuid
from dataclasses import replace
from datetime import date
from pathlib import Path

import psycopg

IMAGE = "postgres:17-alpine"
DB_USER = "fm_play"
DB_PASSWORD = "fm_play"
DB_NAME = "fm_play"
MAX_WAIT_SECONDS = 90.0

SEED = 42
CONCLUDED_YEAR = 2027
CAREER_NAME = "Mercato 2027"

_ROOT = Path(__file__).resolve().parents[1]
_MIGRATIONS_DIR = _ROOT / "supabase" / "migrations"
_SEED_FILE = _ROOT / "supabase" / "seed.sql"


def _free_port() -> int:
    """Chiede al sistema una porta TCP libera su localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_ready(url: str, container_name: str) -> None:
    """Attende che il Postgres del container accetti connessioni."""
    deadline = time.monotonic() + MAX_WAIT_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(url, connect_timeout=2) as connection:
                connection.execute("select 1")
            return
        except psycopg.OperationalError as error:
            last_error = error
            time.sleep(0.5)
    raise RuntimeError(f"Postgres effimero non pronto entro {MAX_WAIT_SECONDS}s: {last_error}")


def _apply_sql(url: str, sql_file: Path) -> None:
    """Esegue un file SQL multi-statement via psycopg."""
    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute(sql_file.read_text(encoding="utf-8"))


def _seed_career() -> None:
    """Semina la Carriera di fine 2027 pronta per il Mercato.

    Importata qui dentro perche' fm_persistence.connect legge
    FM_DATABASE_URL, gia' impostata sul container effimero a questo punto.
    """
    from fm_engine.career import Career
    from fm_engine.economy import DEFAULT_PLAYER_PRESTIGE, TeamLedger, credit_annual_sponsor
    from fm_engine.weekend import WeekendPhase, WeekendState
    from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
    from fm_persistence import connect, save_career

    world = replace(
        generate(SEED),
        player_slot=PlayerSlot(name="Scuderia Test", primary_color="#ff2800"),
    )
    free = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free[0].id, free[1].id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    world = apply_team_setup(world, choices)
    ledger = credit_annual_sponsor(TeamLedger(), DEFAULT_PLAYER_PRESTIGE, date(2026, 1, 1))
    # An already-finished last GP so pressing g advances the season at once.
    weekend = WeekendState(circuit_code="yas_marina", seed=SEED, phase=WeekendPhase.FINISHED)
    career = Career(name=CAREER_NAME, world=world, ledger=ledger, weekend=weekend)
    career = replace(career, season=replace(career.season, year=CONCLUDED_YEAR))
    with connect() as connection:
        save_career(connection, career)


def _instructions() -> str:
    return (
        "\n"
        "================  HARNESS MERCATO PILOTI (DB effimero, non matilde)  ===========\n"
        f'Carriera pronta: "{CAREER_NAME}" (fine stagione {CONCLUDED_YEAR}).\n\n'
        "  1. Apri la Carriera dalla lista.\n"
        "  2. Dalla Griglia premi  m  -> si apre il Mercato (hai 2 sedili liberi).\n"
        "  3. Scegli un pilota dal pool, scrivi un ingaggio (es. 16000000), premi  o .\n"
        "       - offerta alta -> firma (riga 'tuo', header 'Ingaggiati: 1');\n"
        "       - offerta bassa (es. 1000000) -> rifiuto con l'offerta rivale.\n"
        "  4. Esc -> Griglia, poi  g : la stagione avanza al 2028 applicando le firme\n"
        "       e si apre la pre-season che elenca gia' la tua NUOVA coppia di piloti.\n"
        "  5. Per uscire usa  q . Il container effimero viene poi rimosso.\n"
        "================================================================================\n"
    )


def main() -> None:
    if shutil.which("docker") is None:
        raise SystemExit("docker non trovato nel PATH: serve Docker per l'harness.")
    if subprocess.run(["docker", "info"], capture_output=True, check=False).returncode != 0:
        raise SystemExit("il daemon Docker non risponde: avvia Docker e riprova.")

    port = _free_port()
    container_name = f"fm-pg-play-{uuid.uuid4().hex[:12]}"
    started = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container_name,
            "-e",
            f"POSTGRES_USER={DB_USER}",
            "-e",
            f"POSTGRES_PASSWORD={DB_PASSWORD}",
            "-e",
            f"POSTGRES_DB={DB_NAME}",
            "-p",
            f"127.0.0.1:{port}:5432",
            IMAGE,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if started.returncode != 0:
        raise SystemExit(f"docker run di {IMAGE} fallito: {started.stderr}")

    url = f"postgresql://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{port}/{DB_NAME}"
    # Force the game onto the throwaway database, never the exported one.
    os.environ["FM_DATABASE_URL"] = url
    try:
        print(f"Avvio del Postgres effimero ({container_name}) su 127.0.0.1:{port}...")
        _wait_until_ready(url, container_name)
        for sql_file in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            _apply_sql(url, sql_file)
        _apply_sql(url, _SEED_FILE)
        _seed_career()
        print(_instructions())

        from fm_tui.app import FormulaManagerApp

        FormulaManagerApp().run()
    finally:
        subprocess.run(
            ["docker", "stop", container_name], capture_output=True, text=True, check=False
        )
        print("Container effimero rimosso. Nessun dato scritto su matilde.")


if __name__ == "__main__":
    main()
