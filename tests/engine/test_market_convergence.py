"""Test di convergenza del Mercato AI (T5.2.1, sub-issue M2).

L'invariante chiave: a Mercato risolto ogni squadra AI ha esattamente
seats_per_team piloti, nessun sedile vuoto, nessun pilota su due squadre.
Verificato su un numero alto di seed, non su un singolo caso. Engine-only.
"""

from dataclasses import replace
from random import Random

from fm_engine.market import final_roster_ids, open_market, resolve_market
from fm_engine.world.models import (
    Contract,
    Driver,
    PlayerSlot,
    SpendingPersonality,
    Team,
    World,
    WorldConfig,
)

CONCLUDED_YEAR = 2025
SEEDS = range(1, 101)


def _driver(rng: Random, driver_id: int) -> Driver:
    quality = rng.randint(40, 92)
    return Driver(
        id=driver_id,
        name=f"D{driver_id}",
        nationality="it",
        age=27,
        one_lap_pace=quality,
        race_pace=quality,
        duels=quality,
        tyre_management=quality,
        wet_weather=quality,
        consistency=quality,
        potential=70,
        salary_demand_usd=5_000_000,
    )


def _team(rng: Random, team_id: int) -> Team:
    return Team(
        id=team_id,
        name=f"T{team_id}",
        prestige=rng.randint(30, 80),
        cash_usd=rng.randint(25, 60) * 1_000_000,
        chassis_philosophy="balanced",
        engine_supplier_id=None,
        engine_power=70,
        downforce=70,
        aero_efficiency=70,
        mechanical_grip=70,
        tyre_management=70,
        reliability=70,
        personality=SpendingPersonality(
            profile="balanced", spending_propensity=0.5, risk_tolerance=0.5
        ),
    )


def _world(seed: int, n_teams: int = 10, all_expiring: bool = False) -> World:
    """Griglia sintetica: n_teams squadre AI con 2 Contratti ciascuna, 2 liberi.

    Con all_expiring tutti i Contratti scadono nell'anno concluso; altrimenti
    la durata e' casuale 1-3, cosi' alcuni Contratti sopravvivono al Mercato.
    """
    rng = Random(seed)
    teams = tuple(_team(rng, team_id) for team_id in range(1, n_teams + 1))
    drivers: list[Driver] = []
    contracts: list[Contract] = []
    driver_id = 1
    for team_id in range(1, n_teams + 1):
        for _ in range(2):
            drivers.append(_driver(rng, driver_id))
            duration = 1 if all_expiring else rng.randint(1, 3)
            contracts.append(
                Contract(
                    driver_id=driver_id,
                    team_id=team_id,
                    start_season=2025,
                    duration_seasons=duration,
                    salary_usd=5_000_000,
                )
            )
            driver_id += 1
    # Due piloti liberi senza Contratto.
    drivers.append(_driver(rng, driver_id))
    drivers.append(_driver(rng, driver_id + 1))
    config = WorldConfig(
        ai_team_count=n_teams,
        drivers_per_team=2,
        free_agents=2,
        min_engine_suppliers=1,
        max_engine_suppliers=1,
    )
    return World(
        seed=seed,
        config=config,
        ai_teams=teams,
        player_slot=PlayerSlot(),
        drivers=tuple(drivers),
        engine_suppliers=(),
        contracts=tuple(contracts),
    )


def test_every_ai_team_has_exactly_two_drivers_across_seeds():
    for seed in SEEDS:
        world = _world(seed)
        market = open_market(world, CONCLUDED_YEAR)
        resolved = resolve_market(world, market, Random(seed))
        seen: set[int] = set()
        for team in world.ai_teams:
            roster = final_roster_ids(world, resolved, team.id)
            assert len(roster) == 2, f"seed {seed} team {team.id}: roster {roster}"
            assert resolved.vacant_seats_for(team.id) == 0, f"seed {seed} team {team.id} vacante"
            for driver_id in roster:
                assert driver_id not in seen, f"seed {seed}: pilota {driver_id} su due squadre"
                seen.add(driver_id)


def test_convergence_holds_when_all_contracts_expire():
    for seed in SEEDS:
        world = _world(seed, all_expiring=True)
        market = open_market(world, CONCLUDED_YEAR)
        resolved = resolve_market(world, market, Random(seed))
        for team in world.ai_teams:
            assert len(final_roster_ids(world, resolved, team.id)) == 2
            assert resolved.vacant_seats_for(team.id) == 0


def test_resolution_is_deterministic_for_a_seed():
    world = _world(7)
    market = open_market(world, CONCLUDED_YEAR)
    first = resolve_market(world, market, Random(123))
    second = resolve_market(world, market, Random(123))
    assert first == second


def test_resolution_ignores_spending_personality():
    # Su un World ricaricato la SpendingPersonality e' azzerata: la
    # risoluzione deve dare lo stesso esito (usa solo prestige e cash).
    world = _world(11, all_expiring=True)
    zeroed = replace(
        world,
        ai_teams=tuple(
            replace(
                team,
                personality=SpendingPersonality(
                    profile="cautious", spending_propensity=0.0, risk_tolerance=0.0
                ),
            )
            for team in world.ai_teams
        ),
    )
    base = resolve_market(world, open_market(world, CONCLUDED_YEAR), Random(5))
    other = resolve_market(zeroed, open_market(zeroed, CONCLUDED_YEAR), Random(5))
    assert base.signings == other.signings
    assert base.vacant_seats == other.vacant_seats
    assert base.ai_moves == other.ai_moves
