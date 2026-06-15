"""Test del pool del Mercato piloti (T5.2.1, sub-issue M1).

Mondo sintetico riproducibile: i Contratti hanno scadenze note, cosi' le
asserzioni su pool, liberi e sedili vacanti sono esatte. Engine-only:
nessuna dipendenza da database o TUI.
"""

from types import SimpleNamespace

from fm_engine.market import (
    ExpiringContract,
    MarketPhase,
    MarketState,
    is_expiring,
    last_covered_season,
    open_market,
)
from fm_engine.market.pool import _is_active
from fm_engine.world.models import (
    PLAYER_TEAM_ID,
    Contract,
    Driver,
    PlayerSlot,
    SpendingPersonality,
    Team,
    World,
    WorldConfig,
)

CONCLUDED_YEAR = 2026


def _driver(driver_id: int, salary_demand_usd: int = 5_000_000) -> Driver:
    return Driver(
        id=driver_id,
        name=f"Driver {driver_id}",
        nationality="it",
        age=27,
        one_lap_pace=70,
        race_pace=70,
        duels=70,
        tyre_management=70,
        wet_weather=70,
        consistency=70,
        potential=70,
        salary_demand_usd=salary_demand_usd,
    )


def _team(team_id: int) -> Team:
    return Team(
        id=team_id,
        name=f"Team {team_id}",
        prestige=50,
        cash_usd=40_000_000,
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


def _contract(driver_id: int, team_id: int, start_season: int, duration_seasons: int) -> Contract:
    return Contract(
        driver_id=driver_id,
        team_id=team_id,
        start_season=start_season,
        duration_seasons=duration_seasons,
        salary_usd=8_000_000,
    )


def _world() -> World:
    """Due squadre AI, quattro contrattualizzati con scadenze note, due liberi."""
    config = WorldConfig(
        ai_team_count=2,
        drivers_per_team=2,
        free_agents=2,
        min_engine_suppliers=1,
        max_engine_suppliers=1,
    )
    drivers = tuple(_driver(i, salary_demand_usd=1_000_000 * i) for i in range(1, 7))
    contracts = (
        _contract(1, 1, start_season=2025, duration_seasons=2),  # last 2026: expiring
        _contract(2, 1, start_season=2025, duration_seasons=3),  # last 2027: surviving
        _contract(3, 2, start_season=2026, duration_seasons=1),  # last 2026: expiring
        _contract(4, 2, start_season=2024, duration_seasons=3),  # last 2026: expiring
    )
    return World(
        seed=1,
        config=config,
        ai_teams=(_team(1), _team(2)),
        player_slot=PlayerSlot(),
        drivers=drivers,
        engine_suppliers=(),
        contracts=contracts,
    )


def test_last_covered_season_is_start_plus_duration_minus_one():
    assert last_covered_season(_contract(1, 1, 2025, 2)) == 2026
    assert last_covered_season(_contract(3, 2, 2026, 1)) == 2026
    assert last_covered_season(_contract(4, 2, 2024, 3)) == 2026
    assert last_covered_season(_contract(2, 1, 2025, 3)) == 2027


def test_is_expiring_matches_the_concluded_year():
    assert is_expiring(_contract(1, 1, 2025, 2), CONCLUDED_YEAR) is True
    assert is_expiring(_contract(2, 1, 2025, 3), CONCLUDED_YEAR) is False


def test_open_market_opens_the_phase_for_the_concluded_year():
    market = open_market(_world(), CONCLUDED_YEAR)
    assert market.phase is MarketPhase.OPEN
    assert market.is_open is True
    assert market.concluded_year == CONCLUDED_YEAR
    assert market.seats_per_team == 2


def test_expiring_contracts_enter_the_pool():
    market = open_market(_world(), CONCLUDED_YEAR)
    assert set(market.pool_driver_ids) == {1, 3, 4}
    assert all(isinstance(item, ExpiringContract) for item in market.pool)
    expiring = {item.driver_id: item for item in market.pool}
    assert expiring[1].team_id == 1
    assert expiring[3].team_id == 2
    assert all(item.last_season == CONCLUDED_YEAR for item in market.pool)


def test_multi_year_contracts_stay_out_of_the_pool():
    market = open_market(_world(), CONCLUDED_YEAR)
    # Driver 2 ha un Contratto valido fino al 2027: non e' in scadenza.
    assert 2 not in market.pool_driver_ids


def test_free_agents_are_available_with_their_salary_demand():
    market = open_market(_world(), CONCLUDED_YEAR)
    assert set(market.free_agent_ids) == {5, 6}
    assert market.salary_demands == {5: 5_000_000, 6: 6_000_000}
    # Le richieste salariali transitorie riguardano i soli liberi.
    assert set(market.salary_demands) == set(market.free_agent_ids)


def test_available_drivers_are_pool_plus_free_agents():
    market = open_market(_world(), CONCLUDED_YEAR)
    assert set(market.available_driver_ids) == {1, 3, 4, 5, 6}


def test_vacant_seats_are_computed_per_team():
    market = open_market(_world(), CONCLUDED_YEAR)
    # Team 1 perde un pilota (driver 1), ne tiene uno (driver 2): un sedile.
    assert market.vacant_seats_for(1) == 1
    # Team 2 perde entrambi i piloti: due sedili.
    assert market.vacant_seats_for(2) == 2
    # Lo slot del giocatore non ha Contratti in questo Mondo: due sedili.
    assert market.vacant_seats_for(PLAYER_TEAM_ID) == 2


def test_driver_count_per_team_complements_vacant_seats():
    market = open_market(_world(), CONCLUDED_YEAR)
    assert market.driver_count_for(1) == 1
    assert market.driver_count_for(2) == 0
    assert market.driver_count_for(PLAYER_TEAM_ID) == 0


def test_default_market_state_is_the_closed_starting_state():
    market = MarketState()
    assert market.phase is MarketPhase.CLOSED
    assert market.is_open is False
    assert market.concluded_year is None
    assert market.pool == ()
    assert market.free_agent_ids == ()
    assert market.ai_moves == ()
    # Due default coincidono: e' la base del NULL=default in persistenza (M4).
    assert market == MarketState()


def test_active_filter_excludes_retired_drivers_when_flag_present():
    # Anticipa FOR-31e: un pilota col flag retired resta fuori dai liberi.
    assert _is_active(SimpleNamespace(retired=False)) is True
    assert _is_active(SimpleNamespace(retired=True)) is False
    # Un Driver attuale non ha il flag: e' attivo.
    assert _is_active(_driver(1)) is True
