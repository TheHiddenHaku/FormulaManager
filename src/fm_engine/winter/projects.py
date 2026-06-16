"""Progetti invernali della vettura (FOR-32).

Investimenti di sviluppo decisi tra la fine di una stagione e l'inizio
della successiva, con un budget dedicato (distinto dal Cap stagionale e
dalla Cassa: e' la dotazione di sviluppo invernale della squadra). Ogni
Progetto invernale punta un Attributo vettura, costa una quota del budget
e consegna un guadagno deterministico in punti attributo: a differenza dei
Progetti in-season (FOR-25, esito con varianza) l'inverno e' tempo di
pianificazione, l'esito e' certo e si applica alla vettura della stagione
nuova prima del primo GP.

Vincoli di dominio:
- Spesa entro il budget invernale: una selezione che lo supera e' rifiutata
  (WinterBudgetExceeded).
- Una squadra Cliente di un Motorista non puo' sviluppare la Potenza motore
  (CustomerEngineLocked, come per i Progetti in-season): quel valore arriva
  dal fornitore.
- Gli effetti si sommano sulla scala 0-100 della vettura, agganciati.

apply_winter_projects(attributes, selection, ...) ritorna gli Attributi
vettura aggiornati: l'effetto e' DAVVERO sulla vettura della stagione
nuova, non solo selezionabile. Motore puro (ADR 0002): la TUI sceglie, qui
si applica.

Tutti i coefficienti vivono in WinterProjectConfig (tarabili, tuning a FOR-34).
"""

from collections.abc import Iterable
from dataclasses import dataclass

from fm_engine.world.models import CAR_ATTRIBUTES

# Scala 0-100 degli Attributi vettura.
_ATTRIBUTE_FLOOR = 0
_ATTRIBUTE_CEILING = 100

# Etichette italiane degli Attributi vettura, per i testi UI (riuso dei
# Progetti in-season, stesso lessico di dominio).
ATTRIBUTE_LABELS = {
    "engine_power": "Potenza motore",
    "downforce": "Carico aerodinamico",
    "aero_efficiency": "Efficienza aerodinamica",
    "mechanical_grip": "Meccanica",
    "tyre_management": "Gestione gomme",
    "reliability": "Affidabilita'",
}


class WinterBudgetExceeded(Exception):
    """La selezione di Progetti invernali supera il budget dedicato."""

    def __init__(self, requested_usd: int, budget_usd: int) -> None:
        self.requested_usd = requested_usd
        self.budget_usd = budget_usd
        super().__init__(
            f"winter projects cost {requested_usd} USD over a budget of {budget_usd} USD"
        )


class CustomerEngineLocked(Exception):
    """Una squadra Cliente non sviluppa la Potenza motore del fornitore."""


@dataclass(frozen=True)
class WinterProjectConfig:
    """Parametri tarabili dei Progetti invernali, niente valori sparsi.

    budget_usd e' la dotazione di sviluppo invernale (distinta da Cap e
    Cassa). cost_per_point_usd e' il costo di un punto attributo: il budget
    di partenza compra circa max_points_per_project punti su piu' Attributi.
    """

    budget_usd: int = 40_000_000
    cost_per_point_usd: int = 4_000_000
    # Punti massimi investibili su un singolo Attributo in un inverno.
    max_points_per_project: int = 6

    def __post_init__(self) -> None:
        if self.budget_usd < 0:
            raise ValueError("budget_usd cannot be negative")
        if self.cost_per_point_usd <= 0:
            raise ValueError("cost_per_point_usd must be positive")
        if self.max_points_per_project < 1:
            raise ValueError("max_points_per_project must be at least 1")


@dataclass(frozen=True)
class WinterProject:
    """La scelta di un Progetto invernale: un Attributo e i punti da comprare.

    points e' il guadagno in punti attributo richiesto; il costo deriva da
    points * cost_per_point_usd della config. L'esito invernale e'
    deterministico (niente varianza): si applica per intero alla vettura.
    """

    attribute: str
    points: int

    def cost_usd(self, config: WinterProjectConfig) -> int:
        """Il costo della scelta: punti per il costo unitario della config."""
        return self.points * config.cost_per_point_usd


def validate_selection(
    selection: Iterable[WinterProject],
    is_engine_customer: bool,
    config: WinterProjectConfig | None = None,
) -> int:
    """Valida una selezione di Progetti invernali e ritorna il costo totale.

    Solleva ValueError per attributo sconosciuto o punti fuori range,
    CustomerEngineLocked se una squadra Cliente punta la Potenza motore,
    WinterBudgetExceeded se il costo totale supera il budget. Il costo
    ritornato e' la somma dei costi delle scelte.
    """
    if config is None:
        config = WinterProjectConfig()
    total = 0
    for project in selection:
        if project.attribute not in CAR_ATTRIBUTES:
            raise ValueError(f"unknown car attribute: {project.attribute!r}")
        if not 1 <= project.points <= config.max_points_per_project:
            raise ValueError(
                f"winter project points must be between 1 and "
                f"{config.max_points_per_project}, got {project.points}"
            )
        if is_engine_customer and project.attribute == "engine_power":
            raise CustomerEngineLocked(
                "a customer team cannot develop the supplier's engine power in winter"
            )
        total += project.cost_usd(config)
    if total > config.budget_usd:
        raise WinterBudgetExceeded(total, config.budget_usd)
    return total


def apply_winter_projects(
    attributes: dict[str, int],
    selection: Iterable[WinterProject],
    is_engine_customer: bool,
    config: WinterProjectConfig | None = None,
) -> dict[str, int]:
    """Applica i Progetti invernali agli Attributi vettura della stagione nuova.

    Valida la selezione (budget, vincolo Cliente, range punti) e somma il
    guadagno di ogni Progetto al rispettivo Attributo, agganciato alla scala
    0-100. Ritorna un dizionario nuovo: gli attributi in ingresso non vengono
    mutati. L'effetto e' conseguente: e' la vettura con cui si correra'.
    """
    if config is None:
        config = WinterProjectConfig()
    selection = tuple(selection)
    validate_selection(selection, is_engine_customer, config)
    updated = dict(attributes)
    for project in selection:
        new_value = updated[project.attribute] + project.points
        updated[project.attribute] = max(_ATTRIBUTE_FLOOR, min(_ATTRIBUTE_CEILING, new_value))
    return updated
