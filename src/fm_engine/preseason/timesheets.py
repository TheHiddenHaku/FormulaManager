"""Classifica tempi di un giorno di Test pre-season (T5.1.2).

Il cronometro non mente mai: la Classifica tempi del giorno e' esatta per
tutte le 22 vetture (CONTEXT.md, Classifica tempi). Ma il contesto delle
vetture AI (carburante, Programma) resta ignoto: i loro tempi sono Tempi
sporchi, veri ma non direttamente confrontabili. I tempi dei piloti del
giocatore riflettono il Programma svolto.

Deterministico a parita' di (seed, giorno). Motore puro (ADR 0002).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from random import Random

from fm_engine.circuits import Circuit
from fm_engine.laptime import lap_time_seconds
from fm_engine.preseason.programmes import PreseasonProgramme
from fm_engine.state import Aggression, RaceEntry, TimesheetRow

# Best-lap attempts per car per test day.
RUNS_PER_DAY = 4

# Separate RNG stream from race laps, qualifying, practice and forecast.
_PRESEASON_SEED_OFFSET = 13_000_039

# Headline time offset per programme (seconds): who chases the lap is
# faster, who runs long stints or experiments leaves time on the table.
PROGRAMME_HEADLINE_OFFSET_SECONDS: dict[PreseasonProgramme, float] = {
    PreseasonProgramme.KNOWLEDGE: 0.30,
    PreseasonProgramme.DEVELOPMENT: 0.45,
    PreseasonProgramme.RELIABILITY: 0.55,
}

# Mixed, unknown running assumed for the cars the manager does not control:
# their times are dirty (unknown fuel and programme).
AI_DIRTY_OFFSET_SECONDS = 0.35


@dataclass(frozen=True)
class TestDayResult:
    """L'esito di un giorno di Test: la Classifica tempi esatta delle 22 vetture."""

    day: int
    circuit_code: str
    classification: tuple[TimesheetRow, ...]


def _day_rng(seed: int, day: int) -> Random:
    """L'RNG del giorno di Test, su uno stream separato dalle altre sessioni."""
    return Random(seed * 1_000_003 + _PRESEASON_SEED_OFFSET * day)


def simulate_test_day(
    entries: tuple[RaceEntry, ...],
    circuit: Circuit,
    day: int,
    player_programmes: Mapping[int, PreseasonProgramme],
    seed: int,
) -> TestDayResult:
    """Simula un giorno di Test: la Classifica tempi esatta, AI a Tempi sporchi."""
    rng = _day_rng(seed, day)
    best_times: dict[int, float] = {}
    for entry in entries:
        best = min(
            lap_time_seconds(entry, circuit, Aggression.NORMAL, rng, pace_attribute="one_lap_pace")
            for _ in range(RUNS_PER_DAY)
        )
        programme = player_programmes.get(entry.driver.id)
        if programme is not None:
            best += PROGRAMME_HEADLINE_OFFSET_SECONDS[programme]
        else:
            best += AI_DIRTY_OFFSET_SECONDS
        best_times[entry.driver.id] = best
    ranked = sorted(entries, key=lambda entry: best_times[entry.driver.id])
    classification = tuple(
        TimesheetRow(
            position=position,
            driver_id=entry.driver.id,
            time_seconds=best_times[entry.driver.id],
        )
        for position, entry in enumerate(ranked, start=1)
    )
    return TestDayResult(day=day, circuit_code=circuit.code, classification=classification)
