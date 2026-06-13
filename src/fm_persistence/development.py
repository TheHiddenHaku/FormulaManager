"""Persistenza dei Progetti di sviluppo ai Checkpoint (FOR-25).

I Progetti della squadra del giocatore viaggiano sulla tabella baseline
development_projects: una riga per Progetto, team_id = squadra del
giocatore, season_id = stagione corrente del registro. Gli id riusano
row_uuid di mapping con la posizione (1-based) nella tupla
Career.projects, cosi' il load ricostruisce l'ordine originale.
"""

import uuid
from typing import Any

from fm_engine.development import DevelopmentProject, ProjectStatus
from fm_engine.economy import TeamLedger
from fm_persistence.economy import SEASON_UUID_KIND
from fm_persistence.mapping import PLAYER_SLOT_ID, id_from_uuid, row_uuid

PROJECT_UUID_KIND = "development_project"


def project_params(
    career_id: uuid.UUID,
    position: int,
    project: DevelopmentProject,
    ledger: TeamLedger,
) -> tuple[Any, ...]:
    """Parametri per l'INSERT in development_projects."""
    return (
        row_uuid(career_id, PROJECT_UUID_KIND, position),
        career_id,
        row_uuid(career_id, "team", PLAYER_SLOT_ID),
        row_uuid(career_id, SEASON_UUID_KIND, ledger.season_year),
        project.attribute,
        project.cost_usd,
        project.start_date,
        project.duration_days,
        project.status.value,
        project.outcome,
    )


def project_from_row(row: dict[str, Any]) -> DevelopmentProject:
    """Ricostruisce un Progetto da una riga di development_projects."""
    outcome = row["outcome"]
    return DevelopmentProject(
        attribute=row["attribute"],
        cost_usd=int(row["cost_usd"]),
        start_date=row["start_date"],
        duration_days=int(row["duration_days"]),
        status=ProjectStatus(row["status"]),
        outcome=None if outcome is None else int(outcome),
    )


def projects_from_rows(rows: list[dict[str, Any]]) -> tuple[DevelopmentProject, ...]:
    """Riassembla i Progetti nell'ordine di avvio originale."""
    ordered = sorted(rows, key=lambda row: id_from_uuid(row["id"]))
    return tuple(project_from_row(row) for row in ordered)
