"""Test dei Progetti di sviluppo (FOR-25).

API motore pura: avvio con investimento dal Cap, vincoli di slot e
Cliente, avanzamento col calendario, consegna con esito a varianza e
Notizia, sospensione a squadra non sana.
"""

from datetime import date, timedelta
from random import Random

import pytest

from fm_engine.development import (
    MAX_INVESTMENT_USD,
    MAX_PARALLEL_PROJECTS,
    MIN_INVESTMENT_USD,
    PROJECT_DURATION_DAYS,
    CustomerEngineLocked,
    ProjectLimitReached,
    ProjectStatus,
    advance_projects,
    apply_delivery,
    expected_gain_points,
    start_project,
)
from fm_engine.economy import (
    SEASON_CAP_USD,
    SpendingBlocked,
    TeamLedger,
    Transaction,
    TransactionKind,
)

START_DATE = date(2026, 3, 8)
INVESTMENT = 8_000_000


def _funded(amount_usd: int = 100_000_000) -> TeamLedger:
    return TeamLedger().record(
        Transaction(
            kind=TransactionKind.OTHER,
            amount_usd=amount_usd,
            game_date=START_DATE,
            description="Dotazione di prova",
        )
    )


def _start(ledger, projects, attribute="downforce", investment=INVESTMENT, customer=False):
    return start_project(
        ledger, projects, attribute, investment, START_DATE, is_engine_customer=customer
    )


# ---------------------------------------------------------------------------
# Start: investment from the cap, slots, customer rule
# ---------------------------------------------------------------------------


def test_start_spends_from_cash_and_cap():
    ledger, projects = _start(_funded(), ())
    assert len(projects) == 1
    project = projects[0]
    assert project.attribute == "downforce"
    assert project.status is ProjectStatus.IN_PROGRESS
    assert project.outcome is None
    assert project.delivery_date == START_DATE + timedelta(days=PROJECT_DURATION_DAYS)
    entry = ledger.entries[-1]
    assert entry.kind is TransactionKind.DEVELOPMENT_PROJECT
    assert entry.amount_usd == -INVESTMENT
    assert entry.counts_against_cap is True
    assert ledger.cap_remaining_usd == SEASON_CAP_USD - INVESTMENT


def test_third_parallel_project_is_refused():
    ledger, projects = _start(_funded(), ())
    ledger, projects = _start(ledger, projects, attribute="reliability")
    assert len(projects) == MAX_PARALLEL_PROJECTS
    with pytest.raises(ProjectLimitReached):
        _start(ledger, projects, attribute="mechanical_grip")


def test_customer_cannot_develop_the_engine_power():
    with pytest.raises(CustomerEngineLocked):
        _start(_funded(), (), attribute="engine_power", customer=True)
    # Chi produce in proprio puo'.
    _, projects = _start(_funded(), (), attribute="engine_power", customer=False)
    assert projects[0].attribute == "engine_power"


def test_start_validates_attribute_and_investment():
    with pytest.raises(ValueError):
        _start(_funded(), (), attribute="top_speed")
    with pytest.raises(ValueError):
        _start(_funded(), (), investment=MIN_INVESTMENT_USD - 1)
    with pytest.raises(ValueError):
        _start(_funded(), (), investment=MAX_INVESTMENT_USD + 1)


def test_start_respects_the_double_spending_bind():
    poor = _funded(1_000_000)
    with pytest.raises(SpendingBlocked):
        _start(poor, ())


# ---------------------------------------------------------------------------
# Advance and delivery
# ---------------------------------------------------------------------------


def test_advance_before_the_delivery_date_keeps_it_in_progress():
    _, projects = _start(_funded(), ())
    advanced, deliveries = advance_projects(
        projects, START_DATE, START_DATE + timedelta(days=14), Random(1)
    )
    assert deliveries == ()
    assert advanced[0].in_progress


def test_advance_past_the_delivery_date_completes_with_outcome_and_news():
    _, projects = _start(_funded(), ())
    advanced, deliveries = advance_projects(
        projects, START_DATE, START_DATE + timedelta(days=PROJECT_DURATION_DAYS + 7), Random(1)
    )
    assert len(deliveries) == 1
    project = advanced[0]
    assert project.status is ProjectStatus.COMPLETED
    assert project.outcome is not None
    assert deliveries[0].news
    assert "Consegna" in deliveries[0].news


def test_suspension_shifts_the_delivery_without_completing():
    """Squadra non sana (FOR-24): i Progetti sono sospesi e slittano."""
    _, projects = _start(_funded(), ())
    original_delivery = projects[0].delivery_date
    interval = timedelta(days=PROJECT_DURATION_DAYS + 7)
    shifted, deliveries = advance_projects(
        projects, START_DATE, START_DATE + interval, Random(1), suspended=True
    )
    assert deliveries == ()
    assert shifted[0].in_progress
    assert shifted[0].delivery_date == original_delivery + interval


def test_advance_backwards_is_rejected():
    with pytest.raises(ValueError):
        advance_projects((), START_DATE, START_DATE - timedelta(days=1), Random(1))


def test_apply_delivery_updates_and_clamps_the_attribute():
    _, projects = _start(_funded(), ())
    _, deliveries = advance_projects(
        projects, START_DATE, START_DATE + timedelta(days=60), Random(1)
    )
    delivery = deliveries[0]
    outcome = delivery.project.outcome
    assert apply_delivery(70, delivery) == min(100, 70 + outcome)
    assert apply_delivery(99, delivery) <= 100


# ---------------------------------------------------------------------------
# Outcome distribution: variance with a seed
# ---------------------------------------------------------------------------


def test_outcome_distribution_has_variance_and_a_coherent_mean():
    rng = Random(42)
    expected = expected_gain_points(INVESTMENT)
    outcomes = []
    for _ in range(400):
        _, projects = _start(_funded(), ())
        advanced, _ = advance_projects(projects, START_DATE, START_DATE + timedelta(days=60), rng)
        outcomes.append(advanced[0].outcome)
    assert any(outcome < expected for outcome in outcomes), "mai sotto le attese"
    assert any(outcome > expected for outcome in outcomes), "mai sopra le attese"
    mean = sum(outcomes) / len(outcomes)
    # Effetto medio coerente con l'investimento (fattore medio 1.0).
    assert expected * 0.85 <= mean <= expected * 1.15
