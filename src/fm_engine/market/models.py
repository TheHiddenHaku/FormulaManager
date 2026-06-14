"""Modelli del Mercato piloti (T5.2.1, sub-issue M1).

Dataclass immutabili (frozen) che descrivono lo stato transitorio della
fase di Mercato di fine stagione (CONTEXT.md, Mercato piloti) e i record
di supporto. Motore puro (ADR 0002): nessun import di TUI o database.

MarketState e' lo stato della fase mentre e' aperta: il pool dei Contratti
in scadenza, i piloti liberi disponibili, i sedili vacanti per squadra, le
richieste salariali transitorie dei liberi e il log delle mosse AI. Lo
stato di partenza e' la fase chiusa, cioe' MarketState() senza argomenti,
in linea con la convenzione di SeasonState()/PreseasonState(): la
persistenza ai Checkpoint (sub-issue M4) scrive NULL quando lo stato
coincide col default.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class MarketPhase(Enum):
    """Fase del Mercato piloti: chiusa fuori finestra, aperta a fine stagione."""

    CLOSED = "closed"
    OPEN = "open"


class AiMoveKind(Enum):
    """Tipo di una mossa AI registrata nel log del Mercato.

    OFFER: una squadra AI ha presentato un'offerta su un pilota.
    SIGNING: una squadra AI ha ingaggiato un pilota.
    FORCED_ASSIGNMENT: assegnazione forzata di un libero a un sedile vuoto
    per garantire la convergenza (2 piloti per squadra), usata dal
    fallback delle offerte AI nella sub-issue M2.
    """

    OFFER = "offer"
    SIGNING = "signing"
    FORCED_ASSIGNMENT = "forced_assignment"


@dataclass(frozen=True)
class ExpiringContract:
    """Un Contratto in scadenza entrato nel pool del Mercato.

    team_id e' la squadra che il pilota sta lasciando (il sedile che si
    libera); salary_usd e' l'ultimo stipendio, base delle offerte rivali;
    last_season e' l'ultima stagione coperta dal Contratto scaduto.
    """

    driver_id: int
    team_id: int
    salary_usd: int
    last_season: int


@dataclass(frozen=True)
class AiMove:
    """Una riga del log mosse AI: squadra, pilota, tipo, importo, durata.

    E' la forma canonica del log e anche cio' che la persistenza (M4)
    serializza nel payload market_state. duration_seasons e' la durata
    offerta o firmata (1-3 stagioni); salary_usd l'ingaggio in USD.
    """

    team_id: int
    driver_id: int
    kind: AiMoveKind
    salary_usd: int
    duration_seasons: int


@dataclass(frozen=True)
class MarketState:
    """Stato transitorio della fase di Mercato piloti.

    Il default (nessun argomento) e' la fase chiusa: lo stato di partenza,
    coerente con SeasonState()/PreseasonState(), che la persistenza (M4)
    salva come NULL. seats_per_team e' la dimensione obiettivo del roster
    di ogni squadra (2 piloti, CONTEXT.md). pool sono i Contratti in
    scadenza; free_agent_ids i piloti liberi disponibili; salary_demands
    le richieste salariali transitorie dei liberi (driver_id -> USD, vivono
    solo finche' la fase e' aperta); vacant_seats i sedili vacanti per
    squadra (team_id -> conteggio); signings i piloti ingaggiati durante la
    fase per squadra (team_id -> driver_id, prodotti dalla risoluzione AI in
    M2 e dalla negoziazione del giocatore in M3); ai_moves il log delle
    mosse AI.
    """

    phase: MarketPhase = MarketPhase.CLOSED
    concluded_year: int | None = None
    seats_per_team: int = 2
    pool: tuple[ExpiringContract, ...] = ()
    free_agent_ids: tuple[int, ...] = ()
    salary_demands: Mapping[int, int] = field(default_factory=dict)
    vacant_seats: Mapping[int, int] = field(default_factory=dict)
    signings: Mapping[int, tuple[int, ...]] = field(default_factory=dict)
    ai_moves: tuple[AiMove, ...] = ()

    @property
    def is_open(self) -> bool:
        """True quando la finestra di Mercato e' aperta."""
        return self.phase is MarketPhase.OPEN

    @property
    def pool_driver_ids(self) -> tuple[int, ...]:
        """Gli id dei piloti con Contratto in scadenza nel pool."""
        return tuple(contract.driver_id for contract in self.pool)

    @property
    def available_driver_ids(self) -> tuple[int, ...]:
        """Tutti i piloti ingaggiabili: in scadenza piu' liberi."""
        return self.pool_driver_ids + self.free_agent_ids

    @property
    def signed_driver_ids(self) -> frozenset[int]:
        """Tutti i piloti gia' ingaggiati nella fase, da qualsiasi squadra."""
        return frozenset(driver_id for ids in self.signings.values() for driver_id in ids)

    def signings_for(self, team_id: int) -> tuple[int, ...]:
        """I piloti ingaggiati dalla squadra durante la fase (vuoto se nessuno)."""
        return tuple(self.signings.get(team_id, ()))

    def vacant_seats_for(self, team_id: int) -> int:
        """I sedili vacanti della squadra indicata (0 se non vacante)."""
        return self.vacant_seats.get(team_id, 0)

    def driver_count_for(self, team_id: int) -> int:
        """Il conteggio piloti della squadra: obiettivo meno sedili vacanti."""
        return self.seats_per_team - self.vacant_seats_for(team_id)
