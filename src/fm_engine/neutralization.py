"""Neutralizzazioni di gara: Safety car e VSC (FOR-12).

Il trigger dipende dalla gravita' dell'Incidente (T2.2.2) e dalla
probabilita' Safety car del circuito (dai dati statici). La Safety car
compatta il gruppo dietro la vettura di sicurezza e sconta il pit
stop; il VSC congela i distacchi e sconta meno. La durata e' variabile
ma deterministica a parita' di seed; alla ripartenza il rischio di
Errori e contatti in duello resta alto per una finestra di giri.

Modulo foglia: importa solo circuits ed events, cosi' lo stato di gara
puo' esporre il regime corrente senza cicli di import. Costanti
tarabili con l'harness di bilanciamento (T2.4.1).
"""

from enum import Enum
from random import Random

from fm_engine.circuits import Circuit
from fm_engine.events import AccidentSeverity


class RaceRegime(Enum):
    """Il regime corrente della gara."""

    GREEN = "green"
    SAFETY_CAR = "safety_car"
    VSC = "vsc"


# Trigger: a major accident rolls the full circuit probability for a
# Safety car, with a VSC fallback; a minor accident can only bring a VSC.
VSC_FALLBACK_PROBABILITY = 0.5
MINOR_ACCIDENT_VSC_FACTOR = 0.5
# Duration in laps, drawn uniformly (deterministic per seed).
SAFETY_CAR_DURATION_LAPS = (2, 4)
VSC_DURATION_LAPS = (1, 2)
# Lap pace under neutralization, as a factor of the circuit base lap.
SAFETY_CAR_PACE_FACTOR = 1.40
VSC_PACE_FACTOR = 1.25
# Pit stop discounts: pitting under SC costs less, under VSC a bit less.
SAFETY_CAR_PIT_DISCOUNT = 0.5
VSC_PIT_DISCOUNT = 0.75
# Queue gap behind the safety car after the field compacts.
SAFETY_CAR_QUEUE_GAP_SECONDS = 0.5
# Restart window after a Safety car: laps with raised error/contact risk.
RESTART_RISK_LAPS = 2
RESTART_RISK_FACTOR = 1.5


def draw_neutralization(
    circuit: Circuit,
    severities: tuple[AccidentSeverity, ...],
    rng: Random,
) -> tuple[RaceRegime, int] | None:
    """Estrae l'eventuale neutralizzazione dagli Incidenti del giro.

    Ritorna (regime, durata in giri) oppure None se la gara resta
    verde. Un Incidente major gioca la probabilita' piena del circuito
    per la Safety car, con ripiego VSC; un minor puo' portare solo VSC.
    """
    if not severities:
        return None
    if AccidentSeverity.MAJOR in severities:
        if rng.random() < circuit.safety_car_probability:
            return RaceRegime.SAFETY_CAR, rng.randint(*SAFETY_CAR_DURATION_LAPS)
        if rng.random() < VSC_FALLBACK_PROBABILITY:
            return RaceRegime.VSC, rng.randint(*VSC_DURATION_LAPS)
        return None
    if rng.random() < circuit.safety_car_probability * MINOR_ACCIDENT_VSC_FACTOR:
        return RaceRegime.VSC, rng.randint(*VSC_DURATION_LAPS)
    return None


def pit_discount(regime: RaceRegime) -> float:
    """Il fattore di sconto del pit stop nel regime dato."""
    if regime is RaceRegime.SAFETY_CAR:
        return SAFETY_CAR_PIT_DISCOUNT
    if regime is RaceRegime.VSC:
        return VSC_PIT_DISCOUNT
    return 1.0


def neutralized_pace_factor(regime: RaceRegime) -> float:
    """Il fattore sul tempo base del giro nel regime dato."""
    if regime is RaceRegime.SAFETY_CAR:
        return SAFETY_CAR_PACE_FACTOR
    if regime is RaceRegime.VSC:
        return VSC_PACE_FACTOR
    raise ValueError("green laps do not have a neutralized pace")
