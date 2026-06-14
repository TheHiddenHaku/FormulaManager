"""Mercato piloti (T5.2.1): la finestra di fine stagione.

Il pacchetto modella il Mercato piloti (CONTEXT.md, Mercato piloti): la
fase di fine stagione in cui squadre AI e giocatore ingaggiano i piloti
con Contratto in scadenza e i liberi. La sub-issue M1 consegna i modelli
e l'apertura della fase con il popolamento del pool; offerte AI,
negoziazione del giocatore e persistenza arrivano nelle sub-issue
successive. Motore puro (ADR 0002): nessun import di TUI o database.
"""

from fm_engine.market.ai_offers import (
    can_afford,
    desired_salary,
    driver_quality,
    offer_duration,
    resolve_market,
    team_attractiveness,
)
from fm_engine.market.models import (
    AiMove,
    AiMoveKind,
    ExpiringContract,
    MarketPhase,
    MarketState,
)
from fm_engine.market.pool import (
    continuing_driver_ids,
    final_roster_ids,
    is_expiring,
    last_covered_season,
    open_market,
)

__all__ = [
    "AiMove",
    "AiMoveKind",
    "ExpiringContract",
    "MarketPhase",
    "MarketState",
    "can_afford",
    "continuing_driver_ids",
    "desired_salary",
    "driver_quality",
    "final_roster_ids",
    "is_expiring",
    "last_covered_season",
    "offer_duration",
    "open_market",
    "resolve_market",
    "team_attractiveness",
]
