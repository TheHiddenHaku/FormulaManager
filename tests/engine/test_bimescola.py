"""Obbligo bi-mescola in gara asciutta: penalita' in classifica (FOR-10)."""

from test_race_base import _entry

from fm_engine.circuits import circuit_by_code
from fm_engine.events import BiCompoundPenalty, ChequeredFlag
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.race import BI_COMPOUND_PENALTY_SECONDS, start_race, step
from fm_engine.state import DriverOrders, Orders, PitOrder
from fm_engine.tyres import CompoundSlot, nominated_compounds

NO_MISFORTUNE = MisfortuneConfig.disabled()


def _run_with_pit_plan(circuit_code: str, seed: int, pit_for: dict[int, Orders]):
    circuit = circuit_by_code(circuit_code)
    entries = (_entry(1, team_id=1, strength=70), _entry(2, team_id=2, strength=70))
    state, _ = start_race(entries, circuit, seed=seed, misfortune=NO_MISFORTUNE)
    collected = []
    while not state.finished:
        state, events = step(state, pit_for.get(state.lap + 1))
        collected.extend(events)
    return state, collected


def _chequered_flag(events) -> ChequeredFlag:
    return next(event for event in events if isinstance(event, ChequeredFlag))


def test_single_compound_race_is_penalized():
    """Nessuna sosta: tutti penalizzati di 30s in classifica."""
    state, events = _run_with_pit_plan("sakhir", seed=3, pit_for={})
    penalties = [event for event in events if isinstance(event, BiCompoundPenalty)]
    assert {event.driver_id for event in penalties} == {1, 2}
    assert all(event.penalty_seconds == BI_COMPOUND_PENALTY_SECONDS for event in penalties)
    classification = _chequered_flag(events).classification
    assert all(row.penalty_seconds == BI_COMPOUND_PENALTY_SECONDS for row in classification)
    for row in classification:
        car = state.car_of(row.driver_id)
        assert row.total_time_seconds == car.total_time_seconds + BI_COMPOUND_PENALTY_SECONDS


def test_two_compounds_clear_the_rule():
    circuit = circuit_by_code("sakhir")
    soft = nominated_compounds(circuit)[CompoundSlot.SOFT]
    pit_plan = {
        28: Orders(
            drivers={
                1: DriverOrders(pit=PitOrder(compound=soft)),
                2: DriverOrders(pit=PitOrder(compound=soft)),
            }
        )
    }
    _, events = _run_with_pit_plan("sakhir", seed=3, pit_for=pit_plan)
    assert not [event for event in events if isinstance(event, BiCompoundPenalty)]
    classification = _chequered_flag(events).classification
    assert all(row.penalty_seconds == 0.0 for row in classification)


def test_same_compound_stop_does_not_clear_the_rule():
    """Sostare senza cambiare tipo di Mescola non soddisfa l'obbligo."""
    circuit = circuit_by_code("sakhir")
    medium = nominated_compounds(circuit)[CompoundSlot.MEDIUM]
    pit_plan = {28: Orders(drivers={1: DriverOrders(pit=PitOrder(compound=medium))})}
    _, events = _run_with_pit_plan("sakhir", seed=3, pit_for=pit_plan)
    penalized = {event.driver_id for event in events if isinstance(event, BiCompoundPenalty)}
    assert penalized == {1, 2}


def test_penalty_can_flip_the_classification():
    """Il furbo che salta la sosta vince in pista ma perde in classifica."""
    circuit = circuit_by_code("monaco")
    soft = nominated_compounds(circuit)[CompoundSlot.SOFT]
    pit_plan = {74: Orders(drivers={2: DriverOrders(pit=PitOrder(compound=soft))})}
    state, events = _run_with_pit_plan("monaco", seed=6, pit_for=pit_plan)
    classification = _chequered_flag(events).classification
    on_track_leader = state.cars[0].entry.driver.id
    classified_winner = classification[0].driver_id
    assert on_track_leader == 1
    assert classified_winner == 2
    assert classification[1].penalty_seconds == BI_COMPOUND_PENALTY_SECONDS
