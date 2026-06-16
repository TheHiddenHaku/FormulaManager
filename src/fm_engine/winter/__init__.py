"""Fase inverno tra le stagioni: Carry-over, Progetti invernali, rollover (FOR-32).

Il pacchetto raccoglie i pezzi della transizione di stagione che toccano la
vettura e l'economia, da applicare DOPO il Mercato piloti:

- carryover: la vettura nuova eredita una quota degli Attributi con
  regressione verso la media di griglia (i distacchi si comprimono).
- projects: i Progetti invernali con budget dedicato, scelti dal giocatore.
- renegotiation: le scelte di fondo (motore proprio vs Cliente, Filosofia
  telaio) rinegoziabili ogni inverno, con effetti sulla stagione nuova.
- transition: l'orchestrazione (advance_winter) che mette in fila i pezzi e
  il rollover economico esistente (Cap, penalita' da Sforamento, Sponsor).

Motore puro (ADR 0002): nessun import di textual ne' psycopg. La schermata
inverno vive in fm_tui.screens.winter; la persistenza viaggia coi Checkpoint
sullo stato della Carriera gia' esistente (World e TeamLedger).
"""

from fm_engine.winter.carryover import (
    CarryoverConfig,
    apply_carryover,
    carried_over_attributes,
    grid_attribute_means,
    regress_attribute,
)
from fm_engine.winter.projects import (
    ATTRIBUTE_LABELS,
    CustomerEngineLocked,
    WinterBudgetExceeded,
    WinterProject,
    WinterProjectConfig,
    apply_winter_projects,
    validate_selection,
)
from fm_engine.winter.renegotiation import (
    RenegotiationChoices,
    apply_renegotiation,
)
from fm_engine.winter.transition import (
    WinterConfig,
    WinterDecisions,
    WinterOutcome,
    advance_winter,
)

__all__ = [
    "ATTRIBUTE_LABELS",
    "CarryoverConfig",
    "CustomerEngineLocked",
    "RenegotiationChoices",
    "WinterBudgetExceeded",
    "WinterConfig",
    "WinterDecisions",
    "WinterOutcome",
    "WinterProject",
    "WinterProjectConfig",
    "advance_winter",
    "apply_carryover",
    "apply_renegotiation",
    "apply_winter_projects",
    "carried_over_attributes",
    "grid_attribute_means",
    "regress_attribute",
    "validate_selection",
]
