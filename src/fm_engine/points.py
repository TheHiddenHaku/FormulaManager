"""Tabella punti 2026 (FOR-8).

Punti gara reali 2026: 25-18-15-12-10-8-6-4-2-1, nessun punto per il
giro veloce. Mirror Python della riga race_2026 di points_tables in
supabase/seed.sql.
"""

from collections.abc import Iterable

from fm_engine.events import ClassifiedResult

RACE_POINTS_2026: tuple[int, ...] = (25, 18, 15, 12, 10, 8, 6, 4, 2, 1)


def points_for_position(position: int) -> int:
    """I punti 2026 per la posizione finale data (1-based); 0 oltre il decimo."""
    if position < 1:
        raise ValueError(f"position must be 1-based, got {position}")
    if position <= len(RACE_POINTS_2026):
        return RACE_POINTS_2026[position - 1]
    return 0


def constructor_points(classification: Iterable[ClassifiedResult]) -> dict[int, int]:
    """I punti costruttori del GP: somma dei punti dei piloti per squadra.

    Include solo le squadre andate a punti; l'ordine di inserimento
    segue la classifica (la squadra del vincitore per prima).
    """
    totals: dict[int, int] = {}
    for result in classification:
        if result.points == 0:
            continue
        totals[result.team_id] = totals.get(result.team_id, 0) + result.points
    return totals
