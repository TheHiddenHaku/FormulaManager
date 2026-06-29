"""Strategia gomme delle AI come modulo del motore (FOR-39).

I piani estratti dall'harness restano deterministici e programmano
soste plausibili; una gara pilotata dagli stessi Ordini di pit fa
fermare le vetture ai box e non incassa la penalita' bi-mescola
sull'asciutto.
"""

from random import Random

from fm_engine.circuits import circuit_by_code
from fm_engine.events import BiCompoundPenalty, RainStarted, TyreChange
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.race import start_race, step
from fm_engine.strategy import (
    build_plans,
    lap_orders,
    planned_stop_count,
    varied_starting_compounds,
)
from fm_engine.tyres import CompoundSlot, nominated_compounds

SEED = 4321


def _run_ai_race(entries, circuit, seed):
    """Una gara completa pilotata dalla sola strategia AI (Sfiga spenta)."""
    state, events = start_race(entries, circuit, seed, misfortune=MisfortuneConfig.disabled())
    plans = build_plans(entries, circuit, Random(seed))
    collected = list(events)
    while not state.finished:
        state, tick_events = step(state, lap_orders(state, plans))
        collected.extend(tick_events)
    return state, collected


def test_build_plans_is_deterministic(entry_factory):
    """Stesse iscritte, stesso circuito e stesso RNG: piani identici."""
    entries = entry_factory(count=22, seed=7)
    circuit = circuit_by_code("sakhir")
    first = build_plans(entries, circuit, Random(99))
    second = build_plans(entries, circuit, Random(99))
    assert {driver: plan.pit_laps for driver, plan in first.items()} == {
        driver: plan.pit_laps for driver, plan in second.items()
    }


def test_every_plan_schedules_a_stop_within_bounds(entry_factory):
    """Ogni piano programma almeno una sosta, mai al via o a bandiera."""
    circuit = circuit_by_code("sakhir")
    entries = entry_factory(count=22, seed=7)
    plans = build_plans(entries, circuit, Random(1))
    for entry in entries:
        plan = plans[entry.driver.id]
        assert planned_stop_count(entry, circuit) >= 1
        assert plan.pit_laps, "ogni piano programma almeno una sosta"
        for lap in plan.pit_laps:
            assert 2 <= lap <= circuit.race_laps - 2


def test_ai_race_pits_and_avoids_the_bi_compound_penalty(entry_factory):
    """Sull'asciutto le AI si fermano e rispettano l'obbligo bi-mescola."""
    circuit = circuit_by_code("sakhir")
    entries = entry_factory(count=22, seed=7)
    state, events = _run_ai_race(entries, circuit, seed=SEED)
    assert not any(isinstance(event, RainStarted) for event in events), (
        "il seed scelto deve restare asciutto"
    )
    assert any(isinstance(event, TyreChange) for event in events), "le AI devono fermarsi ai box"
    assert not any(isinstance(event, BiCompoundPenalty) for event in events)
    for car in state.cars:
        dry_compounds = {compound for compound in car.compounds_used if compound.is_dry}
        assert len(dry_compounds) >= 2, car.entry.driver.id


# ---------------------------------------------------------------------------
# Starting compound variation (Strategia Pit Stop)
# ---------------------------------------------------------------------------


def test_varied_starting_compounds_vary_and_avoid_hard(entry_factory):
    """Le gomme di partenza variano tra le vetture e restano Soft o Medium."""
    circuit = circuit_by_code("sakhir")
    entries = entry_factory(count=22, seed=7)
    nominated = nominated_compounds(circuit)
    starts = varied_starting_compounds(entries, circuit, Random(99))
    assert set(starts) == {entry.driver.id for entry in entries}
    allowed = {nominated[CompoundSlot.SOFT], nominated[CompoundSlot.MEDIUM]}
    assert all(compound in allowed for compound in starts.values())
    # Across 22 cars the starts are not all identical.
    assert len(set(starts.values())) > 1


def test_varied_starting_compounds_is_deterministic(entry_factory):
    circuit = circuit_by_code("sakhir")
    entries = entry_factory(count=22, seed=7)
    assert varied_starting_compounds(entries, circuit, Random(5)) == varied_starting_compounds(
        entries, circuit, Random(5)
    )


def test_varied_starts_keep_the_bi_compound_rule(entry_factory):
    """Partenze variate piu' piani AI: niente penalita' bi-mescola sull'asciutto."""
    circuit = circuit_by_code("sakhir")
    entries = entry_factory(count=22, seed=7)
    starts = varied_starting_compounds(entries, circuit, Random(99))
    state, events = start_race(
        entries, circuit, SEED, starting_compounds=starts, misfortune=MisfortuneConfig.disabled()
    )
    collected = list(events)
    plans = build_plans(entries, circuit, Random(SEED))
    while not state.finished:
        state, tick = step(state, lap_orders(state, plans))
        collected.extend(tick)
    assert not any(isinstance(event, RainStarted) for event in collected), (
        "il seed scelto deve restare asciutto"
    )
    assert not any(isinstance(event, BiCompoundPenalty) for event in collected)
