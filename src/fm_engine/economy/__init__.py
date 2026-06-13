"""Economia di squadra: registro, flussi di stagione, Danni, solvibilita'.

Copre FOR-15 (registro Cassa e Cap), FOR-22 (entrate e stipendi),
FOR-23 (Danni e Sforamento) e FOR-24 (Misura d'emergenza e fallimento).
"""

from fm_engine.economy.damages import (
    MINIMUM_CAP_USD,
    charge_damage_repairs,
    overspend_penalty_usd,
    repair_cost_usd,
    start_next_season,
)
from fm_engine.economy.emergency import (
    EMERGENCY_HEADROOM_USD,
    LOAN_INTEREST_RATE,
    LOAN_REPAYMENT_RACES,
    STOPGAP_PRESTIGE_MALUS,
    LoanOffer,
    StopgapOffer,
    loan_offer,
    stopgap_offer,
    take_loan,
    take_stopgap_sponsor,
)
from fm_engine.economy.income import (
    DEFAULT_PLAYER_PRESTIGE,
    PLAYER_STARTING_CASH_USD,
    annual_sponsor_usd,
    constructors_pool_usd,
    credit_annual_sponsor,
    credit_constructors_pool,
    credit_race_prizes,
    credit_starting_cash,
    race_prize_usd,
)
from fm_engine.economy.ledger import (
    SEASON_CAP_USD,
    SpendingBlocked,
    TeamLedger,
    Transaction,
    TransactionKind,
)
from fm_engine.economy.salaries import (
    RACES_PER_SEASON,
    charge_salary_instalments,
    salary_instalment_usd,
)
from fm_engine.economy.solvency import (
    BANKRUPTCY_RACES,
    EconomicStatus,
    Settlement,
    SettlementOutcome,
    SolvencyState,
    economic_status,
    optional_spending_blocked,
    settle_post_race,
)

__all__ = [
    "BANKRUPTCY_RACES",
    "DEFAULT_PLAYER_PRESTIGE",
    "EMERGENCY_HEADROOM_USD",
    "EconomicStatus",
    "LOAN_INTEREST_RATE",
    "LOAN_REPAYMENT_RACES",
    "LoanOffer",
    "MINIMUM_CAP_USD",
    "PLAYER_STARTING_CASH_USD",
    "RACES_PER_SEASON",
    "SEASON_CAP_USD",
    "STOPGAP_PRESTIGE_MALUS",
    "Settlement",
    "SettlementOutcome",
    "SolvencyState",
    "SpendingBlocked",
    "StopgapOffer",
    "TeamLedger",
    "Transaction",
    "TransactionKind",
    "annual_sponsor_usd",
    "charge_damage_repairs",
    "charge_salary_instalments",
    "constructors_pool_usd",
    "credit_annual_sponsor",
    "credit_constructors_pool",
    "credit_race_prizes",
    "credit_starting_cash",
    "economic_status",
    "loan_offer",
    "optional_spending_blocked",
    "overspend_penalty_usd",
    "race_prize_usd",
    "repair_cost_usd",
    "salary_instalment_usd",
    "settle_post_race",
    "start_next_season",
    "stopgap_offer",
    "take_loan",
    "take_stopgap_sponsor",
]
