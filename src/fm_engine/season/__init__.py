"""Stagione e Carriera pluristagionale: Calendario, orologio, classifiche (T5.1.1).

Il pacchetto fa avanzare il tempo della Carriera sui giorni del
Calendario 2026 e tiene le classifiche piloti e costruttori coerenti
dopo ogni GP. SeasonState e' lo stato che viaggia coi Checkpoint
(fm_persistence.season). Motore puro (ADR 0002).
"""

from fm_engine.season.calendar import (
    CalendarEntry,
    race_date_in,
    season_calendar,
)
from fm_engine.season.clock import (
    INITIAL_SEASON_YEAR,
    SeasonState,
    advance_to_next_grand_prix,
    advance_to_next_season,
    days_until_next_grand_prix,
    next_grand_prix,
    record_race,
    season_completed,
    season_start_date,
)
from fm_engine.season.standings import (
    ConstructorStanding,
    DriverStanding,
    RoundResult,
    constructor_standings,
    driver_standings,
)

__all__ = [
    "INITIAL_SEASON_YEAR",
    "CalendarEntry",
    "ConstructorStanding",
    "DriverStanding",
    "RoundResult",
    "SeasonState",
    "advance_to_next_grand_prix",
    "advance_to_next_season",
    "constructor_standings",
    "days_until_next_grand_prix",
    "driver_standings",
    "next_grand_prix",
    "race_date_in",
    "record_race",
    "season_calendar",
    "season_completed",
    "season_start_date",
]
