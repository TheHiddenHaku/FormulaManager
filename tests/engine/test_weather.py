"""Meteo: previsione, evoluzione in-sessione, transizioni (FOR-13)."""

from fm_engine.circuits import CALENDAR_2026, circuit_by_code
from fm_engine.events import RainStarted, RainStopped, is_key_event
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.race import start_race, step
from fm_engine.weather import WET_RACE_THRESHOLD, session_forecast

NO_MISFORTUNE = MisfortuneConfig.disabled()


def test_forecast_is_deterministic_and_profile_driven():
    for circuit in CALENDAR_2026:
        first = session_forecast(circuit, seed=42)
        second = session_forecast(circuit, seed=42)
        assert first == second
        assert 0.0 <= first.rain_chance <= 1.0
        assert abs(first.rain_chance - circuit.rain_probability) <= 0.10 + 1e-9
    assert session_forecast(circuit_by_code("spa"), 1) != session_forecast(
        circuit_by_code("spa"), 2
    )


def test_state_exposes_forecast_and_track_conditions(entry_factory):
    entries = entry_factory()
    circuit = circuit_by_code("spa")
    state, _ = start_race(entries, circuit, seed=3)
    assert state.forecast is not None
    assert state.forecast.circuit_code == "spa"
    assert state.rain_intensity == 0.0 and state.track_wetness == 0.0
    for car in state.cars:
        assert car.tyres.compound.is_dry


def _rainy_race(entry_factory, circuit_code: str = "spa", max_seeds: int = 40):
    """La prima gara che vede pioggia: stati per giro ed eventi raccolti."""
    entries = entry_factory()
    circuit = circuit_by_code(circuit_code)
    for seed in range(max_seeds):
        state, _ = start_race(entries, circuit, seed=seed, misfortune=NO_MISFORTUNE)
        states = [state]
        collected = []
        while not state.finished:
            state, events = step(state)
            states.append(state)
            collected.extend(events)
        if any(isinstance(event, RainStarted) for event in collected):
            return states, collected
    raise AssertionError(f"nessuna pioggia a {circuit_code} in {max_seeds} gare")


def test_rain_arrives_wets_the_track_and_dries_after(entry_factory):
    """Transizione completa: asciutto -> bagnato -> asciugatura progressiva."""
    states, events = _rainy_race(entry_factory)
    rain_started = next(e for e in events if isinstance(e, RainStarted))
    assert is_key_event(rain_started)
    assert 0.0 < rain_started.intensity <= 1.0
    wetness_by_lap = [state.track_wetness for state in states]
    assert wetness_by_lap[rain_started.lap - 1] == 0.0
    assert wetness_by_lap[rain_started.lap] > 0.0
    peak = max(wetness_by_lap)
    assert peak > WET_RACE_THRESHOLD
    stopped = [e for e in events if isinstance(e, RainStopped)]
    if stopped:
        assert all(is_key_event(e) for e in stopped)
        last_stop = stopped[-1].lap
        tail = wetness_by_lap[last_stop:]
        if len(tail) > 2 and states[-1].rain_intensity == 0.0:
            assert tail[-1] < tail[0], "la pista deve asciugarsi quando smette"
    assert states[-1].saw_rain


def test_weather_is_deterministic(entry_factory):
    entries = entry_factory()
    circuit = circuit_by_code("spa")

    def weather_trace(seed: int) -> list[tuple[float, float]]:
        state, _ = start_race(entries, circuit, seed=seed, misfortune=NO_MISFORTUNE)
        trace = []
        while not state.finished:
            state, _ = step(state)
            trace.append((state.rain_intensity, state.track_wetness))
        return trace

    assert weather_trace(7) == weather_trace(7)


def test_wet_race_disables_bi_compound_penalty(entry_factory):
    """Se la pista si bagna, l'obbligo bi-mescola decade."""
    from fm_engine.events import BiCompoundPenalty, ChequeredFlag

    states, events = _rainy_race(entry_factory)
    assert states[-1].saw_rain
    flag = next(e for e in events if isinstance(e, ChequeredFlag))
    assert all(row.penalty_seconds == 0.0 for row in flag.classification)
    assert not [e for e in events if isinstance(e, BiCompoundPenalty)]
