"""Test di architettura: fm_engine resta Python puro (ADR 0002).

Due verifiche complementari:
- statica: nessun modulo di fm_engine dichiara import di textual o sqlite3;
- dinamica: importare fm_engine in un interprete pulito non carica
  textual ne' sqlite3 in sys.modules.

sqlite3 e' il database di gioco (ADR 0004) e vive solo in fm_persistence:
il motore non lo importa mai, come non importa la TUI (textual).
"""

import ast
import subprocess
import sys
from pathlib import Path

import fm_engine

FORBIDDEN_MODULES = ("textual", "sqlite3")


def _root(module_name: str) -> str:
    return module_name.split(".")[0]


def _declared_imports(py_file: Path) -> set[str]:
    """Raccoglie le radici dei moduli importati in un file Python."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(_root(alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(_root(node.module))
    return roots


def test_static_no_forbidden_import():
    engine_dir = Path(fm_engine.__file__).parent
    violations: list[str] = []
    for py_file in engine_dir.rglob("*.py"):
        found = _declared_imports(py_file) & set(FORBIDDEN_MODULES)
        if found:
            violations.append(f"{py_file}: {sorted(found)}")
    assert not violations, f"fm_engine importa moduli vietati: {violations}"


def test_dynamic_clean_import():
    code = (
        "import sys\n"
        "import fm_engine\n"
        f"forbidden = [m for m in sys.modules if m.split('.')[0] in {FORBIDDEN_MODULES!r}]\n"
        "sys.exit(1 if forbidden else 0)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"importare fm_engine carica moduli vietati (stderr: {result.stderr})"
    )
