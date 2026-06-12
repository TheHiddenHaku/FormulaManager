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


class DnfCause(Enum):
    """La causa di un Abbandono (FOR-11)."""

    FAILURE = "failure"
    DRIVER_ERROR = "driver_error"
    ACCIDENT = "accident"


class AccidentSeverity(Enum):
    """La gravita' di un Incidente: alimenta il trigger SC/VSC (T2.3.1)."""

    MINOR = "minor"
    MAJOR = "major"


@dataclass(frozen=True)
class CarFailure:
    """Un Guasto meccanico, con il componente ceduto come causa visibile."""

    lap: int
    driver_id: int
    component: str


@dataclass(frozen=True)
class DriverError:
    """Un Errore del pilota sopravvivibile: costa tempo, non la gara."""

    lap: int
    driver_id: int
    cause: str
    time_lost_seconds: float
    in_duel: bool


@dataclass(frozen=True)
class Accident:
    """Un Incidente: contatto in duello o alla partenza."""

    lap: int
    driver_ids: tuple[int, ...]
    severity: AccidentSeverity


@dataclass(frozen=True)
class CarDamage:
    """Un evento danno con l'entita' in USD, per Danni su Cassa e Cap."""

    lap: int
    driver_id: int
    amount_usd: int


@dataclass(frozen=True)
class Dnf:
    """L'Abbandono: la vettura esce dalla sessione e dalla classifica."""

    lap: int
    driver_id: int
    cause: DnfCause
    # Visible detail: failed component, error cause or "contact".
    detail: str


@dataclass(frozen=True)
class PitEntry:
    """La vettura entra in corsia box (FOR-10)."""

    lap: int
    driver_id: int


@dataclass(frozen=True)
class TyreChange:
    """Il cambio gomme al box: dalla Mescola vecchia alla nuova."""

    lap: int
    driver_id: int
    # Compound values of fm_engine.tyres.Compound, kept as str for
    # serialization (events.py stays a leaf module, no engine imports).
    old_compound: str
    new_compound: str


@dataclass(frozen=True)
class PitExit:
    """Il rientro in pista dopo la sosta, col tempo perso totale."""

    lap: int
    driver_id: int
    time_lost_seconds: float


@dataclass(frozen=True)
class BiCompoundPenalty:
    """Penalita' per obbligo bi-mescola violato in gara asciutta.

    Scelta documentata (FOR-10): la regola non blocca la gara, la
    sanziona. Chi chiude una gara asciutta con una sola Mescola da
    asciutto prende una penalita' di tempo in classifica.
    """

    lap: int
    driver_id: int
    penalty_seconds: float


@dataclass(frozen=True)
class ClassifiedResult:
    """Una riga della classifica finale, con i punti 2026 gia' attribuiti.

    total_time_seconds include le penalita'; penalty_seconds ne
    documenta la quota.
    """

    position: int
    driver_id: int
    team_id: int
    total_time_seconds: float
    gap_to_winner_seconds: float
    points: int
    penalty_seconds: float = 0.0


@dataclass(frozen=True)
class ChequeredFlag:
    """La bandiera a scacchi: chiude la gara e porta la classifica finale."""

    lap: int
    classification: tuple[ClassifiedResult, ...]


RaceEvent = (
    RaceStarted
    | Overtake
    | TeamOrderSwap
    | FastestLap
    | CarFailure
    | DriverError
    | Accident
    | CarDamage
    | Dnf
    | PitEntry
    | TyreChange
    | PitExit
    | BiCompoundPenalty
    | ChequeredFlag
)
