"""Sfiga: probabilita', Abbandoni e payload degli eventi (FOR-11)."""

from random import Random

from fm_engine.circuits import circuit_by_code
from fm_engine.events import Accident, CarDamage, CarFailure, Dnf, DnfCause, DriverError
from fm_engine.misfortune import (
    ERROR_CAUSES,
    FAILURE_COMPONENTS,
    MisfortuneConfig,
    damage_amount_usd,
    duel_contact_probability,
    error_probability,
    failure_probability,
)
from fm_engine.race import start_race, step
from fm_engine.state import Aggression


def test_failure_probability_is_inverse_of_reliability():
    config = MisfortuneConfig()
    probabilities = [failure_probability(config, reliability) for reliability in (40, 60, 85)]
    assert probabilities == sorted(probabilities, reverse=True)
    assert all(probability > 0 for probability in probabilities)


def test_error_probability_modulation():
    config = MisfortuneConfig()
    assert error_probability(config, 40, Aggression.NORMAL, False) > error_probability(
        config, 90, Aggression.NORMAL, False
    )
    assert error_probability(config, 60, Aggression.PUSH, False) > error_probability(
        config, 60, Aggression.NORMAL, False
    )
    assert error_probability(config, 60, Aggression.CONSERVE, False) < error_probability(
        config, 60, Aggression.NORMAL, False
    )
    assert error_probability(config, 60, Aggression.NORMAL, True) > error_probability(
        config, 60, Aggression.NORMAL, False
    )


def test_duel_contact_probability_modulation():
    config = MisfortuneConfig()
    assert duel_contact_probability(config, Aggression.PUSH) > duel_contact_probability(
        config, Aggression.NORMAL
    )
    assert duel_contact_probability(config, Aggression.CONSERVE) < duel_contact_probability(
        config, Aggression.NORMAL
    )


def test_damage_amounts_have_a_payload_entity():
    config = MisfortuneConfig()
    rng = Random(1)
    minor = damage_amount_usd(config, severe=False, rng=rng)
    major = damage_amount_usd(config, severe=True, rng=rng)
    assert config.minor_damage_usd_range[0] <= minor <= config.minor_damage_usd_range[1]
    assert config.major_damage_usd_range[0] <= major <= config.major_damage_usd_range[1]


def test_disabled_config_means_sterile_race(entry_factory):
    entries = entry_factory()
    state, _ = start_race(
        entries, circuit_by_code("spa"), seed=11, misfortune=MisfortuneConfig.disabled()
    )
    misfortune_events = []
    while not state.finished:
        state, events = step(state)
        misfortune_events.extend(
            e for e in events if isinstance(e, CarFailure | DriverError | Accident | Dnf)
        )
    assert not misfortune_events
    assert not state.dnfs
    assert len(state.cars) == 22


def test_dnf_leaves_the_session_and_the_classification(entry_factory):
    """Trova una gara con Abbandoni e verifica stato, eventi e payload."""
    entries = entry_factory()
    circuit = circuit_by_code("marina_bay")
    for seed in range(30):
        state, _ = start_race(entries, circuit, seed=seed)
        collected = []
        while not state.finished:
            state, events = step(state)
            collected.extend(events)
        dnf_events = [e for e in collected if isinstance(e, Dnf)]
        if not dnf_events:
            continue
        assert len(state.dnfs) == len(dnf_events)
        running_ids = {car.entry.driver.id for car in state.cars}
        for dnf in dnf_events:
            assert dnf.driver_id not in running_ids
            assert dnf.cause in tuple(DnfCause)
            assert dnf.detail in FAILURE_COMPONENTS + ERROR_CAUSES + ("contact",)
            retired_car = state.car_of(dnf.driver_id)
            assert retired_car.position == 0
        damage_events = [e for e in collected if isinstance(e, CarDamage)]
        assert damage_events, "ogni Sfiga grave porta un evento danno"
        assert all(event.amount_usd > 0 for event in damage_events)
        return
    raise AssertionError("nessun Abbandono in 30 gare: probabilita' troppo basse")


def test_dnf_is_effective_from_its_tick(entry_factory):
    """La vettura ritirata sparisce dai runner dal Tick dell'estrazione."""
    entries = entry_factory()
    circuit = circuit_by_code("marina_bay")
    for seed in range(30):
        state, _ = start_race(entries, circuit, seed=seed)
        while not state.finished:
            previous_running = len(state.cars)
            state, events = step(state)
            dnf_events = [e for e in events if isinstance(e, Dnf)]
            if dnf_events:
                assert len(state.cars) == previous_running - len(dnf_events)
                return
    raise AssertionError("nessun Abbandono in 30 gare: probabilita' troppo basse")
