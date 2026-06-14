"""Test economici del Mercato AI (T5.2.1, sub-issue M2).

Due proprieta': il Prestigio si correla con la qualita' media dei piloti
aggiudicati (le squadre blasonate vincono i migliori) e nessuna offerta AI
supera la Cassa della squadra. La correlazione e' misurata su un numero
alto di seed. Engine-only.
"""

from random import Random

from fm_engine.market import driver_quality, open_market, resolve_market
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


def _driver(driver_id: int, quality: int, salary_demand_usd: int = 5_000_000) -> Driver:
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
        salary_demand_usd=salary_demand_usd,
    )


def _team(team_id: int, prestige: int, cash_usd: int) -> Team:
    return Team(
        id=team_id,
        name=f"T{team_id}",
        prestige=prestige,
        cash_usd=cash_usd,
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


def _config(n_teams: int) -> WorldConfig:
    return WorldConfig(
        ai_team_count=n_teams,
        drivers_per_team=2,
        free_agents=2,
        min_engine_suppliers=1,
        max_engine_suppliers=1,
    )


def _draft_world(seed: int, n_teams: int = 10) -> World:
    """Tutti i Contratti scadono: ogni squadra ridisegna il roster dal pool.

    La Cassa e' ampia rispetto agli ingaggi (25-60M contro un massimo di
    circa 20M), cosi' l'aggiudicazione e' guidata soprattutto dal Prestigio.
    """
    rng = Random(seed)
    teams = tuple(
        _team(team_id, prestige=rng.randint(30, 80), cash_usd=rng.randint(25, 60) * 1_000_000)
        for team_id in range(1, n_teams + 1)
    )
    drivers: list[Driver] = []
    contracts: list[Contract] = []
    driver_id = 1
    for team_id in range(1, n_teams + 1):
        for _ in range(2):
            drivers.append(_driver(driver_id, quality=rng.randint(40, 92)))
            contracts.append(
                Contract(
                    driver_id=driver_id,
                    team_id=team_id,
                    start_season=2025,
                    duration_seasons=1,
                    salary_usd=5_000_000,
                )
            )
            driver_id += 1
    drivers.append(_driver(driver_id, quality=rng.randint(40, 92)))
    drivers.append(_driver(driver_id + 1, quality=rng.randint(40, 92)))
    return World(
        seed=seed,
        config=_config(n_teams),
        ai_teams=teams,
        player_slot=PlayerSlot(),
        drivers=tuple(drivers),
        engine_suppliers=(),
        contracts=tuple(contracts),
    )


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / ((var_x**0.5) * (var_y**0.5))


def test_prestige_correlates_with_acquired_driver_quality():
    prestiges: list[float] = []
    qualities: list[float] = []
    for seed in SEEDS:
        world = _draft_world(seed)
        drivers_by_id = {driver.id: driver for driver in world.drivers}
        resolved = resolve_market(world, open_market(world, CONCLUDED_YEAR), Random(seed))
        for team in world.ai_teams:
            signed = resolved.signings_for(team.id)
            if not signed:
                continue
            avg_quality = sum(driver_quality(drivers_by_id[d]) for d in signed) / len(signed)
            prestiges.append(team.prestige)
            qualities.append(avg_quality)
    correlation = _pearson(prestiges, qualities)
    assert correlation > 0.4, f"correlazione prestige->qualita' troppo bassa: {correlation:.3f}"


def test_no_ai_offer_exceeds_team_cash():
    for seed in SEEDS:
        world = _draft_world(seed)
        cash_by_team = {team.id: team.cash_usd for team in world.ai_teams}
        resolved = resolve_market(world, open_market(world, CONCLUDED_YEAR), Random(seed))
        for move in resolved.ai_moves:
            assert move.salary_usd <= cash_by_team[move.team_id], f"seed {seed}: offerta {move}"


def test_cash_constraint_routes_an_expensive_star_to_the_rich_team():
    # Squadra povera ad alto Prestigio vs squadra ricca a basso Prestigio.
    # La stella costa piu' della Cassa della povera: deve finire alla ricca.
    star_id = 1
    star = _driver(star_id, quality=90)  # ingaggio desiderato 20M
    cheap = [_driver(driver_id, quality=45) for driver_id in (2, 3, 4)]  # circa 11M
    poor_team = _team(1, prestige=80, cash_usd=12_000_000)
    rich_team = _team(2, prestige=30, cash_usd=60_000_000)
    contracts = tuple(
        Contract(
            driver_id=driver_id,
            team_id=1 if driver_id in (1, 2) else 2,
            start_season=2025,
            duration_seasons=1,
            salary_usd=5_000_000,
        )
        for driver_id in (1, 2, 3, 4)
    )
    world = World(
        seed=1,
        config=_config(2),
        ai_teams=(poor_team, rich_team),
        player_slot=PlayerSlot(),
        drivers=(star, *cheap),
        engine_suppliers=(),
        contracts=contracts,
    )
    resolved = resolve_market(world, open_market(world, CONCLUDED_YEAR), Random(1))
    assert star_id in resolved.signings_for(rich_team.id)
    assert star_id not in resolved.signings_for(poor_team.id)
