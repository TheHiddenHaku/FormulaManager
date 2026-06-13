"""Test dell'AI di spesa (FOR-26).

Le squadre AI usano le stesse API economiche e di Progetto del
giocatore: stessi costi, doppio vincolo, massimo 2 paralleli, vincolo
Cliente. Le personalita' producono allocazioni distinguibili a parita'
di seed; i Motoristi sviluppano la Potenza condivisa coi Clienti.
"""

from dataclasses import replace
from datetime import date, timedelta
from random import Random

from fm_engine.ai import (
    AiTeamState,
    advance_ai_interval,
    apply_supplier_power,
    decide_spending,
    develop_supplier_power,
    initial_ai_state,
)
from fm_engine.development import MAX_PARALLEL_PROJECTS, PROJECT_DURATION_DAYS, active_projects
from fm_engine.economy import TransactionKind
from fm_engine.world.models import EngineSupplier, SpendingPersonality, Team

GAME_DATE = date(2026, 3, 8)

AGGRESSIVE = SpendingPersonality(
    profile="aggressive", spending_propensity=1.0, risk_tolerance=0.9, focus="aero"
)
CAUTIOUS = SpendingPersonality(
    profile="cautious", spending_propensity=0.2, risk_tolerance=0.1, focus="aero"
)


def _team(personality: SpendingPersonality, cash_usd: int = 60_000_000, customer: bool = False):
    return Team(
        id=1,
        name="Rivale",
        prestige=50,
        cash_usd=cash_usd,
        chassis_philosophy="balanced",
        engine_supplier_id=7 if customer else None,
        engine_power=60,
        downforce=55,
        aero_efficiency=50,
        mechanical_grip=65,
        tyre_management=70,
        reliability=75,
        personality=personality,
    )


def _run_season(state: AiTeamState, rng: Random, intervals: int = 24) -> AiTeamState:
    """Una stagione di sole decisioni: un intervallo ogni due settimane."""
    current = GAME_DATE
    for _ in range(intervals):
        following = current + timedelta(days=14)
        state, _ = advance_ai_interval(state, current, following, rng)
        state = decide_spending(state, following, rng)
        current = following
    return state


def test_decisions_use_the_player_apis_and_limits():
    state = initial_ai_state(_team(AGGRESSIVE, cash_usd=200_000_000))
    state = _run_season(state, Random(7))
    # Mai oltre i 2 slot, spesa sempre registrata con causale Progetto.
    assert len(active_projects(state.projects)) <= MAX_PARALLEL_PROJECTS
    spent = [e for e in state.ledger.entries if e.kind is TransactionKind.DEVELOPMENT_PROJECT]
    assert spent, "una AI aggressiva con Cassa piena non puo' restare a spesa zero"
    assert all(entry.counts_against_cap for entry in spent)
    assert state.ledger.cap_remaining_usd >= 0  # mai oltre il Cap: spend() rifiuta


def test_poor_team_does_not_spend():
    state = initial_ai_state(_team(AGGRESSIVE, cash_usd=1_000_000))
    state = _run_season(state, Random(7))
    assert state.projects == ()


def test_profiles_produce_distinguishable_allocations():
    """A parita' di seed e squadra, aggressiva e prudente spendono diverso."""
    aggressive = _run_season(initial_ai_state(_team(AGGRESSIVE)), Random(11))
    cautious = _run_season(initial_ai_state(_team(CAUTIOUS)), Random(11))
    spent_aggressive = sum(p.cost_usd for p in aggressive.projects)
    spent_cautious = sum(p.cost_usd for p in cautious.projects)
    assert spent_aggressive > spent_cautious


def test_focus_targets_its_attribute_family():
    """Focus diversi puntano famiglie di Attributi diverse."""
    aero = _run_season(initial_ai_state(_team(replace(AGGRESSIVE, focus="aero"))), Random(11))
    reliability = _run_season(
        initial_ai_state(_team(replace(AGGRESSIVE, focus="reliability"))), Random(11)
    )
    assert {p.attribute for p in aero.projects} <= {"downforce", "aero_efficiency"}
    assert {p.attribute for p in reliability.projects} <= {"reliability", "tyre_management"}


def test_customer_never_develops_the_engine_power():
    """Una Cliente con focus engine ripiega senza mai puntare la Potenza."""
    customer = _team(replace(AGGRESSIVE, focus="engine"), customer=True)
    state = _run_season(initial_ai_state(customer), Random(11))
    assert state.projects, "il focus engine di una Cliente deve ripiegare, non fermarsi"
    assert all(p.attribute != "engine_power" for p in state.projects)


def test_deliveries_update_the_team_attributes():
    state = initial_ai_state(_team(AGGRESSIVE))
    state = decide_spending(state, GAME_DATE, Random(3))
    assert state.projects
    attribute = state.projects[0].attribute
    before = getattr(state.team, attribute)
    advanced, deliveries = advance_ai_interval(
        state, GAME_DATE, GAME_DATE + timedelta(days=PROJECT_DURATION_DAYS + 7), Random(3)
    )
    assert len(deliveries) == 1
    outcome = deliveries[0].project.outcome
    assert getattr(advanced.team, attribute) == min(100, before + outcome)


def test_supplier_development_reaches_all_customers():
    supplier = EngineSupplier(id=7, name="Motori X", engine_power=60, customer_fee_usd=12_000_000)
    developed = develop_supplier_power(supplier, Random(5))
    assert developed.engine_power > supplier.engine_power

    customer = _team(AGGRESSIVE, customer=True)
    own_engine = replace(_team(AGGRESSIVE), id=2)
    teams = apply_supplier_power((customer, own_engine), (developed,))
    assert teams[0].engine_power == developed.engine_power
    assert teams[1].engine_power == own_engine.engine_power
