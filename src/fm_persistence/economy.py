"""Persistenza del registro economico e della solvibilita' (FOR-15, FOR-24).

Il TeamLedger della squadra del giocatore viaggia su due tabelle dello
schema baseline: seasons (anno e Cap stagionale) e financial_transactions
(un movimento per riga, team_id = squadra del giocatore). Gli id riusano
row_uuid di mapping: la riga di stagione codifica l'anno, ogni movimento
la sua posizione (1-based) nella tupla entries, cosi' il load ricostruisce
l'ordine originale senza colonne aggiuntive.

Lo stato di solvibilita' (SolvencyState, FOR-24) viaggia come documento
JSON nella colonna careers.solvency_state, come lo stato weekend.

I Checkpoint precedenti non hanno righe in seasons ne' solvency_state:
il load torna ai valori canonici (registro vuoto, squadra sana).
"""

import uuid
from datetime import date
from typing import Any

from fm_engine.economy import SolvencyState, TeamLedger, Transaction, TransactionKind
from fm_persistence.mapping import PLAYER_SLOT_ID, id_from_uuid, row_uuid

# row_uuid kinds for the economy tables.
SEASON_UUID_KIND = "season"
TRANSACTION_UUID_KIND = "financial_transaction"


def season_params(career_id: uuid.UUID, ledger: TeamLedger) -> tuple[Any, ...]:
    """Parametri per l'INSERT in seasons della stagione corrente."""
    return (
        row_uuid(career_id, SEASON_UUID_KIND, ledger.season_year),
        career_id,
        ledger.season_year,
        ledger.cap_usd,
    )


def transaction_params(
    career_id: uuid.UUID, position: int, transaction: Transaction, ledger: TeamLedger
) -> tuple[Any, ...]:
    """Parametri per l'INSERT in financial_transactions.

    La posizione (1-based) nella tupla ledger.entries e' codificata
    nell'uuid della riga per ricostruire l'ordine al load. La descrizione
    vuota diventa NULL (la colonna e' nullable).
    """
    return (
        row_uuid(career_id, TRANSACTION_UUID_KIND, position),
        career_id,
        row_uuid(career_id, "team", PLAYER_SLOT_ID),
        row_uuid(career_id, SEASON_UUID_KIND, ledger.season_year),
        transaction.kind.value,
        transaction.amount_usd,
        transaction.counts_against_cap,
        transaction.description or None,
        transaction.game_date,
    )


def transaction_from_row(row: dict[str, Any]) -> Transaction:
    """Ricostruisce un movimento da una riga di financial_transactions.

    Le colonne text/integer di SQLite riconvertono al tipo del modello:
    game_date da ISO 8601 a date, counts_against_cap da 0/1 a bool.
    """
    return Transaction(
        kind=TransactionKind(row["kind"]),
        amount_usd=int(row["amount_usd"]),
        game_date=date.fromisoformat(row["game_date"]),
        description=row["description"] or "",
        counts_against_cap=bool(row["counts_against_cap"]),
    )


def ledger_from_rows(
    season_row: dict[str, Any] | None, transaction_rows: list[dict[str, Any]]
) -> TeamLedger:
    """Riassembla il registro dalla riga di stagione e dai movimenti.

    Nessuna riga di stagione = Checkpoint precedente a FOR-15: registro
    vuoto canonico. I movimenti tornano nell'ordine di registrazione
    (posizione decodificata dall'uuid di riga).
    """
    if season_row is None:
        return TeamLedger()
    ordered = sorted(transaction_rows, key=lambda row: id_from_uuid(row["id"]))
    return TeamLedger(
        season_year=int(season_row["year"]),
        cap_usd=int(season_row["cap_usd"]),
        entries=tuple(transaction_from_row(row) for row in ordered),
    )


def solvency_payload(solvency: SolvencyState) -> dict[str, Any] | None:
    """Il documento JSON dello stato di solvibilita', None per la squadra sana.

    Lo stato di default non si scrive: la colonna resta NULL e il load
    torna al canonico SolvencyState(), identico per costruzione.
    """
    if solvency == SolvencyState():
        return None
    return {
        "emergency_used": solvency.emergency_used,
        "emergency_pending": solvency.emergency_pending,
        "insolvent_races": solvency.insolvent_races,
        "loan_instalments_left": solvency.loan_instalments_left,
        "loan_principal_instalment_usd": solvency.loan_principal_instalment_usd,
        "loan_interest_instalment_usd": solvency.loan_interest_instalment_usd,
        "prestige_malus": solvency.prestige_malus,
    }


def solvency_from_payload(payload: dict[str, Any] | None) -> SolvencyState:
    """Ricostruisce lo stato di solvibilita' dal documento JSON, o il default."""
    if payload is None:
        return SolvencyState()
    return SolvencyState(
        emergency_used=bool(payload["emergency_used"]),
        emergency_pending=bool(payload["emergency_pending"]),
        insolvent_races=int(payload["insolvent_races"]),
        loan_instalments_left=int(payload["loan_instalments_left"]),
        loan_principal_instalment_usd=int(payload["loan_principal_instalment_usd"]),
        loan_interest_instalment_usd=int(payload["loan_interest_instalment_usd"]),
        prestige_malus=int(payload["prestige_malus"]),
    )
