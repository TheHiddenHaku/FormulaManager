"""Meteo di sessione e Crossover gomme (FOR-13).

La previsione di sessione nasce dal profilo meteo del circuito (dai
dati statici) ed e' deterministica a parita' di seed. In sessione la
pioggia arriva, varia di intensita' e cessa con un processo per Tick;
la pista si bagna sotto la pioggia e si asciuga progressivamente
quando smette.

Ogni tipo gomma ha una prestazione funzione della bagnatura pista: le
slick crollano sul bagnato, l'Intermedia domina la fascia centrale, la
Bagnato la pioggia piena. Il punto di Crossover emerge dalle curve, e
il passaggio di categoria ottima genera un Evento chiave.

Costanti tarabili con l'harness di bilanciamento (T2.4.1).
"""

from dataclasses import dataclass
from random import Random

from fm_engine.circuits import Circuit
from fm_engine.events import Crossover, RainStarted, RainStopped
from fm_engine.tyres import Compound

# Stream separation for the forecast RNG (race laps use seed*1_000_003+lap).
_FORECAST_SEED_OFFSET = 17_000_023

# Session forecast jitter around the circuit rain probability.
FORECAST_JITTER = 0.10
# Per-lap probability that rain starts, normalized over race length so the
# share of rainy races tracks the circuit rain probability.
RAIN_START_FACTOR = 1.2
# Rain evolution per lap.
RAIN_INTENSITY_RANGE_AT_START = (0.3, 1.0)
RAIN_INTENSITY_DRIFT = (-0.25, 0.20)
RAIN_STOP_PROBABILITY = 0.10
RAIN_MINIMUM_INTENSITY = 0.05
# Track wetness evolution per lap.
WETNESS_GAIN_BASE = 0.12
WETNESS_GAIN_PER_INTENSITY = 0.18
DRYING_RATE = 0.08
# Wetness above this level counts as a wet race (bi-compound rule off).
WET_RACE_THRESHOLD = 0.15
# Driver wet_weather attribute on pace: seconds per missing point at
# full wetness, scaled linearly with wetness.
WET_PACE_SECONDS_PER_POINT = 0.012
# Errors on a wet track (FOR-11 amplification).
WET_ERROR_FACTOR = 1.2
WRONG_TYRE_ERROR_FACTOR = 1.6
SLICK_WET_THRESHOLD = 0.30
# Tyre performance vs conditions: loss in seconds per lap.
SLICK_WETNESS_PENALTY = 14.0
INTERMEDIATE_BASE_LOSS = 2.0
INTERMEDIATE_SWEET_SPOT = 0.45
INTERMEDIATE_SLOPE = 6.0
WET_BASE_LOSS = 3.5
WET_SWEET_SPOT = 0.85
WET_SLOPE = 7.0


@dataclass(frozen=True)
class SessionForecast:
    """La previsione probabilistica mostrabile al giocatore.

    rain_chance e' la probabilita' che la sessione veda pioggia: nasce
    dalla probabilita' del circuito con un piccolo scarto per seed. La
    realizzazione vera resta nascosta nel processo per Tick.
    """

    circuit_code: str
    rain_chance: float


def session_forecast(circuit: Circuit, seed: int) -> SessionForecast:
    """La previsione della sessione, deterministica a parita' di seed."""
    rng = Random(seed * 1_000_003 + _FORECAST_SEED_OFFSET)
    jitter = rng.uniform(-FORECAST_JITTER, FORECAST_JITTER)
    chance = min(max(circuit.rain_probability + jitter, 0.0), 1.0)
    return SessionForecast(circuit_code=circuit.code, rain_chance=chance)


def rain_start_probability(circuit: Circuit, total_laps: int) -> float:
    """Probabilita' per Tick che la pioggia arrivi su pista asciutta."""
    return min(circuit.rain_probability * RAIN_START_FACTOR / total_laps, 1.0)


def evolve_weather(
    circuit: Circuit,
    total_laps: int,
    rain_intensity: float,
    track_wetness: float,
    lap: int,
    rng: Random,
) -> tuple[float, float, list]:
    """Un Tick di meteo: nuova intensita', nuova bagnatura, eventi.

    Va chiamata con l'RNG del giro PRIMA delle estrazioni di gara, cosi'
    l'ordine dei draw resta deterministico.
    """
    events: list = []
    if rain_intensity <= 0.0:
        if rng.random() < rain_start_probability(circuit, total_laps):
            rain_intensity = rng.uniform(*RAIN_INTENSITY_RANGE_AT_START)
            events.append(RainStarted(lap=lap, intensity=rain_intensity))
    else:
        rain_intensity = min(max(rain_intensity + rng.uniform(*RAIN_INTENSITY_DRIFT), 0.0), 1.0)
        if rain_intensity < RAIN_MINIMUM_INTENSITY or rng.random() < RAIN_STOP_PROBABILITY:
            rain_intensity = 0.0
            events.append(RainStopped(lap=lap))
    before = optimal_category(track_wetness)
    if rain_intensity > 0.0:
        track_wetness = min(
            track_wetness + WETNESS_GAIN_BASE + WETNESS_GAIN_PER_INTENSITY * rain_intensity, 1.0
        )
    else:
        track_wetness = max(track_wetness - DRYING_RATE, 0.0)
    after = optimal_category(track_wetness)
    if after != before:
        events.append(
            Crossover(
                lap=lap,
                from_category=before,
                to_category=after,
                track_wetness=track_wetness,
            )
        )
    return rain_intensity, track_wetness, events


def condition_loss_seconds(compound: Compound, track_wetness: float) -> float:
    """La perdita per giro del tipo gomma nelle condizioni pista date.

    Le slick crollano col bagnato, Intermedia e Bagnato hanno una zona
    dolce: il Crossover emerge dall'incrocio delle curve.
    """
    if compound.is_dry:
        return SLICK_WETNESS_PENALTY * track_wetness**1.5
    if compound is Compound.INTERMEDIATE:
        return INTERMEDIATE_BASE_LOSS + INTERMEDIATE_SLOPE * abs(
            track_wetness - INTERMEDIATE_SWEET_SPOT
        )
    return WET_BASE_LOSS + WET_SLOPE * abs(track_wetness - WET_SWEET_SPOT)


def optimal_category(track_wetness: float) -> str:
    """La categoria di gomma piu' veloce nelle condizioni date.

    Valori: "slick", "intermediate", "wet". Calcolata dalle stesse
    curve di condition_loss_seconds: nessuna soglia ad hoc.
    """
    candidates = {
        "slick": condition_loss_seconds(Compound.C3, track_wetness),
        "intermediate": condition_loss_seconds(Compound.INTERMEDIATE, track_wetness),
        "wet": condition_loss_seconds(Compound.WET, track_wetness),
    }
    return min(candidates, key=candidates.get)


def wet_driver_loss_seconds(wet_weather: int, track_wetness: float) -> float:
    """Quanto paga sul passo chi non e' uno specialista del Bagnato."""
    return (100 - wet_weather) * WET_PACE_SECONDS_PER_POINT * track_wetness


def wet_error_multiplier(compound: Compound, track_wetness: float) -> float:
    """L'amplificazione degli Errori sul bagnato, peggio con gomma sbagliata."""
    multiplier = 1.0 + WET_ERROR_FACTOR * track_wetness
    if compound.is_dry and track_wetness >= SLICK_WET_THRESHOLD:
        multiplier *= WRONG_TYRE_ERROR_FACTOR
    return multiplier
