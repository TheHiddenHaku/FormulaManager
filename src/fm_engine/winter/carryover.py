"""Carry-over della vettura tra due stagioni (FOR-32).

La vettura della stagione nuova eredita una quota degli Attributi vettura
attuali, con regressione verso la media di griglia: ogni attributo si
sposta dal valore vecchio verso la media di quella colonna sull'intera
Griglia (giocatore piu' squadre AI). L'effetto chiave del PRD: i distacchi
si comprimono, nessuna squadra resta in testa (o in coda) per sempre,
perche' chi e' sopra la media perde di piu' e chi e' sotto guadagna.

Formula per attributo:
    nuovo = keep_ratio * vecchio + (1 - keep_ratio) * media_di_griglia

Con keep_ratio in [0, 1]: 1 = nessuna regressione (la vettura si porta
dietro tutto), 0 = appiattimento totale sulla media. Il valore di
partenza tarabile sta in CarryoverConfig.keep_ratio.

apply_carryover(world) ritorna un World nuovo (frozen, motore puro ADR
0002) con la vettura del giocatore e quelle delle squadre AI regredite.
Va chiamato nella transizione di stagione, prima dei Progetti invernali e
della rinegoziazione, che operano sulla vettura gia' regredita.

Tutti i coefficienti vivono in CarryoverConfig (tarabili, tuning a FOR-34).
"""

from dataclasses import dataclass, replace

from fm_engine.world.models import (
    CAR_ATTRIBUTES,
    World,
)

# Scala 0-100 degli Attributi vettura (schema DB e WorldConfig).
_ATTRIBUTE_FLOOR = 0
_ATTRIBUTE_CEILING = 100


@dataclass(frozen=True)
class CarryoverConfig:
    """Parametri tarabili del Carry-over, niente valori sparsi nel codice.

    keep_ratio e' la quota di Attributo vettura che la stagione nuova
    eredita dalla vecchia; il resto regredisce verso la media di griglia.
    Valore di partenza 0.7: la vettura conserva il grosso del suo carattere
    ma il 30% di ogni attributo si avvicina alla media, cosi' i distacchi
    si comprimono di stagione in stagione senza azzerare le differenze.
    """

    keep_ratio: float = 0.7

    def __post_init__(self) -> None:
        if not 0.0 <= self.keep_ratio <= 1.0:
            raise ValueError(f"keep_ratio must be in [0, 1], got {self.keep_ratio}")


def grid_attribute_means(world: World) -> dict[str, float]:
    """La media di griglia per ogni Attributo vettura (giocatore + AI).

    Considera la vettura del giocatore solo se la squadra e' gia'
    configurata (Setup squadra fatto): prima del wizard non ha attributi e
    la media e' quella delle sole squadre AI. La media e' il bersaglio
    della regressione del Carry-over.
    """
    cars: list[dict[str, int]] = [
        {name: getattr(team, name) for name in CAR_ATTRIBUTES} for team in world.ai_teams
    ]
    slot = world.player_slot
    if slot.is_set_up:
        cars.append(slot.car_attributes)
    if not cars:
        raise ValueError("grid has no cars: cannot compute attribute means")
    return {name: sum(car[name] for car in cars) / len(cars) for name in CAR_ATTRIBUTES}


def regress_attribute(value: int, mean: float, keep_ratio: float) -> int:
    """Il nuovo valore di un attributo regredito verso la media di griglia.

    keep_ratio del valore vecchio piu' la quota complementare della media,
    agganciato alla scala 0-100 e arrotondato all'intero piu' vicino.
    """
    regressed = keep_ratio * value + (1.0 - keep_ratio) * mean
    return int(round(max(_ATTRIBUTE_FLOOR, min(_ATTRIBUTE_CEILING, regressed))))


def carried_over_attributes(
    attributes: dict[str, int],
    means: dict[str, float],
    config: CarryoverConfig,
) -> dict[str, int]:
    """Gli Attributi vettura della stagione nuova, regrediti verso la media."""
    return {
        name: regress_attribute(attributes[name], means[name], config.keep_ratio)
        for name in CAR_ATTRIBUTES
    }


def apply_carryover(world: World, config: CarryoverConfig | None = None) -> World:
    """Applica il Carry-over a tutta la Griglia e ritorna il World nuovo.

    Ogni vettura (giocatore configurato e squadre AI) regredisce verso la
    media di griglia calcolata sugli attributi attuali. Le medie si calcolano
    una volta sola sullo stato di partenza: tutte le vetture regrediscono
    verso lo stesso bersaglio. Il World in ingresso resta intatto (frozen).
    """
    if config is None:
        config = CarryoverConfig()
    means = grid_attribute_means(world)

    new_ai_teams = tuple(
        replace(
            team,
            **carried_over_attributes(
                {name: getattr(team, name) for name in CAR_ATTRIBUTES}, means, config
            ),
        )
        for team in world.ai_teams
    )

    slot = world.player_slot
    if slot.is_set_up:
        slot = replace(slot, **carried_over_attributes(slot.car_attributes, means, config))

    return replace(world, ai_teams=new_ai_teams, player_slot=slot)
