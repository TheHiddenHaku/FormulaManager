"""Modello del tempo sul giro (FOR-8).

Il tempo e' funzione di: base del circuito (dai dati statici, FOR-37),
Attributi vettura pesati dal profilo circuito, attributo di passo del
pilota (Passo gara in gara, Giro secco in qualifica) e varianza
stocastica modulata da Costanza e Aggressivita'. Tutti i parametri sono
costanti di modulo tarabili con l'harness di bilanciamento (T2.4.1).
"""

from random import Random

from fm_engine.circuits import Circuit
from fm_engine.state import Aggression, CarAttributes, RaceEntry

# Seconds of lap time per point of combined performance below the 0-100 ceiling.
PERFORMANCE_SECONDS_PER_POINT = 0.045
# Weight of the car in the combined performance score; the driver gets the rest.
CAR_PERFORMANCE_SHARE = 0.75
# Flat pace offset per aggression level, in seconds per lap.
AGGRESSION_PACE_OFFSET_SECONDS: dict[Aggression, float] = {
    Aggression.PUSH: -0.18,
    Aggression.NORMAL: 0.0,
    Aggression.CONSERVE: 0.18,
}
# Multiplier on the stochastic variance per aggression level.
AGGRESSION_VARIANCE_FACTOR: dict[Aggression, float] = {
    Aggression.PUSH: 1.3,
    Aggression.NORMAL: 1.0,
    Aggression.CONSERVE: 0.8,
}
# Variance: sigma of the gaussian noise, widened by low driver consistency.
BASE_VARIANCE_SIGMA_SECONDS = 0.18
SIGMA_SECONDS_PER_CONSISTENCY_POINT = 0.004


def base_lap_seconds(circuit: Circuit) -> float:
    """Il tempo base del circuito, dal riferimento realistico nei dati statici.

    La base e' additiva e uguale per tutte le vetture sullo stesso
    circuito: i distacchi e il bilanciamento non ne dipendono (FOR-37).
    """
    return circuit.base_lap_seconds


def weighted_car_score(car: CarAttributes, circuit: Circuit) -> float:
    """Gli Attributi vettura pesati dal profilo del circuito, scala 0-100."""
    weights = circuit.attribute_weights
    attributes = car.as_dict()
    total_weight = sum(weights.values())
    return sum(attributes[name] * weight for name, weight in weights.items()) / total_weight


def variance_sigma_seconds(consistency: int, aggression: Aggression) -> float:
    """La deviazione standard del rumore sul giro per il pilota indicato."""
    sigma = BASE_VARIANCE_SIGMA_SECONDS + (100 - consistency) * SIGMA_SECONDS_PER_CONSISTENCY_POINT
    return sigma * AGGRESSION_VARIANCE_FACTOR[aggression]


def lap_time_seconds(
    entry: RaceEntry,
    circuit: Circuit,
    aggression: Aggression,
    rng: Random,
    pace_attribute: str = "race_pace",
) -> float:
    """Un tempo sul giro estratto per la vettura indicata.

    pace_attribute seleziona l'attributo pilota che conta in sessione:
    race_pace in gara, one_lap_pace in qualifica (T2.1.2).
    """
    car_score = weighted_car_score(entry.car, circuit)
    driver_pace = getattr(entry.driver, pace_attribute)
    performance = CAR_PERFORMANCE_SHARE * car_score + (1 - CAR_PERFORMANCE_SHARE) * driver_pace
    deficit_seconds = (100 - performance) * PERFORMANCE_SECONDS_PER_POINT
    offset = AGGRESSION_PACE_OFFSET_SECONDS[aggression]
    noise = rng.gauss(0.0, variance_sigma_seconds(entry.driver.consistency, aggression))
    return base_lap_seconds(circuit) + deficit_seconds + offset + noise
