"""Qualifiche formato 2026: Q1, Q2, Q3 (FOR-9).

Q1 con 22 vetture elimina le 6 piu' lente, Q2 con 16 ne elimina altre
6, Q3 con 10 assegna la pole. Il giro secco usa l'attributo pilota
one_lap_pace sopra lo stesso modello di tempo della gara (laptime);
ogni pilota fa 2 tentativi per segmento e conta il migliore. Gli
effetti dei Programmi delle libere (FOR-21) correggono il tempo dei
piloti del manager: deficit di setup meno bonus di Focus qualifica
(fm_engine.practice.qualifying_adjustment_seconds). Output: la
Classifica tempi di ogni segmento, gli eventi tipizzati e la griglia di
partenza nel formato consumato da start_race (T2.1.1).
"""

from dataclasses import dataclass
from random import Random

from fm_engine.circuits import Circuit
from fm_engine.events import (
    PolePosition,
    QualifyingElimination,
    QualifyingEvent,
    QualifyingSegment,
    QualifyingTimeSet,
)
from fm_engine.laptime import lap_time_seconds
from fm_engine.practice import PracticeEffects, qualifying_adjustment_seconds
from fm_engine.state import Aggression, RaceEntry, TimesheetRow

# The exact 2026 format: 22 cars, 6 eliminated in Q1 and 6 in Q2.
GRID_SIZE = 22
ADVANCING_FROM_Q1 = 16
ADVANCING_FROM_Q2 = 10
# Runs per driver per segment; the best one counts.
RUNS_PER_SEGMENT = 2
# Offset that separates the qualifying RNG stream from the race laps one.
_SEGMENT_SEED_OFFSET = 7_000_019


@dataclass(frozen=True)
class SegmentClassification:
    """La Classifica tempi di un segmento, ordinata dal piu' veloce."""

    segment: QualifyingSegment
    rows: tuple[TimesheetRow, ...]


@dataclass(frozen=True)
class QualifyingResult:
    """L'esito completo delle Qualifiche: classifiche, griglia e pole."""

    seed: int
    circuit: Circuit
    segments: tuple[SegmentClassification, ...]
    # Starting grid in pole-first order, ready for start_race.
    grid: tuple[RaceEntry, ...]
    pole_driver_id: int


def simulate_qualifying(
    entries: tuple[RaceEntry, ...],
    circuit: Circuit,
    seed: int,
    effects: PracticeEffects | None = None,
) -> tuple[QualifyingResult, tuple[QualifyingEvent, ...]]:
    """Simula la sessione di Qualifiche e produce la griglia di partenza.

    Deterministica a parita' di seed: l'RNG di ogni segmento e' derivato
    da (seed, segmento). effects, se presente, corregge il tempo dei
    soli piloti coperti dai Programmi delle libere (FOR-21): i rivali
    si assumono gia' a posto col loro lavoro del venerdi'.
    """
    if len(entries) != GRID_SIZE:
        raise ValueError(f"2026 qualifying needs exactly {GRID_SIZE} entries, got {len(entries)}")
    driver_ids = [entry.driver.id for entry in entries]
    if len(set(driver_ids)) != len(driver_ids):
        raise ValueError("duplicate driver ids in the qualifying entry list")
    adjustments: dict[int, float] = {}
    if effects is not None:
        adjustments = {
            driver_id: qualifying_adjustment_seconds(effects, driver_id)
            for driver_id in effects.drivers
        }

    events: list[QualifyingEvent] = []
    segments: list[SegmentClassification] = []
    # Grid built from the back: Q1 leftovers take 17-22, Q2 leftovers 11-16.
    grid_tail: list[RaceEntry] = []
    runners = list(entries)
    plan = (
        (QualifyingSegment.Q1, ADVANCING_FROM_Q1),
        (QualifyingSegment.Q2, ADVANCING_FROM_Q2),
        (QualifyingSegment.Q3, None),
    )
    for index, (segment, advancing) in enumerate(plan):
        rng = Random(seed * 1_000_003 + _SEGMENT_SEED_OFFSET * (index + 1))
        best_times: dict[int, float] = {}
        for entry in runners:
            best = min(
                lap_time_seconds(
                    entry,
                    circuit,
                    Aggression.NORMAL,
                    rng,
                    pace_attribute="one_lap_pace",
                )
                for _ in range(RUNS_PER_SEGMENT)
            )
            best += adjustments.get(entry.driver.id, 0.0)
            best_times[entry.driver.id] = best
            events.append(
                QualifyingTimeSet(segment=segment, driver_id=entry.driver.id, time_seconds=best)
            )
        ranked = sorted(runners, key=lambda entry: best_times[entry.driver.id])
        rows = tuple(
            TimesheetRow(
                position=position,
                driver_id=entry.driver.id,
                time_seconds=best_times[entry.driver.id],
            )
            for position, entry in enumerate(ranked, start=1)
        )
        segments.append(SegmentClassification(segment=segment, rows=rows))
        if advancing is None:
            runners = ranked
            continue
        eliminated = ranked[advancing:]
        # Later eliminations sit closer to the front of the final grid.
        grid_tail = eliminated + grid_tail
        for position, entry in enumerate(eliminated, start=advancing + 1):
            events.append(
                QualifyingElimination(segment=segment, driver_id=entry.driver.id, position=position)
            )
        runners = ranked[:advancing]

    grid = tuple(runners + grid_tail)
    pole_driver_id = grid[0].driver.id
    pole_time = segments[-1].rows[0].time_seconds
    events.append(PolePosition(driver_id=pole_driver_id, time_seconds=pole_time))
    result = QualifyingResult(
        seed=seed,
        circuit=circuit,
        segments=tuple(segments),
        grid=grid,
        pole_driver_id=pole_driver_id,
    )
    return result, tuple(events)
