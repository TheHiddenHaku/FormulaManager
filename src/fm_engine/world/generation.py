"""Generazione deterministica del Mondo di inizio Carriera.

generate(seed, config) e' il cuore su cui la TUI (T1.3.1) costruisce una
nuova Carriera: stesso seed, stesso Mondo, sempre. Tutta la casualita'
passa da un unico random.Random(seed) consumato in ordine fisso; nessuno
stato globale, nessun I/O (motore puro, ADR 0002).

Sequenza di generazione (l'ordine e' parte del contratto di determinismo):
1. Motoristi (3-4) con Potenza motore e canone Cliente.
2. Squadre AI (10) con rapporti di fornitura, attributi vettura,
   economia, Filosofia telaio e personalita' di spesa.
3. Piloti (22) con nazionalita' pesate sui vivai reali, eta' plausibili,
   i 6 Attributi pilota, il Potenziale nascosto e l'ingaggio richiesto.
4. Contratti iniziali: 2 piloti per squadra AI, durata 1-3 stagioni;
   gli ultimi 2 piloti del roster restano liberi.
5. Genere dei piloti (No al Patriarcato): uomini e donne secondo la
   proporzione di config, con nome anagrafico coerente. Assegnato dopo
   piloti e contratti per non alterare la mappatura seed -> Mondo.
"""

import random
from dataclasses import replace

from fm_engine.world.models import (
    DRIVER_ATTRIBUTES,
    Contract,
    Driver,
    EngineSupplier,
    PlayerSlot,
    Team,
    World,
    WorldConfig,
)
from fm_engine.world.nationalities import (
    GENDER_FEMALE,
    GENDER_MALE,
    first_name_pool,
    surname_pool,
)

# Rounding step for generated amounts, for readable figures.
_USD_AMOUNT_STEP = 100_000

# Maximum attempts at drawing an unused driver name before accepting a
# namesake (small pools in custom configs).
_NAME_ATTEMPTS = 100


def generate(seed: int, config: WorldConfig | None = None) -> World:
    """Genera il Mondo completo di inizio Carriera in modo deterministico.

    Due chiamate con lo stesso seed e la stessa config producono Mondi
    identici (uguaglianza strutturale tra dataclass frozen). Con config
    omessa si usano i default tarabili di WorldConfig.
    """
    if config is None:
        config = WorldConfig()
    rng = random.Random(seed)

    engine_suppliers = _generate_engine_suppliers(rng, config)
    ai_teams = _generate_teams(rng, config, engine_suppliers)
    drivers = _generate_drivers(rng, config)
    contracts = _generate_contracts(rng, config, ai_teams, drivers)
    # Gender pass (No al Patriarcato): assigned after drivers and contracts so
    # the core seed -> world mapping (attributes, contracts) stays unchanged.
    # Women get a name from the female pool; men keep the default name.
    drivers = _assign_genders(rng, config, drivers)

    return World(
        seed=seed,
        config=config,
        ai_teams=ai_teams,
        player_slot=PlayerSlot(),
        drivers=drivers,
        engine_suppliers=engine_suppliers,
        contracts=contracts,
    )


def _round_amount(amount: float, minimum: int, maximum: int) -> int:
    """Arrotonda al passo standard restando dentro [minimum, maximum]."""
    rounded = round(amount / _USD_AMOUNT_STEP) * _USD_AMOUNT_STEP
    return min(max(rounded, minimum), maximum)


def _amount_in_range(rng: random.Random, interval: tuple[int, int]) -> int:
    """Estrae un importo uniforme nel range, arrotondato al passo standard."""
    minimum, maximum = interval
    return _round_amount(rng.uniform(minimum, maximum), minimum, maximum)


def _generate_engine_suppliers(
    rng: random.Random, config: WorldConfig
) -> tuple[EngineSupplier, ...]:
    """Genera 3-4 Motoristi indipendenti con nome di fantasia editabile."""
    count = rng.randint(config.min_engine_suppliers, config.max_engine_suppliers)
    names = rng.sample(config.engine_supplier_names, k=count)
    return tuple(
        EngineSupplier(
            id=index,
            name=name,
            engine_power=rng.randint(*config.car_attribute_range),
            customer_fee_usd=_amount_in_range(rng, config.customer_fee_usd_range),
        )
        for index, name in enumerate(names, start=1)
    )


def _assign_supply_deals(
    rng: random.Random, config: WorldConfig, engine_suppliers: tuple[EngineSupplier, ...]
) -> list[int | None]:
    """Decide per ogni squadra AI l'engine_supplier_id (None = motore in proprio).

    Garanzie strutturali: ogni Motorista ha almeno un Cliente e almeno una
    squadra produce il motore in proprio. Le squadre restanti scelgono a
    caso tra produzione propria e uno dei Motoristi.
    """
    positions = list(range(config.ai_team_count))
    rng.shuffle(positions)
    supply_deals: list[int | None] = [None] * config.ai_team_count
    # One guaranteed customer per engine supplier.
    for index, supplier in enumerate(engine_suppliers):
        supply_deals[positions[index]] = supplier.id
    # At least one team building its own engine (already None, made explicit).
    supply_deals[positions[len(engine_suppliers)]] = None
    # The remaining teams choose freely.
    options: list[int | None] = [None, *(supplier.id for supplier in engine_suppliers)]
    for position in positions[len(engine_suppliers) + 1 :]:
        supply_deals[position] = rng.choice(options)
    return supply_deals


def _generate_teams(
    rng: random.Random, config: WorldConfig, engine_suppliers: tuple[EngineSupplier, ...]
) -> tuple[Team, ...]:
    """Genera le squadre AI: fornitura motore, vettura, economia, personalita'."""
    names = rng.sample(config.team_names, k=config.ai_team_count)
    supply_deals = _assign_supply_deals(rng, config, engine_suppliers)
    supplier_powers = {supplier.id: supplier.engine_power for supplier in engine_suppliers}
    teams = []
    for index, name in enumerate(names, start=1):
        engine_supplier_id = supply_deals[index - 1]
        if engine_supplier_id is None:
            # Own engine: the engine power belongs to the team.
            engine_power = rng.randint(*config.car_attribute_range)
        else:
            # Customer: engine power shared with the supplying engine supplier.
            engine_power = supplier_powers[engine_supplier_id]
        teams.append(
            Team(
                id=index,
                name=name,
                prestige=rng.randint(*config.prestige_range),
                cash_usd=_amount_in_range(rng, config.cash_usd_range),
                chassis_philosophy=rng.choice(config.chassis_philosophies),
                engine_supplier_id=engine_supplier_id,
                engine_power=engine_power,
                downforce=rng.randint(*config.car_attribute_range),
                aero_efficiency=rng.randint(*config.car_attribute_range),
                mechanical_grip=rng.randint(*config.car_attribute_range),
                tyre_management=rng.randint(*config.car_attribute_range),
                reliability=rng.randint(*config.car_attribute_range),
                # Development focus in round-robin over the team index:
                # varied and distinguishable (FOR-26) without consuming
                # the rng stream (same seed, same World as before).
                personality=replace(
                    rng.choice(config.available_personalities),
                    focus=config.spending_focuses[(index - 1) % len(config.spending_focuses)],
                ),
            )
        )
    return tuple(teams)


def _draw_age(rng: random.Random, config: WorldConfig) -> int:
    """Eta' plausibile: triangolare con moda configurabile, code agli estremi."""
    minimum, maximum = config.age_range
    age = round(rng.triangular(minimum, maximum, config.age_mode))
    return min(max(age, minimum), maximum)


def _draw_gender(rng: random.Random, config: WorldConfig) -> str:
    """Estrae il genere del pilota secondo la proporzione di donne in config."""
    return GENDER_FEMALE if rng.random() < config.female_probability else GENDER_MALE


def _draw_driver_name(rng: random.Random, nationality: str, gender: str, used: set[str]) -> str:
    """Compone nome e cognome coerenti col genere, evitando omonimi."""
    first_names = first_name_pool(nationality, gender)
    last_names = surname_pool(nationality)
    for _ in range(_NAME_ATTEMPTS):
        full_name = f"{rng.choice(first_names)} {rng.choice(last_names)}"
        if full_name not in used:
            used.add(full_name)
            return full_name
    # Pool exhausted (very tight custom config): namesake accepted.
    return full_name


def _salary_demand(rng: random.Random, config: WorldConfig, attribute_mean: float) -> int:
    """Ingaggio proporzionale alla forza del pilota, con rumore +-10%.

    La media dei 6 Attributi mappa linearmente il range attributi sul
    range ingaggi: i piloti migliori chiedono di piu'.
    """
    attr_min, attr_max = config.driver_attribute_range
    salary_min, salary_max = config.salary_demand_usd_range
    if attr_max == attr_min:
        fraction = 0.5
    else:
        fraction = (attribute_mean - attr_min) / (attr_max - attr_min)
    base = salary_min + fraction * (salary_max - salary_min)
    return _round_amount(base * rng.uniform(0.9, 1.1), salary_min, salary_max)


def _generate_drivers(rng: random.Random, config: WorldConfig) -> tuple[Driver, ...]:
    """Genera il roster dei 22 piloti con Potenziale nascosto.

    Nazionalita' estratte con i pesi dei vivai reali; i 6 Attributi pilota
    e il Potenziale sono uniformi nei rispettivi range di config (valori
    di partenza tarabili).
    """
    nations = [nation for nation, _ in config.nationality_weights]
    weights = [weight for _, weight in config.nationality_weights]
    used_names: set[str] = set()
    drivers = []
    for index in range(1, config.total_drivers + 1):
        nationality = rng.choices(nations, weights=weights, k=1)[0]
        attributes = {
            name: rng.randint(*config.driver_attribute_range) for name in DRIVER_ATTRIBUTES
        }
        mean = sum(attributes.values()) / len(attributes)
        drivers.append(
            Driver(
                id=index,
                # Default (male) name; the gender pass renames the women later.
                name=_draw_driver_name(rng, nationality, GENDER_MALE, used_names),
                nationality=nationality,
                age=_draw_age(rng, config),
                potential=rng.randint(*config.potential_range),
                salary_demand_usd=_salary_demand(rng, config, mean),
                **attributes,
            )
        )
    return tuple(drivers)


def _assign_genders(
    rng: random.Random, config: WorldConfig, drivers: tuple[Driver, ...]
) -> tuple[Driver, ...]:
    """Assegna il genere a ogni pilota e da' alle donne un nome coerente.

    I piloti possono essere uomini o donne (No al Patriarcato): per ciascuno
    si estrae il genere con la proporzione di config.female_probability. Gli
    uomini tengono il nome gia' generato; alle donne si assegna un nome dal
    pool femminile della loro nazionalita' (cognomi condivisi), evitando
    omonimi. Il genere e' una proprieta' di generazione: non un campo del
    pilota, ma e' riflesso nel nome anagrafico. La fase viene dopo piloti e
    contratti per non alterare la mappatura seed -> Mondo di attributi e
    contratti (l'unico effetto e' il nome delle donne).
    """
    used = {driver.name for driver in drivers}
    result = []
    for driver in drivers:
        if _draw_gender(rng, config) == GENDER_FEMALE:
            name = _draw_driver_name(rng, driver.nationality, GENDER_FEMALE, used)
            result.append(replace(driver, name=name))
        else:
            result.append(driver)
    return tuple(result)


def _generate_contracts(
    rng: random.Random,
    config: WorldConfig,
    ai_teams: tuple[Team, ...],
    drivers: tuple[Driver, ...],
) -> tuple[Contract, ...]:
    """Assegna 2 piloti a ogni squadra AI; gli ultimi del mazzo restano liberi.

    Lo stipendio del Contratto coincide con l'ingaggio richiesto del
    pilota; la durata e' uniforme nel range 1-3 stagioni.
    """
    deck = list(drivers)
    rng.shuffle(deck)
    contracts = []
    for team_index, team in enumerate(ai_teams):
        start = team_index * config.drivers_per_team
        for driver in deck[start : start + config.drivers_per_team]:
            contracts.append(
                Contract(
                    driver_id=driver.id,
                    team_id=team.id,
                    start_season=config.initial_season,
                    duration_seasons=rng.randint(*config.contract_duration_range),
                    salary_usd=driver.salary_demand_usd,
                )
            )
    return tuple(contracts)
