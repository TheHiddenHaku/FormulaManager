"""Rinegoziazione delle scelte di fondo, ogni inverno (FOR-32).

Le due scelte di progetto prese alla creazione della squadra (FOR-7) sono
rinegoziabili all'inverno e i loro effetti valgono per la stagione nuova:

- Motore: in proprio (sviluppo libero) oppure Cliente di un Motorista
  (Potenza motore del fornitore, condivisa). Cambiare fornitore o passare
  a/da motore proprio rimette la Potenza motore al valore della nuova
  scelta: il fornitore la impone, il motore proprio la lascia a quella
  ereditata dal Carry-over.
- Filosofia telaio: veloce / equilibrata / tecnica, che sbilancia
  aero_efficiency, downforce e mechanical_grip. La rinegoziazione toglie i
  delta della Filosofia vecchia e applica quelli della nuova, cosi' il
  cambio e' davvero un cambio di carattere della vettura e non un accumulo.

apply_renegotiation(...) ritorna gli Attributi vettura aggiornati e i nuovi
campi di scelta (engine_supplier_id, chassis_philosophy). Riusa i delta di
Filosofia di fm_engine.world.team_setup (stessa TeamSetupConfig) per non
duplicare la regola. Motore puro (ADR 0002): la TUI sceglie, qui si applica.

Default dichiarato: senza rinegoziazione le scelte restano quelle dell'anno
concluso (nessun cambio). E' il caso DEFAULT della transizione di stagione.
"""

from dataclasses import dataclass

from fm_engine.world.models import (
    CHASSIS_PHILOSOPHIES,
    EngineSupplier,
)
from fm_engine.world.team_setup import TeamSetupConfig

# Scala 0-100 degli Attributi vettura.
_ATTRIBUTE_FLOOR = 0
_ATTRIBUTE_CEILING = 100


@dataclass(frozen=True)
class RenegotiationChoices:
    """Le scelte di fondo rinegoziate per la stagione nuova.

    engine_supplier_id None = motore in proprio; valorizzato = Cliente del
    Motorista indicato. chassis_philosophy e' una di CHASSIS_PHILOSOPHIES.
    """

    engine_supplier_id: int | None
    chassis_philosophy: str


def _philosophy_deltas(philosophy: str, config: TeamSetupConfig) -> dict[str, int]:
    """I delta di una Filosofia telaio sui 3 Attributi che sbilancia.

    Stessa regola di team_setup.initial_car_attributes: veloce = bonus su
    aero_efficiency, malus su downforce e mechanical_grip; tecnica =
    l'inverso; equilibrata = nessun delta.
    """
    if philosophy not in CHASSIS_PHILOSOPHIES:
        raise ValueError(
            f"unknown chassis philosophy {philosophy!r}: expected one of {CHASSIS_PHILOSOPHIES}"
        )
    if philosophy == "fast":
        return {
            "aero_efficiency": config.chassis_bonus,
            "downforce": -config.chassis_malus,
            "mechanical_grip": -config.chassis_malus,
        }
    if philosophy == "technical":
        return {
            "aero_efficiency": -config.chassis_bonus,
            "downforce": config.chassis_malus,
            "mechanical_grip": config.chassis_malus,
        }
    return {}


def _clamp(value: int) -> int:
    return max(_ATTRIBUTE_FLOOR, min(_ATTRIBUTE_CEILING, value))


def apply_renegotiation(
    attributes: dict[str, int],
    current_philosophy: str,
    current_engine_supplier_id: int | None,
    choices: RenegotiationChoices,
    suppliers: dict[int, EngineSupplier],
    config: TeamSetupConfig | None = None,
) -> dict[str, int]:
    """Applica le scelte rinegoziate e ritorna gli Attributi vettura nuovi.

    Toglie i delta della Filosofia vecchia, applica quelli della nuova, e
    rimette la Potenza motore secondo il motore scelto: quella del Motorista
    se Cliente, quella ereditata dal Carry-over se in proprio. Solleva
    ValueError per Filosofia o Motorista sconosciuti. Non muta il dizionario
    in ingresso.
    """
    if config is None:
        config = TeamSetupConfig()
    if choices.chassis_philosophy not in CHASSIS_PHILOSOPHIES:
        raise ValueError(
            f"unknown chassis philosophy {choices.chassis_philosophy!r}: "
            f"expected one of {CHASSIS_PHILOSOPHIES}"
        )
    updated = dict(attributes)

    # Filosofia telaio: rimuovi i delta vecchi, applica i nuovi.
    old_deltas = _philosophy_deltas(current_philosophy, config)
    new_deltas = _philosophy_deltas(choices.chassis_philosophy, config)
    for attribute in ("aero_efficiency", "downforce", "mechanical_grip"):
        value = updated[attribute] - old_deltas.get(attribute, 0) + new_deltas.get(attribute, 0)
        updated[attribute] = _clamp(value)

    # Motore: Cliente -> Potenza motore del fornitore; in proprio -> quella
    # ereditata dal Carry-over (nessun cambio dal Carry-over).
    if choices.engine_supplier_id is not None:
        supplier = suppliers.get(choices.engine_supplier_id)
        if supplier is None:
            raise ValueError(f"unknown engine supplier id {choices.engine_supplier_id}")
        updated["engine_power"] = _clamp(supplier.engine_power)

    return updated
