"""Calendario di stagione: i 24 GP dell'anno dal Calendario 2026 (T5.1.1).

Il Calendario statico vive in fm_engine.circuits (CALENDAR_2026, 24
circuiti con calendar_order, data 2026 e Formato weekend). Le stagioni
successive replicano lo stesso Calendario traslando solo l'anno
(supabase initial_schema, commento su circuits.race_date_2026): qui si
costruiscono le righe della stagione per un anno qualsiasi.

Motore puro (ADR 0002): nessun import di TUI o database.
"""

from dataclasses import dataclass
from datetime import date

from fm_engine.circuits import CALENDAR_2026, Circuit


@dataclass(frozen=True)
class CalendarEntry:
    """Un Gran Premio del Calendario in una stagione: round, circuito, data.

    round e' il calendar_order del circuito (1-24); race_date e' la data
    della gara nell'anno della stagione (la data 2026 con l'anno traslato).
    """

    round: int
    circuit: Circuit
    race_date: date

    @property
    def is_standard(self) -> bool:
        """True per i GP in Formato weekend Standard, giocabili nel MVP."""
        return self.circuit.weekend_format_2026 == "standard"


def race_date_in(circuit: Circuit, year: int) -> date:
    """La data della gara del circuito nell'anno dato: il 2026 traslato.

    Il Calendario si ripete ogni stagione con il solo anno che avanza
    (initial_schema): giorno e mese restano quelli del 2026.
    """
    base = circuit.race_date_2026
    return date(year, base.month, base.day)


def season_calendar(year: int) -> tuple[CalendarEntry, ...]:
    """I 24 GP della stagione, in ordine di Calendario, con le date dell'anno."""
    return tuple(
        CalendarEntry(
            round=circuit.calendar_order,
            circuit=circuit,
            race_date=race_date_in(circuit, year),
        )
        for circuit in CALENDAR_2026
    )
