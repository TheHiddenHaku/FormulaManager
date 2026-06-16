"""Test del ricambio generazionale del parco piloti (FOR-31, T5.2.2).

Engine-only: nessuna dipendenza da database o TUI. Coprono i tre
meccanismi (evoluzione annuale degli Attributi, Ritiri probabilistici
seedati, generazione di Giovani nel pool del Mercato) e l'effetto a regime
su una simulazione headless di 10 stagioni.
"""

from dataclasses import replace
from random import Random

from fm_engine.market import apply_market, open_market, resolve_market
from fm_engine.world import (
    active_driver_count,
    age_drivers,
    evolve_driver_attributes,
    generate,
    refresh_generation,
    replenish_youngsters,
    retire_drivers,
    retirement_probability,
)
from fm_engine.world.generational import generate_youngster
from fm_engine.world.models import DRIVER_ATTRIBUTES, Driver, WorldConfig

SEED = 42


def _driver(
    driver_id: int, age: int, potential: int, attr: int = 60, retired: bool = False
) -> Driver:
    return Driver(
        id=driver_id,
        name=f"Driver {driver_id}",
        nationality="it",
        age=age,
        one_lap_pace=attr,
        race_pace=attr,
        duels=attr,
        tyre_management=attr,
        wet_weather=attr,
        consistency=attr,
        potential=potential,
        salary_demand_usd=5_000_000,
        retired=retired,
    )


# ---------------------------------------------------------------------------
# 1. Evoluzione annuale degli Attributi
# ---------------------------------------------------------------------------


def test_young_high_potential_driver_grows():
    """Un Giovane con Potenziale alto cresce sugli Attributi visibili."""
    config = WorldConfig()
    young = _driver(1, age=20, potential=90, attr=55)
    evolved = evolve_driver_attributes(young, config)
    assert all(getattr(evolved, attr) >= 55 for attr in DRIVER_ATTRIBUTES)
    assert any(getattr(evolved, attr) > 55 for attr in DRIVER_ATTRIBUTES)


def test_old_low_potential_driver_declines():
    """Un anziano declina sugli Attributi visibili."""
    config = WorldConfig()
    old = _driver(1, age=36, potential=40, attr=75)
    evolved = evolve_driver_attributes(old, config)
    assert all(getattr(evolved, attr) <= 75 for attr in DRIVER_ATTRIBUTES)
    assert any(getattr(evolved, attr) < 75 for attr in DRIVER_ATTRIBUTES)


def test_evolution_is_bounded_to_0_100():
    """L'evoluzione resta nella scala di dominio 0-100."""
    config = WorldConfig()
    high = evolve_driver_attributes(_driver(1, age=18, potential=95, attr=99), config)
    low = evolve_driver_attributes(_driver(2, age=40, potential=20, attr=2), config)
    assert all(0 <= getattr(high, a) <= 100 for a in DRIVER_ATTRIBUTES)
    assert all(0 <= getattr(low, a) <= 100 for a in DRIVER_ATTRIBUTES)


def test_age_drivers_advances_age_and_freezes_retired():
    """age_drivers invecchia gli attivi di un anno e congela i ritirati."""
    config = WorldConfig()
    world = generate(SEED, config)
    retired_id = world.drivers[0].id
    world = replace(
        world,
        drivers=(replace(world.drivers[0], retired=True), *world.drivers[1:]),
    )
    aged = age_drivers(world)
    by_id = {d.id: d for d in world.drivers}
    for driver in aged.drivers:
        if driver.id == retired_id:
            assert driver.age == by_id[driver.id].age  # frozen
        else:
            assert driver.age == by_id[driver.id].age + 1


def test_same_driver_has_different_values_next_season():
    """Effetto end-to-end: lo stesso pilota ha valori diversi nella stagione N+1."""
    config = WorldConfig()
    world = generate(SEED, config)
    refreshed, _ = refresh_generation(world, concluded_year=2026, rng=Random(1))
    before = {d.id: d for d in world.drivers}
    changed = False
    for driver in refreshed.drivers:
        if driver.id in before and not driver.retired:
            original = before[driver.id]
            assert driver.age == original.age + 1
            if any(getattr(driver, a) != getattr(original, a) for a in DRIVER_ATTRIBUTES):
                changed = True
    assert changed, "almeno un pilota deve mutare gli Attributi tra le stagioni"


# ---------------------------------------------------------------------------
# 2. Ritiri probabilistici seedati
# ---------------------------------------------------------------------------


def test_retirement_probability_zero_below_threshold():
    config = WorldConfig(retirement_age=33)
    assert retirement_probability(30, config) == 0.0
    assert retirement_probability(32, config) == 0.0
    assert retirement_probability(33, config) > 0.0


def test_retirement_probability_grows_with_age_and_is_capped():
    config = WorldConfig()
    assert retirement_probability(33, config) < retirement_probability(38, config)
    assert retirement_probability(100, config) <= config.retirement_probability_cap
    assert retirement_probability(100, config) < 1.0  # mai obbligatorio


def test_retirements_are_deterministic_with_seed():
    """Stesso seed -> stessi Ritiri (seedabile e riproducibile)."""
    config = WorldConfig()
    drivers = tuple(_driver(i, age=37, potential=50) for i in range(1, 13))
    world = generate(SEED, config)
    world = replace(world, drivers=drivers, contracts=())
    a, ids_a = retire_drivers(world, Random(7))
    b, ids_b = retire_drivers(world, Random(7))
    assert ids_a == ids_b
    assert tuple(d.retired for d in a.drivers) == tuple(d.retired for d in b.drivers)


def test_exists_a_seed_with_no_retirements_and_one_with_retirements():
    """Esistono run senza Ritiri e run con Ritiri (mai obbligatori)."""
    config = WorldConfig()
    drivers = tuple(_driver(i, age=36, potential=50) for i in range(1, 13))
    world = replace(generate(SEED, config), drivers=drivers, contracts=())

    found_empty = False
    found_nonempty = False
    for seed in range(200):
        _, ids = retire_drivers(world, Random(seed))
        if ids:
            found_nonempty = True
        else:
            found_empty = True
        if found_empty and found_nonempty:
            break
    assert found_empty, "deve esistere una stagione senza alcun Ritiro"
    assert found_nonempty, "deve esistere una stagione con almeno un Ritiro"


def test_young_drivers_never_retire():
    """I Giovani non si ritirano: probabilita' nulla sotto la soglia."""
    config = WorldConfig()
    drivers = tuple(_driver(i, age=22, potential=50) for i in range(1, 11))
    world = replace(generate(SEED, config), drivers=drivers, contracts=())
    for seed in range(50):
        _, ids = retire_drivers(world, Random(seed))
        assert ids == ()


def test_retired_driver_leaves_the_active_pool_and_seat():
    """Effetto end-to-end: un Ritiro libera davvero il pilota dal parco attivo."""
    config = WorldConfig()
    world = generate(SEED, config)
    # Forza il primo pilota contrattualizzato a un'eta' da Ritiro certo.
    contracted_id = world.contracts[0].driver_id
    drivers = tuple(replace(d, age=45) if d.id == contracted_id else d for d in world.drivers)
    # Probabilita' al tetto a 45 anni; con piu' tentativi il Ritiro avviene.
    world = replace(world, drivers=drivers)
    retired = False
    for seed in range(100):
        after, ids = retire_drivers(world, Random(seed))
        if contracted_id in ids:
            retired = True
            by_id = {d.id: d for d in after.drivers}
            assert by_id[contracted_id].retired
            # Il pilota ritirato non entra nel pool del Mercato.
            market = open_market(after, concluded_year=2026)
            assert contracted_id not in market.available_driver_ids
            break
    assert retired, "con probabilita' al tetto un Ritiro deve avvenire in 100 tentativi"


# ---------------------------------------------------------------------------
# 3. Giovani nel pool del Mercato
# ---------------------------------------------------------------------------


def test_youngster_has_hidden_potential_and_low_age():
    config = WorldConfig()
    used: set[str] = set()
    youngster = generate_youngster(Random(3), config, driver_id=100, used_names=used)
    age_min, age_max = config.youngster_age_range
    potential_min, potential_max = config.youngster_potential_range
    assert age_min <= youngster.age <= age_max
    assert potential_min <= youngster.potential <= potential_max
    assert not youngster.retired


def test_replenish_brings_active_pool_to_target():
    config = WorldConfig(active_pool_target=24)
    world = generate(SEED, config)
    # Ritira meta' parco, poi rigenera.
    drivers = tuple(replace(d, retired=(i % 2 == 0)) for i, d in enumerate(world.drivers))
    world = replace(world, drivers=drivers)
    replenished, youngsters = replenish_youngsters(world, Random(5))
    assert active_driver_count(replenished) == config.active_pool_target
    assert len(youngsters) > 0


def test_generated_youngster_enters_market_pool_as_free_agent():
    """Effetto end-to-end: un Giovane generato compare nel pool del Mercato."""
    config = WorldConfig()
    world = generate(SEED, config)
    refreshed, _ = refresh_generation(world, concluded_year=2026, rng=Random(11))
    new_ids = {d.id for d in refreshed.drivers} - {d.id for d in world.drivers}
    # Se non ci sono Ritiri il parco e' gia' a regime: forza un buco.
    if not new_ids:
        drivers = tuple(replace(d, retired=(i < 5)) for i, d in enumerate(world.drivers))
        refreshed, _ = refresh_generation(
            replace(world, drivers=drivers), concluded_year=2026, rng=Random(11)
        )
        new_ids = {d.id for d in refreshed.drivers} - {d.id for d in world.drivers}
    assert new_ids, "almeno un Giovane deve essere generato quando il parco e' sotto target"
    market = open_market(refreshed, concluded_year=2026)
    assert new_ids & set(market.free_agent_ids), "i Giovani devono entrare come liberi nel pool"


def test_generated_youngster_is_engageable_through_apply_market():
    """Effetto end-to-end: un Giovane e' ingaggiabile col flusso esistente."""
    config = WorldConfig()
    world = generate(SEED, config)
    # Crea un buco: ritira 4 piloti cosi' i Giovani sono necessari.
    drivers = tuple(replace(d, retired=(i < 4)) for i, d in enumerate(world.drivers))
    refreshed, _ = refresh_generation(
        replace(world, drivers=drivers), concluded_year=2026, rng=Random(13)
    )
    market = open_market(refreshed, concluded_year=2026)
    market = resolve_market(refreshed, market, Random(13))
    closed_world = apply_market(refreshed, market)
    contracted_ids = {c.driver_id for c in closed_world.contracts}
    new_ids = {d.id for d in refreshed.drivers} - {d.id for d in world.drivers}
    # Ogni squadra ha esattamente i sedili attesi e nessun ritirato e' sotto contratto.
    by_id = {d.id: d for d in closed_world.drivers}
    assert all(not by_id[did].retired for did in contracted_ids)
    # Almeno un Giovane risulta ingaggiato (i buchi vanno riempiti coi liberi).
    assert new_ids & contracted_ids, "almeno un Giovane deve risultare sotto contratto"


# ---------------------------------------------------------------------------
# 5. Long-run: parco a regime su 10 stagioni
# ---------------------------------------------------------------------------


def _simulate_seasons(seed: int, n_seasons: int):
    """Simula n stagioni di solo ricambio + Mercato, headless. Ritorna le eta' medie."""
    config = WorldConfig()
    world = generate(seed, config)
    mean_ages = []
    for offset in range(n_seasons):
        concluded_year = config.initial_season + offset
        rng = Random(seed * 1_000 + offset * 100 + 900)
        world, _news = refresh_generation(world, concluded_year, rng)
        market = open_market(world, concluded_year)
        market = resolve_market(world, market, Random(seed * 1_000 + offset * 100 + 800))
        world = apply_market(world, market)
        active = [d for d in world.drivers if not d.retired]
        mean_ages.append(sum(d.age for d in active) / len(active))
    return world, mean_ages


def test_ten_seasons_keep_the_grid_fillable_and_age_stable():
    """Simulazione headless di 10 stagioni: parco a regime, eta' media nella banda."""
    for seed in (1, 7, 42, 99, 123):
        world, mean_ages = _simulate_seasons(seed, 10)
        config = world.config
        active = [d for d in world.drivers if not d.retired]
        grid_size = config.ai_team_count * config.drivers_per_team
        # Piloti attivi sufficienti a riempire la Griglia (piu' la riserva).
        assert len(active) >= grid_size, f"seed {seed}: parco insufficiente"
        # Eta' media stabile entro una banda definita per ogni stagione.
        for year, mean_age in enumerate(mean_ages):
            assert 23.0 <= mean_age <= 33.0, (
                f"seed {seed}, stagione {year}: eta' media {mean_age:.1f} fuori banda"
            )
        # Ogni squadra ha esattamente i suoi sedili dopo il Mercato.
        for team in world.ai_teams:
            count = sum(1 for c in world.contracts if c.team_id == team.id)
            assert count == config.drivers_per_team


def test_long_run_produces_retirements_overall():
    """Su 10 stagioni e piu' seed compaiono Ritiri (il ricambio e' vivo)."""
    total_new = 0
    for seed in (1, 7, 42):
        world, _ = _simulate_seasons(seed, 10)
        total_new += sum(1 for d in world.drivers if d.retired)
    assert total_new > 0, "su 10 stagioni e piu' seed devono esserci dei Ritiri"
