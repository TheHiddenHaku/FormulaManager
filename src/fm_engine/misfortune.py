"""Sfiga: Guasti, Errori e Incidenti estratti giro per giro (FOR-11).

Tre estrazioni indipendenti a ogni Tick:
- Guasto: probabilita' inversa dell'Affidabilita' della vettura.
- Errore pilota: probabilita' inversa della Costanza, aggravata da
  Aggressivita' Push e dai duelli in corso (vetture in lotta ravvicinata).
- Incidente: contatti nei duelli e alla partenza.

Decisione di design, esplicita e vincolante: NESSUN correttivo nascosto
anti-strisce. Le estrazioni sono indipendenti tra giri e tra gare, le
probabilita' sono funzioni dei soli attributi e Ordini correnti, mai
della storia recente. La sfortuna e' onesta.

Tutti i parametri vivono in MisfortuneConfig: tarabili con l'harness di
bilanciamento (T2.4.1) e azzerabili nei test che vogliono una gara
sterile (MisfortuneConfig.disabled()).
"""

from dataclasses import dataclass, replace
from random import Random

from fm_engine.state import Aggression

# Components that can fail, surfaced as the visible cause of the Guasto.
FAILURE_COMPONENTS: tuple[str, ...] = (
    "engine",
    "gearbox",
    "hydraulics",
    "brakes",
    "electronics",
    "suspension",
)

# Visible causes of a driver error.
ERROR_CAUSES: tuple[str, ...] = (
    "braking_too_deep",
    "kerb_ride",
    "cold_tyres",
    "traffic_misjudged",
)


@dataclass(frozen=True)
class MisfortuneConfig:
    """Parametri della Sfiga, tarabili e azzerabili.

    Le probabilita' base sono per vettura per Tick; i fattori modulano
    in funzione di attributi e contesto.
    """

    # Failure: probability = failure_base * (failure_ceiling - reliability).
    failure_base: float = 0.000022
    failure_ceiling: float = 130.0
    # Driver error: probability = error_base * (100 - consistency), then
    # multiplied by the push / duel factors below.
    error_base: float = 0.00010
    error_push_factor: float = 1.5
    error_conserve_factor: float = 0.7
    error_duel_factor: float = 1.5
    # Share of errors severe enough to end the race on the spot.
    terminal_error_share: float = 0.12
    # Time lost by a survivable error, uniform range in seconds.
    error_time_loss_range: tuple[float, float] = (1.5, 4.0)
    # Contacts: per-car draw on lap 1, per-attempt draw inside a duel.
    start_contact_probability: float = 0.018
    duel_contact_probability: float = 0.0035
    duel_contact_push_factor: float = 1.5
    duel_contact_conserve_factor: float = 0.7
    # Outcome of a contact for each involved car.
    accident_dnf_probability: float = 0.55
    # Time lost by a car that survives a contact, uniform range in seconds.
    accident_time_loss_range: tuple[float, float] = (2.0, 6.0)
    # Damage entity ranges (USD), minor (car continues) and major (DNF).
    minor_damage_usd_range: tuple[int, int] = (100_000, 800_000)
    major_damage_usd_range: tuple[int, int] = (800_000, 3_000_000)
    # Cars within this gap from the car ahead count as "in a duel" for
    # the error aggravation (proxy of close racing at the previous Tick).
    duel_proximity_seconds: float = 1.0

    @classmethod
    def disabled(cls) -> "MisfortuneConfig":
        """Sfiga spenta: per test e scenari controllati."""
        return cls(
            failure_base=0.0,
            error_base=0.0,
            start_contact_probability=0.0,
            duel_contact_probability=0.0,
        )

    def scaled(self, factor: float) -> "MisfortuneConfig":
        """Una copia con le probabilita' base scalate del fattore dato."""
        return replace(
            self,
            failure_base=self.failure_base * factor,
            error_base=self.error_base * factor,
            start_contact_probability=self.start_contact_probability * factor,
            duel_contact_probability=self.duel_contact_probability * factor,
        )


def failure_probability(config: MisfortuneConfig, reliability: int) -> float:
    """Probabilita' di Guasto per Tick: inversa dell'Affidabilita'."""
    return max(config.failure_base * (config.failure_ceiling - reliability), 0.0)


def error_probability(
    config: MisfortuneConfig,
    consistency: int,
    aggression: Aggression,
    in_duel: bool,
) -> float:
    """Probabilita' di Errore per Tick: inversa della Costanza, aggravata."""
    probability = max(config.error_base * (100 - consistency), 0.0)
    if aggression is Aggression.PUSH:
        probability *= config.error_push_factor
    elif aggression is Aggression.CONSERVE:
        probability *= config.error_conserve_factor
    if in_duel:
        probability *= config.error_duel_factor
    return probability


def duel_contact_probability(config: MisfortuneConfig, aggression: Aggression) -> float:
    """Probabilita' di contatto in un tentativo di sorpasso."""
    probability = config.duel_contact_probability
    if aggression is Aggression.PUSH:
        probability *= config.duel_contact_push_factor
    elif aggression is Aggression.CONSERVE:
        probability *= config.duel_contact_conserve_factor
    return probability


def damage_amount_usd(config: MisfortuneConfig, severe: bool, rng: Random) -> int:
    """L'entita' del danno, pronta per Danni su Cassa e Cap (Economia)."""
    low, high = config.major_damage_usd_range if severe else config.minor_damage_usd_range
    return rng.randint(low, high)
