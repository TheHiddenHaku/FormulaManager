"""Stato di gara e Ordini del manager (FOR-8).

Dataclass immutabili: ogni Tick (= giro) il riduttore step produce un
nuovo RaceState senza mutare il precedente. Gli Ordini del MVP sono
Aggressivita', Ordine di scuderia e Istruzione sui duelli; l'Ordine di
pit stop arriva con T2.2.1.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from fm_engine.circuits import Circuit
from fm_engine.neutralization import RaceRegime
from fm_engine.world.models import CAR_ATTRIBUTES, Driver, PlayerSlot, Team

if TYPE_CHECKING:
    # Solo per typing: l'import runtime andrebbe in ciclo (tyres,
    # misfortune e weather importano state, direttamente o via tyres).
    from fm_engine.misfortune import MisfortuneConfig
    from fm_engine.tyres import Compound, TyreState
    from fm_engine.weather import SessionForecast


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
class PitOrder:
    """Ordine di pit stop con scelta della Mescola (FOR-10)."""

    compound: "Compound"


@dataclass(frozen=True)
class DriverOrders:
    """Gli Ordini attivi su un singolo pilota per il prossimo Tick.

    pit, se presente, fa rientrare la vettura ai box in questo giro.
    """

    aggression: Aggression = Aggression.NORMAL
    duel_instruction: DuelInstruction = DuelInstruction.STANDARD
    pit: PitOrder | None = None


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
    # Fitted tyre set: compound, age in laps, current degradation (FOR-10).
    tyres: "TyreState"
    # Every compound fitted so far, starting set included (bi-compound rule).
    compounds_used: tuple["Compound", ...]


@dataclass(frozen=True)
class RaceState:
    """Lo stato completo della gara dopo l'ultimo Tick simulato.

    cars e' ordinata per posizione (la prima e' il leader) e contiene
    solo le vetture in gara; gli Abbandoni vivono in dnfs, in ordine di
    uscita (position = 0, non classificate). Il seed della gara vive
    nello stato: step deriva da (seed, giro) un RNG dedicato, cosi' due
    run con lo stesso seed e gli stessi Ordini producono stati ed
    eventi identici.
    """

    seed: int
    circuit: Circuit
    lap: int
    total_laps: int
    cars: tuple[CarRaceState, ...]
    fastest_lap_seconds: float | None
    fastest_lap_driver_id: int | None
    finished: bool
    # Misfortune parameters for this race (FOR-11); see fm_engine.misfortune.
    misfortune: "MisfortuneConfig"
    dnfs: tuple[CarRaceState, ...] = ()
    # Current race regime (FOR-12): green, safety car or VSC, with the
    # laps left under neutralization and the post-restart risk window.
    regime: RaceRegime = RaceRegime.GREEN
    regime_laps_remaining: int = 0
    restart_risk_laps_remaining: int = 0
    # Duel hysteresis (FOR-36): (overtaker, overtaken) driver id pairs
    # from the last lap; the overtaken driver does not retry at once.
    last_lap_overtakes: tuple[tuple[int, int], ...] = ()
    # Undercut window registry (FOR-38): (attacker, target) driver id
    # pairs whose window is currently open. One UndercutWindow event per
    # opening: an open pair stays silent until its window closes.
    active_undercut_windows: tuple[tuple[int, int], ...] = ()
    # Session weather (FOR-13): forecast, current rain and track wetness.
    forecast: "SessionForecast | None" = None
    rain_intensity: float = 0.0
    track_wetness: float = 0.0
    # True once the track got properly wet: the bi-compound rule only
    # applies to dry races.
    saw_rain: bool = False
    # Flat per-lap pace corrections from the practice programmes
    # (FOR-21), by driver id: setup deficit minus race pace bonus.
    # Sparse like Orders: absent drivers run with no correction.
    pace_adjustments: Mapping[int, float] = field(default_factory=dict)

    def car_of(self, driver_id: int) -> CarRaceState:
        """Lo stato della vettura del pilota indicato, anche se ritirata."""
        for car in self.cars + self.dnfs:
            if car.entry.driver.id == driver_id:
                return car
        raise KeyError(f"no car for driver id {driver_id}")
