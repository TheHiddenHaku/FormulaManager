"""Eventi extra-gara: il pool e l'estrazione tra un GP e l'altro (FOR-27)."""

from fm_engine.events_extra.draw import (
    EXTRA_EVENT_PROBABILITY,
    ExtraEventOutcome,
    draw_extra_event,
)
from fm_engine.events_extra.pool import (
    EXTRA_EVENT_POOL,
    ExtraEvent,
    ExtraEventKind,
)

__all__ = [
    "EXTRA_EVENT_POOL",
    "EXTRA_EVENT_PROBABILITY",
    "ExtraEvent",
    "ExtraEventKind",
    "ExtraEventOutcome",
    "draw_extra_event",
]
