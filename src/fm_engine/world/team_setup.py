"""Setup squadra: applicazione pura delle scelte del wizard (FOR-7).

apply_team_setup(world, choices) e' la funzione con cui il wizard
post-creazione (fm_tui.screens.team_setup) compone la squadra del
giocatore: 2 piloti dal roster, motore interno oppure Cliente di un
Motorista, Filosofia telaio. Motore puro (ADR 0002): nessun I/O, World
e' frozen e si ritorna un Mondo nuovo; il Mondo in ingresso resta intatto.

Decisioni di design (FOR-7):
- Roster completo: il giocatore sceglie 2 piloti QUALSIASI tra i 22 del
  Mondo, contrattualizzati nelle squadre AI o liberi. E' la "scommessa
  informata" del PRD: gli attributi restano Stime, l'ingaggio richiesto
  e' pubblico.
- Rimpiazzi automatici: ogni squadra AI che perde un pilota riceve uno
  dei liberi rimasti, con un nuovo Contratto di durata pari a quella del
  Contratto rimpiazzato e stipendio pari all'ingaggio richiesto del
  subentrante. Invarianti dopo il setup: 22 piloti totali, ogni squadra
  (incluso il giocatore) esattamente 2 piloti, nessun doppio Contratto.
- Vettura iniziale: baseline neutra a meta' del range attributi di
  WorldConfig (meta' griglia). Motore interno = Potenza motore alla
  baseline (sviluppo libero, costo alto); Cliente = Potenza motore del
  Motorista, condivisa. Filosofia veloce = bonus su aero_efficiency e
  malus su downforce e mechanical_grip; tecnica = l'esatto inverso;
  balanced = nessun delta. I valori sono tarabili in TeamSetupConfig.
- Contratti del giocatore: durata default tarabile, stipendio uguale
  all'ingaggio richiesto del pilota. Nessuna negoziazione (fuori scope).
- I costi del passo motore (costo interno vs canone Cliente) sono
  informativi: nessuna Cassa o Cap runtime (T4.x).
"""

from dataclasses import dataclass, replace

from fm_engine.world.models import (
    CAR_ATTRIBUTES,
    CHASSIS_PHILOSOPHIES,
    PLAYER_TEAM_ID,
    Contract,
    World,
    WorldConfig,
)

# Bounds of the 0-100 attribute scale (DB schema and WorldConfig).
_SCALE_MIN = 0
_SCALE_MAX = 100


@dataclass(frozen=True)
class TeamSetupConfig:
    """Parametri tarabili del Setup squadra, niente valori sparsi nel codice.

    chassis_bonus e chassis_malus definiscono la Filosofia veloce (bonus
    su aero_efficiency, malus su downforce e mechanical_grip); la tecnica
    applica l'esatto inverso, quindi le due scelte muovono la stessa
    quantita' totale di attributi.
    """

    # Default duration of the player's driver contracts, in seasons.
    player_contract_duration_seasons: int = 2
    # Informative yearly cost of building the engine in-house, shown in
    # the wizard next to the suppliers' customer fees (no runtime economy).
    in_house_engine_cost_usd: int = 30_000_000
    # Fast philosophy: +bonus on aero_efficiency, -malus on downforce and
    # mechanical_grip. Technical philosophy: exact inverse.
    chassis_bonus: int = 8
    chassis_malus: int = 4

    def __post_init__(self) -> None:
        if self.player_contract_duration_seasons < 1:
            raise ValueError("player_contract_duration_seasons must be at least 1")
        if self.in_house_engine_cost_usd < 0:
            raise ValueError("in_house_engine_cost_usd cannot be negative")
        if self.chassis_bonus < 0 or self.chassis_malus < 0:
            raise ValueError("chassis_bonus and chassis_malus cannot be negative")


@dataclass(frozen=True)
class TeamSetupChoices:
    """Le scelte del wizard: 2 piloti, motore, Filosofia telaio.

    engine_supplier_id None = motore interno; valorizzato = Cliente del
    Motorista indicato (Potenza motore condivisa col fornitore).
    """

    driver_ids: tuple[int, int]
    engine_supplier_id: int | None
    chassis_philosophy: str


def baseline_car_attribute(config: WorldConfig) -> int:
    """La baseline neutra di un Attributo vettura: meta' griglia.

    Punto medio del range attributi vettura di WorldConfig: la vettura
    del giocatore parte ne' in testa ne' in coda.
    """
    minimum, maximum = config.car_attribute_range
    return round((minimum + maximum) / 2)


def _clamp(value: int) -> int:
    return min(max(value, _SCALE_MIN), _SCALE_MAX)


def initial_car_attributes(
    world: World,
    engine_supplier_id: int | None,
    chassis_philosophy: str,
    config: TeamSetupConfig | None = None,
) -> dict[str, int]:
    """Gli Attributi vettura iniziali del giocatore per le scelte date.

    Baseline neutra su tutti gli attributi, poi: Potenza motore del
    Motorista se Cliente (condivisa), baseline se interno; delta della
    Filosofia telaio su aero_efficiency, downforce e mechanical_grip,
    agganciati alla scala 0-100. Usata sia da apply_team_setup sia
    dall'anteprima del wizard (passo Filosofia telaio).
    """
    if config is None:
        config = TeamSetupConfig()
    if chassis_philosophy not in CHASSIS_PHILOSOPHIES:
        raise ValueError(
            f"unknown chassis philosophy {chassis_philosophy!r}: "
            f"expected one of {CHASSIS_PHILOSOPHIES}"
        )
    baseline = baseline_car_attribute(world.config)
    attributes = dict.fromkeys(CAR_ATTRIBUTES, baseline)

    if engine_supplier_id is not None:
        suppliers = {supplier.id: supplier for supplier in world.engine_suppliers}
        if engine_supplier_id not in suppliers:
            raise ValueError(f"unknown engine supplier id {engine_supplier_id}")
        attributes["engine_power"] = suppliers[engine_supplier_id].engine_power

    if chassis_philosophy == "fast":
        attributes["aero_efficiency"] += config.chassis_bonus
        attributes["downforce"] -= config.chassis_malus
        attributes["mechanical_grip"] -= config.chassis_malus
    elif chassis_philosophy == "technical":
        attributes["aero_efficiency"] -= config.chassis_bonus
        attributes["downforce"] += config.chassis_malus
        attributes["mechanical_grip"] += config.chassis_malus
    # balanced: neutral baseline, no deltas.

    return {name: _clamp(value) for name, value in attributes.items()}


def apply_team_setup(
    world: World,
    choices: TeamSetupChoices,
    config: TeamSetupConfig | None = None,
) -> World:
    """Applica le scelte del Setup squadra e ritorna il Mondo nuovo.

    Valida le scelte (2 piloti distinti ed esistenti, Motorista esistente,
    Filosofia telaio nota, slot del giocatore con identita' e non ancora
    configurato), poi: valorizza la vettura iniziale dello slot, crea i 2
    Contratti del giocatore e rimpiazza nelle squadre AI i piloti
    sottratti con i liberi rimasti. Solleva ValueError con messaggio
    esplicito a ogni violazione; il Mondo in ingresso non viene toccato.
    """
    if config is None:
        config = TeamSetupConfig()
    _validate(world, choices)

    drivers_by_id = {driver.id: driver for driver in world.drivers}
    picked = set(choices.driver_ids)

    # AI contracts that survive, in their original order.
    kept = tuple(c for c in world.contracts if c.driver_id not in picked)
    replaced = tuple(c for c in world.contracts if c.driver_id in picked)

    # Free agents available as substitutes, in roster order.
    substitutes = [d for d in world.drivers_without_contract if d.id not in picked]
    if len(substitutes) < len(replaced):
        raise ValueError(
            f"not enough free agents to refill the AI teams: "
            f"{len(replaced)} needed, {len(substitutes)} available"
        )

    # Automatic refills: same duration as the replaced contract, salary
    # equal to the substitute's salary demand.
    refills = tuple(
        Contract(
            driver_id=substitute.id,
            team_id=contract.team_id,
            start_season=contract.start_season,
            duration_seasons=contract.duration_seasons,
            salary_usd=substitute.salary_demand_usd,
        )
        for contract, substitute in zip(replaced, substitutes, strict=False)
    )

    # The player's contracts: tunable default duration, no negotiation.
    player_contracts = tuple(
        Contract(
            driver_id=driver_id,
            team_id=PLAYER_TEAM_ID,
            start_season=world.config.initial_season,
            duration_seasons=config.player_contract_duration_seasons,
            salary_usd=drivers_by_id[driver_id].salary_demand_usd,
        )
        for driver_id in choices.driver_ids
    )

    player_slot = replace(
        world.player_slot,
        chassis_philosophy=choices.chassis_philosophy,
        engine_supplier_id=choices.engine_supplier_id,
        **initial_car_attributes(
            world, choices.engine_supplier_id, choices.chassis_philosophy, config
        ),
    )

    result = replace(
        world,
        player_slot=player_slot,
        contracts=kept + refills + player_contracts,
    )
    _check_invariants(result)
    return result


def _validate(world: World, choices: TeamSetupChoices) -> None:
    """Validazioni esplicite delle scelte, con errori chiari."""
    if world.player_slot.name is None:
        raise ValueError("player slot has no identity yet: create the career first")
    if world.player_slot.is_set_up:
        raise ValueError("team setup already applied to this world")
    if len(set(choices.driver_ids)) != 2:
        raise ValueError(f"exactly 2 distinct drivers required, got {choices.driver_ids}")
    known_ids = {driver.id for driver in world.drivers}
    unknown = [driver_id for driver_id in choices.driver_ids if driver_id not in known_ids]
    if unknown:
        raise ValueError(f"unknown driver ids: {unknown}")
    if any(c.team_id == PLAYER_TEAM_ID for c in world.contracts):
        raise ValueError("the player team already has contracts")
    # Engine supplier and chassis philosophy are validated by
    # initial_car_attributes; validate them here too so the error comes
    # before any contract work.
    if choices.engine_supplier_id is not None:
        supplier_ids = {supplier.id for supplier in world.engine_suppliers}
        if choices.engine_supplier_id not in supplier_ids:
            raise ValueError(f"unknown engine supplier id {choices.engine_supplier_id}")
    if choices.chassis_philosophy not in CHASSIS_PHILOSOPHIES:
        raise ValueError(
            f"unknown chassis philosophy {choices.chassis_philosophy!r}: "
            f"expected one of {CHASSIS_PHILOSOPHIES}"
        )


def _check_invariants(world: World) -> None:
    """Invarianti post-setup: roster intero, 2 piloti ovunque, niente doppi."""
    driver_ids = [contract.driver_id for contract in world.contracts]
    if len(driver_ids) != len(set(driver_ids)):
        raise ValueError("a driver ended up with more than one contract")
    expected = world.config.drivers_per_team
    team_ids = [PLAYER_TEAM_ID, *(team.id for team in world.ai_teams)]
    for team_id in team_ids:
        count = sum(1 for contract in world.contracts if contract.team_id == team_id)
        if count != expected:
            raise ValueError(f"team {team_id} has {count} drivers instead of {expected}")
