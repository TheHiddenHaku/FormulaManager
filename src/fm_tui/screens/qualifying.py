"""Schermata Qualifiche: Classifica tempi di Q1, Q2, Q3 e griglia (FOR-21).

Il formato 2026: Q1 con le 22 vetture elimina le 6 piu' lente, Q2 con
16 ne elimina altre 6, Q3 con 10 assegna la pole. La simulazione e'
istantanea (simulate_qualifying, con gli effetti dei Programmi delle
libere); la schermata rivela i segmenti uno alla volta, come il sabato
vero: Q1, poi Q2, poi Q3, infine la griglia di partenza risultante. Le
eliminazioni sono marcate riga per riga, i tempi sono esatti per tutti
(il cronometro non mente mai).

Alla chiusura la schermata restituisce il QualifyingResult al flusso
weekend (dismiss), che avanza la macchina a stati e scrive il
Checkpoint. Niente scritture su database qui (ADR 0001).
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from fm_engine.circuits import Circuit
from fm_engine.practice import PracticeEffects
from fm_engine.qualifying import (
    ADVANCING_FROM_Q1,
    ADVANCING_FROM_Q2,
    QualifyingResult,
    SegmentClassification,
    simulate_qualifying,
)
from fm_engine.state import RaceEntry

# Cars advancing from each segment; None = the segment assigns the pole.
_SEGMENT_ADVANCING = {
    "q1": ADVANCING_FROM_Q1,
    "q2": ADVANCING_FROM_Q2,
    "q3": None,
}

_SEGMENT_TITLES = {
    "q1": "Q1: 22 vetture, le 6 piu' lente eliminate",
    "q2": "Q2: 16 vetture, altre 6 eliminate",
    "q3": "Q3: 10 vetture per la pole",
}

_GRID_STEP_TITLE = "Griglia di partenza"
_ELIMINATED_LABEL = "Eliminata"
_ADVANCING_LABEL = ""
_POLE_LABEL = "Pole position"


def _format_lap_time(seconds: float) -> str:
    """Il tempo sul giro in formato m:ss.mmm."""
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes)}:{remainder:06.3f}"


class QualifyingScreen(Screen[QualifyingResult | None]):
    """Le Qualifiche del GP: i 3 segmenti rivelati in sequenza, poi la griglia."""

    NAME = "qualifying"

    DEFAULT_CSS = """
    QualifyingScreen #qualifying-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    QualifyingScreen .section-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    QualifyingScreen #segment-table {
        height: auto;
        margin: 0 1 1 1;
    }
    """

    BINDINGS = [
        Binding("space", "next_step", "Prossimo segmento"),
        Binding("escape", "back", "Continua il weekend"),
    ]

    def __init__(
        self,
        entries: tuple[RaceEntry, ...],
        driver_names: dict[int, str],
        circuit: Circuit,
        seed: int,
        effects: PracticeEffects | None = None,
    ) -> None:
        super().__init__(name=self.NAME)
        self._entries = entries
        self._driver_names = driver_names
        self._circuit = circuit
        self._seed = seed
        self._effects = effects
        self._result: QualifyingResult | None = None
        # Reveal steps: one per segment, plus the final starting grid.
        self._step_index = 0

    # ------------------------------------------------------------------
    # Read-only state, for the header and the Pilot tests
    # ------------------------------------------------------------------

    @property
    def result(self) -> QualifyingResult | None:
        """L'esito completo delle Qualifiche (disponibile dal mount)."""
        return self._result

    @property
    def current_step(self) -> str:
        """Il passo rivelato: q1, q2, q3 oppure grid."""
        segments = ("q1", "q2", "q3")
        return segments[self._step_index] if self._step_index < len(segments) else "grid"

    @property
    def all_revealed(self) -> bool:
        """True quando anche la griglia di partenza e' in tabella."""
        return self.current_step == "grid"

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static("", id="qualifying-header")
        with VerticalScroll():
            yield Static("", id="segment-title", classes="section-title")
            yield DataTable(id="segment-table", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        result, _ = simulate_qualifying(
            self._entries, self._circuit, seed=self._seed, effects=self._effects
        )
        self._result = result
        table = self.query_one("#segment-table", DataTable)
        table.add_columns("Pos", "Pilota", "Tempo", "Distacco", "Esito")
        self._show_current_step()

    # ------------------------------------------------------------------
    # Reveal flow
    # ------------------------------------------------------------------

    def action_next_step(self) -> None:
        """Rivela il prossimo segmento (Q1 -> Q2 -> Q3 -> griglia)."""
        if self.all_revealed:
            self.notify("Qualifiche concluse: esc per continuare il weekend.")
            return
        self._step_index += 1
        self._show_current_step()

    def action_back(self) -> None:
        """Chiude le Qualifiche e restituisce l'esito al flusso weekend.

        L'esito c'e' sempre (la simulazione avviene al mount): la
        griglia e' decisa anche se il manager salta la rivelazione.
        """
        self.dismiss(self._result)

    def _show_current_step(self) -> None:
        step = self.current_step
        if step == "grid":
            self._populate_grid_table()
        else:
            index = ("q1", "q2", "q3").index(step)
            self._populate_segment_table(self._result.segments[index])
        self._update_header()

    def _populate_segment_table(self, segment: SegmentClassification) -> None:
        table = self.query_one("#segment-table", DataTable)
        table.clear()
        advancing = _SEGMENT_ADVANCING[segment.segment.value]
        best = segment.rows[0].time_seconds
        for row in segment.rows:
            if advancing is None:
                outcome = _POLE_LABEL if row.position == 1 else _ADVANCING_LABEL
            else:
                outcome = _ELIMINATED_LABEL if row.position > advancing else _ADVANCING_LABEL
            gap = "-" if row.position == 1 else f"+{row.time_seconds - best:.3f}"
            table.add_row(
                str(row.position),
                self._driver_names[row.driver_id],
                _format_lap_time(row.time_seconds),
                gap,
                outcome,
            )
        title = _SEGMENT_TITLES[segment.segment.value]
        self.query_one("#segment-title", Static).update(title)

    def _populate_grid_table(self) -> None:
        table = self.query_one("#segment-table", DataTable)
        table.clear()
        for position, entry in enumerate(self._result.grid, start=1):
            outcome = _POLE_LABEL if position == 1 else _ADVANCING_LABEL
            table.add_row(
                str(position),
                self._driver_names[entry.driver.id],
                "",
                "",
                outcome,
            )
        self.query_one("#segment-title", Static).update(_GRID_STEP_TITLE)

    def _update_header(self) -> None:
        if self.all_revealed:
            status = "Griglia decisa: esc per continuare il weekend"
        else:
            status = f"Segmento: {self.current_step.upper()}  |  spazio per proseguire"
        self.query_one("#qualifying-header", Static).update(
            f"Qualifiche: {self._circuit.name}  |  {status}"
        )
