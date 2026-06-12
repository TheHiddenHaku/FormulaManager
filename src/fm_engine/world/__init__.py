"""Modulo Mondo: generazione deterministica dello stato di inizio Carriera.

Espone generate(seed, config) e i modelli del Mondo: la Griglia (10
squadre AI piu' lo slot vuoto del giocatore), i 22 piloti, i Motoristi
con i rapporti di fornitura, i Contratti iniziali e le personalita' di
spesa. Il Setup squadra (FOR-7) vive in fm_engine.world.team_setup:
apply_team_setup applica le scelte del wizard. Motore puro (ADR 0002):
solo stdlib, niente textual ne' psycopg.
"""

from fm_engine.world.generation import generate
from fm_engine.world.models import (
    PLAYER_TEAM_ID,
    Contract,
    Driver,
    EngineSupplier,
    PlayerSlot,
    SpendingPersonality,
    Team,
    World,
    WorldConfig,
)
from fm_engine.world.team_setup import (
    TeamSetupChoices,
    TeamSetupConfig,
    apply_team_setup,
)

__all__ = [
    "PLAYER_TEAM_ID",
    "Contract",
    "Driver",
    "EngineSupplier",
    "PlayerSlot",
    "SpendingPersonality",
    "Team",
    "TeamSetupChoices",
    "TeamSetupConfig",
    "World",
    "WorldConfig",
    "apply_team_setup",
    "generate",
]
