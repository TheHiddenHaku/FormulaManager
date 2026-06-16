"""Round-trip della transizione di stagione (fase inverno, FOR-32).

La transizione e' transazionale a granularita' di Carriera (ADR 0001): dopo
advance_winter, un singolo save_career scrive vettura nuova (attributi
regrediti dal Carry-over, motore e Filosofia rinegoziati, Progetti
invernali) ed economia nuova (Cap, Cassa riportata, Sponsor) in un'unica
transazione. load_career deve ricostruire esattamente quello stato: nessuna
perdita dati. I round-trip girano sul Postgres effimero Docker.
"""

from dataclasses import replace
from datetime import date

from fm_engine.career import Career
from fm_engine.economy import (
    DEFAULT_PLAYER_PRESTIGE,
    SEASON_CAP_USD,
    TeamLedger,
    Transaction,
    TransactionKind,
    credit_annual_sponsor,
)
from fm_engine.winter import (
    RenegotiationChoices,
    WinterDecisions,
    WinterProject,
    advance_winter,
)
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_engine.world.models import CAR_ATTRIBUTES
from fm_persistence import load_career, save_career

SEED = 42
CONCLUDED_YEAR = 2026


def _career(ledger: TeamLedger) -> Career:
    world = generate(SEED)
    world = replace(world, player_slot=PlayerSlot(name="Scuderia X", primary_color="#ff2800"))
    free = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free[0].id, free[1].id),
        engine_supplier_id=None,
        chassis_philosophy="balanced",
    )
    return Career(name="Scuderia X", world=apply_team_setup(world, choices), ledger=ledger)


def _funded(amount_usd: int) -> TeamLedger:
    ledger = credit_annual_sponsor(TeamLedger(), DEFAULT_PLAYER_PRESTIGE, date(2026, 1, 1))
    if amount_usd:
        ledger = ledger.record(
            Transaction(
                kind=TransactionKind.OTHER,
                amount_usd=amount_usd,
                game_date=date(2026, 1, 1),
                description="Dotazione di prova",
            )
        )
    return ledger


def test_winter_transition_round_trips_the_new_season_state(conn):
    """Carry-over, rinegoziazione, Progetti e rollover sopravvivono al Checkpoint."""
    career = _career(_funded(30_000_000))
    supplier = career.world.engine_suppliers[0]
    decisions = WinterDecisions(
        renegotiation=RenegotiationChoices(
            engine_supplier_id=supplier.id, chassis_philosophy="fast"
        ),
        winter_projects=(WinterProject(attribute="reliability", points=3),),
    )

    outcome = advance_winter(career.world, career.ledger, CONCLUDED_YEAR, decisions)
    transitioned = replace(career, world=outcome.world, ledger=outcome.ledger)

    saved = save_career(conn, transitioned)
    reloaded = load_career(conn, saved.id)

    # Vettura nuova: attributi regrediti + Progetto + rinegoziazione.
    expected_car = transitioned.world.player_slot.car_attributes
    assert reloaded.world.player_slot.car_attributes == expected_car
    assert reloaded.world.player_slot.engine_supplier_id == supplier.id
    assert reloaded.world.player_slot.chassis_philosophy == "fast"
    # Economia nuova: stagione, Cap pieno (nessuno Sforamento), Cassa riportata.
    assert reloaded.ledger.season_year == CONCLUDED_YEAR + 1
    assert reloaded.ledger.cap_usd == SEASON_CAP_USD
    assert reloaded.ledger.cash_usd == transitioned.ledger.cash_usd


def test_winter_transition_round_trips_overspend_penalty(conn):
    """Caso limite Sforamento pesante: il Cap ridotto sopravvive al Checkpoint."""
    ledger = _funded(400_000_000).record(
        Transaction(
            kind=TransactionKind.DAMAGE,
            amount_usd=-(SEASON_CAP_USD + 12_000_000),
            game_date=date(CONCLUDED_YEAR, 12, 1),
            description="Danno",
            counts_against_cap=True,
        )
    )
    career = _career(ledger)
    assert career.ledger.overspend_usd == 12_000_000

    outcome = advance_winter(career.world, career.ledger, CONCLUDED_YEAR)
    transitioned = replace(career, world=outcome.world, ledger=outcome.ledger)

    saved = save_career(conn, transitioned)
    reloaded = load_career(conn, saved.id)

    assert reloaded.ledger.cap_usd == SEASON_CAP_USD - 12_000_000
    assert reloaded.ledger.season_year == CONCLUDED_YEAR + 1


def test_default_winter_round_trips_carryover_only(conn):
    """Senza decisioni: Carry-over e rollover, round-trip identico."""
    career = _career(_funded(0))
    before = career.world.player_slot.car_attributes

    outcome = advance_winter(career.world, career.ledger, CONCLUDED_YEAR)
    transitioned = replace(career, world=outcome.world, ledger=outcome.ledger)

    saved = save_career(conn, transitioned)
    reloaded = load_career(conn, saved.id)

    after = reloaded.world.player_slot.car_attributes
    assert after == transitioned.world.player_slot.car_attributes
    # La vettura e' davvero cambiata (Carry-over conseguente).
    assert after != before
    # Le squadre AI sono regredite anch'esse e sopravvivono al round-trip.
    for name in CAR_ATTRIBUTES:
        for reloaded_team, expected_team in zip(
            reloaded.world.ai_teams, transitioned.world.ai_teams, strict=True
        ):
            assert getattr(reloaded_team, name) == getattr(expected_team, name)
