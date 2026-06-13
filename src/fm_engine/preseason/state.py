"""Stato della fase Test pre-season (T5.1.2).

PreseasonState e' immutabile e tiene i giorni gia' svolti, ciascuno con i
Programmi assegnati ai piloti del giocatore. Lo stato di partenza (nessun
giorno svolto) e' il default: la persistenza non lo scrive. La fase e'
conclusa quando i giorni svolti raggiungono il totale.

Motore puro (ADR 0002).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from fm_engine.preseason.programmes import (
    PRESEASON_DAYS,
    PreseasonProgramme,
)


@dataclass(frozen=True)
class PreseasonDay:
    """Un giorno di Test svolto: i Programmi assegnati per pilota."""

    day: int
    programmes: Mapping[int, PreseasonProgramme]

    @property
    def has_knowledge(self) -> bool:
        """True se almeno un pilota ha svolto un Programma di Conoscenza."""
        return any(
            programme is PreseasonProgramme.KNOWLEDGE for programme in self.programmes.values()
        )


@dataclass(frozen=True)
class PreseasonState:
    """La fase Test pre-season: giorni totali e giorni gia' svolti."""

    total_days: int = PRESEASON_DAYS
    days_done: tuple[PreseasonDay, ...] = field(default_factory=tuple)

    @property
    def current_day(self) -> int:
        """Il prossimo giorno da svolgere (1-based)."""
        return len(self.days_done) + 1

    @property
    def completed(self) -> bool:
        """True quando tutti i giorni di Test sono stati svolti."""
        return len(self.days_done) >= self.total_days

    @property
    def knowledge_days(self) -> int:
        """Quanti giorni hanno incluso almeno un Programma di Conoscenza."""
        return sum(1 for day in self.days_done if day.has_knowledge)
