"""Strategia gomme delle squadre AI, condivisa dal motore (FOR-39).

Conteggio soste ottimale, piani per pilota e Ordini di pit al giro
giusto: la stessa logica che l'harness di bilanciamento usava per far
girare le stagioni (FOR-14) vive qui come modulo puro del motore, cosi'
la Gara interattiva puo' iniettare gli stessi Ordini AI a ogni Tick.

Non e' una meccanica nuova ne' una strategia AI per i piloti del
giocatore: e' l'orchestrazione che un manager farebbe a mano, decisa
dalle stesse curve di Degrado (FOR-10) e dalla reazione al Crossover
quando piove (FOR-13). I piani sono deterministici dato l'RNG passato.
"""

from dataclasses import dataclass, field
from random import Random

from fm_engine.circuits import Circuit
from fm_engine.pitstop import PIT_STOP_BASE_SECONDS
from fm_engine.state import (
    Aggression,
    DriverOrders,
    Orders,
    PitOrder,
    RaceEntry,
    RaceState,
)
from fm_engine.tyres import (
    Compound,
    CompoundSlot,
    degradation_step_seconds,
    fresh_set,
    nominated_compounds,
)
from fm_engine.weather import optimal_category

# Minimum laps between two stops of the same car: no pit ping-pong when
# conditions hover around a crossover point.
MIN_LAPS_BETWEEN_STOPS = 4


def planned_stop_count(entry: RaceEntry, circuit: Circuit) -> int:
    """Le soste pianificate sull'asciutto, dalle curve di Degrado del motore."""
    medium = nominated_compounds(circuit)[CompoundSlot.MEDIUM]
    step_seconds = degradation_step_seconds(
        fresh_set(medium), entry, circuit, aggression=Aggression.NORMAL
    )
    laps = circuit.race_laps

    def race_cost(stops: int) -> float:
        stint = laps / (stops + 1)
        return (stops + 1) * step_seconds * stint * stint / 2 + stops * PIT_STOP_BASE_SECONDS

    best = min(range(4), key=race_cost)
    # The bi-compound rule makes a stop mandatory anyway.
    return max(1, best)


@dataclass
class StrategyPlan:
    """Il piano gomme di una vettura: soste secche piu' reazione al meteo."""

    pit_laps: dict[int, Compound] = field(default_factory=dict)
    last_stop_lap: int = -10


def build_plans(
    entries: tuple[RaceEntry, ...], circuit: Circuit, rng: Random
) -> dict[int, StrategyPlan]:
    """I piani gomme per le vetture date, scaglionati e bi-mescola conformi."""
    nominated = nominated_compounds(circuit)
    plans: dict[int, StrategyPlan] = {}
    for entry in entries:
        stops = planned_stop_count(entry, circuit)
        # Compound rotation that always satisfies the bi-compound rule.
        rotation = (
            [nominated[CompoundSlot.HARD]]
            if stops == 1
            else [nominated[CompoundSlot.HARD], nominated[CompoundSlot.MEDIUM]]
        )
        plan = StrategyPlan()
        for index in range(stops):
            lap = circuit.race_laps * (index + 1) // (stops + 1) + rng.randint(-3, 3)
            lap = min(max(lap, 2), circuit.race_laps - 2)
            plan.pit_laps[lap] = rotation[index % len(rotation)]
        plans[entry.driver.id] = plan
    return plans


def varied_starting_compounds(
    entries: tuple[RaceEntry, ...], circuit: Circuit, rng: Random
) -> dict[int, Compound]:
    """Gomma di partenza variata tra le vetture (Strategia Pit Stop).

    Alterna Soft (partenza aggressiva) e Medium (equilibrata) per ciascuna
    vettura, cosi' le strategie iniziali non sono tutte identiche. Resta
    compatibile con la regola bi-mescola: la rotazione ai box (build_plans)
    usa la Hard, quindi partire su Soft o Medium garantisce comunque due
    mescole diverse in gara. La Hard non si assegna in partenza per non
    forzare soste innaturali. Deterministico dato l'RNG passato.
    """
    nominated = nominated_compounds(circuit)
    options = (nominated[CompoundSlot.SOFT], nominated[CompoundSlot.MEDIUM])
    return {entry.driver.id: rng.choice(options) for entry in entries}


def _weather_compound(category: str, circuit: Circuit) -> Compound:
    if category == "intermediate":
        return Compound.INTERMEDIATE
    if category == "wet":
        return Compound.WET
    return nominated_compounds(circuit)[CompoundSlot.MEDIUM]


def _category_of(compound: Compound) -> str:
    if compound is Compound.INTERMEDIATE:
        return "intermediate"
    if compound is Compound.WET:
        return "wet"
    return "slick"


def lap_orders(state: RaceState, plans: dict[int, StrategyPlan]) -> Orders | None:
    """Gli Ordini di pit del prossimo Tick: piano asciutto piu' Crossover.

    Solo le vetture con un piano vengono orchestrate: i piloti senza
    piano (quelli del giocatore nella Gara interattiva) restano al
    manager. Le vetture ritirate non sono in state.cars, quindi escono
    da sole. La funzione muta last_stop_lap del piano quando emette un
    Ordine, per non sovrapporre due soste troppo ravvicinate.
    """
    next_lap = state.lap + 1
    optimal = optimal_category(state.track_wetness)
    drivers: dict[int, DriverOrders] = {}
    for car in state.cars:
        driver_id = car.entry.driver.id
        plan = plans.get(driver_id)
        if plan is None:
            continue
        if next_lap - plan.last_stop_lap < MIN_LAPS_BETWEEN_STOPS:
            continue
        current_category = _category_of(car.tyres.compound)
        compound: Compound | None = None
        if current_category != optimal:
            # React to the crossover, both ways (rain in, track drying).
            compound = _weather_compound(optimal, state.circuit)
        elif optimal == "slick" and next_lap in plan.pit_laps:
            compound = plan.pit_laps[next_lap]
        if compound is not None and compound is not car.tyres.compound:
            drivers[driver_id] = DriverOrders(pit=PitOrder(compound=compound))
            plan.last_stop_lap = next_lap
    if not drivers:
        return None
    return Orders(drivers=drivers)
