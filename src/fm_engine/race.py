"""Riduttore puro della gara: step(stato, ordini) -> (stato', eventi) (FOR-8).

Tick = giro: ogni chiamata a step simula un giro completo per tutte le
vetture, risolve sorpassi e duelli dentro al giro e produce un nuovo
stato immutabile piu' gli eventi tipizzati (ADR 0003). Il determinismo
e' garantito derivando l'RNG del giro da (seed, giro): stesso seed e
stessi Ordini, stessa gara.

Gara asciutta senza pit stop: gomme (T2.2.1), Sfiga (T2.2.2),
neutralizzazioni (T2.3.1) e meteo (T2.3.2) si innestano qui.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from random import Random

from fm_engine.circuits import Circuit
from fm_engine.events import (
    BiCompoundPenalty,
    ChequeredFlag,
    ClassifiedResult,
    FastestLap,
    Overtake,
    PitEntry,
    PitExit,
    RaceEvent,
    RaceStarted,
    TeamOrderSwap,
    TyreChange,
)
from fm_engine.laptime import lap_time_seconds
from fm_engine.pitstop import pit_stop_seconds
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
from fm_engine.tyres import (
    Compound,
    CompoundSlot,
    TyreState,
    after_lap,
    fresh_set,
    nominated_compounds,
    tyre_lap_loss_seconds,
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
# Bi-compound rule (FOR-10), documented choice: the rule does not force a
# stop, it sanctions. Finishing a dry race on a single dry compound costs
# a flat time penalty applied to the final classification.
BI_COMPOUND_PENALTY_SECONDS = 30.0


@dataclass
class _LapRun:
    """Stato di lavoro mutabile di una vettura dentro al giro corrente."""

    car: CarRaceState
    orders: DriverOrders
    new_total: float
    new_tyres: TyreState
    compounds_used: tuple[Compound, ...]
    # True if the car stopped at the box this lap: rivals pass for free.
    pitted: bool = False


def start_race(
    entries: tuple[RaceEntry, ...],
    circuit: Circuit,
    seed: int,
    starting_compounds: Mapping[int, Compound] | None = None,
) -> tuple[RaceState, tuple[RaceEvent, ...]]:
    """Lo stato iniziale della gara, con le vetture in ordine di griglia.

    entries e' la griglia di partenza: la prima e' in pole. Ogni slot
    paga un piccolo distacco iniziale, cosi' i distacchi cumulati
    partono coerenti con le posizioni. starting_compounds assegna la
    Mescola di partenza per driver id; default: la Medium del GP.
    """
    if len(entries) < 2:
        raise ValueError("a race needs at least 2 entries")
    driver_ids = [entry.driver.id for entry in entries]
    if len(set(driver_ids)) != len(driver_ids):
        raise ValueError("duplicate driver ids on the starting grid")
    nominated = nominated_compounds(circuit)
    default_compound = nominated[CompoundSlot.MEDIUM]
    compounds: dict[int, Compound] = {}
    for entry in entries:
        compound = (starting_compounds or {}).get(entry.driver.id, default_compound)
        _validate_race_compound(compound, circuit)
        compounds[entry.driver.id] = compound
    cars = tuple(
        CarRaceState(
            entry=entry,
            position=index + 1,
            total_time_seconds=index * GRID_SLOT_GAP_SECONDS,
            last_lap_seconds=0.0,
            gap_to_leader_seconds=index * GRID_SLOT_GAP_SECONDS,
            tyres=fresh_set(compounds[entry.driver.id]),
            compounds_used=(compounds[entry.driver.id],),
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

    running: list[_LapRun] = []
    for car in state.cars:
        driver_orders = orders.for_driver(car.entry.driver.id)
        lap_seconds = lap_time_seconds(
            car.entry, state.circuit, driver_orders.aggression, rng
        ) + tyre_lap_loss_seconds(car.tyres)
        compounds_used = car.compounds_used
        if driver_orders.pit is not None:
            compound = driver_orders.pit.compound
            _validate_race_compound(compound, state.circuit)
            stop_seconds = pit_stop_seconds(rng)
            lap_seconds += stop_seconds
            driver_id = car.entry.driver.id
            events.append(PitEntry(lap=lap, driver_id=driver_id))
            events.append(
                TyreChange(
                    lap=lap,
                    driver_id=driver_id,
                    old_compound=car.tyres.compound.value,
                    new_compound=compound.value,
                )
            )
            events.append(PitExit(lap=lap, driver_id=driver_id, time_lost_seconds=stop_seconds))
            new_tyres = fresh_set(compound)
            if compound not in compounds_used:
                compounds_used = (*compounds_used, compound)
        else:
            new_tyres = after_lap(car.tyres, car.entry, state.circuit, driver_orders.aggression)
        running.append(
            _LapRun(
                car=car,
                orders=driver_orders,
                new_total=car.total_time_seconds + lap_seconds,
                new_tyres=new_tyres,
                compounds_used=compounds_used,
                pitted=driver_orders.pit is not None,
            )
        )

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
            tyres=run.new_tyres,
            compounds_used=run.compounds_used,
        )
        for index, run in enumerate(running)
    )
    finished = lap == state.total_laps
    if finished:
        penalty_events, chequered_flag = _final_classification(cars, lap)
        events.extend(penalty_events)
        events.append(chequered_flag)

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


def _validate_race_compound(compound: Compound, circuit: Circuit) -> None:
    """Solo le 3 Mescole nominate per il GP sono montabili in gara.

    Intermedia e Bagnato esistono nel modello dati ma restano inattivi
    finche' il meteo non li attiva (T2.3.2).
    """
    if not compound.is_dry:
        raise ValueError(
            f"{compound.value} is inactive until weather lands (T2.3.2): dry races only"
        )
    nominated = nominated_compounds(circuit)
    if compound not in nominated.values():
        allowed = ", ".join(c.value for c in nominated.values())
        raise ValueError(f"{compound.value} is not nominated at {circuit.code}: pick {allowed}")


def _final_classification(
    cars: tuple[CarRaceState, ...],
    lap: int,
) -> tuple[list[RaceEvent], ChequeredFlag]:
    """La classifica finale con la regola bi-mescola applicata.

    Chi ha usato meno di 2 Mescole da asciutto prende la penalita'
    fissa; la classifica e' riordinata sui tempi penalizzati.
    """
    penalty_events: list[RaceEvent] = []
    penalties: dict[int, float] = {}
    for car in cars:
        driver_id = car.entry.driver.id
        dry_compounds = {compound for compound in car.compounds_used if compound.is_dry}
        penalty = 0.0 if len(dry_compounds) >= 2 else BI_COMPOUND_PENALTY_SECONDS
        penalties[driver_id] = penalty
        if penalty:
            penalty_events.append(
                BiCompoundPenalty(lap=lap, driver_id=driver_id, penalty_seconds=penalty)
            )
    ranked = sorted(
        cars,
        key=lambda car: car.total_time_seconds + penalties[car.entry.driver.id],
    )
    winner_total = ranked[0].total_time_seconds + penalties[ranked[0].entry.driver.id]
    classification = tuple(
        ClassifiedResult(
            position=position,
            driver_id=car.entry.driver.id,
            team_id=car.entry.team_id,
            total_time_seconds=car.total_time_seconds + penalties[car.entry.driver.id],
            gap_to_winner_seconds=(
                car.total_time_seconds + penalties[car.entry.driver.id] - winner_total
            ),
            points=points_for_position(position),
            penalty_seconds=penalties[car.entry.driver.id],
        )
        for position, car in enumerate(ranked, start=1)
    )
    return penalty_events, ChequeredFlag(lap=lap, classification=classification)


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
            if ahead.pitted:
                # Pit rejoin, not a duel: the rival goes by for free.
                running[index], running[index + 1] = behind, ahead
                swapped = True
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
