"""Modello di Carriera: la partita del giocatore (CONTEXT.md, sezione Stagione).

Dataclass pura di dominio (ADR 0002): nessun import di TUI o database.
La persistenza a Checkpoint (fm_persistence, FOR-5) salva e ricarica
istanze di Career; la TUI di nuova Carriera (T1.3.1) le costruisce.

Scelte di modellazione:
- L'identita' della squadra del giocatore vive in world.player_slot:
  nome e colori della livrea scelti nel flusso di nuova Carriera (T1.3.1).
- I metadati di Checkpoint (id, created_at, last_checkpoint_at) sono
  None per una Carriera nuova mai salvata: li valorizza fm_persistence
  al primo salvataggio e restano opachi per il motore.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from fm_engine.development import DevelopmentProject
from fm_engine.economy import SolvencyState, TeamLedger
from fm_engine.info import KnowledgeState
from fm_engine.preseason import PreseasonState
from fm_engine.season import SeasonState
from fm_engine.weekend import WeekendState
from fm_engine.world.models import World


@dataclass(frozen=True)
class Career:
    """La partita del giocatore: nome, Mondo e metadati di Checkpoint.

    Possono esistere piu' Carriere parallele e indipendenti: l'id (UUID
    assegnato dal database al primo Checkpoint) le distingue. weekend
    e' lo stato del weekend di gara in corso (FOR-21): None fuori dal
    weekend, persistito ai Checkpoint per riprendere dalla sessione
    giusta. ledger e' il registro economico della squadra del giocatore
    (FOR-15): parte vuoto a inizio Carriera e viaggia coi Checkpoint.
    solvency e' la storia di solvibilita' (FOR-24): Misura d'emergenza,
    prestito attivo e conto alla rovescia del fallimento. projects sono
    i Progetti di sviluppo della squadra del giocatore (FOR-25). season
    e' lo stato pluristagionale (T5.1.1): anno, data di gioco e risultati
    dei GP da cui si ricostruiscono le classifiche, anch'esso ai Checkpoint.
    knowledge e' quanto il giocatore conosce gli attributi (Stime, T5.1.2),
    che si stringe con Test, prove libere e gare; preseason e' lo stato
    della fase Test pre-season (T5.1.2). Anch'essi viaggiano coi Checkpoint.
    """

    name: str
    world: World
    id: uuid.UUID | None = None
    created_at: datetime | None = None
    last_checkpoint_at: datetime | None = None
    weekend: WeekendState | None = None
    ledger: TeamLedger = field(default_factory=TeamLedger)
    solvency: SolvencyState = field(default_factory=SolvencyState)
    projects: tuple[DevelopmentProject, ...] = ()
    season: SeasonState = field(default_factory=SeasonState)
    knowledge: KnowledgeState = field(default_factory=KnowledgeState)
    preseason: PreseasonState = field(default_factory=PreseasonState)

    @property
    def never_saved(self) -> bool:
        """True se la Carriera non ha ancora un Checkpoint su database."""
        return self.id is None
