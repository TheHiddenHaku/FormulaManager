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
from dataclasses import dataclass, replace
from random import Random

from fm_engine.circuits import Circuit
from fm_engine.events import (
    Accident,
    AccidentSeverity,
    BiCompoundPenalty,
    CarDamage,
    CarFailure,
    ChequeredFlag,
    ClassifiedResult,
    Dnf,
    DnfCause,
    DriverError,
    FastestLap,
    Overtake,
    PitEntry,
    PitExit,
    RaceEvent,
    RaceStarted,
    SafetyCarDeployed,
    SafetyCarEnding,
    TeamOrderSwap,
    TyreChange,
    VscDeployed,
    VscEnding,
)
from fm_engine.laptime import base_lap_seconds, lap_time_seconds
from fm_engine.misfortune import (
    ERROR_CAUSES,
    FAILURE_COMPONENTS,
    MisfortuneConfig,
    damage_amount_usd,
    duel_contact_probability,
    error_probability,
    failure_probability,
)
from fm_engine.neutralization import (
    RESTART_RISK_FACTOR,
    RESTART_RISK_LAPS,
    SAFETY_CAR_QUEUE_GAP_SECONDS,
    RaceRegime,
    draw_neutralization,
    neutralized_pace_factor,
    pit_discount,
)
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
    misfortune: MisfortuneConfig | None = None,
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
        misfortune=misfortune if misfortune is not None else MisfortuneConfig(),
        dnfs=(),
    )
    started = RaceStarted(lap=0, circuit_code=circuit.code, total_laps=circuit.race_laps)
    return state, (started,)


def step(state: RaceState, orders: Orders | None = None) -> tuple[RaceState, tuple[RaceEvent, ...]]:
    """Simula il prossimo Tick (= giro) e ritorna nuovo stato ed eventi."""
    if state.finished:
        raise ValueError("race already finished: no further ticks")
    if orders is None:
        orders = Orders()
    if state.regime is not RaceRegime.GREEN:
        return _neutralized_step(state, orders)
    lap = state.lap + 1
    # One dedicated RNG per (seed, lap): step stays a pure function.
    rng = Random(state.seed * 1_000_003 + lap)
    events: list[RaceEvent] = []
    config = state.misfortune
    # Post-restart window: errors and duel contacts are more likely.
    risk_factor = RESTART_RISK_FACTOR if state.restart_risk_laps_remaining > 0 else 1.0

    # Close racing at the end of the previous Tick: error aggravation.
    in_duel_ids = _drivers_in_close_racing(state, config.duel_proximity_seconds)

    running: list[_LapRun] = []
    retired: list[CarRaceState] = []
    for car in state.cars:
        driver_id = car.entry.driver.id
        driver_orders = orders.for_driver(driver_id)
        # Guasto: drawn before the lap is run, inverse of reliability.
        if rng.random() < failure_probability(config, car.entry.car.reliability):
            component = rng.choice(FAILURE_COMPONENTS)
            events.append(CarFailure(lap=lap, driver_id=driver_id, component=component))
            events.append(
                CarDamage(
                    lap=lap,
                    driver_id=driver_id,
                    amount_usd=damage_amount_usd(config, severe=True, rng=rng),
                )
            )
            events.append(
                Dnf(lap=lap, driver_id=driver_id, cause=DnfCause.FAILURE, detail=component)
            )
            retired.append(replace(car, position=0))
            continue
        lap_seconds = lap_time_seconds(
            car.entry, state.circuit, driver_orders.aggression, rng
        ) + tyre_lap_loss_seconds(car.tyres)
        # Incidente alla partenza: independent per-car draw on lap 1.
        if lap == 1 and rng.random() < config.start_contact_probability:
            is_dnf = rng.random() < config.accident_dnf_probability
            severity = AccidentSeverity.MAJOR if is_dnf else AccidentSeverity.MINOR
            events.append(Accident(lap=lap, driver_ids=(driver_id,), severity=severity))
            events.append(
                CarDamage(
                    lap=lap,
                    driver_id=driver_id,
                    amount_usd=damage_amount_usd(config, severe=is_dnf, rng=rng),
                )
            )
            if is_dnf:
                events.append(
                    Dnf(lap=lap, driver_id=driver_id, cause=DnfCause.ACCIDENT, detail="contact")
                )
                retired.append(replace(car, position=0))
                continue
            lap_seconds += rng.uniform(*config.accident_time_loss_range)
        # Errore pilota: inverse of consistency, aggravated by Push and duels.
        in_duel = driver_id in in_duel_ids
        if (
            rng.random()
            < error_probability(
                config, car.entry.driver.consistency, driver_orders.aggression, in_duel
            )
            * risk_factor
        ):
            cause = rng.choice(ERROR_CAUSES)
            if rng.random() < config.terminal_error_share:
                events.append(
                    CarDamage(
                        lap=lap,
                        driver_id=driver_id,
                        amount_usd=damage_amount_usd(config, severe=True, rng=rng),
                    )
                )
                events.append(
                    Dnf(lap=lap, driver_id=driver_id, cause=DnfCause.DRIVER_ERROR, detail=cause)
                )
                retired.append(replace(car, position=0))
                continue
            time_lost = rng.uniform(*config.error_time_loss_range)
            lap_seconds += time_lost
            events.append(
                DriverError(
                    lap=lap,
                    driver_id=driver_id,
                    cause=cause,
                    time_lost_seconds=time_lost,
                    in_duel=in_duel,
                )
            )
        compounds_used = car.compounds_used
        if driver_orders.pit is not None:
            compound = driver_orders.pit.compound
            _validate_race_compound(compound, state.circuit)
            stop_seconds = pit_stop_seconds(rng)
            lap_seconds += stop_seconds
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
    _resolve_duels(running, orders, lap, rng, events, config, retired, risk_factor)

    fastest_seconds = state.fastest_lap_seconds
    fastest_driver_id = state.fastest_lap_driver_id
    if not running:
        raise ValueError("the whole field retired: no runners left to classify")
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

    # Neutralization trigger: this lap's accidents can bring SC or VSC
    # from the next Tick (FOR-12).
    new_regime = RaceRegime.GREEN
    regime_laps_remaining = 0
    restart_risk_laps_remaining = max(0, state.restart_risk_laps_remaining - 1)
    if not finished:
        severities = tuple(event.severity for event in events if isinstance(event, Accident))
        outcome = draw_neutralization(state.circuit, severities, rng)
        if outcome is not None:
            new_regime, regime_laps_remaining = outcome
            restart_risk_laps_remaining = 0
            if new_regime is RaceRegime.SAFETY_CAR:
                events.append(SafetyCarDeployed(lap=lap, duration_laps=regime_laps_remaining))
            else:
                events.append(VscDeployed(lap=lap, duration_laps=regime_laps_remaining))

    new_state = RaceState(
        seed=state.seed,
        circuit=state.circuit,
        lap=lap,
        total_laps=state.total_laps,
        cars=cars,
        fastest_lap_seconds=fastest_seconds,
        fastest_lap_driver_id=fastest_driver_id,
        finished=finished,
        misfortune=state.misfortune,
        dnfs=state.dnfs + tuple(retired),
        regime=new_regime,
        regime_laps_remaining=regime_laps_remaining,
        restart_risk_laps_remaining=restart_risk_laps_remaining,
    )
    return new_state, tuple(events)


def _neutralized_step(state: RaceState, orders: Orders) -> tuple[RaceState, tuple[RaceEvent, ...]]:
    """Un Tick sotto Safety car o VSC: niente duelli, passo imposto.

    Sotto SC il gruppo si compatta in coda alla vettura di sicurezza (i
    tempi cumulati vengono ribasati sui distacchi di coda); sotto VSC
    ogni vettura somma lo stesso tempo, quindi i distacchi restano
    congelati. Il pit stop e' scontato in entrambi i regimi.
    """
    lap = state.lap + 1
    rng = Random(state.seed * 1_000_003 + lap)
    events: list[RaceEvent] = []
    config = state.misfortune
    pace_seconds = base_lap_seconds(state.circuit) * neutralized_pace_factor(state.regime)
    discount = pit_discount(state.regime)

    running: list[_LapRun] = []
    retired: list[CarRaceState] = []
    for car in state.cars:
        driver_id = car.entry.driver.id
        driver_orders = orders.for_driver(driver_id)
        # Mechanical failures do not care about the regime.
        if rng.random() < failure_probability(config, car.entry.car.reliability):
            component = rng.choice(FAILURE_COMPONENTS)
            events.append(CarFailure(lap=lap, driver_id=driver_id, component=component))
            events.append(
                CarDamage(
                    lap=lap,
                    driver_id=driver_id,
                    amount_usd=damage_amount_usd(config, severe=True, rng=rng),
                )
            )
            events.append(
                Dnf(lap=lap, driver_id=driver_id, cause=DnfCause.FAILURE, detail=component)
            )
            retired.append(replace(car, position=0))
            continue
        lap_seconds = pace_seconds
        compounds_used = car.compounds_used
        if driver_orders.pit is not None:
            compound = driver_orders.pit.compound
            _validate_race_compound(compound, state.circuit)
            stop_seconds = pit_stop_seconds(rng) * discount
            lap_seconds += stop_seconds
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
            # Cruising behind the neutralization: tyres age gently.
            new_tyres = after_lap(car.tyres, car.entry, state.circuit, Aggression.CONSERVE)
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

    if not running:
        raise ValueError("the whole field retired: no runners left to classify")
    # No duels under neutralization: track order follows cumulative time
    # (a pitting car slots back according to the time it lost).
    running.sort(key=lambda run: run.new_total)
    if state.regime is RaceRegime.SAFETY_CAR:
        # The field compacts behind the safety car: cumulative times are
        # rebased on the queue gaps.
        leader_total = running[0].new_total
        for index, run in enumerate(running):
            run.new_total = leader_total + index * SAFETY_CAR_QUEUE_GAP_SECONDS

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

    regime_laps_remaining = state.regime_laps_remaining - 1
    new_regime = state.regime
    restart_risk_laps_remaining = 0
    if regime_laps_remaining <= 0 and not finished:
        if state.regime is RaceRegime.SAFETY_CAR:
            events.append(SafetyCarEnding(lap=lap))
            restart_risk_laps_remaining = RESTART_RISK_LAPS
        else:
            events.append(VscEnding(lap=lap))
        new_regime = RaceRegime.GREEN
        regime_laps_remaining = 0

    new_state = RaceState(
        seed=state.seed,
        circuit=state.circuit,
        lap=lap,
        total_laps=state.total_laps,
        cars=cars,
        fastest_lap_seconds=state.fastest_lap_seconds,
        fastest_lap_driver_id=state.fastest_lap_driver_id,
        finished=finished,
        misfortune=state.misfortune,
        dnfs=state.dnfs + tuple(retired),
        regime=new_regime,
        regime_laps_remaining=max(regime_laps_remaining, 0),
        restart_risk_laps_remaining=restart_risk_laps_remaining,
    )
    return new_state, tuple(events)


def _drivers_in_close_racing(state: RaceState, proximity_seconds: float) -> set[int]:
    """I piloti in lotta ravvicinata a fine Tick precedente (proxy duello)."""
    in_duel: set[int] = set()
    for ahead, behind in zip(state.cars, state.cars[1:], strict=False):
        gap = behind.total_time_seconds - ahead.total_time_seconds
        if gap < proximity_seconds:
            in_duel.add(ahead.entry.driver.id)
            in_duel.add(behind.entry.driver.id)
    return in_duel


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
    config: MisfortuneConfig,
    retired: list[CarRaceState],
    risk_factor: float = 1.0,
) -> None:
    """Risolve sorpassi e duelli dentro al giro, dal fondo della scia.

    Passate a bolla sull'ordine di pista: chi ha un tempo cumulato
    migliore della vettura davanti tenta il sorpasso; se fallisce (o se
    un Ordine glielo vieta) resta incollato dietro e paga l'aria
    sporca. Ogni tentativo puo' degenerare in un contatto (FOR-11).
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
            if rng.random() < duel_contact_probability(config, behind.orders.aggression) * (
                risk_factor
            ):
                _handle_duel_contact(running, index, lap, rng, events, config, retired)
                # The field changed under our feet: restart the pass.
                swapped = True
                break
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


def _handle_duel_contact(
    running: list[_LapRun],
    index: int,
    lap: int,
    rng: Random,
    events: list[RaceEvent],
    config: MisfortuneConfig,
    retired: list[CarRaceState],
) -> None:
    """Un contatto in duello: danni per entrambi, Abbandoni possibili."""
    ahead, behind = running[index], running[index + 1]
    attacker_dnf = rng.random() < config.accident_dnf_probability
    defender_dnf = rng.random() < config.accident_dnf_probability
    severity = AccidentSeverity.MAJOR if (attacker_dnf or defender_dnf) else AccidentSeverity.MINOR
    events.append(
        Accident(
            lap=lap,
            driver_ids=(behind.car.entry.driver.id, ahead.car.entry.driver.id),
            severity=severity,
        )
    )
    for run, is_dnf in ((behind, attacker_dnf), (ahead, defender_dnf)):
        driver_id = run.car.entry.driver.id
        events.append(
            CarDamage(
                lap=lap,
                driver_id=driver_id,
                amount_usd=damage_amount_usd(config, severe=is_dnf, rng=rng),
            )
        )
        if is_dnf:
            events.append(
                Dnf(lap=lap, driver_id=driver_id, cause=DnfCause.ACCIDENT, detail="contact")
            )
            retired.append(replace(run.car, position=0))
            running.remove(run)
        else:
            run.new_total += rng.uniform(*config.accident_time_loss_range)


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
