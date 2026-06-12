"""VSC: distacchi congelati e sconto pit ridotto (FOR-12)."""

from fm_engine.circuits import circuit_by_code
from fm_engine.events import (
    Overtake,
    PitExit,
    VscDeployed,
    VscEnding,
    is_key_event,
)
from fm_engine.neutralization import (
    SAFETY_CAR_PIT_DISCOUNT,
    VSC_PIT_DISCOUNT,
    RaceRegime,
)
from fm_engine.pitstop import PIT_STOP_BASE_SECONDS
from fm_engine.race import start_race, step
from fm_engine.state import DriverOrders, Orders, PitOrder
from fm_engine.tyres import CompoundSlot, nominated_compounds


def _race_until_vsc(entry_factory, max_seeds: int = 120):
    """La prima gara che vede un VSC, fermata al deploy."""
    entries = entry_factory()
    circuit = circuit_by_code("jeddah")
    for seed in range(max_seeds):
        state, _ = start_race(entries, circuit, seed=seed)
        while not state.finished:
            state, events = step(state)
            deployed = [e for e in events if isinstance(e, VscDeployed)]
            if deployed:
                return state, deployed[0]
    raise AssertionError(f"nessun VSC a Jeddah in {max_seeds} gare")


def test_vsc_deploys_and_is_a_key_event(entry_factory):
    state, deployed = _race_until_vsc(entry_factory)
    assert is_key_event(deployed)
    assert state.regime is RaceRegime.VSC
    assert state.regime_laps_remaining == deployed.duration_laps > 0


def test_vsc_freezes_the_gaps(entry_factory):
    state, _ = _race_until_vsc(entry_factory)
    gaps_before = {car.entry.driver.id: car.gap_to_leader_seconds for car in state.cars}
    state, events = step(state)
    assert not [e for e in events if isinstance(e, Overtake)]
    for car in state.cars:
        assert abs(car.gap_to_leader_seconds - gaps_before[car.entry.driver.id]) < 1e-9


def test_pit_under_vsc_costs_more_than_under_safety_car():
    assert VSC_PIT_DISCOUNT > SAFETY_CAR_PIT_DISCOUNT


def test_pit_under_vsc_is_discounted_but_less(entry_factory):
    state, _ = _race_until_vsc(entry_factory)
    leader_id = state.cars[0].entry.driver.id
    soft = nominated_compounds(state.circuit)[CompoundSlot.SOFT]
    orders = Orders(drivers={leader_id: DriverOrders(pit=PitOrder(compound=soft))})
    _, events = step(state, orders)
    pit_exit = next(e for e in events if isinstance(e, PitExit))
    assert pit_exit.time_lost_seconds < PIT_STOP_BASE_SECONDS
    assert (
        pit_exit.time_lost_seconds
        > PIT_STOP_BASE_SECONDS * (SAFETY_CAR_PIT_DISCOUNT + VSC_PIT_DISCOUNT) / 2 - 3
    )


def test_vsc_ends_without_restart_window(entry_factory):
    state, _ = _race_until_vsc(entry_factory)
    while state.regime is RaceRegime.VSC and not state.finished:
        state, events = step(state)
    ending = [e for e in events if isinstance(e, VscEnding)]
    assert len(ending) == 1 and is_key_event(ending[0])
    assert state.regime is RaceRegime.GREEN
    assert state.restart_risk_laps_remaining == 0
