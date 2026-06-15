"""Offerte AI e risoluzione del Mercato piloti (T5.2.1, sub-issue M2).

Le squadre AI ingaggiano i piloti del pool e i liberi. Le offerte sono
guidate dal Prestigio e vincolate dalla Cassa (cash_usd): entrambi sono
persistiti e sopravvivono ai Checkpoint. La risoluzione NON usa la
SpendingPersonality, che non viaggia coi Checkpoint e si azzera dopo un
reload (fm_engine.ai.spending riguarda i Progetti, non gli stipendi):
qui la logica salariale e' nuova ma riusa il concetto di vincolo Cassa.

La risoluzione e' deterministica dato il seed (random.Random) e converge:
alla chiusura ogni squadra AI ha esattamente seats_per_team piloti, senza
sedili vuoti, grazie a un fallback di assegnazione forzata dei liberi
rimanenti. Ogni mossa entra nel log (AiMove).

Tutti i coefficienti sono costanti nominate con valori iniziali
ragionevoli; il tuning e' rimandato a FOR-34. Motore puro (ADR 0002).
"""

from dataclasses import replace
from random import Random

from fm_engine.market.models import AiMove, AiMoveKind, MarketState
from fm_engine.world.models import DRIVER_ATTRIBUTES, Driver, Team, World

# Dimensionamento ingaggio: l'AI offre uno stipendio funzione della
# qualita' del pilota (media degli Attributi visibili, scala 0-100).
SALARY_FLOOR_USD = 2_000_000
SALARY_PER_QUALITY_USD = 200_000

# Politica di durata AI (1-3 stagioni), deterministica dalla qualita':
# i piloti migliori firmano piu' a lungo.
HIGH_QUALITY_DURATION_THRESHOLD = 75.0
LOW_QUALITY_DURATION_THRESHOLD = 55.0

# Attrattivita' di una squadra: combinazione pesata di Prestigio e Cassa,
# normalizzati a 0-1. Il Prestigio domina (peso piu' alto): le squadre
# piu' blasonate attraggono i piloti migliori.
ATTRACTIVENESS_PRESTIGE_WEIGHT = 0.85
ATTRACTIVENESS_CASH_WEIGHT = 0.15
PRESTIGE_REFERENCE = 100.0
CASH_REFERENCE_USD = 60_000_000.0

# Soglia di accettazione: il pilota accetta se l'offerta copre almeno
# questa quota dell'ingaggio desiderato. Le offerte AI sono generate solo
# quando credibili (sostenibili per intero dalla Cassa), quindi coprono
# sempre il desiderato e l'accettazione e' garantita.
AI_ACCEPTANCE_RATIO = 1.0


def driver_quality(driver: Driver) -> float:
    """La qualita' del pilota: media dei 6 Attributi visibili (scala 0-100).

    L'AI valuta i piloti ai valori veri: le Stime sono solo cio' che il
    giocatore VEDE, la decisione interna usa gli attributi reali.
    """
    return sum(getattr(driver, attr) for attr in DRIVER_ATTRIBUTES) / len(DRIVER_ATTRIBUTES)


def desired_salary(quality: float) -> int:
    """L'ingaggio che l'AI offre per un pilota di data qualita' (USD)."""
    return SALARY_FLOOR_USD + int(SALARY_PER_QUALITY_USD * quality)


def offer_duration(quality: float) -> int:
    """La durata offerta (1-3 stagioni), deterministica dalla qualita'."""
    if quality >= HIGH_QUALITY_DURATION_THRESHOLD:
        return 3
    if quality < LOW_QUALITY_DURATION_THRESHOLD:
        return 1
    return 2


def team_attractiveness(team: Team) -> float:
    """L'attrattivita' della squadra: Prestigio e Cassa pesati e normalizzati."""
    prestige_term = ATTRACTIVENESS_PRESTIGE_WEIGHT * (team.prestige / PRESTIGE_REFERENCE)
    cash_term = ATTRACTIVENESS_CASH_WEIGHT * (team.cash_usd / CASH_REFERENCE_USD)
    return prestige_term + cash_term


def can_afford(team: Team, salary_usd: int) -> bool:
    """True se la Cassa sostiene per intero l'ingaggio: offerta credibile."""
    return salary_usd <= team.cash_usd


def resolve_market(world: World, market: MarketState, rng: Random) -> MarketState:
    """Risolve il Mercato AI e ritorna un MarketState avanzato.

    Le squadre AI con sedili vacanti offrono sui piloti disponibili (pool
    piu' liberi), in ordine di qualita': ogni pilota raccoglie le offerte
    credibili e sceglie la squadra piu' attraente. Esaurite le offerte, un
    fallback forza i piloti rimanenti nei sedili ancora vuoti, cosi' ogni
    squadra AI raggiunge seats_per_team piloti. Aggiorna sedili vacanti,
    firme e log mosse. Non tocca i sedili del giocatore (negoziazione M3).

    Determinismo: i pari (qualita' o attrattivita' identiche) sono rotti da
    chiavi pseudocasuali estratte dal seed, quindi stesso seed -> stesso
    MarketState finale.
    """
    drivers_by_id = {driver.id: driver for driver in world.drivers}
    teams_by_id = {team.id: team for team in world.ai_teams}

    quality = {
        driver_id: driver_quality(drivers_by_id[driver_id])
        for driver_id in market.available_driver_ids
    }
    # Chiavi pseudocasuali per rompere i pari in modo deterministico.
    driver_jitter = {driver_id: rng.random() for driver_id in market.available_driver_ids}
    team_jitter = {team_id: rng.random() for team_id in teams_by_id}

    vacant = {team_id: market.vacant_seats_for(team_id) for team_id in teams_by_id}
    signed: dict[int, list[int]] = {team_id: [] for team_id in teams_by_id}
    taken: set[int] = set()
    moves: list[AiMove] = []

    # Piloti migliori per primi (qualita' decrescente, jitter per i pari).
    order = sorted(
        market.available_driver_ids,
        key=lambda driver_id: (quality[driver_id], driver_jitter[driver_id]),
        reverse=True,
    )

    for driver_id in order:
        salary = desired_salary(quality[driver_id])
        duration = offer_duration(quality[driver_id])
        candidates = [
            teams_by_id[team_id]
            for team_id in teams_by_id
            if vacant[team_id] > 0 and can_afford(teams_by_id[team_id], salary)
        ]
        if not candidates:
            continue
        # Ogni squadra candidata presenta un'offerta credibile (log OFFER).
        for team in candidates:
            moves.append(AiMove(team.id, driver_id, AiMoveKind.OFFER, salary, duration))
        winner = max(
            candidates,
            key=lambda team: (team_attractiveness(team), team_jitter[team.id]),
        )
        # Le offerte sono pre-filtrate come credibili: coprono il desiderato.
        if salary >= int(AI_ACCEPTANCE_RATIO * desired_salary(quality[driver_id])):
            moves.append(AiMove(winner.id, driver_id, AiMoveKind.SIGNING, salary, duration))
            signed[winner.id].append(driver_id)
            vacant[winner.id] -= 1
            taken.add(driver_id)

    # Fallback di convergenza: forza i piloti rimanenti nei sedili vuoti,
    # squadre piu' attraenti per prime, dal pilota piu' economico (coda di
    # order, ordinato per qualita' decrescente).
    remaining = [driver_id for driver_id in order if driver_id not in taken]
    fallback_team_order = sorted(
        teams_by_id,
        key=lambda team_id: (team_attractiveness(teams_by_id[team_id]), team_jitter[team_id]),
        reverse=True,
    )
    for team_id in fallback_team_order:
        team = teams_by_id[team_id]
        while vacant[team_id] > 0 and remaining:
            driver_id = remaining.pop()
            salary = min(desired_salary(quality[driver_id]), team.cash_usd)
            duration = offer_duration(quality[driver_id])
            moves.append(AiMove(team_id, driver_id, AiMoveKind.FORCED_ASSIGNMENT, salary, duration))
            signed[team_id].append(driver_id)
            vacant[team_id] -= 1
            taken.add(driver_id)

    new_vacant = dict(market.vacant_seats)
    new_signings = dict(market.signings)
    for team_id in teams_by_id:
        new_vacant[team_id] = vacant[team_id]
        if signed[team_id]:
            new_signings[team_id] = (*new_signings.get(team_id, ()), *signed[team_id])

    return replace(
        market,
        vacant_seats=new_vacant,
        signings=new_signings,
        ai_moves=(*market.ai_moves, *moves),
    )
