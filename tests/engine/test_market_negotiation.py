"""Test della negoziazione del giocatore (T5.2.1, sub-issue M3).

Esiti strutturati: rilancio vincente che tiene il pilota, rilancio perdente
che lo perde, controfferta insostenibile bloccata con motivo tipizzato,
durata fuori range rifiutata, determinismo. La sostenibilita' usa il
vincolo dell'economia (rata stagionale sulla Cassa). Engine-only.
"""

from datetime import date

from fm_engine.economy import TeamLedger, Transaction, TransactionKind
from fm_engine.market import (
    AiMove,
    AiMoveKind,
    MarketPhase,
    MarketState,
    NegotiationOutcomeKind,
    counter_offer,
)
from fm_engine.world.models import PLAYER_TEAM_ID

GAME_DATE = date(2026, 11, 15)
DRIVER_ID = 1


def _market(rival_salary_usd: int | None = None, player_vacant: int = 2) -> MarketState:
    moves: tuple[AiMove, ...] = ()
    if rival_salary_usd is not None:
        moves = (
            AiMove(
                team_id=2,
                driver_id=DRIVER_ID,
                kind=AiMoveKind.OFFER,
                salary_usd=rival_salary_usd,
                duration_seasons=2,
            ),
        )
    return MarketState(
        phase=MarketPhase.OPEN,
        concluded_year=2025,
        vacant_seats={PLAYER_TEAM_ID: player_vacant},
        ai_moves=moves,
    )


def _ledger(cash_usd: int) -> TeamLedger:
    ledger = TeamLedger()
    if cash_usd:
        ledger = ledger.record(
            Transaction(
                kind=TransactionKind.OTHER,
                amount_usd=cash_usd,
                game_date=GAME_DATE,
                description="dotazione di test",
            )
        )
    return ledger


def test_winning_counter_offer_signs_the_driver():
    market = _market(rival_salary_usd=5_000_000)
    outcome = counter_offer(
        market, _ledger(50_000_000), DRIVER_ID, 8_000_000, 2, GAME_DATE, player_prestige=50
    )
    assert outcome.kind is NegotiationOutcomeKind.ACCEPTED
    assert outcome.accepted is True
    assert DRIVER_ID in outcome.market.signings_for(PLAYER_TEAM_ID)
    assert outcome.market.vacant_seats_for(PLAYER_TEAM_ID) == 1
    last_move = outcome.market.ai_moves[-1]
    assert last_move.team_id == PLAYER_TEAM_ID
    assert last_move.driver_id == DRIVER_ID
    assert last_move.kind is AiMoveKind.SIGNING


def test_losing_counter_offer_keeps_the_driver_with_the_rival():
    market = _market(rival_salary_usd=20_000_000)
    outcome = counter_offer(
        market, _ledger(50_000_000), DRIVER_ID, 5_000_000, 2, GAME_DATE, player_prestige=0
    )
    assert outcome.kind is NegotiationOutcomeKind.REJECTED_BY_DRIVER
    assert outcome.rival_salary_usd == 20_000_000
    # Il MarketState non cambia: nessuna firma, sedile ancora vacante.
    assert outcome.market is market
    assert outcome.market.signings_for(PLAYER_TEAM_ID) == ()
    assert outcome.market.vacant_seats_for(PLAYER_TEAM_ID) == 2


def test_unsustainable_counter_offer_is_cash_blocked_with_reason():
    market = _market(rival_salary_usd=1_000_000)
    outcome = counter_offer(market, _ledger(5_000_000), DRIVER_ID, 200_000_000, 2, GAME_DATE)
    assert outcome.kind is NegotiationOutcomeKind.CASH_BLOCKED
    assert outcome.blocked_constraint == "cash"
    assert outcome.allowed_usd == 5_000_000
    # Bloccata: nessuna mutazione del MarketState.
    assert outcome.market is market
    assert outcome.market.signings_for(PLAYER_TEAM_ID) == ()


def test_duration_out_of_range_is_rejected():
    market = _market(rival_salary_usd=1_000_000)
    for bad_duration in (0, 4):
        outcome = counter_offer(
            market, _ledger(50_000_000), DRIVER_ID, 5_000_000, bad_duration, GAME_DATE
        )
        assert outcome.kind is NegotiationOutcomeKind.INVALID_DURATION
        assert outcome.market is market


def test_counter_offer_without_rival_is_accepted_when_sustainable():
    market = _market(rival_salary_usd=None)
    outcome = counter_offer(
        market, _ledger(50_000_000), DRIVER_ID, 5_000_000, 3, GAME_DATE, player_prestige=50
    )
    assert outcome.kind is NegotiationOutcomeKind.ACCEPTED
    assert outcome.rival_salary_usd == 0
    assert DRIVER_ID in outcome.market.signings_for(PLAYER_TEAM_ID)


def test_player_prestige_tips_a_close_negotiation():
    market = _market(rival_salary_usd=10_000_000)
    # Stesso ingaggio sotto il rivale: con Prestigio il bonus colma il divario.
    with_prestige = counter_offer(
        market, _ledger(50_000_000), DRIVER_ID, 6_000_000, 2, GAME_DATE, player_prestige=50
    )
    without_prestige = counter_offer(
        market, _ledger(50_000_000), DRIVER_ID, 6_000_000, 2, GAME_DATE, player_prestige=0
    )
    assert with_prestige.kind is NegotiationOutcomeKind.ACCEPTED
    assert without_prestige.kind is NegotiationOutcomeKind.REJECTED_BY_DRIVER


def test_sustainability_uses_the_seasonal_instalment_not_the_annual_salary():
    # Cassa 1M: l'ingaggio annuale di 12M la supera, ma la rata per gara
    # (500k) ci sta: la controfferta non e' bloccata dalla Cassa.
    affordable = counter_offer(
        _market(rival_salary_usd=None), _ledger(1_000_000), DRIVER_ID, 12_000_000, 2, GAME_DATE
    )
    assert affordable.kind is NegotiationOutcomeKind.ACCEPTED
    # Con un annuale di 48M la rata (2M) supera la Cassa: bloccata.
    blocked = counter_offer(
        _market(rival_salary_usd=None), _ledger(1_000_000), DRIVER_ID, 48_000_000, 2, GAME_DATE
    )
    assert blocked.kind is NegotiationOutcomeKind.CASH_BLOCKED


def test_outcome_is_deterministic_for_the_same_inputs():
    market = _market(rival_salary_usd=7_000_000)
    first = counter_offer(market, _ledger(50_000_000), DRIVER_ID, 9_000_000, 2, GAME_DATE)
    second = counter_offer(market, _ledger(50_000_000), DRIVER_ID, 9_000_000, 2, GAME_DATE)
    assert first == second
