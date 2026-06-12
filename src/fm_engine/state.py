"""Stato di gara e Ordini del manager (FOR-8).

Dataclass immutabili: ogni Tick (= giro) il riduttore step produce un
nuovo RaceState senza mutare il precedente. Gli Ordini del MVP sono
Aggressivita', Ordine di scuderia e Istruzione sui duelli; l'Ordine di
pit stop arriva con T2.2.1.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from fm_engine.circuits import Circuit
from fm_engine.world.models import CAR_ATTRIBUTES, Driver, PlayerSlot, Team


class Aggression(Enum):
    """Aggressivita': livello di spinta richiesto a un pilota."""

    PUSH = "push"
    NORMAL = "normal"
    CONSERVE = "conserve"


class TeamOrder(Enum):
    """Ordine di scuderia: regola i rapporti tra i 2 piloti della squadra."""

    SWAP_POSITIONS = "swap_positions"
    HOLD_POSITIONS = "hold_positions"
    NO_ATTACK = "no_attack"


class DuelInstruction(Enum):
    """Istruzione sui duelli: comportamento nei confronti diretti."""

    STANDARD = "standard"
    DEFEND_HARD = "defend_hard"
    NO_RISK = "no_risk"


@dataclass(frozen=True)
class CarAttributes:
    """I 6 Attributi vettura di una iscritta alla gara, scala 0-100."""

    engine_power: int
    downforce: int
    aero_efficiency: int
    mechanical_grip: int
    tyre_management: int
    reliability: int

    @classmethod
    def from_team(cls, team: Team) -> "CarAttributes":
        """Gli attributi vettura di una squadra AI della Griglia."""
        return cls(**{name: getattr(team, name) for name in CAR_ATTRIBUTES})

    @classmethod
    def from_player_slot(cls, slot: PlayerSlot) -> "CarAttributes":
        """Gli attributi della vettura del giocatore, dopo il Setup squadra."""
        return cls(**slot.car_attributes)

    def as_dict(self) -> dict[str, int]:
        """Gli attributi indicizzati per nome canonico."""
        return {name: getattr(self, name) for name in CAR_ATTRIBUTES}


@dataclass(frozen=True)
class RaceEntry:
    """Una vettura iscritta alla sessione: pilota, squadra e vettura."""

    driver: Driver
    team_id: int
    car: CarAttributes


@dataclass(frozen=True)
class DriverOrders:
    """Gli Ordini attivi su un singolo pilota per il prossimo Tick."""

    aggression: Aggression = Aggression.NORMAL
    duel_instruction: DuelInstruction = DuelInstruction.STANDARD


_DEFAULT_DRIVER_ORDERS = DriverOrders()


@dataclass(frozen=True)
class Orders:
    """Gli Ordini del manager consumati da step a ogni Tick.

    Mappature sparse: i piloti e le squadre assenti corrono con i
    default (Aggressivita' normale, nessun Ordine di scuderia).
    """

    drivers: Mapping[int, DriverOrders] = field(default_factory=dict)
    teams: Mapping[int, TeamOrder] = field(default_factory=dict)

    def for_driver(self, driver_id: int) -> DriverOrders:
        """Gli Ordini del pilota indicato, o i default."""
        return self.drivers.get(driver_id, _DEFAULT_DRIVER_ORDERS)

    def for_team(self, team_id: int) -> TeamOrder | None:
        """L'Ordine di scuderia attivo sulla squadra, se presente."""
        return self.teams.get(team_id)


@dataclass(frozen=True)
class TimesheetRow:
    """Una riga della Classifica tempi: i tempi sono sempre esatti (CONTEXT.md)."""

    position: int
    driver_id: int
    time_seconds: float


@dataclass(frozen=True)
class CarRaceState:
    """Lo stato in gara di una singola vettura a fine Tick."""

    entry: RaceEntry
    # 1-based race position at the end of the last completed lap.
    position: int
    total_time_seconds: float
    last_lap_seconds: float
    # Cumulative gap from the race leader at the end of the last lap.
    gap_to_leader_seconds: float


@dataclass(frozen=True)
class RaceState:
    """Lo stato completo della gara dopo l'ultimo Tick simulato.

    cars e' ordinata per posizione (la prima e' il leader). Il seed
    della gara vive nello stato: step deriva da (seed, giro) un RNG
    dedicato, cosi' due run con lo stesso seed e gli stessi Ordini
    producono stati ed eventi identici.
    """

    seed: int
    circuit: Circuit
    lap: int
    total_laps: int
    cars: tuple[CarRaceState, ...]
    fastest_lap_seconds: float | None
    fastest_lap_driver_id: int | None
    finished: bool

    def car_of(self, driver_id: int) -> CarRaceState:
        """Lo stato della vettura del pilota indicato."""
        for car in self.cars:
            if car.entry.driver.id == driver_id:
                return car
        raise KeyError(f"no car for driver id {driver_id}")
