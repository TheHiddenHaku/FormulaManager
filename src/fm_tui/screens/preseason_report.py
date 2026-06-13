"""Schermata report di fine Test pre-season (T5.1.2).

Riassume la fase: i giorni di Conoscenza spesi e i margini delle Stime
ottenuti sui propri piloti e sulla propria vettura. Se non si e' dedicato
alcun giorno alla Conoscenza lo segnala esplicitamente (Stime ancora
larghe). Schermata di sola presentazione: riceve il report gia' calcolato.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Static

from fm_engine.preseason import PreseasonReport

_ZERO_KNOWLEDGE_WARNING = (
    "0 giorni di Conoscenza: le Stime restano larghe. "
    "Affronterai il primo GP senza una lettura affidabile della tua vettura."
)


class PreseasonReportScreen(Screen[None]):
    """Il report di fine Test pre-season: conoscenza spesa e Stime ottenute."""

    NAME = "preseason_report"

    DEFAULT_CSS = """
    PreseasonReportScreen #report-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    PreseasonReportScreen #report-body {
        margin: 1;
        padding: 0 1;
    }

    PreseasonReportScreen #report-warning {
        margin: 0 1;
        padding: 0 1;
        color: $warning;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Chiudi il report"),
    ]

    def __init__(self, report: PreseasonReport, driver_names: dict[int, str]) -> None:
        super().__init__(name=self.NAME)
        self._report = report
        self._driver_names = driver_names

    def compose(self) -> ComposeResult:
        yield Static("Report Test pre-season", id="report-header")
        with VerticalScroll():
            yield Static(self._body_text(), id="report-body")
            if self._report.zero_knowledge:
                yield Static(_ZERO_KNOWLEDGE_WARNING, id="report-warning")
        yield Footer()

    def action_back(self) -> None:
        """Chiude il report e prosegue verso la stagione."""
        self.dismiss(None)

    def _body_text(self) -> str:
        report = self._report
        lines = [
            f"Giorni di Conoscenza spesi: {report.knowledge_days}",
            "",
            "Margini delle Stime a fine fase (piu' basso = piu' preciso):",
            f"  La tua vettura: +/- {report.car_margin:.1f}",
        ]
        for info in report.drivers:
            name = self._driver_names.get(info.driver_id, str(info.driver_id))
            lines.append(f"  {name}: +/- {info.margin:.1f}")
        return "\n".join(lines)
