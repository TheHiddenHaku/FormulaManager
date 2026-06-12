"""Entry point CLI dell'harness: python -m fm_engine.balance (FOR-14)."""

import argparse

from fm_engine.balance.report import render_report
from fm_engine.balance.simulate import simulate


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m fm_engine.balance",
        description=(
            "Simula N stagioni complete (Qualifiche e gara dei 24 GP) e "
            "stampa il report statistico di bilanciamento del motore."
        ),
    )
    parser.add_argument("--seasons", type=int, default=5, help="stagioni da simulare (default 5)")
    parser.add_argument("--seed", type=int, default=2026, help="seed della simulazione")
    arguments = parser.parse_args()
    print(render_report(simulate(seasons=arguments.seasons, seed=arguments.seed)))


if __name__ == "__main__":
    main()
