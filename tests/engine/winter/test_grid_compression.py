"""La regressione comprime i distacchi: simulazione headless multi-stagione.

Deliverable chiave di FOR-32: nessuna squadra domina per sempre. Su molte
stagioni, con shock di sviluppo casuali stagione per stagione, lo spread
della Griglia (max-min e deviazione standard degli Attributi vettura) non
diverge nel tempo quando agisce il Carry-over con regressione verso la
media. Il confronto col caso senza regressione (keep_ratio=1.0) mostra che
e' proprio la regressione a tenere insieme la Griglia.

Tutto deterministico col seed: la simulazione e' headless, niente gare,
solo l'evoluzione degli Attributi vettura stagione su stagione.
"""

import statistics
from dataclasses import replace
from random import Random

from fm_engine.winter.carryover import CarryoverConfig, apply_carryover
from fm_engine.world import generate
from fm_engine.world.models import CAR_ATTRIBUTES

SEED = 42
SEASONS = 40
# Shock di sviluppo per stagione, in punti: ogni squadra spinge un po' i
# suoi attributi in modo casuale (chi piu', chi meno), come farebbero i
# Progetti e il caso. E' la forza che, senza Carry-over, farebbe divergere.
_SHOCK_RANGE = (-6, 6)


def _grid_attribute_lists(world) -> dict[str, list[int]]:
    """Per ogni Attributo vettura, la lista dei valori sulle 10 squadre AI."""
    return {name: [getattr(team, name) for team in world.ai_teams] for name in CAR_ATTRIBUTES}


def _max_spread(world) -> float:
    """Lo spread massimo (max-min) tra tutti gli Attributi della Griglia AI."""
    lists = _grid_attribute_lists(world)
    return max(max(values) - min(values) for values in lists.values())


def _mean_stdev(world) -> float:
    """La deviazione standard media degli Attributi sulla Griglia AI."""
    lists = _grid_attribute_lists(world)
    return statistics.fmean(statistics.pstdev(values) for values in lists.values())


def _apply_development_shocks(world, rng: Random):
    """Spinge a caso gli Attributi di ogni squadra AI di una stagione."""
    low, high = _SHOCK_RANGE
    new_teams = []
    for team in world.ai_teams:
        updates = {}
        for name in CAR_ATTRIBUTES:
            value = getattr(team, name) + rng.randint(low, high)
            updates[name] = max(0, min(100, value))
        new_teams.append(replace(team, **updates))
    return replace(world, ai_teams=tuple(new_teams))


def _simulate(keep_ratio: float) -> list[float]:
    """Spread massimo per stagione: shock di sviluppo poi Carry-over."""
    world = generate(SEED)
    rng = Random(f"compression:{keep_ratio}")
    config = CarryoverConfig(keep_ratio=keep_ratio)
    spreads = [_max_spread(world)]
    for _ in range(SEASONS):
        world = _apply_development_shocks(world, rng)
        world = apply_carryover(world, config)
        spreads.append(_max_spread(world))
    return spreads


def test_carryover_keeps_the_grid_spread_bounded():
    """Con la regressione lo spread non diverge: resta dentro un tetto sano."""
    spreads = _simulate(keep_ratio=0.7)
    # Lo spread si stabilizza: la media delle ultime 20 stagioni non e'
    # molto piu' alta del punto di partenza (la regressione tiene).
    steady = statistics.fmean(spreads[-20:])
    assert steady <= spreads[0] + 25, f"spread divergente: {steady} vs iniziale {spreads[0]}"
    # E non esplode mai oltre la scala 0-100.
    assert max(spreads) <= 100


def test_regression_compresses_more_than_no_regression():
    """La regressione comprime davvero: spread minore che senza Carry-over."""
    with_regression = _simulate(keep_ratio=0.7)
    no_regression = _simulate(keep_ratio=1.0)
    steady_with = statistics.fmean(with_regression[-20:])
    steady_without = statistics.fmean(no_regression[-20:])
    assert steady_with < steady_without, (
        f"la regressione deve comprimere: con {steady_with}, senza {steady_without}"
    )


def test_no_team_dominates_forever():
    """Nessuna squadra resta in testa per sempre: il leader cambia nel tempo.

    Con shock e Carry-over, la squadra col miglior punteggio medio vettura
    non e' la stessa per tutta la simulazione: la regressione riavvicina
    tutti, lo sviluppo rimescola la testa.
    """
    world = generate(SEED)
    rng = Random("dominance")
    config = CarryoverConfig(keep_ratio=0.7)
    leaders = []
    for _ in range(SEASONS):
        world = _apply_development_shocks(world, rng)
        world = apply_carryover(world, config)
        scores = {
            team.id: statistics.fmean(getattr(team, name) for name in CAR_ATTRIBUTES)
            for team in world.ai_teams
        }
        leaders.append(max(scores, key=scores.get))
    # Piu' squadre diverse hanno guidato la Griglia nel tempo.
    assert len(set(leaders)) >= 3, f"troppo poche squadre in testa: {set(leaders)}"


def test_mean_stdev_does_not_grow_unbounded():
    """La deviazione standard media non cresce stagione dopo stagione."""
    world = generate(SEED)
    rng = Random("stdev")
    config = CarryoverConfig(keep_ratio=0.7)
    first_stdev = _mean_stdev(world)
    for _ in range(SEASONS):
        world = _apply_development_shocks(world, rng)
        world = apply_carryover(world, config)
    last_stdev = _mean_stdev(world)
    # La dispersione resta nello stesso ordine di grandezza (non diverge).
    assert last_stdev <= first_stdev * 2.5 + 5
