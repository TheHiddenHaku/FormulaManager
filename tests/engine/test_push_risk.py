"""Il Push alza misurabilmente il rischio di Errori e Incidenti (FOR-11)."""

from fm_engine.circuits import circuit_by_code
from fm_engine.events import Accident, DriverError
from fm_engine.race import start_race, step
from fm_engine.state import Aggression, DriverOrders, Orders


def _risk_events(entries, aggression: Aggression, races: int) -> int:
    """Errori e Incidenti totali su N gare con la stessa Aggressivita' per tutti."""
    circuit = circuit_by_code("spa")
    orders = Orders(
        drivers={entry.driver.id: DriverOrders(aggression=aggression) for entry in entries}
    )
    total = 0
    for seed in range(races):
        state, _ = start_race(entries, circuit, seed=seed)
        while not state.finished:
            state, events = step(state, orders)
            total += sum(1 for event in events if isinstance(event, DriverError | Accident))
    return total


def test_push_raises_error_and_accident_risk(entry_factory):
    """A parita' di seed di partenza, tutto il campo in Push sbaglia di piu'."""
    entries = entry_factory()
    races = 60
    push_events = _risk_events(entries, Aggression.PUSH, races)
    conserve_events = _risk_events(entries, Aggression.CONSERVE, races)
    assert push_events > conserve_events * 1.3, (
        f"Push {push_events} eventi vs Conserva {conserve_events}: differenza non misurabile"
    )
