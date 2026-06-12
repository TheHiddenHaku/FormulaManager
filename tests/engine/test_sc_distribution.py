"""Distribuzione delle Safety car per circuito e determinismo (FOR-12)."""

from fm_engine.circuits import circuit_by_code
from fm_engine.events import SafetyCarDeployed, VscDeployed
from fm_engine.race import start_race, step


def _neutralization_laps(entries, circuit_code: str, seed: int) -> list[tuple[str, int]]:
    """La sequenza (tipo, giro) delle neutralizzazioni di una gara."""
    circuit = circuit_by_code(circuit_code)
    state, _ = start_race(entries, circuit, seed=seed)
    sequence = []
    while not state.finished:
        state, events = step(state)
        for event in events:
            if isinstance(event, SafetyCarDeployed):
                sequence.append(("sc", event.lap))
            elif isinstance(event, VscDeployed):
                sequence.append(("vsc", event.lap))
    return sequence


def _safety_car_races(entries, circuit_code: str, races: int) -> int:
    """In quante gare su N e' uscita almeno una Safety car."""
    count = 0
    for seed in range(races):
        sequence = _neutralization_laps(entries, circuit_code, seed)
        if any(kind == "sc" for kind, _ in sequence):
            count += 1
    return count


def test_high_probability_circuits_see_more_safety_cars(entry_factory):
    """Monaco e Baku (profilo alto) vedono piu' SC di Barcellona (profilo basso)."""
    entries = entry_factory()
    races = 80
    monaco = _safety_car_races(entries, "monaco", races)
    baku = _safety_car_races(entries, "baku", races)
    barcellona = _safety_car_races(entries, "barcellona", races)
    assert monaco > barcellona, (monaco, barcellona)
    assert baku > barcellona, (baku, barcellona)


def test_neutralization_sequence_is_deterministic(entry_factory):
    """Stesso seed, stessa sequenza di neutralizzazioni (giri e tipi)."""
    entries = entry_factory()
    for seed in (3, 7, 21):
        first = _neutralization_laps(entries, "monaco", seed)
        second = _neutralization_laps(entries, "monaco", seed)
        assert first == second
