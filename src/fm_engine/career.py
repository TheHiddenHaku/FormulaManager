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
from dataclasses import dataclass
from datetime import datetime

from fm_engine.world.models import World


@dataclass(frozen=True)
class Career:
    """La partita del giocatore: nome, Mondo e metadati di Checkpoint.

    Possono esistere piu' Carriere parallele e indipendenti: l'id (UUID
    assegnato dal database al primo Checkpoint) le distingue.
    """

    name: str
    world: World
    id: uuid.UUID | None = None
    created_at: datetime | None = None
    last_checkpoint_at: datetime | None = None

    @property
    def never_saved(self) -> bool:
        """True se la Carriera non ha ancora un Checkpoint su database."""
        return self.id is None
