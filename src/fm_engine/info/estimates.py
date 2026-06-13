"""Stime degli attributi con margine che si stringe (T5.1.2).

Una Stima e' un intervallo [low, high] che contiene sempre il valore vero
di un Attributo (vettura o pilota), mai il numero esatto (CONTEXT.md,
Stima). Il margine (semiampiezza) parte largo e si stringe accumulando
informazione: i Programmi di Conoscenza dei Test pre-season, le prove
libere e le gare disputate alzano il "livello di conoscenza" del soggetto
e restringono il margine, in modo monotono e mai sotto un minimo.

La conoscenza vive per soggetto (una vettura o un pilota), non per singolo
attributo: conoscere meglio un pilota stringe le Stime di tutti i suoi
attributi. Il valore vero resta sempre dentro l'intervallo, anche dopo
l'aggancio alla scala 0-100.

Motore puro (ADR 0002): nessun import di TUI o database.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

# Attributes live on a 0-100 scale (DB schema and WorldConfig).
MAX_SCALE = 100.0

# Margin (half-width) at knowledge level 0: a wide estimate to start.
INITIAL_MARGIN = 12.0
# Floor of the margin: even full knowledge keeps a residual uncertainty.
MINIMUM_MARGIN = 2.0
# Each knowledge level multiplies the margin by this factor (geometric
# decay towards the floor): monotone non-increasing, never negative.
MARGIN_DECAY = 0.55


def margin_for_level(level: int) -> float:
    """Il margine della Stima per il livello di conoscenza dato.

    Monotono non crescente nel livello, mai sotto MINIMUM_MARGIN.
    """
    if level < 0:
        raise ValueError(f"knowledge level cannot be negative, got {level}")
    return max(MINIMUM_MARGIN, INITIAL_MARGIN * (MARGIN_DECAY**level))


@dataclass(frozen=True)
class Estimate:
    """Una Stima: l'intervallo [low, high] che contiene il valore vero."""

    low: float
    high: float

    @property
    def margin(self) -> float:
        """La semiampiezza dell'intervallo: l'incertezza residua."""
        return (self.high - self.low) / 2

    def contains(self, value: float) -> bool:
        """True se il valore vero cade dentro l'intervallo della Stima."""
        return self.low <= value <= self.high


def estimate_band(true_value: float, margin: float) -> Estimate:
    """L'intervallo di Stima centrato sul valore vero, agganciato a 0-100.

    Il valore vero e' sempre contenuto: l'aggancio ai bordi sposta gli
    estremi verso l'interno senza mai escludere il vero.
    """
    low = max(0.0, true_value - margin)
    high = min(MAX_SCALE, true_value + margin)
    return Estimate(low=low, high=high)


def driver_subject(driver_id: int) -> str:
    """La chiave di conoscenza di un pilota (vale per i suoi 6 attributi)."""
    return f"driver:{driver_id}"


def car_subject(team_id: int) -> str:
    """La chiave di conoscenza della vettura di una squadra."""
    return f"car:{team_id}"


@dataclass(frozen=True)
class KnowledgeState:
    """Quanto il giocatore conosce ogni soggetto (vettura o pilota).

    levels mappa la chiave di soggetto al livello di conoscenza (intero
    non negativo); le chiavi assenti valgono livello 0 (Stima larga). Lo
    stato e' immutabile: observed() ritorna un nuovo stato con i livelli
    aggiornati.
    """

    levels: Mapping[str, int] = field(default_factory=dict)

    def level_for(self, subject: str) -> int:
        """Il livello di conoscenza del soggetto, 0 se mai osservato."""
        return self.levels.get(subject, 0)

    def estimate_for(self, subject: str, true_value: float) -> Estimate:
        """La Stima di un attributo del soggetto, col margine del suo livello."""
        return estimate_band(true_value, margin_for_level(self.level_for(subject)))

    def observed(self, subjects: Iterable[str], amount: int = 1) -> "KnowledgeState":
        """Alza il livello di conoscenza dei soggetti osservati (margine piu' stretto)."""
        if amount < 0:
            raise ValueError(f"knowledge gain cannot be negative, got {amount}")
        if amount == 0:
            return self
        levels = dict(self.levels)
        for subject in subjects:
            levels[subject] = levels.get(subject, 0) + amount
        return KnowledgeState(levels=levels)


def default_estimate(true_value: float) -> Estimate:
    """La Stima al livello 0 (nessuna conoscenza): il margine piu' largo."""
    return estimate_band(true_value, INITIAL_MARGIN)


def format_estimate(estimate: Estimate) -> str:
    """La Stima come intervallo testuale, es. "48-72"; il vero resta dentro.

    Il limite inferiore arrotondato per difetto e il superiore per
    eccesso: l'intervallo mostrato contiene sempre quello reale e quindi
    il valore vero.
    """
    low = int(math.floor(estimate.low))
    high = int(math.ceil(estimate.high))
    return f"{low}-{high}"
