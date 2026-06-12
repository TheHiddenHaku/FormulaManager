"""Round-trip del registro economico ai Checkpoint (FOR-15).

Il TeamLedger viaggia su seasons (anno e Cap) e financial_transactions
(un movimento per riga della squadra del giocatore): save seguito da
load deve ricostruirlo identico, nell'ordine di registrazione. I
Checkpoint precedenti a FOR-15 (nessuna riga in seasons) tornano al
registro vuoto canonico.
"""

from dataclasses import replace
from datetime import date

import pytest

from fm_engine.career import Career
from fm_engine.economy import TeamLedger, Transaction, TransactionKind
from fm_engine.world import PlayerSlot, generate
from fm_persistence import load_career, save_career

SEED = 7
GAME_DATE = date(2026, 3, 8)


@pytest.fixture
def world():
    return replace(generate(SEED), player_slot=PlayerSlot(name="Scuderia Economia"))


def _sample_ledger() -> TeamLedger:
    ledger = TeamLedger().record(
        Transaction(
            kind=TransactionKind.OTHER,
            amount_usd=30_000_000,
            game_date=GAME_DATE,
            description="Dotazione iniziale",
        )
    )
    ledger = ledger.spend(TransactionKind.OTHER, 4_000_000, GAME_DATE, description="Spesa di prova")
    return ledger.record(
        Transaction(
            kind=TransactionKind.SALARY,
            amount_usd=-2_000_000,
            game_date=date(2026, 3, 15),
            description="Stipendi piloti",
            counts_against_cap=False,
        )
    )


def test_ledger_round_trip_identical(conn, world):
    ledger = _sample_ledger()
    saved = save_career(conn, Career(name="Con registro", world=world, ledger=ledger))
    reloaded = load_career(conn, saved.id)
    assert reloaded.ledger == ledger
    assert reloaded.ledger.cash_usd == ledger.cash_usd
    assert reloaded.ledger.cap_remaining_usd == ledger.cap_remaining_usd


def test_empty_ledger_round_trip(conn, world):
    saved = save_career(conn, Career(name="Registro vuoto", world=world))
    reloaded = load_career(conn, saved.id)
    assert reloaded.ledger == TeamLedger()


def test_next_checkpoint_overwrites_transactions(conn, world):
    """Delete e reinsert: l'ultimo stato vince, senza righe duplicate."""
    first = save_career(conn, Career(name="Primo", world=world, ledger=_sample_ledger()))
    grown = first.ledger.spend(
        TransactionKind.OTHER, 1_000_000, date(2026, 4, 1), description="Altra spesa"
    )
    second = save_career(conn, replace(first, ledger=grown))

    reloaded = load_career(conn, second.id)
    assert reloaded.ledger == grown

    transactions = conn.execute(
        "select count(*) from financial_transactions where career_id = %s",
        (second.id,),
    ).fetchone()[0]
    assert transactions == len(grown.entries)
    seasons = conn.execute(
        "select count(*) from seasons where career_id = %s", (second.id,)
    ).fetchone()[0]
    assert seasons == 1


def test_checkpoint_before_for15_loads_the_empty_ledger(conn, world):
    """Un salvataggio senza righe economy (pre FOR-15) carica il registro vuoto."""
    saved = save_career(conn, Career(name="Vecchio Checkpoint", world=world))
    with conn.transaction():
        conn.execute("delete from financial_transactions where career_id = %s", (saved.id,))
        conn.execute("delete from seasons where career_id = %s", (saved.id,))
    reloaded = load_career(conn, saved.id)
    assert reloaded.ledger == TeamLedger()
