"""Calendario 2026: sanita' dei dati statici dei circuiti (FOR-8).

Replica in pytest i CHECK della tabella SQL circuits: se i due mirror
(fm_engine.circuits e supabase/seed.sql) divergono nei vincoli, almeno
uno dei due lo segnala.
"""

import pytest

from fm_engine.circuits import CALENDAR_2026, circuit_by_code

DRY_COMPOUNDS = ("C1", "C2", "C3", "C4", "C5")


def test_calendar_has_24_rounds_in_order():
    assert len(CALENDAR_2026) == 24
    assert [circuit.calendar_order for circuit in CALENDAR_2026] == list(range(1, 25))


def test_circuit_codes_are_unique():
    codes = [circuit.code for circuit in CALENDAR_2026]
    assert len(set(codes)) == len(codes)


def test_circuit_values_respect_schema_checks():
    for circuit in CALENDAR_2026:
        assert circuit.length_metres > 0
        assert circuit.race_laps > 0
        assert circuit.weekend_format_2026 in ("standard", "sprint")
        for weight in circuit.attribute_weights.values():
            assert 0.0 <= weight <= 1.0
        assert 1 <= circuit.tyre_severity <= 5
        assert 0.0 <= circuit.safety_car_probability <= 1.0
        assert circuit.weather_profile in ("dry", "variable", "wet")
        assert 0.0 <= circuit.rain_probability <= 1.0


def test_nominated_compounds_are_ordered_hard_to_soft():
    for circuit in CALENDAR_2026:
        hard, medium, soft = circuit.nominated_compounds
        assert hard in DRY_COMPOUNDS and medium in DRY_COMPOUNDS and soft in DRY_COMPOUNDS
        assert hard < medium < soft


def test_circuit_by_code_lookup():
    monaco = circuit_by_code("monaco")
    assert monaco.name == "Circuit de Monaco"
    with pytest.raises(KeyError):
        circuit_by_code("imola")
