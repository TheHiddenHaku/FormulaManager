"""Applicazione del Mercato al roster: dalle firme ai Contratti (T5.2.1).

apply_market chiude la fase di Mercato trasformando le firme transitorie
(MarketState.signings) nei Contratti della stagione nuova del Mondo. E' il
ponte mancante tra la negoziazione e il gioco vero: senza, le firme
restano nello stato di fase e la Griglia non cambia mai.

Regole di chiusura (motore puro, ADR 0002):
- I Contratti non in scadenza nell'anno concluso sopravvivono invariati.
- Ogni firma (giocatore e AI) diventa un Contratto nuovo che parte
  dall'anno successivo, con ingaggio e durata della mossa che l'ha
  prodotta (AiMove SIGNING o FORCED_ASSIGNMENT nel log).
- La firma del giocatore e' autoritativa: se il giocatore ingaggia un
  pilota gia' firmato da una rivale, il pilota va al giocatore e la rivale
  resta scoperta (la negoziazione M3 non libera il sedile dell'AI).
- Convergenza: ogni squadra rimasta sotto l'obiettivo (per uno "scippo" o
  perche' non ha riempito i sedili) e' completata in modo deterministico
  coi migliori piloti attivi ancora liberi, come il fallback delle offerte
  AI (M2). Alla fine ogni squadra ha esattamente seats_per_team piloti e
  nessun pilota ha due Contratti.

Default documentato (tuning a FOR-34): il riempimento forzato dei sedili
non scelti usa lo stesso modello salariale delle offerte AI
(desired_salary/offer_duration sulla qualita' del pilota).
"""

from dataclasses import replace

from fm_engine.market.ai_offers import desired_salary, driver_quality, offer_duration
from fm_engine.market.models import AiMoveKind, MarketState
from fm_engine.market.pool import is_expiring
from fm_engine.world.models import PLAYER_TEAM_ID, Contract, Driver, World


def _is_active(driver: Driver) -> bool:
    """True se il pilota e' in attivita' (non ritirato), come in pool._is_active.

    Anticipa il flag retired di FOR-31: finche' non esiste, getattr lo
    tratta come assente e ogni pilota e' attivo.
    """
    return not getattr(driver, "retired", False)


def apply_market(world: World, market: MarketState) -> World:
    """Chiude il Mercato: trasforma le firme in Contratti della stagione nuova.

    Ritorna un Mondo nuovo (World e' frozen) con i Contratti ricostruiti:
    i Contratti sopravvissuti, le firme di giocatore e AI come Contratti
    che partono dall'anno successivo, e il riempimento forzato dei sedili
    rimasti scoperti. Ogni squadra converge a seats_per_team piloti.

    Solleva ValueError se il Mercato non e' aperto o se i piloti attivi non
    bastano a riempire tutti i sedili (possibile solo coi Ritiri di FOR-31).
    """
    if market.concluded_year is None:
        raise ValueError("apply_market requires an open market (concluded_year set)")

    next_season = market.concluded_year + 1
    seats = market.seats_per_team
    drivers_by_id = {driver.id: driver for driver in world.drivers}
    team_ids = (PLAYER_TEAM_ID, *(team.id for team in world.ai_teams))

    # Negotiated terms (salary, duration) per signing, read from the log.
    terms = {
        (move.team_id, move.driver_id): (move.salary_usd, move.duration_seasons)
        for move in market.ai_moves
        if move.kind in (AiMoveKind.SIGNING, AiMoveKind.FORCED_ASSIGNMENT)
    }

    assigned: set[int] = set()
    rosters: dict[int, list[Contract]] = {team_id: [] for team_id in team_ids}

    # 1) Contracts that did not expire this year survive unchanged.
    for contract in world.contracts:
        if not is_expiring(contract, market.concluded_year):
            rosters[contract.team_id].append(contract)
            assigned.add(contract.driver_id)

    # 2) Player signings first: they win any conflict with a rival signing.
    for driver_id in market.signings_for(PLAYER_TEAM_ID):
        if driver_id in assigned:
            continue
        rosters[PLAYER_TEAM_ID].append(
            _signed_contract(drivers_by_id[driver_id], PLAYER_TEAM_ID, next_season, terms)
        )
        assigned.add(driver_id)

    # 3) AI signings, skipping drivers already taken (e.g. stolen by the player).
    for team in world.ai_teams:
        for driver_id in market.signings_for(team.id):
            if driver_id in assigned:
                continue
            rosters[team.id].append(
                _signed_contract(drivers_by_id[driver_id], team.id, next_season, terms)
            )
            assigned.add(driver_id)

    # 4) Convergence: fill every short seat with the best leftover active
    #    drivers, mirroring the AI fallback (deterministic by quality, id).
    leftover = sorted(
        (driver for driver in world.drivers if driver.id not in assigned and _is_active(driver)),
        key=lambda driver: (driver_quality(driver), driver.id),
        reverse=True,
    )
    cursor = 0
    for team_id in team_ids:
        while len(rosters[team_id]) < seats:
            if cursor >= len(leftover):
                raise ValueError("not enough active drivers to fill every seat")
            driver = leftover[cursor]
            cursor += 1
            quality = driver_quality(driver)
            rosters[team_id].append(
                Contract(
                    driver_id=driver.id,
                    team_id=team_id,
                    start_season=next_season,
                    duration_seasons=offer_duration(quality),
                    salary_usd=desired_salary(quality),
                )
            )
            assigned.add(driver.id)

    contracts = tuple(contract for team_id in team_ids for contract in rosters[team_id])
    _check_invariants(contracts, team_ids, seats)
    return replace(world, contracts=contracts)


def _signed_contract(
    driver: Driver,
    team_id: int,
    next_season: int,
    terms: dict[tuple[int, int], tuple[int, int]],
) -> Contract:
    """Il Contratto nuovo di una firma: ingaggio e durata dalla mossa di firma."""
    salary_usd, duration_seasons = terms.get((team_id, driver.id), (driver.salary_demand_usd, 1))
    return Contract(
        driver_id=driver.id,
        team_id=team_id,
        start_season=next_season,
        duration_seasons=duration_seasons,
        salary_usd=salary_usd,
    )


def _check_invariants(
    contracts: tuple[Contract, ...], team_ids: tuple[int, ...], seats: int
) -> None:
    """Invarianti post-Mercato: niente doppi Contratti, seats piloti per squadra."""
    driver_ids = [contract.driver_id for contract in contracts]
    if len(driver_ids) != len(set(driver_ids)):
        raise ValueError("a driver ended up with more than one contract after the market")
    for team_id in team_ids:
        count = sum(1 for contract in contracts if contract.team_id == team_id)
        if count != seats:
            raise ValueError(f"team {team_id} has {count} drivers instead of {seats}")
