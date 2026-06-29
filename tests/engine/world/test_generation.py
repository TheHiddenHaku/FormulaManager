"""Property test e test di determinismo per fm_engine.world.generate.

Le proprieta' strutturali del Mondo (criteri di accettazione FOR-4) sono
verificate su un ventaglio fisso di seed: senza hypothesis (il motore e i
test restano su stdlib + pytest), la parametrizzazione sui seed fa da
property test deterministico.
"""

from collections import Counter

import pytest

from fm_engine.world import WorldConfig, generate
from fm_engine.world.models import CAR_ATTRIBUTES, DRIVER_ATTRIBUTES
from fm_engine.world.nationalities import DRIVER_NAMES

SEEDS = tuple(range(20))

_WORLD_CACHE = {seed: generate(seed) for seed in SEEDS}


@pytest.fixture(params=SEEDS)
def world(request):
    return _WORLD_CACHE[request.param]


CONFIG = WorldConfig()


# ---------------------------------------------------------------------------
# Grid and roster
# ---------------------------------------------------------------------------


def test_roster_of_22_drivers(world):
    assert len(world.drivers) == 22


def test_ten_ai_teams_and_empty_player_slot(world):
    assert len(world.ai_teams) == 10
    assert world.player_slot.name is None
    # The player slot is empty: no contract references it.
    ai_team_ids = {team.id for team in world.ai_teams}
    assert all(contract.team_id in ai_team_ids for contract in world.contracts)


def test_every_ai_team_has_exactly_two_drivers(world):
    per_team = Counter(contract.team_id for contract in world.contracts)
    assert all(per_team[team.id] == 2 for team in world.ai_teams)
    assert len(world.contracts) == 20


def test_two_free_agents_without_contract(world):
    free_agents = world.drivers_without_contract
    assert len(free_agents) == 2
    # Free agents also carry a salary demand for the wizard.
    assert all(driver.salary_demand_usd > 0 for driver in free_agents)


def test_every_contract_references_a_distinct_driver(world):
    driver_ids = [contract.driver_id for contract in world.contracts]
    assert len(driver_ids) == len(set(driver_ids))


# ---------------------------------------------------------------------------
# Engine suppliers and supply deals
# ---------------------------------------------------------------------------


def test_three_or_four_engine_suppliers(world):
    assert 3 <= len(world.engine_suppliers) <= 4


def test_every_ai_team_has_an_engine(world):
    supplier_ids = {supplier.id for supplier in world.engine_suppliers}
    for team in world.ai_teams:
        if team.engine_supplier_id is None:
            assert team.builds_own_engine
        else:
            assert team.engine_supplier_id in supplier_ids


def test_every_engine_supplier_has_at_least_one_customer(world):
    used_suppliers = {
        team.engine_supplier_id for team in world.ai_teams if team.engine_supplier_id is not None
    }
    assert used_suppliers == {supplier.id for supplier in world.engine_suppliers}


def test_at_least_one_team_builds_its_own_engine(world):
    assert any(team.builds_own_engine for team in world.ai_teams)


def test_customer_shares_the_supplier_engine_power(world):
    powers = {supplier.id: supplier.engine_power for supplier in world.engine_suppliers}
    for team in world.ai_teams:
        if team.engine_supplier_id is not None:
            assert team.engine_power == powers[team.engine_supplier_id]


# ---------------------------------------------------------------------------
# Attribute and generated value ranges
# ---------------------------------------------------------------------------


def test_driver_attributes_within_config_ranges(world):
    minimum, maximum = CONFIG.driver_attribute_range
    for driver in world.drivers:
        for name in DRIVER_ATTRIBUTES:
            assert minimum <= getattr(driver, name) <= maximum


def test_age_potential_and_salary_demand_within_ranges(world):
    for driver in world.drivers:
        assert CONFIG.age_range[0] <= driver.age <= CONFIG.age_range[1]
        assert CONFIG.potential_range[0] <= driver.potential <= CONFIG.potential_range[1]
        assert (
            CONFIG.salary_demand_usd_range[0]
            <= driver.salary_demand_usd
            <= CONFIG.salary_demand_usd_range[1]
        )


def test_car_attributes_within_config_ranges(world):
    minimum, maximum = CONFIG.car_attribute_range
    for team in world.ai_teams:
        for name in CAR_ATTRIBUTES:
            assert minimum <= getattr(team, name) <= maximum
        assert CONFIG.prestige_range[0] <= team.prestige <= CONFIG.prestige_range[1]
        assert CONFIG.cash_usd_range[0] <= team.cash_usd <= CONFIG.cash_usd_range[1]
        assert team.chassis_philosophy in CONFIG.chassis_philosophies
    for supplier in world.engine_suppliers:
        assert minimum <= supplier.engine_power <= maximum
        assert (
            CONFIG.customer_fee_usd_range[0]
            <= supplier.customer_fee_usd
            <= CONFIG.customer_fee_usd_range[1]
        )


def test_contract_durations_from_one_to_three_seasons(world):
    for contract in world.contracts:
        assert 1 <= contract.duration_seasons <= 3
        assert contract.start_season == CONFIG.initial_season
        assert (
            CONFIG.salary_demand_usd_range[0]
            <= contract.salary_usd
            <= CONFIG.salary_demand_usd_range[1]
        )


def test_custom_config_respected():
    config = WorldConfig(
        driver_attribute_range=(60, 65),
        age_range=(20, 30),
        age_mode=24,
        potential_range=(50, 60),
    )
    world = generate(7, config)
    for driver in world.drivers:
        for name in DRIVER_ATTRIBUTES:
            assert 60 <= getattr(driver, name) <= 65
        assert 20 <= driver.age <= 30
        assert 50 <= driver.potential <= 60


# ---------------------------------------------------------------------------
# Spending personalities
# ---------------------------------------------------------------------------


def test_every_ai_team_has_a_spending_personality(world):
    """Profilo dalla rosa configurata, focus di sviluppo dai valori validi (FOR-26)."""
    profiles = {
        (p.profile, p.spending_propensity, p.risk_tolerance) for p in CONFIG.available_personalities
    }
    for team in world.ai_teams:
        personality = team.personality
        assert (
            personality.profile,
            personality.spending_propensity,
            personality.risk_tolerance,
        ) in profiles
        assert personality.focus in CONFIG.spending_focuses
        assert 0 <= personality.spending_propensity <= 1
        assert 0 <= personality.risk_tolerance <= 1


def test_focus_varies_across_the_grid(world):
    """Il focus di sviluppo non e' identico per tutta la Griglia (FOR-26)."""
    assert len({team.personality.focus for team in world.ai_teams}) > 1


def test_ai_teams_have_distinct_livery_colors(world):
    """Ogni squadra AI ha due colori di livrea, distinti dalle altre (colori-team)."""
    liveries = [(team.primary_color, team.secondary_color) for team in world.ai_teams]
    assert all(primary and secondary for primary, secondary in liveries)
    assert len(set(liveries)) == len(liveries)


def test_config_rejects_too_few_livery_colors():
    with pytest.raises(ValueError):
        WorldConfig(team_livery_colors=(("#ffffff", "#000000"),))


# ---------------------------------------------------------------------------
# Hidden potential and nationalities
# ---------------------------------------------------------------------------


def test_hidden_potential_distinct_from_the_six_attributes(world):
    for driver in world.drivers:
        visible = driver.visible_attributes
        assert set(visible) == set(DRIVER_ATTRIBUTES)
        assert "potential" not in visible


def test_nationalities_among_the_weighted_ones(world):
    allowed = {nation for nation, _ in CONFIG.nationality_weights}
    assert all(driver.nationality in allowed for driver in world.drivers)


def test_nationalities_in_lowercase_iso_alpha2(world):
    # Canonical project form: lowercase ISO 3166-1 alpha-2 code,
    # matching the drivers.nationality column in the DB schema.
    for driver in world.drivers:
        assert len(driver.nationality) == 2
        assert driver.nationality.isalpha()
        assert driver.nationality == driver.nationality.lower()


def test_nationalities_follow_talent_pool_weights():
    # Deterministic aggregate over the fixed seeds: big talent pools
    # (weight 14) must produce more drivers than long-tail ones (weight 1).
    counts = Counter(
        driver.nationality for world in _WORLD_CACHE.values() for driver in world.drivers
    )
    weights = dict(CONFIG.nationality_weights)
    big = sum(counts[n] for n, weight in weights.items() if weight >= 8)
    tail = sum(counts[n] for n, weight in weights.items() if weight <= 2)
    assert big > tail


# ---------------------------------------------------------------------------
# Genere dei piloti e coerenza dei nomi (No al Patriarcato)
# ---------------------------------------------------------------------------


def _recognisably_female(driver) -> bool:
    """Vero se il nome proprio appartiene al solo pool femminile della nazione."""
    male_first, female_first, _ = DRIVER_NAMES[driver.nationality]
    first = driver.name.split(" ", 1)[0]
    return first in female_first and first not in male_first


def _recognisably_male(driver) -> bool:
    """Vero se il nome proprio appartiene al solo pool maschile della nazione."""
    male_first, female_first, _ = DRIVER_NAMES[driver.nationality]
    first = driver.name.split(" ", 1)[0]
    return first in male_first and first not in female_first


def test_roster_includes_both_men_and_women():
    # Aggregato deterministico sui seed fissi: il roster mescola i due generi.
    drivers = [driver for world in _WORLD_CACHE.values() for driver in world.drivers]
    assert any(_recognisably_female(driver) for driver in drivers)
    assert any(_recognisably_male(driver) for driver in drivers)


def test_every_first_name_belongs_to_its_nationality_pool():
    # Coerenza nome/genere: il nome proprio viene sempre da un pool della nazione.
    for world in _WORLD_CACHE.values():
        for driver in world.drivers:
            male_first, female_first, _ = DRIVER_NAMES[driver.nationality]
            first = driver.name.split(" ", 1)[0]
            assert first in set(male_first) | set(female_first)


def test_all_women_when_probability_one():
    world = generate(3, WorldConfig(female_probability=1.0))
    assert all(not _recognisably_male(driver) for driver in world.drivers)
    assert any(_recognisably_female(driver) for driver in world.drivers)


def test_all_men_when_probability_zero():
    world = generate(3, WorldConfig(female_probability=0.0))
    assert all(not _recognisably_female(driver) for driver in world.drivers)
    assert any(_recognisably_male(driver) for driver in world.drivers)


def test_config_rejects_female_probability_out_of_range():
    with pytest.raises(ValueError):
        WorldConfig(female_probability=1.5)
    with pytest.raises(ValueError):
        WorldConfig(female_probability=-0.1)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_seed_same_world():
    assert generate(424242) == generate(424242)


def test_same_seed_with_explicit_config():
    config = WorldConfig()
    assert generate(99, config) == generate(99, config)


@pytest.mark.parametrize(("seed_a", "seed_b"), [(0, 1), (1, 2), (42, 43), (7, 1000)])
def test_different_seeds_different_worlds(seed_a, seed_b):
    assert generate(seed_a) != generate(seed_b)


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


def test_config_rejects_too_many_engine_suppliers():
    # 4 AI teams are not enough for 4 suppliers plus one own-engine team.
    with pytest.raises(ValueError):
        WorldConfig(ai_team_count=4)


def test_config_rejects_inverted_range():
    with pytest.raises(ValueError):
        WorldConfig(driver_attribute_range=(90, 40))


def test_config_rejects_nationality_without_name_pool():
    with pytest.raises(ValueError):
        WorldConfig(nationality_weights=(("Atlantide", 5),))
