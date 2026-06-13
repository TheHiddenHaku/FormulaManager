"""Danni e Sforamento: il costo degli eventi danno di gara (FOR-23).

Gli eventi CarDamage della Sfiga (T2.2.2) portano l'entita' in USD: qui
diventano costi di riparazione che pesano sulla Cassa E consumano Cap,
come nella F1 reale. L'addebito e' forzoso: la vettura corre sempre,
anche quando il Cap residuo non basta, e il Cap negativo che ne risulta
e' lo Sforamento (TeamLedger.overspend_usd).

Al rollover di stagione lo Sforamento si traduce in una riduzione
proporzionale del Cap dell'anno successivo (start_next_season); la
Cassa finale viene riportata nel nuovo registro come saldo iniziale.
"""

from collections.abc import Iterable, Mapping
from datetime import date

from fm_engine.economy.ledger import (
    SEASON_CAP_USD,
    TeamLedger,
    Transaction,
    TransactionKind,
)
from fm_engine.events import CarDamage

# Repair cost per damage dollar: kept explicit and tunable.
REPAIR_COST_RATIO = 1.0

# Next season cap reduction per overspent dollar (proportional penalty).
OVERSPEND_PENALTY_RATIO = 1.0

# Floor of the next season cap after the penalty: the championship never
# strangles a team to zero spending. Starting value, tunable.
MINIMUM_CAP_USD = 50_000_000


def repair_cost_usd(damage: CarDamage) -> int:
    """Il costo di riparazione, proporzionale all'entita' del danno."""
    return int(damage.amount_usd * REPAIR_COST_RATIO)


def charge_damage_repairs(
    ledger: TeamLedger,
    damages: Iterable[CarDamage],
    player_driver_ids: Iterable[int],
    game_date: date,
    driver_names: Mapping[int, str] | None = None,
) -> TeamLedger:
    """Addebita le riparazioni delle vetture del giocatore dopo il GP.

    Addebito forzoso (record, non spend): mai vetture ferme per Cap, lo
    Sforamento e' il Cap negativo che ne risulta. Un movimento per
    evento danno, con pilota e giro nella causale.
    """
    player_ids = set(player_driver_ids)
    names = driver_names or {}
    for damage in damages:
        if damage.driver_id not in player_ids:
            continue
        cost = repair_cost_usd(damage)
        if cost == 0:
            continue
        name = names.get(damage.driver_id, f"vettura {damage.driver_id}")
        ledger = ledger.record(
            Transaction(
                kind=TransactionKind.DAMAGE,
                amount_usd=-cost,
                game_date=game_date,
                description=f"Riparazione {name} (giro {damage.lap})",
                counts_against_cap=True,
            )
        )
    return ledger


def overspend_penalty_usd(overspend_usd: int) -> int:
    """La riduzione del Cap del prossimo anno, proporzionale allo Sforamento."""
    if overspend_usd < 0:
        raise ValueError(f"overspend cannot be negative, got {overspend_usd}")
    return int(overspend_usd * OVERSPEND_PENALTY_RATIO)


def start_next_season(ledger: TeamLedger, game_date: date) -> TeamLedger:
    """Il registro del nuovo anno: Cap pieno meno la penalita' di Sforamento.

    Senza Sforamento il Cap torna intero (nessuna penalita'). La Cassa
    finale viaggia nel nuovo registro come saldo riportato; lo storico
    movimenti riparte vuoto con la stagione.
    """
    penalty = overspend_penalty_usd(ledger.overspend_usd)
    new_cap = max(SEASON_CAP_USD - penalty, MINIMUM_CAP_USD)
    entries: tuple[Transaction, ...] = ()
    cash = ledger.cash_usd
    if cash != 0:
        entries = (
            Transaction(
                kind=TransactionKind.OTHER,
                amount_usd=cash,
                game_date=game_date,
                description=f"Saldo riportato dalla stagione {ledger.season_year}",
            ),
        )
    return TeamLedger(
        season_year=ledger.season_year + 1,
        cap_usd=new_cap,
        entries=entries,
    )
