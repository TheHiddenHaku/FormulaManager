"""Simulazione di stagioni complete per l'harness di bilanciamento (FOR-14).

La Griglia nasce da fm_engine.world.generate: 10 squadre AI con i loro
20 piloti contrattualizzati, piu' i 2 piloti liberi su una vettura
neutra (mediana della griglia) nello slot dell'undicesima squadra. Ogni
GP gioca Qualifiche e gara; in gara una strategia gomme di base (non
una meccanica nuova: l'orchestrazione che fara' il giocatore) decide
soste e Mescole dalle stesse curve di Degrado del motore, e reagisce al
Crossover quando piove.
"""

from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import date
from random import Random

from fm_engine.ai import advance_ai_interval, decide_spending, initial_ai_state
from fm_engine.circuits import CALENDAR_2026, Circuit
from fm_engine.economy import (
    Transaction,
    TransactionKind,
    charge_salary_instalments,
    credit_annual_sponsor,
    race_prize_usd,
)
from fm_engine.events import (
    ChequeredFlag,
    Dnf,
    Overtake,
    RainStarted,
    SafetyCarDeployed,
    VscDeployed,
)
from fm_engine.pitstop import PIT_STOP_BASE_SECONDS
from fm_engine.qualifying import simulate_qualifying
from fm_engine.race import start_race, step
from fm_engine.state import (
    Aggression,
    CarAttributes,
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
from fm_engine.world.generation import generate
from fm_engine.world.models import CAR_ATTRIBUTES, PLAYER_TEAM_ID, WorldConfig

# Minimum laps between two stops of the same car: no pit ping-pong when
# conditions hover around a crossover point.
MIN_LAPS_BETWEEN_STOPS = 4


@dataclass(frozen=True)
class RaceRecord:
    """Le misure raccolte da un singolo GP simulato."""

    season: int
    round: int
    circuit_code: str
    dnf_count: int
    overtake_count: int
    safety_cars: int
    vscs: int
    rained: bool
    # Points per driver id and per team id from the final classification.
    driver_points: dict[int, int]
    team_points: dict[int, int]
    # Pit stops per driver id and every compound fitted in the race.
    stops_by_driver: dict[int, int]
    compounds_used: tuple[str, ...]
    # Race prize income per team id from the finishing positions (FOR-26).
    team_prizes: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class TeamSpendingRecord:
    """Le misure di spesa AI di una squadra in una stagione (FOR-26)."""

    season: int
    team_id: int
    profile: str
    focus: str
    total_spent_usd: int
    spend_by_attribute: dict[str, int]
    completed_projects: int
    overspend_usd: int
    final_cash_usd: int


@dataclass(frozen=True)
class SimulationResult:
    """L'esito di una simulazione: gare, griglia e indici di prestazione."""

    seasons: int
    seed: int
    races: tuple[RaceRecord, ...]
    # Combined car+driver performance proxy per driver id, for the
    # attribute-to-results correlation.
    performance_by_driver: dict[int, float]
    team_of_driver: dict[int, int]
    # AI spending measures, one record per team per season (FOR-26).
    spending: tuple[TeamSpendingRecord, ...] = ()


def build_grid(seed: int) -> tuple[RaceEntry, ...]:
    """La Griglia a 22 vetture dal Mondo generato con il seed dato."""
    world = generate(seed, WorldConfig())
    drivers_by_id = {driver.id: driver for driver in world.drivers}
    entries: list[RaceEntry] = []
    for team in world.ai_teams:
        for contract in world.contracts_of(team.id):
            entries.append(
                RaceEntry(
                    driver=drivers_by_id[contract.driver_id],
                    team_id=team.id,
                    car=CarAttributes.from_team(team),
                )
            )
    # The 11th slot: the free agents drive a neutral, median car.
    median_car = CarAttributes(
        **{
            name: sorted(getattr(team, name) for team in world.ai_teams)[len(world.ai_teams) // 2]
            for name in CAR_ATTRIBUTES
        }
    )
    for driver in world.drivers_without_contract:
        entries.append(RaceEntry(driver=driver, team_id=PLAYER_TEAM_ID, car=median_car))
    return tuple(entries)


def _planned_stop_count(entry: RaceEntry, circuit: Circuit) -> int:
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
class _StrategyPlan:
    """Il piano gomme di una vettura: soste secche piu' reazione al meteo."""

    pit_laps: dict[int, Compound] = field(default_factory=dict)
    last_stop_lap: int = -10


def _build_plans(
    entries: tuple[RaceEntry, ...], circuit: Circuit, rng: Random
) -> dict[int, _StrategyPlan]:
    nominated = nominated_compounds(circuit)
    plans: dict[int, _StrategyPlan] = {}
    for entry in entries:
        stops = _planned_stop_count(entry, circuit)
        # Compound rotation that always satisfies the bi-compound rule.
        rotation = (
            [nominated[CompoundSlot.HARD]]
            if stops == 1
            else [nominated[CompoundSlot.HARD], nominated[CompoundSlot.MEDIUM]]
        )
        plan = _StrategyPlan()
        for index in range(stops):
            lap = circuit.race_laps * (index + 1) // (stops + 1) + rng.randint(-3, 3)
            lap = min(max(lap, 2), circuit.race_laps - 2)
            plan.pit_laps[lap] = rotation[index % len(rotation)]
        plans[entry.driver.id] = plan
    return plans


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


def _lap_orders(state: RaceState, plans: dict[int, _StrategyPlan]) -> Orders | None:
    """Gli Ordini di pit del prossimo Tick: piano asciutto piu' Crossover."""
    next_lap = state.lap + 1
    optimal = optimal_category(state.track_wetness)
    drivers: dict[int, DriverOrders] = {}
    for car in state.cars:
        driver_id = car.entry.driver.id
        plan = plans[driver_id]
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


def _simulate_race(
    entries: tuple[RaceEntry, ...],
    circuit: Circuit,
    season: int,
    round_number: int,
    seed: int,
) -> RaceRecord:
    race_seed = seed * 1_000 + season * 100 + round_number
    qualifying, _ = simulate_qualifying(entries, circuit, seed=race_seed)
    state, _ = start_race(qualifying.grid, circuit, seed=race_seed)
    plans = _build_plans(entries, circuit, Random(race_seed))
    dnf_count = 0
    overtake_count = 0
    safety_cars = 0
    vscs = 0
    rained = False
    stops: Counter[int] = Counter()
    compounds: set[str] = {car.tyres.compound.value for car in state.cars}
    driver_points: dict[int, int] = {}
    team_points: dict[int, int] = {}
    team_prizes: dict[int, int] = {}
    while not state.finished:
        orders = _lap_orders(state, plans)
        if orders is not None:
            for driver_id in orders.drivers:
                stops[driver_id] += 1
        state, events = step(state, orders)
        for event in events:
            if isinstance(event, Dnf):
                dnf_count += 1
            elif isinstance(event, Overtake):
                overtake_count += 1
            elif isinstance(event, SafetyCarDeployed):
                safety_cars += 1
            elif isinstance(event, VscDeployed):
                vscs += 1
            elif isinstance(event, RainStarted):
                rained = True
            elif isinstance(event, ChequeredFlag):
                for row in event.classification:
                    driver_points[row.driver_id] = row.points
                    team_points[row.team_id] = team_points.get(row.team_id, 0) + row.points
                    team_prizes[row.team_id] = team_prizes.get(row.team_id, 0) + race_prize_usd(
                        row.position
                    )
    for car in state.cars + state.dnfs:
        compounds.update(compound.value for compound in car.compounds_used)
    return RaceRecord(
        season=season,
        round=round_number,
        circuit_code=circuit.code,
        dnf_count=dnf_count,
        overtake_count=overtake_count,
        safety_cars=safety_cars,
        vscs=vscs,
        rained=rained,
        driver_points=driver_points,
        team_points=team_points,
        stops_by_driver=dict(stops),
        compounds_used=tuple(sorted(compounds)),
        team_prizes=team_prizes,
    )


def simulate(seasons: int, seed: int) -> SimulationResult:
    """Simula N stagioni complete e raccoglie le misure per il report.

    Accanto alle gare gira l'economia delle squadre AI (FOR-26): Sponsor
    annuale, Premi gara, stipendi e decisioni di spesa con le stesse API
    del giocatore. Le consegne aggiornano la copia economica delle
    squadre; la griglia di gara resta quella generata (il feedback
    prestazionale dello sviluppo sul passo e' una taratura futura:
    l'harness misura, non corregge).
    """
    if seasons < 1:
        raise ValueError("seasons must be at least 1")
    world = generate(seed, WorldConfig())
    entries = build_grid(seed)
    races: list[RaceRecord] = []
    spending: list[TeamSpendingRecord] = []
    for season in range(1, seasons + 1):
        season_records = []
        for circuit in CALENDAR_2026:
            record = _simulate_race(entries, circuit, season, circuit.calendar_order, seed)
            races.append(record)
            season_records.append(record)
        spending.extend(_simulate_season_spending(world, season, seed, season_records))
    performance = {
        entry.driver.id: 0.75 * _average_car_score(entry) + 0.25 * entry.driver.race_pace
        for entry in entries
    }
    team_of_driver = {entry.driver.id: entry.team_id for entry in entries}
    return SimulationResult(
        seasons=seasons,
        seed=seed,
        races=tuple(races),
        performance_by_driver=performance,
        team_of_driver=team_of_driver,
        spending=tuple(spending),
    )


def _simulate_season_spending(world, season, seed, records) -> list[TeamSpendingRecord]:
    """L'anno economico delle squadre AI, intrecciato con le gare giocate.

    Per ogni squadra: Sponsor annuale a inizio stagione, poi gara per
    gara consegne dell'intervallo, una decisione di spesa, Premio gara
    incassato e rata stipendi. Tutte le regole passano dalle API del
    giocatore (fm_engine.ai.spending).
    """
    rng = Random(f"ai-spending:{seed}:{season}")
    states = {}
    for team in world.ai_teams:
        state = initial_ai_state(team)
        ledger = credit_annual_sponsor(state.ledger, int(team.prestige), date(2026, 1, 1))
        states[team.id] = replace(state, ledger=ledger)
    previous_date = None
    for record in records:
        circuit = CALENDAR_2026[record.round - 1]
        race_date = circuit.race_date_2026
        for team in world.ai_teams:
            state = states[team.id]
            if previous_date is not None:
                state, _ = advance_ai_interval(state, previous_date, race_date, rng)
            state = decide_spending(state, race_date, rng)
            ledger = state.ledger
            prize = record.team_prizes.get(team.id, 0)
            if prize:
                ledger = ledger.record(
                    Transaction(
                        kind=TransactionKind.RACE_PRIZE,
                        amount_usd=prize,
                        game_date=race_date,
                        description=circuit.name,
                    )
                )
            ledger = charge_salary_instalments(ledger, world.contracts_of(team.id), race_date)
            states[team.id] = replace(state, ledger=ledger)
        previous_date = race_date
    season_spending: list[TeamSpendingRecord] = []
    for team in world.ai_teams:
        state = states[team.id]
        spend_by_attribute: dict[str, int] = {}
        for project in state.projects:
            spend_by_attribute[project.attribute] = (
                spend_by_attribute.get(project.attribute, 0) + project.cost_usd
            )
        season_spending.append(
            TeamSpendingRecord(
                season=season,
                team_id=team.id,
                profile=team.personality.profile,
                focus=team.personality.focus,
                total_spent_usd=sum(spend_by_attribute.values()),
                spend_by_attribute=spend_by_attribute,
                completed_projects=sum(1 for project in state.projects if not project.in_progress),
                overspend_usd=state.ledger.overspend_usd,
                final_cash_usd=state.ledger.cash_usd,
            )
        )
    return season_spending


def _average_car_score(entry: RaceEntry) -> float:
    attributes = entry.car.as_dict()
    return sum(attributes.values()) / len(attributes)
