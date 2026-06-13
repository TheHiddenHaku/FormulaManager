"""Progetti di sviluppo in-season della vettura (FOR-25).

Un Progetto punta un Attributo vettura, costa un investimento che esce
dal Cap (registro di FOR-15, via TeamLedger.spend), dura giorni di
calendario reali e consegna un esito con varianza: puo' deludere o
superare le attese. Regole di gioco: massimo 2 Progetti paralleli; una
squadra Cliente di un Motorista non puo' sviluppare la Potenza motore.

L'avanzamento segue il calendario di gioco: advance_projects porta i
Progetti dalla data di un GP alla successiva e consegna quelli maturati
(esito estratto dall'rng del chiamante, deterministico per transizione).
Con le spese facoltative bloccate (FOR-24) i Progetti sono sospesi: la
data di avvio slitta in avanti dell'intervallo, cosi' la sospensione
sopravvive allo schema (start_date + duration_days, nessuna colonna di
avanzamento).

Motore puro (ADR 0002): la persistenza vive in fm_persistence.development.
"""

from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import Enum
from random import Random

from fm_engine.economy.ledger import TeamLedger, TransactionKind
from fm_engine.world.models import CAR_ATTRIBUTES

# Game rule: at most 2 parallel projects.
MAX_PARALLEL_PROJECTS = 2

# Real calendar days from start to delivery. Starting value, tunable.
PROJECT_DURATION_DAYS = 42

# Investment bounds. Tunable.
MIN_INVESTMENT_USD = 4_000_000
MAX_INVESTMENT_USD = 40_000_000

# Expected attribute points per invested dollar: 1 point every $4M.
INVESTMENT_PER_POINT_USD = 4_000_000

# Outcome variance: multiplier range around the expected gain. Mean 1.0,
# below = the department disappoints, above = it exceeds expectations.
OUTCOME_FACTOR_RANGE = (0.3, 1.7)

# Italian labels of the car attributes, for the delivery news.
_ATTRIBUTE_LABELS = {
    "engine_power": "Potenza motore",
    "downforce": "Carico aerodinamico",
    "aero_efficiency": "Efficienza aerodinamica",
    "mechanical_grip": "Meccanica",
    "tyre_management": "Gestione gomme",
    "reliability": "Affidabilita'",
}


class ProjectLimitReached(Exception):
    """Terzo Progetto rifiutato: massimo 2 paralleli, regola di gioco."""


class CustomerEngineLocked(Exception):
    """Una squadra Cliente non sviluppa la Potenza motore del fornitore."""


class ProjectStatus(Enum):
    """Lo stato di un Progetto, allineato al CHECK di development_projects."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True)
class DevelopmentProject:
    """Un Progetto di sviluppo su un Attributo vettura."""

    attribute: str
    cost_usd: int
    start_date: date
    duration_days: int = PROJECT_DURATION_DAYS
    status: ProjectStatus = ProjectStatus.IN_PROGRESS
    # Delta applied to the attribute on completion (variance, can be 0).
    # None while the project is in progress.
    outcome: int | None = None

    @property
    def delivery_date(self) -> date:
        """La data di consegna stimata: avvio piu' durata."""
        return self.start_date + timedelta(days=self.duration_days)

    @property
    def in_progress(self) -> bool:
        return self.status is ProjectStatus.IN_PROGRESS

    @property
    def expected_gain(self) -> int:
        """L'effetto atteso dall'investimento, in punti attributo."""
        return expected_gain_points(self.cost_usd)


@dataclass(frozen=True)
class Delivery:
    """Una consegna: il Progetto completato e la Notizia per il giocatore."""

    project: DevelopmentProject
    news: str


def expected_gain_points(investment_usd: int) -> int:
    """I punti attributo attesi per l'investimento: 1 ogni $4M, almeno 1."""
    return max(1, round(investment_usd / INVESTMENT_PER_POINT_USD))


def active_projects(projects: tuple[DevelopmentProject, ...]) -> tuple[DevelopmentProject, ...]:
    """I soli Progetti in corso (gli slot occupati)."""
    return tuple(project for project in projects if project.in_progress)


def start_project(
    ledger: TeamLedger,
    projects: tuple[DevelopmentProject, ...],
    attribute: str,
    investment_usd: int,
    start_date: date,
    is_engine_customer: bool,
    duration_days: int = PROJECT_DURATION_DAYS,
) -> tuple[TeamLedger, tuple[DevelopmentProject, ...]]:
    """Avvia un Progetto: investimento dal Cap, slot e vincolo Cliente.

    Solleva ProjectLimitReached al terzo Progetto parallelo,
    CustomerEngineLocked se una squadra Cliente punta la Potenza motore,
    SpendingBlocked (da TeamLedger.spend) oltre min(Cassa, Cap residuo),
    ValueError per attributo o investimento fuori range.
    """
    if attribute not in CAR_ATTRIBUTES:
        raise ValueError(f"unknown car attribute: {attribute!r}")
    if not MIN_INVESTMENT_USD <= investment_usd <= MAX_INVESTMENT_USD:
        raise ValueError(
            f"investment must be between {MIN_INVESTMENT_USD} and "
            f"{MAX_INVESTMENT_USD} USD, got {investment_usd}"
        )
    if is_engine_customer and attribute == "engine_power":
        raise CustomerEngineLocked("a customer team cannot develop the supplier's engine power")
    if len(active_projects(projects)) >= MAX_PARALLEL_PROJECTS:
        raise ProjectLimitReached(f"at most {MAX_PARALLEL_PROJECTS} parallel projects")
    ledger = ledger.spend(
        TransactionKind.DEVELOPMENT_PROJECT,
        investment_usd,
        start_date,
        description=f"Progetto: {_ATTRIBUTE_LABELS[attribute]}",
    )
    project = DevelopmentProject(
        attribute=attribute,
        cost_usd=investment_usd,
        start_date=start_date,
        duration_days=duration_days,
    )
    return ledger, (*projects, project)


def advance_projects(
    projects: tuple[DevelopmentProject, ...],
    from_date: date,
    to_date: date,
    rng: Random,
    suspended: bool = False,
) -> tuple[tuple[DevelopmentProject, ...], tuple[Delivery, ...]]:
    """Porta i Progetti avanti col calendario, consegnando i maturati.

    Squadra sospesa (FOR-24): nessun avanzamento, la data di avvio dei
    Progetti in corso slitta dell'intervallo. Altrimenti ogni Progetto
    in corso con consegna entro to_date viene completato: l'esito e'
    l'effetto atteso moltiplicato per un fattore estratto dall'rng
    (sotto o sopra le attese), e produce la Notizia.
    """
    if to_date < from_date:
        raise ValueError(f"cannot advance backwards: {from_date} -> {to_date}")
    if suspended:
        interval = (to_date - from_date).days
        shifted = tuple(
            replace(project, start_date=project.start_date + timedelta(days=interval))
            if project.in_progress
            else project
            for project in projects
        )
        return shifted, ()

    advanced: list[DevelopmentProject] = []
    deliveries: list[Delivery] = []
    for project in projects:
        if not project.in_progress or project.delivery_date > to_date:
            advanced.append(project)
            continue
        low, high = OUTCOME_FACTOR_RANGE
        outcome = round(project.expected_gain * rng.uniform(low, high))
        completed = replace(project, status=ProjectStatus.COMPLETED, outcome=outcome)
        advanced.append(completed)
        deliveries.append(Delivery(project=completed, news=_delivery_news(completed)))
    return tuple(advanced), tuple(deliveries)


def apply_delivery(value: int, delivery: Delivery) -> int:
    """Il nuovo valore dell'Attributo vettura dopo la consegna (scala 0-100)."""
    outcome = delivery.project.outcome
    assert outcome is not None  # guaranteed by advance_projects
    return max(0, min(100, value + outcome))


def _delivery_news(project: DevelopmentProject) -> str:
    """La Notizia di consegna, da template parametrico (ADR 0003)."""
    label = _ATTRIBUTE_LABELS[project.attribute]
    outcome = project.outcome or 0
    if outcome > project.expected_gain:
        verdict = "il reparto supera le attese"
    elif outcome < project.expected_gain:
        verdict = "il reparto delude le attese"
    else:
        verdict = "il reparto centra l'obiettivo"
    return f"Consegna dello sviluppo su {label}: {verdict} (+{outcome} punti)."
