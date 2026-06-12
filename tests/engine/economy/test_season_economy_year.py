"""Anno economico simulato: una stagione intera nel registro (FOR-22).

Sponsor annuale a inizio stagione, 24 GP con Premio gara per le due
vetture del giocatore e rata stipendi, Montepremi costruttori a fine
anno: il registro risultante deve avere tutti i movimenti con causale e
i saldi finali corretti, col Cap mai toccato da questi flussi.
"""

from datetime import date

from fm_engine.circuits import CALENDAR_2026
from fm_engine.economy import (
    DEFAULT_PLAYER_PRESTIGE,
    SEASON_CAP_USD,
    TeamLedger,
    TransactionKind,
    annual_sponsor_usd,
    charge_salary_instalments,
    constructors_pool_usd,
    credit_annual_sponsor,
    credit_constructors_pool,
    credit_race_prizes,
    race_prize_usd,
)
from fm_engine.events import ClassifiedResult
from fm_engine.world.models import PLAYER_TEAM_ID, Contract

FIRST_SALARY_USD = 12_000_000
SECOND_SALARY_USD = 6_000_000
FIRST_POSITION = 3
SECOND_POSITION = 11
FINAL_STANDING = 4


def _player_classification() -> tuple[ClassifiedResult, ...]:
    def result(position: int, driver_id: int, team_id: int) -> ClassifiedResult:
        return ClassifiedResult(
            position=position,
            driver_id=driver_id,
            team_id=team_id,
            total_time_seconds=5400.0 + position,
            gap_to_winner_seconds=float(position - 1),
            points=0,
            penalty_seconds=0.0,
        )

    return (
        result(1, driver_id=99, team_id=5),
        result(FIRST_POSITION, driver_id=1, team_id=PLAYER_TEAM_ID),
        result(SECOND_POSITION, driver_id=2, team_id=PLAYER_TEAM_ID),
    )


def test_a_full_season_produces_a_coherent_ledger():
    contracts = (
        Contract(
            driver_id=1,
            team_id=PLAYER_TEAM_ID,
            start_season=2026,
            duration_seasons=2,
            salary_usd=FIRST_SALARY_USD,
        ),
        Contract(
            driver_id=2,
            team_id=PLAYER_TEAM_ID,
            start_season=2026,
            duration_seasons=2,
            salary_usd=SECOND_SALARY_USD,
        ),
    )

    ledger = credit_annual_sponsor(TeamLedger(), DEFAULT_PLAYER_PRESTIGE, date(2026, 1, 1))
    for circuit in CALENDAR_2026:
        classification = _player_classification()
        ledger = credit_race_prizes(ledger, classification, circuit.race_date_2026, circuit.name)
        ledger = charge_salary_instalments(ledger, contracts, circuit.race_date_2026)
    ledger = credit_constructors_pool(ledger, FINAL_STANDING, date(2026, 12, 15))

    races = len(CALENDAR_2026)
    # 1 sponsor + 2 premi e 1 rata stipendi per GP + 1 montepremi finale.
    assert len(ledger.entries) == 1 + races * 3 + 1

    instalment = FIRST_SALARY_USD // races + SECOND_SALARY_USD // races
    expected_cash = (
        annual_sponsor_usd(DEFAULT_PLAYER_PRESTIGE)
        + races * (race_prize_usd(FIRST_POSITION) + race_prize_usd(SECOND_POSITION))
        - races * instalment
        + constructors_pool_usd(FINAL_STANDING)
    )
    assert ledger.cash_usd == expected_cash
    # Nessuno di questi flussi tocca il Cap.
    assert ledger.cap_remaining_usd == SEASON_CAP_USD

    # Ogni movimento ha causale e descrizione; gli stipendi sono fuori Cap.
    assert all(entry.description for entry in ledger.entries)
    salary_entries = [entry for entry in ledger.entries if entry.kind is TransactionKind.SALARY]
    assert len(salary_entries) == races
    assert all(entry.counts_against_cap is False for entry in salary_entries)
    assert all(entry.amount_usd == -instalment for entry in salary_entries)
    prize_entries = [entry for entry in ledger.entries if entry.kind is TransactionKind.RACE_PRIZE]
    assert len(prize_entries) == races * 2
