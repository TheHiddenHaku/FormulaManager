"""Svolgimento di un giorno di Test e report pre-stagione (T5.1.2).

run_test_day fa girare un giorno con i Programmi assegnati: produce la
Classifica tempi (Tempi sporchi per le AI) e, per ogni Programma di
Conoscenza, stringe le Stime del pilota e della vettura del giocatore.
preseason_report riassume la fase: i giorni di Conoscenza spesi e i
margini delle Stime ottenuti, segnalando esplicitamente il caso "0
giorni di Conoscenza" (Stime ancora larghe).

Motore puro (ADR 0002).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from fm_engine.circuits import circuit_by_code
from fm_engine.info.estimates import (
    KnowledgeState,
    car_subject,
    driver_subject,
    margin_for_level,
)
from fm_engine.preseason.programmes import (
    KNOWLEDGE_GAIN_PER_DAY,
    TEST_CIRCUIT_CODE,
    PreseasonProgramme,
)
from fm_engine.preseason.state import PreseasonDay, PreseasonState
from fm_engine.preseason.timesheets import TestDayResult, simulate_test_day
from fm_engine.state import RaceEntry
from fm_engine.world.models import PLAYER_TEAM_ID


@dataclass(frozen=True)
class TestDayOutcome:
    """L'esito di un giorno di Test: nuovo stato fase, conoscenza e Classifica."""

    preseason: PreseasonState
    knowledge: KnowledgeState
    result: TestDayResult


@dataclass(frozen=True)
class DriverPreseasonInfo:
    """Il margine di Stima raggiunto su un pilota del giocatore a fine fase."""

    driver_id: int
    margin: float


@dataclass(frozen=True)
class PreseasonReport:
    """Il report di fine Test pre-season: conoscenza spesa e Stime ottenute."""

    knowledge_days: int
    zero_knowledge: bool
    car_margin: float
    drivers: tuple[DriverPreseasonInfo, ...]


def run_test_day(
    preseason: PreseasonState,
    knowledge: KnowledgeState,
    entries: tuple[RaceEntry, ...],
    programmes: Mapping[int, PreseasonProgramme],
    seed: int,
) -> TestDayOutcome:
    """Svolge il prossimo giorno di Test: Classifica tempi e Stime aggiornate.

    I Programmi di Conoscenza alzano il livello del pilota e della vettura
    del giocatore (Stime piu' strette). Solleva ValueError a fase gia'
    conclusa.
    """
    if preseason.completed:
        raise ValueError("pre-season already completed: no test day to run")
    day = preseason.current_day
    circuit = circuit_by_code(TEST_CIRCUIT_CODE)
    result = simulate_test_day(entries, circuit, day, programmes, seed)

    updated_knowledge = knowledge
    for driver_id, programme in programmes.items():
        if programme is PreseasonProgramme.KNOWLEDGE:
            updated_knowledge = updated_knowledge.observed(
                (driver_subject(driver_id), car_subject(PLAYER_TEAM_ID)),
                amount=KNOWLEDGE_GAIN_PER_DAY,
            )

    new_state = replace(
        preseason,
        days_done=(*preseason.days_done, PreseasonDay(day=day, programmes=dict(programmes))),
    )
    return TestDayOutcome(preseason=new_state, knowledge=updated_knowledge, result=result)


def preseason_report(
    preseason: PreseasonState,
    knowledge: KnowledgeState,
    player_driver_ids: Sequence[int],
) -> PreseasonReport:
    """Riassume la fase: giorni di Conoscenza, margini ottenuti, caso 0 Conoscenza."""
    knowledge_days = preseason.knowledge_days
    drivers = tuple(
        DriverPreseasonInfo(
            driver_id=driver_id,
            margin=margin_for_level(knowledge.level_for(driver_subject(driver_id))),
        )
        for driver_id in player_driver_ids
    )
    return PreseasonReport(
        knowledge_days=knowledge_days,
        zero_knowledge=knowledge_days == 0,
        car_margin=margin_for_level(knowledge.level_for(car_subject(PLAYER_TEAM_ID))),
        drivers=drivers,
    )
