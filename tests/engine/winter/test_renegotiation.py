"""Rinegoziazione delle scelte di fondo all'inverno (FOR-32).

Motore proprio vs Cliente di un Motorista e Filosofia telaio sono
rinegoziabili e i loro effetti valgono per la stagione nuova: cambiare
Filosofia ribilancia gli attributi (niente accumulo), cambiare fornitore
rimette la Potenza motore.
"""

import pytest

from fm_engine.winter.renegotiation import (
    RenegotiationChoices,
    apply_renegotiation,
)
from fm_engine.world.models import CAR_ATTRIBUTES, EngineSupplier
from fm_engine.world.team_setup import TeamSetupConfig

_CONFIG = TeamSetupConfig(chassis_bonus=8, chassis_malus=4)
_SUPPLIERS = {
    1: EngineSupplier(id=1, name="Rosso Corse", engine_power=80, customer_fee_usd=15_000_000),
    2: EngineSupplier(id=2, name="Blu Power", engine_power=55, customer_fee_usd=12_000_000),
}


def _baseline() -> dict[str, int]:
    return dict.fromkeys(CAR_ATTRIBUTES, 60)


def test_switching_balanced_to_fast_applies_the_fast_deltas():
    out = apply_renegotiation(
        _baseline(),
        current_philosophy="balanced",
        current_engine_supplier_id=None,
        choices=RenegotiationChoices(engine_supplier_id=None, chassis_philosophy="fast"),
        suppliers=_SUPPLIERS,
        config=_CONFIG,
    )
    assert out["aero_efficiency"] == 68  # +bonus
    assert out["downforce"] == 56  # -malus
    assert out["mechanical_grip"] == 56  # -malus


def test_switching_fast_to_technical_removes_old_and_applies_new():
    # Vettura gia' veloce: aero 68, downforce 56, meccanica 56 (su baseline 60).
    fast_car = {**_baseline(), "aero_efficiency": 68, "downforce": 56, "mechanical_grip": 56}
    out = apply_renegotiation(
        fast_car,
        current_philosophy="fast",
        current_engine_supplier_id=None,
        choices=RenegotiationChoices(engine_supplier_id=None, chassis_philosophy="technical"),
        suppliers=_SUPPLIERS,
        config=_CONFIG,
    )
    # Tolti i delta veloci (torna a 60), applicati i tecnici.
    assert out["aero_efficiency"] == 52  # 60 - bonus
    assert out["downforce"] == 64  # 60 + malus
    assert out["mechanical_grip"] == 64  # 60 + malus


def test_no_philosophy_change_is_a_no_op_on_the_chassis_axes():
    out = apply_renegotiation(
        _baseline(),
        current_philosophy="balanced",
        current_engine_supplier_id=None,
        choices=RenegotiationChoices(engine_supplier_id=None, chassis_philosophy="balanced"),
        suppliers=_SUPPLIERS,
        config=_CONFIG,
    )
    assert out == _baseline()


def test_becoming_a_customer_sets_the_supplier_engine_power():
    out = apply_renegotiation(
        _baseline(),
        current_philosophy="balanced",
        current_engine_supplier_id=None,
        choices=RenegotiationChoices(engine_supplier_id=1, chassis_philosophy="balanced"),
        suppliers=_SUPPLIERS,
        config=_CONFIG,
    )
    assert out["engine_power"] == 80  # Rosso Corse


def test_switching_supplier_changes_the_engine_power():
    customer_car = {**_baseline(), "engine_power": 80}
    out = apply_renegotiation(
        customer_car,
        current_philosophy="balanced",
        current_engine_supplier_id=1,
        choices=RenegotiationChoices(engine_supplier_id=2, chassis_philosophy="balanced"),
        suppliers=_SUPPLIERS,
        config=_CONFIG,
    )
    assert out["engine_power"] == 55  # Blu Power


def test_going_in_house_keeps_the_carried_over_engine_power():
    customer_car = {**_baseline(), "engine_power": 80}
    out = apply_renegotiation(
        customer_car,
        current_philosophy="balanced",
        current_engine_supplier_id=1,
        choices=RenegotiationChoices(engine_supplier_id=None, chassis_philosophy="balanced"),
        suppliers=_SUPPLIERS,
        config=_CONFIG,
    )
    # In proprio: la Potenza motore resta quella ereditata dal Carry-over.
    assert out["engine_power"] == 80


def test_unknown_supplier_is_rejected():
    with pytest.raises(ValueError):
        apply_renegotiation(
            _baseline(),
            current_philosophy="balanced",
            current_engine_supplier_id=None,
            choices=RenegotiationChoices(engine_supplier_id=99, chassis_philosophy="balanced"),
            suppliers=_SUPPLIERS,
            config=_CONFIG,
        )


def test_unknown_philosophy_is_rejected():
    with pytest.raises(ValueError):
        apply_renegotiation(
            _baseline(),
            current_philosophy="balanced",
            current_engine_supplier_id=None,
            choices=RenegotiationChoices(engine_supplier_id=None, chassis_philosophy="sporty"),
            suppliers=_SUPPLIERS,
            config=_CONFIG,
        )
