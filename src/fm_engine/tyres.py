"""Modello gomme: Mescole, nomina per GP e Degrado (FOR-10).

Gamma stagionale C1 (piu' dura) - C5 (piu' morbida) piu' Intermedia e
Bagnato. Ogni GP nomina 3 Mescole da asciutto (Soft/Medium/Hard
relative) dai dati statici del circuito. Ogni Mescola ha un offset di
passo (Soft piu' veloce) e un tasso di Degrado (Soft piu' fragile); il
Degrado cumulato e' monotono crescente coi giri e modulato da severita'
del circuito, Gestione gomme (vettura e pilota) e Aggressivita'.

Intermedia e Bagnato esistono nel modello dati ma restano inattivi in
gara: li attiva il meteo (T2.3.2). Costanti tarabili con l'harness di
bilanciamento (T2.4.1).
"""

from dataclasses import dataclass
from enum import Enum
from random import Random

from fm_engine.circuits import Circuit
from fm_engine.state import Aggression, RaceEntry


class Compound(Enum):
    """Una Mescola della gamma stagionale."""

    C1 = "c1"
    C2 = "c2"
    C3 = "c3"
    C4 = "c4"
    C5 = "c5"
    INTERMEDIATE = "intermediate"
    WET = "wet"

    @property
    def is_dry(self) -> bool:
        """True per le slick C1-C5."""
        return self not in (Compound.INTERMEDIATE, Compound.WET)


class CompoundSlot(Enum):
    """Il ruolo relativo di una Mescola nominata per il GP."""

    HARD = "hard"
    MEDIUM = "medium"
    SOFT = "soft"


# Pace offset per compound, relative to a C3 reference: softer is faster.
COMPOUND_PACE_OFFSET_SECONDS: dict[Compound, float] = {
    Compound.C1: 0.50,
    Compound.C2: 0.25,
    Compound.C3: 0.00,
    Compound.C4: -0.25,
    Compound.C5: -0.50,
    # Wet-weather tyres have no flat offset: their pace is entirely a
    # function of the track conditions (fm_engine.weather, T2.3.2).
    Compound.INTERMEDIATE: 0.0,
    Compound.WET: 0.0,
}

# Base degradation rate per lap of age: softer wears faster.
COMPOUND_DEGRADATION_RATE_SECONDS_PER_LAP: dict[Compound, float] = {
    Compound.C1: 0.030,
    Compound.C2: 0.045,
    Compound.C3: 0.060,
    Compound.C4: 0.080,
    Compound.C5: 0.105,
    Compound.INTERMEDIATE: 0.050,
    Compound.WET: 0.040,
}

# Degradation modulation parameters.
SEVERITY_FACTOR_BASE = 0.6
SEVERITY_FACTOR_PER_POINT = 0.2
MANAGEMENT_FACTOR_BASE = 1.35
MANAGEMENT_FACTOR_PER_POINT = 0.007
AGGRESSION_DEGRADATION_FACTOR: dict[Aggression, float] = {
    Aggression.PUSH: 1.25,
    Aggression.NORMAL: 1.0,
    Aggression.CONSERVE: 0.8,
}


@dataclass(frozen=True)
class TyreState:
    """Il set montato su una vettura: Mescola, eta' e Degrado cumulato.

    degradation_seconds e' la perdita di tempo sul giro dovuta all'usura
    corrente: ricalcolata a ogni Tick, monotona crescente con l'eta'.
    """

    compound: Compound
    age_laps: int
    degradation_seconds: float


def fresh_set(compound: Compound) -> TyreState:
    """Un set nuovo della Mescola data."""
    return TyreState(compound=compound, age_laps=0, degradation_seconds=0.0)


def nominated_compounds(circuit: Circuit) -> dict[CompoundSlot, Compound]:
    """Le 3 Mescole da asciutto nominate per il GP, dai dati statici."""
    hard, medium, soft = circuit.nominated_compounds
    return {
        CompoundSlot.HARD: Compound[hard],
        CompoundSlot.MEDIUM: Compound[medium],
        CompoundSlot.SOFT: Compound[soft],
    }


def severity_factor(circuit: Circuit) -> float:
    """Quanto l'asfalto del circuito accelera il Degrado (severita' 1-5)."""
    return SEVERITY_FACTOR_BASE + SEVERITY_FACTOR_PER_POINT * circuit.tyre_severity


def management_factor(entry: RaceEntry) -> float:
    """Quanto Gestione gomme di vettura e pilota frena il Degrado."""
    average = (entry.car.tyre_management + entry.driver.tyre_management) / 2
    return MANAGEMENT_FACTOR_BASE - MANAGEMENT_FACTOR_PER_POINT * average


def degradation_step_seconds(
    tyres: TyreState,
    entry: RaceEntry,
    circuit: Circuit,
    aggression: Aggression,
) -> float:
    """Il Degrado aggiunto dal giro appena percorso sul set montato."""
    rate = COMPOUND_DEGRADATION_RATE_SECONDS_PER_LAP[tyres.compound]
    return (
        rate
        * severity_factor(circuit)
        * management_factor(entry)
        * AGGRESSION_DEGRADATION_FACTOR[aggression]
    )


def after_lap(
    tyres: TyreState,
    entry: RaceEntry,
    circuit: Circuit,
    aggression: Aggression,
) -> TyreState:
    """Il set dopo un giro in piu': eta' +1, Degrado cumulato aggiornato."""
    increment = degradation_step_seconds(tyres, entry, circuit, aggression)
    return TyreState(
        compound=tyres.compound,
        age_laps=tyres.age_laps + 1,
        degradation_seconds=tyres.degradation_seconds + increment,
    )


def tyre_lap_loss_seconds(tyres: TyreState) -> float:
    """La perdita di tempo sul giro del set montato: offset piu' Degrado."""
    return COMPOUND_PACE_OFFSET_SECONDS[tyres.compound] + tyres.degradation_seconds


def random_dry_compound(circuit: Circuit, rng: Random) -> Compound:
    """Una Mescola nominata estratta a caso: utile per griglie di test."""
    return rng.choice(list(nominated_compounds(circuit).values()))
