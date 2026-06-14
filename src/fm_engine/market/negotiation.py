"""Negoziazione del giocatore nel Mercato piloti (T5.2.1, sub-issue M3).

Il giocatore rilancia su un pilota del pool (un proprio pilota in scadenza
o un libero) alzando ingaggio e durata. counter_offer e' una funzione pura
che, dato un MarketState e una controfferta, ritorna un esito strutturato
(NegotiationOutcome) con motivo tipizzato, mai una stringa libera.

La sostenibilita' rispetto alla Cassa riusa il vincolo dell'economia
esistente: la rata stagionale (salary_instalment_usd) e' uno stipendio,
quindi pesa solo sulla Cassa (esclusa dal Cap, CONTEXT.md) e passa per la
stessa TeamLedger.spend che addebita gli stipendi, intercettando
SpendingBlocked. Nessuna formula nuova e divergente.

Una chiamata modella una sola tornata di controfferta per pilota (default
documentato): l'eventuale ripetizione e' decisa dal livello superiore, non
qui. Motore puro (ADR 0002).
"""

from dataclasses import replace
from datetime import date

from fm_engine.economy import (
    DEFAULT_PLAYER_PRESTIGE,
    SpendingBlocked,
    TeamLedger,
    TransactionKind,
    salary_instalment_usd,
)
from fm_engine.market.models import (
    AiMove,
    AiMoveKind,
    MarketState,
    NegotiationOutcome,
    NegotiationOutcomeKind,
)
from fm_engine.world.models import PLAYER_TEAM_ID

# Durata ammessa per una controfferta (stagioni), come i Contratti.
MIN_CONTRACT_DURATION = 1
MAX_CONTRACT_DURATION = 3

# Soglia di accettazione: il valore della controfferta deve almeno
# eguagliare la migliore offerta rivale. A parita' la controfferta e'
# accettata, perche' il giocatore sta rilanciando attivamente.
ACCEPTANCE_MARGIN = 1.0

# Peso del Prestigio nella decisione del pilota: ogni punto di Prestigio
# della squadra del giocatore vale come un bonus in USD sull'offerta.
PRESTIGE_BONUS_PER_POINT_USD = 100_000


def prestige_bonus_usd(player_prestige: int) -> int:
    """Il bonus equivalente in USD dato dal Prestigio della squadra del giocatore."""
    return PRESTIGE_BONUS_PER_POINT_USD * player_prestige


def best_rival_salary_usd(market: MarketState, driver_id: int) -> int:
    """Il piu' alto ingaggio offerto da una squadra rivale (AI) per il pilota.

    Zero se nessun rivale ha mosso sul pilota: senza concorrenza la
    controfferta sostenibile viene accettata.
    """
    rival = [
        move.salary_usd
        for move in market.ai_moves
        if move.driver_id == driver_id and move.team_id != PLAYER_TEAM_ID
    ]
    return max(rival, default=0)


def counter_offer(
    market: MarketState,
    ledger: TeamLedger,
    driver_id: int,
    salary_usd: int,
    duration_seasons: int,
    game_date: date,
    player_prestige: int = DEFAULT_PLAYER_PRESTIGE,
) -> NegotiationOutcome:
    """La controfferta del giocatore su un pilota del pool o un libero.

    Esito strutturato con motivo tipizzato:
    - INVALID_DURATION: durata fuori dall'intervallo 1-3.
    - CASH_BLOCKED: la rata stagionale dell'ingaggio non e' sostenibile
      dalla Cassa secondo il vincolo dell'economia (la stessa
      TeamLedger.spend usata per gli stipendi); riporta il lato del vincolo
      e il massimo sostenibile.
    - REJECTED_BY_DRIVER: la controfferta non eguaglia la migliore offerta
      rivale, considerato il bonus di Prestigio del giocatore.
    - ACCEPTED: il pilota firma; il MarketState ritorna aggiornato con la
      firma, il sedile occupato e la mossa nel log.
    """
    if salary_usd <= 0:
        raise ValueError(f"salary must be positive, got {salary_usd}")

    if not MIN_CONTRACT_DURATION <= duration_seasons <= MAX_CONTRACT_DURATION:
        return NegotiationOutcome(
            kind=NegotiationOutcomeKind.INVALID_DURATION,
            market=market,
            driver_id=driver_id,
            salary_usd=salary_usd,
            duration_seasons=duration_seasons,
        )

    instalment = salary_instalment_usd(salary_usd)
    if instalment > 0:
        try:
            # Riusa il vincolo dell'economia: la rata e' uno stipendio
            # (fuori Cap), vincolato dalla sola Cassa. Il registro
            # risultante non si conserva: l'addebito vero avviene gara per
            # gara, qui si verifica solo la sostenibilita'.
            ledger.spend(
                TransactionKind.SALARY,
                instalment,
                game_date,
                counts_against_cap=False,
            )
        except SpendingBlocked as blocked:
            return NegotiationOutcome(
                kind=NegotiationOutcomeKind.CASH_BLOCKED,
                market=market,
                driver_id=driver_id,
                salary_usd=salary_usd,
                duration_seasons=duration_seasons,
                blocked_constraint=blocked.constraint,
                allowed_usd=blocked.allowed_usd,
            )

    rival_salary = best_rival_salary_usd(market, driver_id)
    offer_value = salary_usd + prestige_bonus_usd(player_prestige)
    if offer_value < ACCEPTANCE_MARGIN * rival_salary:
        return NegotiationOutcome(
            kind=NegotiationOutcomeKind.REJECTED_BY_DRIVER,
            market=market,
            driver_id=driver_id,
            salary_usd=salary_usd,
            duration_seasons=duration_seasons,
            rival_salary_usd=rival_salary,
        )

    signed = _record_player_signing(market, driver_id, salary_usd, duration_seasons)
    return NegotiationOutcome(
        kind=NegotiationOutcomeKind.ACCEPTED,
        market=signed,
        driver_id=driver_id,
        salary_usd=salary_usd,
        duration_seasons=duration_seasons,
        rival_salary_usd=rival_salary,
    )


def _record_player_signing(
    market: MarketState, driver_id: int, salary_usd: int, duration_seasons: int
) -> MarketState:
    """Registra la firma del giocatore: sedile occupato, firma e mossa nel log."""
    new_signings = dict(market.signings)
    new_signings[PLAYER_TEAM_ID] = (*new_signings.get(PLAYER_TEAM_ID, ()), driver_id)
    new_vacant = dict(market.vacant_seats)
    new_vacant[PLAYER_TEAM_ID] = max(0, market.vacant_seats_for(PLAYER_TEAM_ID) - 1)
    move = AiMove(
        team_id=PLAYER_TEAM_ID,
        driver_id=driver_id,
        kind=AiMoveKind.SIGNING,
        salary_usd=salary_usd,
        duration_seasons=duration_seasons,
    )
    return replace(
        market,
        signings=new_signings,
        vacant_seats=new_vacant,
        ai_moves=(*market.ai_moves, move),
    )
