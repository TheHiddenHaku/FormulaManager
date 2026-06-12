"""Riduttore puro della gara: step(stato, ordini) -> (stato', eventi) (FOR-8).

Tick = giro: ogni chiamata a step simula un giro completo per tutte le
vetture, risolve sorpassi e duelli dentro al giro e produce un nuovo
stato immutabile piu' gli eventi tipizzati (ADR 0003). Il determinismo
e' garantito derivando l'RNG del giro da (seed, giro): stesso seed e
stessi Ordini, stessa gara.

Gara asciutta senza pit stop: gomme (T2.2.1), Sfiga (T2.2.2),
neutralizzazioni (T2.3.1) e meteo (T2.3.2) si innestano qui.
"""

from dataclasses import dataclass
from random import Random

from fm_engine.circuits import Circuit
from fm_engine.events import (
    ChequeredFlag,
    ClassifiedResult,
    FastestLap,
    Overtake,
    RaceEvent,
    RaceStarted,
    TeamOrderSwap,
)
from fm_engine.laptime import lap_time_seconds
from fm_engine.points import points_for_position
from fm_engine.state import (
    Aggression,
    CarRaceState,
    DriverOrders,
    DuelInstruction,
    Orders,
    RaceEntry,
    RaceState,
    TeamOrder,
)

# Time lost on the grid per starting slot, applied once at lights out.
GRID_SLOT_GAP_SECONDS = 0.25
# A faster car stuck behind a rival sits this close, losing the difference.
DIRTY_AIR_GAP_SECONDS = 0.5
# Gap taken by the demoted teammate after a team order swap.
TEAM_ORDER_TUCK_GAP_SECONDS = 0.3
# Duel resolution parameters, tunable via the balance harness (T2.4.1).
DUEL_BASE_PROBABILITY = 0.30
DUEL_PROBABILITY_PER_DUELS_POINT = 0.005
DUEL_PROBABILITY_PER_ADVANTAGE_SECOND = 0.15
DUEL_MAX_ADVANTAGE_SECONDS = 2.0
DUEL_PROBABILITY_FLOOR = 0.05
DUEL_PROBABILITY_CEILING = 0.95
AGGRESSION_DUEL_PROBABILITY_OFFSET: dict[Aggression, float] = {
    Aggression.PUSH: 0.08,
    Aggression.NORMAL: 0.0,
    Aggression.CONSERVE: -0.08,
}
DEFEND_HARD_PROBABILITY_MALUS = 0.10


@dataclass
class _LapRun:
    """Stato di lavoro mutabile di una vettura dentro al giro corrente."""

    car: CarRaceState
    orders: DriverOrders
    new_total: float


def start_race(
    entries: tuple[RaceEntry, ...],
    circuit: Circuit,
    seed: int,
) -> tuple[RaceState, tuple[RaceEvent, ...]]:
    """Lo stato iniziale della gara, con le vetture in ordine di griglia.

    entries e' la griglia di partenza: la prima e' in pole. Ogni slot
    paga un piccolo distacco iniziale, cosi' i distacchi cumulati
    partono coerenti con le posizioni.
    """
    if len(entries) < 2:
        raise ValueError("a race needs at least 2 entries")
    driver_ids = [entry.driver.id for entry in entries]
    if len(set(driver_ids)) != len(driver_ids):
        raise ValueError("duplicate driver ids on the starting grid")
    cars = tuple(
        CarRaceState(
            entry=entry,
            position=index + 1,
            total_time_seconds=index * GRID_SLOT_GAP_SECONDS,
            last_lap_seconds=0.0,
            gap_to_leader_seconds=index * GRID_SLOT_GAP_SECONDS,
        )
        for index, entry in enumerate(entries)
    )
    state = RaceState(
        seed=seed,
        circuit=circuit,
        lap=0,
        total_laps=circuit.race_laps,
        cars=cars,
        fastest_lap_seconds=None,
        fastest_lap_driver_id=None,
        finished=False,
    )
    started = RaceStarted(lap=0, circuit_code=circuit.code, total_laps=circuit.race_laps)
    return state, (started,)


def step(state: RaceState, orders: Orders | None = None) -> tuple[RaceState, tuple[RaceEvent, ...]]:
    """Simula il prossimo Tick (= giro) e ritorna nuovo stato ed eventi."""
    if state.finished:
        raise ValueError("race already finished: no further ticks")
    if orders is None:
        orders = Orders()
    lap = state.lap + 1
    # One dedicated RNG per (seed, lap): step stays a pure function.
    rng = Random(state.seed * 1_000_003 + lap)
    events: list[RaceEvent] = []

    running = [
        _LapRun(
            car=car,
            orders=orders.for_driver(car.entry.driver.id),
            new_total=car.total_time_seconds
            + lap_time_seconds(
                car.entry,
                state.circuit,
                orders.for_driver(car.entry.driver.id).aggression,
                rng,
            ),
        )
        for car in state.cars
    ]

    _apply_team_order_swaps(running, orders, lap, events)
    _resolve_duels(running, orders, lap, rng, events)

    fastest_seconds = state.fastest_lap_seconds
    fastest_driver_id = state.fastest_lap_driver_id
    best_run = min(running, key=lambda run: run.new_total - run.car.total_time_seconds)
    best_lap_seconds = best_run.new_total - best_run.car.total_time_seconds
    if fastest_seconds is None or best_lap_seconds < fastest_seconds:
        fastest_seconds = best_lap_seconds
        fastest_driver_id = best_run.car.entry.driver.id
        events.append(
            FastestLap(lap=lap, driver_id=fastest_driver_id, time_seconds=fastest_seconds)
        )

    leader_total = running[0].new_total
    cars = tuple(
        CarRaceState(
            entry=run.car.entry,
            position=index + 1,
            total_time_seconds=run.new_total,
            last_lap_seconds=run.new_total - run.car.total_time_seconds,
            gap_to_leader_seconds=run.new_total - leader_total,
        )
        for index, run in enumerate(running)
    )
    finished = lap == state.total_laps
    if finished:
        classification = tuple(
            ClassifiedResult(
                position=car.position,
                driver_id=car.entry.driver.id,
                team_id=car.entry.team_id,
                total_time_seconds=car.total_time_seconds,
                gap_to_winner_seconds=car.gap_to_leader_seconds,
                points=points_for_position(car.position),
            )
            for car in cars
        )
        events.append(ChequeredFlag(lap=lap, classification=classification))

    new_state = RaceState(
        seed=state.seed,
        circuit=state.circuit,
        lap=lap,
        total_laps=state.total_laps,
        cars=cars,
        fastest_lap_seconds=fastest_seconds,
        fastest_lap_driver_id=fastest_driver_id,
        finished=finished,
    )
    return new_state, tuple(events)


def _apply_team_order_swaps(
    running: list[_LapRun],
    orders: Orders,
    lap: int,
    events: list[RaceEvent],
) -> None:
    """Applica gli scambi di posizione imposti dagli Ordini di scuderia.

    Lo scambio agisce solo su compagni adiacenti in pista e solo quando
    il compagno dietro ha il passo migliore nel giro: l'Ordine "fai
    passare" e' stabile anche se resta attivo per piu' giri (niente
    scambi a ping-pong). Il retrocesso si accoda fuori dalla scia.
    """
    for index in range(len(running) - 1):
        ahead, behind = running[index], running[index + 1]
        team_id = ahead.car.entry.team_id
        if behind.car.entry.team_id != team_id:
            continue
        if orders.for_team(team_id) is not TeamOrder.SWAP_POSITIONS:
            continue
        if behind.new_total >= ahead.new_total:
            continue
        running[index], running[index + 1] = behind, ahead
        ahead.new_total = max(ahead.new_total, behind.new_total + TEAM_ORDER_TUCK_GAP_SECONDS)
        events.append(
            TeamOrderSwap(
                lap=lap,
                team_id=team_id,
                promoted_driver_id=behind.car.entry.driver.id,
                demoted_driver_id=ahead.car.entry.driver.id,
                position=index + 1,
            )
        )


def _resolve_duels(
    running: list[_LapRun],
    orders: Orders,
    lap: int,
    rng: Random,
    events: list[RaceEvent],
) -> None:
    """Risolve sorpassi e duelli dentro al giro, dal fondo della scia.

    Passate a bolla sull'ordine di pista: chi ha un tempo cumulato
    migliore della vettura davanti tenta il sorpasso; se fallisce (o se
    un Ordine glielo vieta) resta incollato dietro e paga l'aria sporca.
    """
    for _ in range(len(running)):
        swapped = False
        for index in range(len(running) - 1):
            ahead, behind = running[index], running[index + 1]
            if behind.new_total >= ahead.new_total - 1e-9:
                continue
            same_team = ahead.car.entry.team_id == behind.car.entry.team_id
            if same_team and orders.for_team(ahead.car.entry.team_id) is not None:
                # Any active team order freezes the fight between teammates.
                behind.new_total = ahead.new_total + DIRTY_AIR_GAP_SECONDS
                continue
            if behind.orders.duel_instruction is DuelInstruction.NO_RISK:
                behind.new_total = ahead.new_total + DIRTY_AIR_GAP_SECONDS
                continue
            if rng.random() < _duel_success_probability(ahead, behind):
                running[index], running[index + 1] = behind, ahead
                events.append(
                    Overtake(
                        lap=lap,
                        driver_id=behind.car.entry.driver.id,
                        overtaken_driver_id=ahead.car.entry.driver.id,
                        position=index + 1,
                    )
                )
                swapped = True
            else:
                behind.new_total = ahead.new_total + DIRTY_AIR_GAP_SECONDS
        if not swapped:
            break


def _duel_success_probability(ahead: _LapRun, behind: _LapRun) -> float:
    """La probabilita' che l'attacco della vettura dietro riesca."""
    attacker = behind.car.entry.driver
    defender = ahead.car.entry.driver
    advantage = min(ahead.new_total - behind.new_total, DUEL_MAX_ADVANTAGE_SECONDS)
    probability = (
        DUEL_BASE_PROBABILITY
        + DUEL_PROBABILITY_PER_DUELS_POINT * (attacker.duels - defender.duels)
        + DUEL_PROBABILITY_PER_ADVANTAGE_SECOND * advantage
        + AGGRESSION_DUEL_PROBABILITY_OFFSET[behind.orders.aggression]
    )
    if ahead.orders.duel_instruction is DuelInstruction.DEFEND_HARD:
        probability -= DEFEND_HARD_PROBABILITY_MALUS
    return min(max(probability, DUEL_PROBABILITY_FLOOR), DUEL_PROBABILITY_CEILING)
