"""Test di apply_market: dalle firme del Mercato ai Contratti (T5.2.1).

Verificano la chiusura della fase: i Contratti sopravvissuti restano, le
firme diventano Contratti della stagione nuova coi termini negoziati, lo
"scippo" del giocatore prevale sulla rivale e ogni squadra converge a due
piloti. Tutto deterministico dal seed.
"""

from datetime import date
from random import Random

import pytest

from fm_engine.economy import DEFAULT_PLAYER_PRESTIGE, TeamLedger, Transaction, TransactionKind
from fm_engine.market import (
    apply_market,
    best_rival_salary_usd,
    counter_offer,
    open_market,
    resolve_market,
)
from fm_engine.market.models import MarketState
from fm_engine.world import generate
from fm_engine.world.models import PLAYER_TEAM_ID

SEED = 42
CONCLUDED_YEAR = 2026
GAME_DATE = date(2026, 11, 1)


def _resolved_market(world, year: int = CONCLUDED_YEAR) -> MarketState:
    market = open_market(world, year)
    return resolve_market(world, market, Random(SEED * 1_000 + 800))


def _funded_ledger() -> TeamLedger:
    return TeamLedger().record(
        Transaction(
            kind=TransactionKind.ANNUAL_SPONSOR,
            amount_usd=100_000_000,
            game_date=date(2026, 1, 1),
            description="Sponsor",
        )
    )


def test_apply_requires_an_open_market():
    world = generate(SEED)
    with pytest.raises(ValueError, match="open market"):
        apply_market(world, MarketState())


def test_every_team_converges_to_two_drivers():
    world = generate(SEED)
    result = apply_market(world, _resolved_market(world))

    team_ids = [PLAYER_TEAM_ID, *(team.id for team in world.ai_teams)]
    for team_id in team_ids:
        assert len(result.contracts_of(team_id)) == 2
    driver_ids = [contract.driver_id for contract in result.contracts]
    assert len(driver_ids) == len(set(driver_ids))
    assert len(result.contracts) == 2 * len(team_ids)


def test_new_contracts_start_the_following_season():
    world = generate(SEED)
    result = apply_market(world, _resolved_market(world))

    surviving = {
        (contract.team_id, contract.driver_id, contract.start_season)
        for contract in world.contracts
        if contract.start_season + contract.duration_seasons - 1 != CONCLUDED_YEAR
    }
    for contract in result.contracts:
        key = (contract.team_id, contract.driver_id, contract.start_season)
        if key in surviving:
            continue  # contratto sopravvissuto, invariato
        assert contract.start_season == CONCLUDED_YEAR + 1


def test_signing_terms_come_from_the_move():
    world = generate(SEED)
    market = _resolved_market(world)
    # Una firma AI qualsiasi e i suoi termini dal log.
    move = next(
        m
        for m in market.ai_moves
        if m.kind.name in {"SIGNING", "FORCED_ASSIGNMENT"} and m.team_id != PLAYER_TEAM_ID
    )
    result = apply_market(world, market)

    signed = next(
        contract
        for contract in result.contracts_of(move.team_id)
        if contract.driver_id == move.driver_id
    )
    assert signed.salary_usd == move.salary_usd
    assert signed.duration_seasons == move.duration_seasons
    assert signed.start_season == CONCLUDED_YEAR + 1


def test_player_signing_wins_the_conflict_and_rival_is_refilled():
    world = generate(SEED)
    market = _resolved_market(world)

    # Un pilota gia' firmato da una rivale, su cui il giocatore rilancia.
    rival_team_id, target = next(
        (team.id, market.signings_for(team.id)[0])
        for team in world.ai_teams
        if market.signings_for(team.id)
    )
    rival_offer = best_rival_salary_usd(market, target)
    outcome = counter_offer(
        market,
        _funded_ledger(),
        target,
        salary_usd=rival_offer + 1_000_000,
        duration_seasons=2,
        game_date=GAME_DATE,
        player_prestige=DEFAULT_PLAYER_PRESTIGE,
    )
    assert outcome.accepted

    result = apply_market(world, outcome.market)
    player_ids = {contract.driver_id for contract in result.contracts_of(PLAYER_TEAM_ID)}
    rival_ids = {contract.driver_id for contract in result.contracts_of(rival_team_id)}

    assert target in player_ids
    assert target not in rival_ids
    # La rivale resta comunque con due piloti (sedile ricoperto).
    assert len(result.contracts_of(rival_team_id)) == 2
    all_ids = [contract.driver_id for contract in result.contracts]
    assert len(all_ids) == len(set(all_ids))


def test_apply_is_deterministic():
    world = generate(SEED)
    market = _resolved_market(world)
    assert apply_market(world, market).contracts == apply_market(world, market).contracts
