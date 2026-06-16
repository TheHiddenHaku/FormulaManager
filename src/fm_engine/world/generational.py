"""Ricambio generazionale del parco piloti tra le stagioni (FOR-31).

Tre meccanismi, applicati a fine stagione dentro la transizione, su un
World immutabile (ritorna sempre un World nuovo, motore puro ADR 0002):

1. Evoluzione annuale degli Attributi pilota guidata da eta' e Potenziale
   nascosto: i Giovani con buon Potenziale crescono, gli anziani declinano.
2. Ritiri di carriera probabilistici per gli anziani: possibili ma mai
   obbligatori (esistono stagioni senza alcun Ritiro). Seedabili e
   deterministici col seed. Ogni Ritiro produce una Notizia.
3. Generazione di Giovani con Potenziale nascosto e attributi di partenza
   bassi (Stime larghe nel gioco, perche' poco conosciuti): entrano nel
   roster senza Contratto, quindi nel pool del Mercato piloti come liberi.

L'entry point e' refresh_generation(world, concluded_year, rng): ritorna il
World aggiornato e le Notizie dell'intervallo. Va chiamato prima
dell'apertura del Mercato, cosi' i ritirati sono fuori dal pool e i Giovani
dentro quando le squadre AI e il giocatore ingaggiano.

Tutti i coefficienti vivono in WorldConfig (tarabili, tuning a FOR-34).
"""

from dataclasses import replace
from random import Random

from fm_engine.world.models import (
    DRIVER_ATTRIBUTES,
    Driver,
    World,
    WorldConfig,
)
from fm_engine.world.nationalities import DRIVER_NAMES

# Limiti dell'evoluzione annuale di un singolo Attributo, in punti su 100.
# La crescita di un Giovane di Potenziale alto e il declino di un anziano
# restano dentro questi tetti: niente salti irrealistici in una stagione.
_MAX_GROWTH_PER_YEAR = 4.0
_MAX_DECLINE_PER_YEAR = 5.0

# Scala del Potenziale (0-100) intorno alla media: sopra spinge la crescita,
# sotto la frena. 50 e' il Potenziale neutro.
_POTENTIAL_PIVOT = 50.0

# Attributo pilota minimo e massimo (la scala di dominio resta 0-100).
_ATTRIBUTE_FLOOR = 0
_ATTRIBUTE_CEILING = 100

# Tentativi di estrazione di un nome non gia' in uso prima di accettare un
# omonimo (pool nazionale piccolo in config personalizzate).
_NAME_ATTEMPTS = 100

# Passo di arrotondamento per l'ingaggio richiesto dei Giovani, come in
# generation._USD_AMOUNT_STEP: cifre leggibili.
_USD_AMOUNT_STEP = 100_000


def evolve_driver_attributes(driver: Driver, config: WorldConfig) -> Driver:
    """Evolve i 6 Attributi visibili di un pilota di un anno (eta' + Potenziale).

    Sotto l'eta' di picco il pilota cresce; la spinta scala col Potenziale
    nascosto sopra la media (un Giovane di gran Potenziale cresce di piu').
    Dall'eta' di picco in su declina, tanto piu' quanto piu' e' anziano. Il
    Potenziale e' nascosto: muta gli Attributi VISIBILI ma non si rivela.
    Ritorna un Driver nuovo (frozen); non tocca eta', id, ne' il flag retired.
    """
    potential_factor = (driver.potential - _POTENTIAL_PIVOT) / _POTENTIAL_PIVOT
    if driver.age < config.peak_age:
        # Crescita: anni che mancano al picco, modulati dal Potenziale.
        years_to_peak = config.peak_age - driver.age
        growth_weight = max(0.0, 0.5 + potential_factor)
        delta = min(_MAX_GROWTH_PER_YEAR, _MAX_GROWTH_PER_YEAR * growth_weight)
        # Piu' lontano dal picco, piu' margine di crescita (decresce verso il picco).
        delta *= min(1.0, years_to_peak / 4.0)
    else:
        # Declino: anni oltre il picco; un buon Potenziale rallenta la curva.
        years_past_peak = driver.age - config.peak_age
        decline_weight = max(0.0, 1.0 - potential_factor)
        delta = -min(
            _MAX_DECLINE_PER_YEAR,
            _MAX_DECLINE_PER_YEAR * decline_weight * min(1.0, years_past_peak / 4.0),
        )

    if delta == 0.0:
        return driver

    updates = {}
    for attribute in DRIVER_ATTRIBUTES:
        value = getattr(driver, attribute) + delta
        updates[attribute] = int(round(max(_ATTRIBUTE_FLOOR, min(_ATTRIBUTE_CEILING, value))))
    return replace(driver, **updates)


def age_drivers(world: World) -> World:
    """Invecchia di un anno i piloti attivi ed evolve i loro Attributi.

    I piloti ritirati restano congelati nel roster (storia della Carriera):
    non invecchiano ne' cambiano. Ritorna un World nuovo coi piloti attivi
    aggiornati. Lo stesso pilota avra' valori diversi nella stagione N+1.
    """
    config = world.config
    new_drivers = tuple(
        driver
        if driver.retired
        else evolve_driver_attributes(replace(driver, age=driver.age + 1), config)
        for driver in world.drivers
    )
    return replace(world, drivers=new_drivers)


def retirement_probability(age: int, config: WorldConfig) -> float:
    """La probabilita' di Ritiro a fine stagione per un pilota di data eta'.

    Zero sotto l'eta' di Ritiro; dalla soglia in su parte da una base e
    cresce di un incremento per ogni anno oltre, con un tetto. Mai 1: il
    Ritiro e' sempre possibile, mai obbligatorio.
    """
    if age < config.retirement_age:
        return 0.0
    years_over = age - config.retirement_age
    probability = config.retirement_base_probability + years_over * (
        config.retirement_probability_per_year
    )
    return min(config.retirement_probability_cap, probability)


def retire_drivers(world: World, rng: Random) -> tuple[World, tuple[int, ...]]:
    """Estrae i Ritiri di carriera tra gli anziani attivi (seedabile).

    Per ogni pilota attivo sopra l'eta' di Ritiro estrae il Ritiro con la
    sua probabilita'. Determinismo: stesso rng -> stessi Ritiri. Ritorna il
    World coi ritirati marcati (retired=True) e gli id dei piloti ritirati,
    in ordine di id. Puo' ritornare nessun Ritiro: e' un esito ammesso.
    """
    config = world.config
    retired_ids = []
    new_drivers = []
    for driver in world.drivers:
        if not driver.retired and rng.random() < retirement_probability(driver.age, config):
            new_drivers.append(replace(driver, retired=True))
            retired_ids.append(driver.id)
        else:
            new_drivers.append(driver)
    return replace(world, drivers=tuple(new_drivers)), tuple(retired_ids)


def _next_driver_id(world: World) -> int:
    """Il prossimo id pilota libero: massimo esistente piu' uno."""
    return max((driver.id for driver in world.drivers), default=0) + 1


def _draw_youngster_name(rng: Random, nationality: str, used: set[str]) -> str:
    """Compone nome e cognome dal pool della nazionalita', evitando omonimi."""
    first_names, last_names = DRIVER_NAMES[nationality]
    full_name = f"{rng.choice(first_names)} {rng.choice(last_names)}"
    for _ in range(_NAME_ATTEMPTS):
        if full_name not in used:
            used.add(full_name)
            return full_name
        full_name = f"{rng.choice(first_names)} {rng.choice(last_names)}"
    used.add(full_name)
    return full_name


def _round_amount(amount: float, minimum: int, maximum: int) -> int:
    """Arrotonda al passo standard restando dentro [minimum, maximum]."""
    rounded = round(amount / _USD_AMOUNT_STEP) * _USD_AMOUNT_STEP
    return min(max(rounded, minimum), maximum)


def generate_youngster(
    rng: Random, config: WorldConfig, driver_id: int, used_names: set[str]
) -> Driver:
    """Genera un Giovane: eta' bassa, Potenziale nascosto alto, attributi acerbi.

    Gli Attributi visibili partono nella meta' bassa del range (un Giovane e'
    grezzo), mentre il Potenziale e' tendenzialmente alto: il margine di
    crescita c'e' ma e' nascosto. Nel gioco un Giovane appena arrivato e'
    poco conosciuto, quindi le sue Stime sono naturalmente larghe (la
    conoscenza si costruisce con le prestazioni). L'ingaggio richiesto e'
    basso, proporzionato agli Attributi grezzi.
    """
    nations = [nation for nation, _ in config.nationality_weights]
    weights = [weight for _, weight in config.nationality_weights]
    nationality = rng.choices(nations, weights=weights, k=1)[0]

    attr_min, attr_max = config.driver_attribute_range
    # Meta' bassa del range attributi: i Giovani sono acerbi sui valori veri.
    youngster_attr_ceiling = attr_min + (attr_max - attr_min) // 2
    attributes = {name: rng.randint(attr_min, youngster_attr_ceiling) for name in DRIVER_ATTRIBUTES}
    mean = sum(attributes.values()) / len(attributes)

    salary_min, salary_max = config.salary_demand_usd_range
    if attr_max == attr_min:
        fraction = 0.0
    else:
        fraction = (mean - attr_min) / (attr_max - attr_min)
    salary_base = salary_min + fraction * (salary_max - salary_min)

    return Driver(
        id=driver_id,
        name=_draw_youngster_name(rng, nationality, used_names),
        nationality=nationality,
        age=rng.randint(*config.youngster_age_range),
        one_lap_pace=attributes["one_lap_pace"],
        race_pace=attributes["race_pace"],
        duels=attributes["duels"],
        tyre_management=attributes["tyre_management"],
        wet_weather=attributes["wet_weather"],
        consistency=attributes["consistency"],
        potential=rng.randint(*config.youngster_potential_range),
        salary_demand_usd=_round_amount(salary_base, salary_min, salary_max),
        retired=False,
    )


def active_driver_count(world: World) -> int:
    """Quanti piloti del roster sono ancora in attivita' (non ritirati)."""
    return sum(1 for driver in world.drivers if not driver.retired)


def replenish_youngsters(world: World, rng: Random) -> tuple[World, tuple[Driver, ...]]:
    """Genera Giovani finche' il parco attivo raggiunge l'obiettivo di config.

    I Giovani entrano nel roster senza Contratto: sono liberi, quindi
    finiscono nel pool del Mercato piloti (world.drivers_without_contract,
    pool.open_market) ed e' lo stesso flusso esistente a renderli
    ingaggiabili. Ritorna il World con i Giovani aggiunti e la tupla dei
    Giovani generati (vuota se il parco e' gia' a regime).
    """
    config = world.config
    target = config.active_pool_target
    used_names = {driver.name for driver in world.drivers}
    next_id = _next_driver_id(world)
    new_youngsters = []
    while active_driver_count(world) + len(new_youngsters) < target:
        youngster = generate_youngster(rng, config, next_id, used_names)
        new_youngsters.append(youngster)
        next_id += 1
    if not new_youngsters:
        return world, ()
    return replace(world, drivers=(*world.drivers, *new_youngsters)), tuple(new_youngsters)


def retirement_news(
    world: World, retired_ids: tuple[int, ...], concluded_year: int
) -> tuple[str, ...]:
    """Le Notizie dei Ritiri: una voce di rassegna stampa leggibile per pilota.

    Stringhe UI in italiano (lessico di dominio: Ritiro di carriera). Vuota
    se nessuno si e' ritirato.
    """
    by_id = {driver.id: driver for driver in world.drivers}
    news = []
    for driver_id in retired_ids:
        driver = by_id[driver_id]
        news.append(
            f"Ritiro di carriera: {driver.name} ({driver.age} anni) lascia le corse "
            f"al termine della stagione {concluded_year}."
        )
    return tuple(news)


def refresh_generation(
    world: World, concluded_year: int, rng: Random
) -> tuple[World, tuple[str, ...]]:
    """Il ricambio generazionale di fine stagione: aging, Ritiri, Giovani.

    Applica in ordine, su un World nuovo:
    1. invecchiamento ed evoluzione degli Attributi dei piloti attivi;
    2. Ritiri di carriera probabilistici degli anziani (seedabili);
    3. generazione di Giovani liberi finche' il parco attivo torna a regime.

    Ritorna il World aggiornato e le Notizie (i Ritiri; i Giovani entrano in
    sordina, come da dominio). Va chiamato prima di open_market: i ritirati
    escono dal pool e i Giovani vi entrano come liberi. Deterministico col
    seed di rng.
    """
    aged = age_drivers(world)
    retired_world, retired_ids = retire_drivers(aged, rng)
    replenished, _new_youngsters = replenish_youngsters(retired_world, rng)
    news = retirement_news(replenished, retired_ids, concluded_year)
    return replenished, news
