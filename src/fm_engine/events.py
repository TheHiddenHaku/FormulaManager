"""Eventi tipizzati del motore di gara (FOR-8, ADR 0003).

Il motore non produce mai testo libero: ogni accadimento e' una
dataclass immutabile con payload strutturato. La Telecronaca (progetto
Weekend interattivo) trasforma questi eventi in frasi a template; la
serializzazione passa da dataclasses.asdict, tutti i campi sono
primitivi o tuple di dataclass.
"""

from dataclasses import dataclass
from enum import Enum


class QualifyingSegment(Enum):
    """I 3 segmenti delle Qualifiche formato 2026 (FOR-9)."""

    Q1 = "q1"
    Q2 = "q2"
    Q3 = "q3"


@dataclass(frozen=True)
class QualifyingTimeSet:
    """Il miglior tempo segnato da un pilota nel segmento."""

    segment: QualifyingSegment
    driver_id: int
    time_seconds: float


@dataclass(frozen=True)
class QualifyingElimination:
    """Un pilota eliminato a fine segmento, con la posizione di griglia presa."""

    segment: QualifyingSegment
    driver_id: int
    # Final grid position locked in by the elimination, 1-based.
    position: int


@dataclass(frozen=True)
class PolePosition:
    """La pole position assegnata a fine Q3."""

    driver_id: int
    time_seconds: float


QualifyingEvent = QualifyingTimeSet | QualifyingElimination | PolePosition


@dataclass(frozen=True)
class RaceStarted:
    """La partenza della gara: emesso da start_race al giro 0."""

    lap: int
    circuit_code: str
    total_laps: int


@dataclass(frozen=True)
class Overtake:
    """Un sorpasso riuscito dentro al giro: l'attaccante guadagna la posizione."""

    lap: int
    driver_id: int
    overtaken_driver_id: int
    # Position gained by the attacker, 1-based (1 = race lead).
    position: int


@dataclass(frozen=True)
class TeamOrderSwap:
    """Scambio di posizioni tra compagni imposto da un Ordine di scuderia."""

    lap: int
    team_id: int
    promoted_driver_id: int
    demoted_driver_id: int
    # Position taken by the promoted driver, 1-based.
    position: int


@dataclass(frozen=True)
class FastestLap:
    """Nuovo giro veloce della gara. Nessun punto associato (regole 2026)."""

    lap: int
    driver_id: int
    time_seconds: float


@dataclass(frozen=True)
class ClassifiedResult:
    """Una riga della classifica finale, con i punti 2026 gia' attribuiti."""

    position: int
    driver_id: int
    team_id: int
    total_time_seconds: float
    gap_to_winner_seconds: float
    points: int


@dataclass(frozen=True)
class ChequeredFlag:
    """La bandiera a scacchi: chiude la gara e porta la classifica finale."""

    lap: int
    classification: tuple[ClassifiedResult, ...]


RaceEvent = RaceStarted | Overtake | TeamOrderSwap | FastestLap | ChequeredFlag
