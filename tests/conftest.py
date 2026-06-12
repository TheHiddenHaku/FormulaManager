"""Postgres effimero in Docker, condiviso dai test che toccano il database.

Fixture promossa a livello di suite (FOR-6): la usano i test di
persistenza (FOR-5) e i test Pilot della TUI. Avvia un container
postgres:17-alpine nudo (NON uno stack Supabase, mai matilde) su una
porta libera, attende la readiness, applica TUTTE le migrazioni di
supabase/migrations/ in ordine di timestamp (oggi una sola baseline,
FOR-35) e il seed dei dati statici via psycopg (psql non e' installato
sulla macchina), e ferma il container a fine sessione (docker run --rm:
lo stop rimuove anche il container). Se Docker non e' disponibile i test
che la richiedono vengono saltati con messaggio chiaro.
"""

import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path

import psycopg
import pytest

IMAGE = "postgres:17-alpine"
USERNAME = "fm_test"
PASSWORD = "fm_test"
DATABASE = "fm_test"
MAX_WAIT_SECONDS = 90.0

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MIGRATIONS_DIR = _PROJECT_ROOT / "supabase" / "migrations"
_SEED_FILE = _PROJECT_ROOT / "supabase" / "seed.sql"


def _free_port() -> int:
    """Chiede al sistema una porta TCP libera su localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_ready(url: str, container_name: str) -> None:
    """Attende che il Postgres del container accetti connessioni TCP."""
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
    log = subprocess.run(
        ["docker", "logs", container_name], capture_output=True, text=True, check=False
    )
    pytest.fail(
        f"Postgres effimero non pronto entro {MAX_WAIT_SECONDS}s: "
        f"{last_error}\nlog container:\n{log.stderr[-2000:]}"
    )


def _apply_sql(url: str, sql_file: Path) -> None:
    """Esegue un file SQL multi-statement via psycopg (niente psql)."""
    text = sql_file.read_text(encoding="utf-8")
    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute(text)


@pytest.fixture(scope="session")
def ephemeral_database_url():
    """URL del Postgres effimero con schema completo e seed gia' applicati."""
    if shutil.which("docker") is None:
        pytest.skip("docker non trovato nel PATH: test con database saltati")
    daemon = subprocess.run(["docker", "info"], capture_output=True, text=True, check=False)
    if daemon.returncode != 0:
        pytest.skip("il daemon Docker non risponde: test con database saltati")
    port = _free_port()
    container_name = f"fm-pg-test-{uuid.uuid4().hex[:12]}"
    start = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container_name,
            "-e",
            f"POSTGRES_USER={USERNAME}",
            "-e",
            f"POSTGRES_PASSWORD={PASSWORD}",
            "-e",
            f"POSTGRES_DB={DATABASE}",
            "-p",
            f"127.0.0.1:{port}:5432",
            IMAGE,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if start.returncode != 0:
        pytest.fail(f"docker run di {IMAGE} fallito: {start.stderr}")
    url = f"postgresql://{USERNAME}:{PASSWORD}@127.0.0.1:{port}/{DATABASE}"
    try:
        _wait_until_ready(url, container_name)
        # All migrations, in timestamp order (file names sort correctly).
        for sql_file in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            _apply_sql(url, sql_file)
        _apply_sql(url, _SEED_FILE)
        yield url
    finally:
        subprocess.run(
            ["docker", "stop", container_name], capture_output=True, text=True, check=False
        )
