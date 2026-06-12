"""Macchina a stati del Formato weekend Standard (FOR-21).

Il weekend di un Gran Premio e' una sequenza rigida di fasi:
FP1 -> FP2 -> FP3 -> Qualifiche (Q1/Q2/Q3) -> Gara -> concluso.
WeekendState e' immutabile: ogni sessione conclusa produce un nuovo
stato tramite le funzioni advance_after_*, che validano la fase
corrente e l'esito ricevuto (nessun salto, nessuno stato
irraggiungibile). Gli effetti dei Programmi delle libere
(PracticeEffects) viaggiano nello stato e vengono cablati su Qualifiche
e Gara dai chiamanti (simulate_qualifying e start_race accettano gli
stessi effetti).

Il Formato weekend si legge dal flag del circuito
(Circuit.weekend_format_2026): nel MVP e' giocabile solo il formato
Standard; il formato Sprint e' previsto dal modello ma post-MVP e i
formati sconosciuti vengono rifiutati. Motore puro (ADR 0002): la
persistenza dello stato ai Checkpoint vive in fm_persistence.
"""

from dataclasses import dataclass, field, replace
from enum import Enum

from fm_engine.circuits import Circuit
from fm_engine.events import ClassifiedResult
from fm_engine.practice import PracticeEffects, PracticeSession, PracticeSessionResult
from fm_engine.qualifying import QualifyingResult


class WeekendFormat(Enum):
    """Il Formato weekend di un Gran Premio (CONTEXT.md)."""

    STANDARD = "standard"
    SPRINT = "sprint"


class WeekendPhase(Enum):
    """Una fase del weekend Standard: la prossima sessione da giocare."""

    FP1 = "fp1"
    FP2 = "fp2"
    FP3 = "fp3"
    QUALIFYING = "qualifying"
    RACE = "race"
    FINISHED = "finished"


# The phases of the standard weekend, in playing order.
STANDARD_PHASES: tuple[WeekendPhase, ...] = (
    WeekendPhase.FP1,
    WeekendPhase.FP2,
    WeekendPhase.FP3,
    WeekendPhase.QUALIFYING,
    WeekendPhase.RACE,
    WeekendPhase.FINISHED,
)

# Practice session played in each free practice phase.
PHASE_PRACTICE_SESSIONS: dict[WeekendPhase, PracticeSession] = {
    WeekendPhase.FP1: PracticeSession.FP1,
    WeekendPhase.FP2: PracticeSession.FP2,
    WeekendPhase.FP3: PracticeSession.FP3,
}


@dataclass(frozen=True)
class WeekendState:
    """Lo stato del weekend di gara in corso, tra una sessione e l'altra.

    phase e' la prossima sessione da giocare (FINISHED = weekend
    concluso). effects cumula i Programmi delle libere; grid_driver_ids
    e' la griglia di partenza in ordine di pole dopo le Qualifiche;
    race_classification e' l'ordine d'arrivo con i punti dopo la Gara.
    """

    circuit_code: str
    seed: int
    phase: WeekendPhase = WeekendPhase.FP1
    weekend_format: WeekendFormat = WeekendFormat.STANDARD
    effects: PracticeEffects = field(default_factory=PracticeEffects)
    grid_driver_ids: tuple[int, ...] | None = None
    race_classification: tuple[ClassifiedResult, ...] | None = None

    @property
    def finished(self) -> bool:
        """True a weekend concluso: la classifica di gara e' definitiva."""
        return self.phase is WeekendPhase.FINISHED

    @property
    def next_practice_session(self) -> PracticeSession | None:
        """La sessione di libere della fase corrente, se e' una fase di libere."""
        return PHASE_PRACTICE_SESSIONS.get(self.phase)


def _next_phase(phase: WeekendPhase) -> WeekendPhase:
    """La fase successiva nell'ordine del weekend Standard."""
    return STANDARD_PHASES[STANDARD_PHASES.index(phase) + 1]


def start_weekend(circuit: Circuit, seed: int) -> WeekendState:
    """Apre il weekend del GP leggendo il Formato weekend dal flag del circuito.

    Solleva ValueError per i formati sconosciuti e per quelli previsti
    ma non ancora giocabili (Sprint, post-MVP).
    """
    try:
        weekend_format = WeekendFormat(circuit.weekend_format_2026)
    except ValueError:
        raise ValueError(
            f"unknown weekend format {circuit.weekend_format_2026!r} at {circuit.code}"
        ) from None
    if weekend_format is not WeekendFormat.STANDARD:
        raise ValueError(
            f"weekend format {weekend_format.value!r} is not playable in the MVP: "
            "only the standard format is"
        )
    return WeekendState(circuit_code=circuit.code, seed=seed, weekend_format=weekend_format)


def advance_after_practice(state: WeekendState, result: PracticeSessionResult) -> WeekendState:
    """Registra una sessione di libere conclusa e passa alla fase successiva.

    L'esito deve appartenere alla sessione della fase corrente: niente
    salti (FP2 prima di FP1) ne' ripetizioni.
    """
    expected = state.next_practice_session
    if expected is None:
        raise ValueError(f"phase {state.phase.value} does not accept a practice result")
    if result.session is not expected:
        raise ValueError(
            f"expected a {expected.value} result in phase {state.phase.value}, "
            f"got {result.session.value}"
        )
    return replace(state, phase=_next_phase(state.phase), effects=result.effects)


def advance_after_qualifying(state: WeekendState, result: QualifyingResult) -> WeekendState:
    """Registra le Qualifiche concluse: la griglia di partenza entra nello stato."""
    if state.phase is not WeekendPhase.QUALIFYING:
        raise ValueError(f"phase {state.phase.value} does not accept a qualifying result")
    grid_driver_ids = tuple(entry.driver.id for entry in result.grid)
    return replace(state, phase=WeekendPhase.RACE, grid_driver_ids=grid_driver_ids)


def advance_after_race(
    state: WeekendState, classification: tuple[ClassifiedResult, ...]
) -> WeekendState:
    """Registra la Gara conclusa: l'ordine d'arrivo coi punti chiude il weekend."""
    if state.phase is not WeekendPhase.RACE:
        raise ValueError(f"phase {state.phase.value} does not accept a race classification")
    if not classification:
        raise ValueError("a race classification cannot be empty")
    return replace(state, phase=WeekendPhase.FINISHED, race_classification=tuple(classification))
