"""Fase Test pre-season: Programmi, Classifica tempi e Stime (T5.1.2).

I giorni di Test prima del primo GP: per ogni giorno e pilota si sceglie
un Programma (Sviluppo, Conoscenza, Affidabilita'). I Programmi di
Conoscenza stringono le Stime sugli attributi propri; la Classifica tempi
e' esatta per tutti ma i tempi delle AI sono sporchi. Motore puro
(ADR 0002).
"""

from fm_engine.preseason.programmes import (
    KNOWLEDGE_GAIN_PER_DAY,
    PRESEASON_DAYS,
    TEST_CIRCUIT_CODE,
    PreseasonProgramme,
)
from fm_engine.preseason.run import (
    DriverPreseasonInfo,
    PreseasonReport,
    TestDayOutcome,
    preseason_report,
    run_test_day,
)
from fm_engine.preseason.state import PreseasonDay, PreseasonState
from fm_engine.preseason.timesheets import TestDayResult, simulate_test_day

__all__ = [
    "KNOWLEDGE_GAIN_PER_DAY",
    "PRESEASON_DAYS",
    "TEST_CIRCUIT_CODE",
    "DriverPreseasonInfo",
    "PreseasonDay",
    "PreseasonProgramme",
    "PreseasonReport",
    "PreseasonState",
    "TestDayOutcome",
    "TestDayResult",
    "preseason_report",
    "run_test_day",
    "simulate_test_day",
]
