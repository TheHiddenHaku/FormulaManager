"""Estrazione e applicazione degli Eventi extra-gara (FOR-27).

Al massimo un evento per intervallo tra due GP, con frequenza bassa
configurabile: il silenzio e' normale. L'evento estratto applica subito
il suo effetto meccanico secco (entrata in Cassa con causale, consegna
di un Progetto anticipata o posticipata, attributo di un rivale in
calo) e produce la Notizia dal template parametrico del pool.

Motore puro (ADR 0002): l'rng arriva dal chiamante, deterministico per
intervallo. Gli effetti vivono negli stati gia' persistiti (registro,
Progetti, squadre): nessuno stato nuovo da salvare.
"""

from dataclasses import dataclass, replace
from datetime import date, timedelta
from random import Random

from fm_engine.development import DevelopmentProject, active_projects
from fm_engine.economy import TeamLedger, Transaction, TransactionKind
from fm_engine.events_extra.pool import EXTRA_EVENT_POOL, ExtraEvent, ExtraEventKind
from fm_engine.world.models import CAR_ATTRIBUTES, World

# Probability that an interval produces an event. Low by design: most
# intervals stay silent. Tunable.
EXTRA_EVENT_PROBABILITY = 0.25

# Italian labels of the car attributes, for the news templates.
_ATTRIBUTE_LABELS = {
    "engine_power": "Potenza motore",
    "downforce": "Carico aerodinamico",
    "aero_efficiency": "Efficienza aerodinamica",
    "mechanical_grip": "Meccanica",
    "tyre_management": "Gestione gomme",
    "reliability": "Affidabilita'",
}


@dataclass(frozen=True)
class ExtraEventOutcome:
    """L'evento estratto, la sua Notizia e gli stati aggiornati."""

    event: ExtraEvent
    news: str
    ledger: TeamLedger
    projects: tuple[DevelopmentProject, ...]
    world: World


def draw_extra_event(
    world: World,
    ledger: TeamLedger,
    projects: tuple[DevelopmentProject, ...],
    game_date: date,
    rng: Random,
    probability: float = EXTRA_EVENT_PROBABILITY,
) -> ExtraEventOutcome | None:
    """Estrae al piu' un Evento extra-gara per l'intervallo corrente.

    None nella maggioranza dei casi (frequenza bassa). Gli eventi sui
    Progetti sono estraibili solo con un Progetto in corso; sponsor e
    guai dei rivali sono sempre applicabili.
    """
    if rng.random() >= probability:
        return None
    has_active_projects = bool(active_projects(projects))
    applicable = tuple(
        event
        for event in EXTRA_EVENT_POOL
        if has_active_projects
        or event.kind not in (ExtraEventKind.PROJECT_DELAYED, ExtraEventKind.PROJECT_ACCELERATED)
    )
    weights = [event.weight for event in applicable]
    event = rng.choices(applicable, weights=weights, k=1)[0]

    if event.kind is ExtraEventKind.ONE_OFF_SPONSOR:
        return _apply_sponsor(event, world, ledger, projects, game_date)
    if event.kind in (ExtraEventKind.PROJECT_DELAYED, ExtraEventKind.PROJECT_ACCELERATED):
        return _apply_project_shift(event, world, ledger, projects, rng)
    return _apply_rival_setback(event, world, ledger, projects, rng)


def _format_amount(amount_usd: int) -> str:
    return f"${amount_usd / 1_000_000:.1f}M"


def _apply_sponsor(event, world, ledger, projects, game_date) -> ExtraEventOutcome:
    """Entrata una tantum in Cassa, con causale nel registro."""
    news = event.headline_template.format(amount=_format_amount(event.amount_usd))
    ledger = ledger.record(
        Transaction(
            kind=TransactionKind.ONE_OFF_SPONSOR,
            amount_usd=event.amount_usd,
            game_date=game_date,
            description=news,
        )
    )
    return ExtraEventOutcome(event=event, news=news, ledger=ledger, projects=projects, world=world)


def _apply_project_shift(event, world, ledger, projects, rng) -> ExtraEventOutcome:
    """Consegna di un Progetto in corso anticipata o posticipata."""
    target = rng.choice(active_projects(projects))
    days = event.shift_days
    if event.kind is ExtraEventKind.PROJECT_DELAYED:
        shifted = replace(target, start_date=target.start_date + timedelta(days=days))
    else:
        shifted = replace(target, start_date=target.start_date - timedelta(days=days))
    projects = tuple(shifted if project is target else project for project in projects)
    news = event.headline_template.format(attribute=_ATTRIBUTE_LABELS[target.attribute], days=days)
    return ExtraEventOutcome(event=event, news=news, ledger=ledger, projects=projects, world=world)


def _apply_rival_setback(event, world, ledger, projects, rng) -> ExtraEventOutcome:
    """Guaio in fabbrica di un rivale: un suo Attributo vettura cala."""
    rival = rng.choice(world.ai_teams)
    attribute = rng.choice(CAR_ATTRIBUTES)
    dropped = replace(rival, **{attribute: max(0, getattr(rival, attribute) - 1)})
    teams = tuple(dropped if team is rival else team for team in world.ai_teams)
    world = replace(world, ai_teams=teams)
    news = event.headline_template.format(rival=rival.name, attribute=_ATTRIBUTE_LABELS[attribute])
    return ExtraEventOutcome(event=event, news=news, ledger=ledger, projects=projects, world=world)
