"""Safety car: compattamento, sconto pit, ripartenza (FOR-12)."""

from dataclasses import replace

from fm_engine.circuits import circuit_by_code
from fm_engine.events import (
    Accident,
    DriverError,
    Overtake,
    PitExit,
    SafetyCarDeployed,
    SafetyCarEnding,
    is_key_event,
)
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.neutralization import (
    RESTART_RISK_LAPS,
    SAFETY_CAR_PIT_DISCOUNT,
    SAFETY_CAR_QUEUE_GAP_SECONDS,
    RaceRegime,
)
from fm_engine.pitstop import PIT_STOP_BASE_SECONDS
from fm_engine.race import start_race, step
from fm_engine.state import DriverOrders, Orders, PitOrder
from fm_engine.tyres import CompoundSlot, nominated_compounds


def _race_until_safety_car(entry_factory, max_seeds: int = 60):
    """La prima gara a Monaco che vede una Safety car, fermata al deploy."""
    entries = entry_factory()
    circuit = circuit_by_code("monaco")
    for seed in range(max_seeds):
        state, _ = start_race(entries, circuit, seed=seed)
        while not state.finished:
            state, events = step(state)
            deployed = [e for e in events if isinstance(e, SafetyCarDeployed)]
            if deployed:
                return state, deployed[0]
    raise AssertionError(f"nessuna Safety car a Monaco in {max_seeds} gare")


def test_safety_car_deploys_and_is_a_key_event(entry_factory):
    state, deployed = _race_until_safety_car(entry_factory)
    assert is_key_event(deployed)
    assert state.regime is RaceRegime.SAFETY_CAR
    assert state.regime_laps_remaining == deployed.duration_laps > 0


def test_safety_car_compacts_the_field_and_blocks_duels(entry_factory):
    state, _ = _race_until_safety_car(entry_factory)
    state, events = step(state)
    assert not [e for e in events if isinstance(e, Overtake)]
    gaps = [car.gap_to_leader_seconds for car in state.cars]
    expected = [index * SAFETY_CAR_QUEUE_GAP_SECONDS for index in range(len(state.cars))]
    assert gaps == expected


def test_pit_under_safety_car_is_discounted(entry_factory):
    state, _ = _race_until_safety_car(entry_factory)
    leader_id = state.cars[0].entry.driver.id
    soft = nominated_compounds(state.circuit)[CompoundSlot.SOFT]
    orders = Orders(drivers={leader_id: DriverOrders(pit=PitOrder(compound=soft))})
    state, events = step(state, orders)
    pit_exit = next(e for e in events if isinstance(e, PitExit))
    assert pit_exit.time_lost_seconds < PIT_STOP_BASE_SECONDS * (SAFETY_CAR_PIT_DISCOUNT + 0.2)
    # Misurabile dai distacchi: dopo la compattazione chi ha sostato
    # resta in coda al gruppo, non a 20+ secondi come in regime verde.
    pitted_car = state.car_of(leader_id)
    assert pitted_car.gap_to_leader_seconds <= SAFETY_CAR_QUEUE_GAP_SECONDS * len(state.cars)
    assert pitted_car.gap_to_leader_seconds < PIT_STOP_BASE_SECONDS


def test_restart_opens_a_risk_window(entry_factory):
    state, _ = _race_until_safety_car(entry_factory)
    while state.regime is RaceRegime.SAFETY_CAR and not state.finished:
        state, events = step(state)
    ending = [e for e in events if isinstance(e, SafetyCarEnding)]
    assert len(ending) == 1 and is_key_event(ending[0])
    assert state.regime is RaceRegime.GREEN
    assert state.restart_risk_laps_remaining == RESTART_RISK_LAPS


def test_restart_window_raises_risk_comparatively(entry_factory):
    """A parita' di seed, la finestra di ripartenza produce piu' Sfiga."""
    entries = entry_factory()
    circuit = circuit_by_code("monaco")
    base_state, _ = start_race(entries, circuit, seed=5, misfortune=MisfortuneConfig.disabled())
    for _ in range(5):
        base_state, _ = step(base_state)
    loud_config = MisfortuneConfig().scaled(10.0)
    with_window = 0
    without_window = 0
    for seed in range(200):
        for restart_laps, bucket in ((RESTART_RISK_LAPS, "window"), (0, "green")):
            probe = replace(
                base_state,
                seed=seed + 10_000,
                misfortune=loud_config,
                restart_risk_laps_remaining=restart_laps,
            )
            _, events = step(probe)
            count = sum(1 for e in events if isinstance(e, DriverError | Accident))
            if bucket == "window":
                with_window += count
            else:
                without_window += count
    assert with_window > without_window, (with_window, without_window)
