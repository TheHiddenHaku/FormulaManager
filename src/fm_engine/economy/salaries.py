"""Stipendi piloti: addebito periodico solo sulla Cassa (FOR-22).

Gli stipendi sono esclusi dal Cap (regole F1 2026, CONTEXT.md): ogni
addebito e' un movimento con counts_against_cap False. La scadenza
periodica del MVP e' il Gran Premio: a ogni gara si addebita la rata
per gara (stipendio annuale diviso per i GP del Calendario) di ogni
Contratto della squadra del giocatore, in un unico movimento aggregato.
"""

from collections.abc import Iterable
from datetime import date

from fm_engine.circuits import CALENDAR_2026
from fm_engine.economy.ledger import TeamLedger, Transaction, TransactionKind
from fm_engine.world.models import Contract

RACES_PER_SEASON = len(CALENDAR_2026)


def salary_instalment_usd(annual_salary_usd: int, race_count: int = RACES_PER_SEASON) -> int:
    """La rata per gara di uno stipendio annuale (divisione intera)."""
    if race_count < 1:
        raise ValueError(f"race_count must be positive, got {race_count}")
    if annual_salary_usd < 0:
        raise ValueError(f"annual salary cannot be negative, got {annual_salary_usd}")
    return annual_salary_usd // race_count


def charge_salary_instalments(
    ledger: TeamLedger,
    contracts: Iterable[Contract],
    game_date: date,
    race_count: int = RACES_PER_SEASON,
) -> TeamLedger:
    """Addebita la rata stipendi della scadenza: un movimento aggregato.

    Pesa SOLO sulla Cassa (counts_against_cap False). Senza Contratti, o
    con rate tutte a zero, il registro resta intatto.
    """
    instalments = [salary_instalment_usd(c.salary_usd, race_count) for c in contracts]
    total = sum(instalments)
    if total == 0:
        return ledger
    return ledger.record(
        Transaction(
            kind=TransactionKind.SALARY,
            amount_usd=-total,
            game_date=game_date,
            description=f"Stipendi piloti ({len(instalments)} Contratti)",
            counts_against_cap=False,
        )
    )
