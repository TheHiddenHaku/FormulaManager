"""Apertura della fase di Mercato e popolamento del pool (T5.2.1, sub-issue M1).

open_market legge il Mondo a fine stagione e produce il MarketState
iniziale della finestra: i Contratti la cui ultima stagione coperta
coincide con l'anno concluso entrano nel pool, i piloti liberi attivi
entrano come disponibili con la loro richiesta salariale, i sedili
vacanti si calcolano per squadra. Nessuna logica di offerta o
negoziazione: solo selezione del pool e stato di partenza, query di sola
lettura. Motore puro (ADR 0002).
"""

from fm_engine.market.models import ExpiringContract, MarketPhase, MarketState
from fm_engine.world.models import PLAYER_TEAM_ID, Contract, Driver, World


def last_covered_season(contract: Contract) -> int:
    """L'ultima stagione coperta da un Contratto.

    Un Contratto che parte in start_season e dura duration_seasons copre
    le stagioni da start_season a start_season + duration_seasons - 1
    incluse: l'ultima e' start_season + duration_seasons - 1. E' la
    definizione operativa di "Contratto in scadenza": scade quando la sua
    ultima stagione coperta coincide con l'anno appena concluso.
    """
    return contract.start_season + contract.duration_seasons - 1


def is_expiring(contract: Contract, concluded_year: int) -> bool:
    """True se il Contratto scade con l'anno concluso (ultima stagione coperta)."""
    return last_covered_season(contract) == concluded_year


def _is_active(driver: Driver) -> bool:
    """True se il pilota e' in attivita' (non ritirato).

    Anticipa il filtro active_drivers di FOR-31e: finche' il flag retired
    non esiste sul modello Driver, getattr lo tratta come assente e ogni
    pilota e' attivo. Quando FOR-31e atterra, i piloti ritirati restano
    fuori dal pool dei liberi senza altre modifiche qui.
    """
    return not getattr(driver, "retired", False)


def open_market(world: World, concluded_year: int) -> MarketState:
    """Apre il Mercato a fine stagione e popola il pool.

    Entrano nel pool i Contratti la cui ultima stagione coperta coincide
    con concluded_year e il cui pilota e' ancora in attivita'; i piloti
    liberi attivi entrano come disponibili da subito con la loro richiesta
    salariale iniziale (salary_demand_usd). I sedili vacanti di ogni squadra
    sono i posti lasciati liberi dai Contratti in scadenza piu' quelli dei
    piloti ritirati (FOR-31), rispetto all'obiettivo di drivers_per_team;
    sono calcolati per tutte le squadre AI e per lo slot del giocatore.

    Un pilota ritirato lascia la scena: il suo Contratto non sopravvive (il
    sedile si libera) e lui non entra nel pool, anche se il Contratto non
    sarebbe ancora scaduto.
    """
    seats_per_team = world.config.drivers_per_team
    retired_ids = {driver.id for driver in world.drivers if not _is_active(driver)}

    pool = tuple(
        ExpiringContract(
            driver_id=contract.driver_id,
            team_id=contract.team_id,
            salary_usd=contract.salary_usd,
            last_season=last_covered_season(contract),
        )
        for contract in world.contracts
        if is_expiring(contract, concluded_year) and contract.driver_id not in retired_ids
    )

    free_agents = tuple(driver for driver in world.drivers_without_contract if _is_active(driver))
    free_agent_ids = tuple(driver.id for driver in free_agents)
    salary_demands = {driver.id: driver.salary_demand_usd for driver in free_agents}

    # Sedili vacanti per squadra: l'obiettivo meno i Contratti che
    # sopravvivono al Mercato (non in scadenza e di un pilota ancora attivo).
    team_ids = {PLAYER_TEAM_ID, *(team.id for team in world.ai_teams)}
    surviving_by_team = dict.fromkeys(team_ids, 0)
    for contract in world.contracts:
        if not is_expiring(contract, concluded_year) and contract.driver_id not in retired_ids:
            surviving_by_team[contract.team_id] = surviving_by_team.get(contract.team_id, 0) + 1
    vacant_seats = {
        team_id: max(0, seats_per_team - surviving_by_team[team_id]) for team_id in team_ids
    }

    return MarketState(
        phase=MarketPhase.OPEN,
        concluded_year=concluded_year,
        seats_per_team=seats_per_team,
        pool=pool,
        free_agent_ids=free_agent_ids,
        salary_demands=salary_demands,
        vacant_seats=vacant_seats,
    )


def continuing_driver_ids(world: World, concluded_year: int, team_id: int) -> tuple[int, ...]:
    """I piloti della squadra il cui Contratto sopravvive al Mercato.

    Sono i Contratti non in scadenza nell'anno concluso, di un pilota ancora
    in attivita': restano legati alla squadra e non entrano nel pool. Il
    Contratto di un pilota ritirato (FOR-31) non sopravvive.
    """
    retired_ids = {driver.id for driver in world.drivers if not _is_active(driver)}
    return tuple(
        contract.driver_id
        for contract in world.contracts
        if contract.team_id == team_id
        and not is_expiring(contract, concluded_year)
        and contract.driver_id not in retired_ids
    )


def final_roster_ids(world: World, market: MarketState, team_id: int) -> tuple[int, ...]:
    """Il roster della squadra a Mercato risolto: piloti confermati piu' firme.

    Unisce i Contratti sopravvissuti (non in scadenza) e i piloti
    ingaggiati durante la fase. Richiede un Mercato aperto (concluded_year
    valorizzato).
    """
    if market.concluded_year is None:
        raise ValueError("final roster requires an open market (concluded_year set)")
    continuing = continuing_driver_ids(world, market.concluded_year, team_id)
    return continuing + market.signings_for(team_id)
