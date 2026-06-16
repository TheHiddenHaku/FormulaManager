"""Archivio permanente della Carriera: Almanacco, classifiche, Albo d'oro (T5.3.2).

Il pacchetto tiene la memoria storica della Carriera: per ogni GP la
griglia di partenza, l'ordine d'arrivo e gli eventi principali; per ogni
stagione le classifiche finali e i Titoli. L'archivio (CareerArchive)
accumula e non perde mai le stagioni passate, viaggia coi Checkpoint
(fm_persistence.history) e alimenta le statistiche cumulative e l'Albo
d'oro. Calcolo puro (ADR 0002): nessun import di TUI o database.
"""

from fm_engine.history.archiving import (
    build_archived_grand_prix,
    final_standings,
)
from fm_engine.history.models import (
    PODIUM_POSITIONS,
    ArchivedGrandPrix,
    CareerArchive,
    PrincipalEvent,
    PrincipalEventKind,
    SeasonArchive,
    archive_grand_prix,
    finalize_season,
)
from fm_engine.history.stats import (
    DriverStats,
    HallOfFameEntry,
    TeamStats,
    driver_stats,
    hall_of_fame,
    team_stats,
)

__all__ = [
    "PODIUM_POSITIONS",
    "ArchivedGrandPrix",
    "CareerArchive",
    "DriverStats",
    "HallOfFameEntry",
    "PrincipalEvent",
    "PrincipalEventKind",
    "SeasonArchive",
    "TeamStats",
    "archive_grand_prix",
    "build_archived_grand_prix",
    "driver_stats",
    "final_standings",
    "finalize_season",
    "hall_of_fame",
    "team_stats",
]
