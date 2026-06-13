"""AI di spesa: l'economia delle squadre rivali (FOR-26).

Le 10 squadre AI della Griglia gestiscono Cassa, Cap e Progetti con le
STESSE API del giocatore: TeamLedger (doppio vincolo min(Cassa, Cap
residuo)) e fm_engine.development (stessi costi, massimo 2 Progetti
paralleli, vincolo Cliente sulla Potenza motore). Niente cheating e
niente sconti: una AI povera o al Cap non spende, esattamente come il
giocatore.

Le decisioni sono parametrizzate dalla personalita' di spesa generata
dal Mondo: la propensione decide quanto spesso si investe, la tolleranza
al rischio quanto grande e' l'investimento, il focus (aero / engine /
reliability) quale famiglia di Attributi vettura si privilegia.

I Motoristi produttori sviluppano la Potenza motore per conto proprio:
i frutti si applicano alla Potenza condivisa con tutte le squadre
Clienti (apply_supplier_power).

Motore puro (ADR 0002): nessun import TUI o database.
"""

from dataclasses import dataclass, replace
from datetime import date
from random import Random

from fm_engine.development import (
    MAX_INVESTMENT_USD,
    MAX_PARALLEL_PROJECTS,
    MIN_INVESTMENT_USD,
    Delivery,
    DevelopmentProject,
    active_projects,
    advance_projects,
    apply_delivery,
    start_project,
)
from fm_engine.economy import SpendingBlocked, TeamLedger, Transaction, TransactionKind
from fm_engine.world.models import CAR_ATTRIBUTES, EngineSupplier, Team

# Attribute families favoured by each development focus.
FOCUS_ATTRIBUTES: dict[str, tuple[str, ...]] = {
    "aero": ("downforce", "aero_efficiency"),
    "engine": ("engine_power", "mechanical_grip"),
    "reliability": ("reliability", "tyre_management"),
}

# Investment sizing: share of the allowed spending, scaled by risk
# tolerance. Starting values, tunable.
BASE_INVESTMENT_FRACTION = 0.15
RISK_INVESTMENT_FRACTION = 0.35

# Seasonal engine power gain of a supplier's own development. Tunable.
SUPPLIER_SEASON_GAIN_RANGE = (1, 4)


@dataclass(frozen=True)
class AiTeamState:
    """Lo stato economico di una squadra AI: squadra, registro, Progetti."""

    team: Team
    ledger: TeamLedger
    projects: tuple[DevelopmentProject, ...] = ()


def initial_ai_state(team: Team, season_year: int = 2026) -> AiTeamState:
    """Lo stato di inizio stagione: la Cassa della squadra apre il registro."""
    ledger = TeamLedger(season_year=season_year)
    if team.cash_usd:
        ledger = ledger.record(
            Transaction(
                kind=TransactionKind.OTHER,
                amount_usd=team.cash_usd,
                game_date=date(season_year, 1, 1),
                description="Dotazione di inizio stagione",
            )
        )
    return AiTeamState(team=team, ledger=ledger)


def decide_spending(state: AiTeamState, game_date: date, rng: Random) -> AiTeamState:
    """Una decisione per intervallo: al piu' un nuovo Progetto.

    La propensione della personalita' decide se investire in questo
    intervallo; la tolleranza al rischio dimensiona l'investimento come
    quota della spesa consentita; il focus sceglie l'Attributo (il piu'
    debole della famiglia). Tutti i vincoli passano dalle API del
    giocatore: slot pieni, doppio vincolo e regola Cliente fermano la
    spesa esattamente come per il giocatore.
    """
    personality = state.team.personality
    if len(active_projects(state.projects)) >= MAX_PARALLEL_PROJECTS:
        return state
    if rng.random() > personality.spending_propensity:
        return state
    budget = state.ledger.allowed_spending_usd
    if budget < MIN_INVESTMENT_USD:
        return state
    fraction = BASE_INVESTMENT_FRACTION + RISK_INVESTMENT_FRACTION * personality.risk_tolerance
    investment = int(budget * fraction)
    investment = max(MIN_INVESTMENT_USD, min(investment, MAX_INVESTMENT_USD, budget))
    attribute = _focus_attribute(state.team)
    try:
        ledger, projects = start_project(
            state.ledger,
            state.projects,
            attribute,
            investment,
            game_date,
            is_engine_customer=not state.team.builds_own_engine,
        )
    except SpendingBlocked:
        return state
    return replace(state, ledger=ledger, projects=projects)


def advance_ai_interval(
    state: AiTeamState, from_date: date, to_date: date, rng: Random
) -> tuple[AiTeamState, tuple[Delivery, ...]]:
    """L'intervallo tra due GP per una squadra AI: consegne applicate.

    Le consegne mature aggiornano gli Attributi vettura della squadra
    (stessa apply_delivery del giocatore, clamp 0-100).
    """
    projects, deliveries = advance_projects(state.projects, from_date, to_date, rng)
    team = state.team
    for delivery in deliveries:
        attribute = delivery.project.attribute
        team = replace(team, **{attribute: apply_delivery(getattr(team, attribute), delivery)})
    return replace(state, team=team, projects=projects), deliveries


def develop_supplier_power(supplier: EngineSupplier, rng: Random) -> EngineSupplier:
    """Lo sviluppo stagionale del Motorista sulla sua Potenza motore."""
    low, high = SUPPLIER_SEASON_GAIN_RANGE
    gain = rng.randint(low, high)
    return replace(supplier, engine_power=min(100, supplier.engine_power + gain))


def apply_supplier_power(
    teams: tuple[Team, ...], suppliers: tuple[EngineSupplier, ...]
) -> tuple[Team, ...]:
    """Le squadre Clienti ereditano la Potenza motore del loro Motorista."""
    powers = {supplier.id: supplier.engine_power for supplier in suppliers}
    return tuple(
        team
        if team.engine_supplier_id is None
        else replace(team, engine_power=powers[team.engine_supplier_id])
        for team in teams
    )


def _focus_attribute(team: Team) -> str:
    """L'Attributo bersaglio: il piu' debole della famiglia del focus.

    Una squadra Cliente non puo' puntare la Potenza motore: la famiglia
    si restringe e, se vuota, si ripiega sul piu' debole tra tutti gli
    Attributi sviluppabili.
    """
    pool = FOCUS_ATTRIBUTES.get(team.personality.focus, CAR_ATTRIBUTES)
    if not team.builds_own_engine:
        pool = tuple(attribute for attribute in pool if attribute != "engine_power")
    if not pool:
        pool = tuple(attribute for attribute in CAR_ATTRIBUTES if attribute != "engine_power")
    return min(pool, key=lambda attribute: getattr(team, attribute))
