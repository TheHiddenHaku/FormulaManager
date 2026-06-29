"""Visuale Scuderie: una vista d'insieme per squadra (visuale-scuderie).

Raccoglie in un unico posto, per ogni scuderia della Griglia, le informazioni
economiche, tecniche e sportive: posizione in classifica e punti, piloti con
stipendio, Attributi vettura (a Stime, come altrove), Cassa, fornitura motore e
Filosofia telaio, e gli Sviluppi (i Progetti del giocatore; per le avversarie il
dato non e' tracciato). La tabella elenca le squadre in ordine di classifica coi
colori di livrea; selezionando una riga il pannello di dettaglio mostra la
scuderia con i suoi colori in evidenza. Solo resa (ADR 0002): nessuna logica qui.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from fm_engine.career import Career
from fm_engine.info import car_subject, format_estimate
from fm_engine.season import constructor_standings
from fm_engine.world.models import CAR_ATTRIBUTES, PLAYER_TEAM_ID
from fm_tui.widgets.balance_bar import format_usd
from fm_tui.widgets.team_colors import name_with_team_swatches, team_swatches

_PLAYER_TEAM_FALLBACK = "(la tua squadra)"
_PLAYER_SUFFIX = " (tu)"
_EMPTY_CELL = "-"
_NO_SETUP = "Setup squadra non completato."
_AI_DEVELOPMENTS = "Sviluppi: non disponibili (squadra avversaria)."

# Italian labels of the 6 car attributes, in CAR_ATTRIBUTES order.
_CAR_ATTRIBUTE_LABELS: dict[str, str] = {
    "engine_power": "Potenza",
    "downforce": "Carico",
    "aero_efficiency": "Efficienza",
    "mechanical_grip": "Meccanica",
    "tyre_management": "G. gomme",
    "reliability": "Affidabilita'",
}

# Italian labels of the chassis philosophies.
_PHILOSOPHY_LABELS: dict[str, str] = {
    "fast": "veloce",
    "balanced": "equilibrata",
    "technical": "tecnica",
}


class ScuderieScreen(Screen[None]):
    """La visuale Scuderie: tabella delle squadre e dettaglio di quella scelta."""

    NAME = "scuderie"

    DEFAULT_CSS = """
    ScuderieScreen #scuderie-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    ScuderieScreen DataTable {
        height: auto;
        margin: 1;
    }

    ScuderieScreen #scuderie-detail {
        margin: 0 1 1 1;
        padding: 1 2;
        border: solid $primary;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Chiudi le scuderie"),
    ]

    def __init__(self, career: Career) -> None:
        super().__init__(name=self.NAME)
        self._career = career
        world = career.world
        self._driver_names = {driver.id: driver.name for driver in world.drivers}
        self._ai_teams = {team.id: team for team in world.ai_teams}
        self._supplier_names = {supplier.id: supplier.name for supplier in world.engine_suppliers}
        team_ids = [PLAYER_TEAM_ID, *(team.id for team in world.ai_teams)]
        self._standings = constructor_standings(career.season.results, team_ids)

    def compose(self) -> ComposeResult:
        yield Static(self._header(), id="scuderie-header")
        with VerticalScroll():
            yield DataTable(id="scuderie-table", cursor_type="row", zebra_stripes=True)
            yield Static("", id="scuderie-detail")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#scuderie-table", DataTable)
        table.add_columns("Pos", "Scuderia", "Punti", "Cassa")
        for standing in self._standings:
            team_id = standing.team_id
            primary, secondary = self._team_colors(team_id)
            table.add_row(
                str(standing.position),
                name_with_team_swatches(self._team_name(team_id), primary, secondary),
                str(standing.points),
                format_usd(self._team_cash(team_id)),
                key=str(team_id),
            )
        # Open on the first team in the standings.
        if self._standings:
            self._show_detail(self._standings[0].team_id)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Aggiorna il dettaglio con la scuderia selezionata."""
        if event.row_key.value is not None:
            self._show_detail(int(event.row_key.value))

    def action_back(self) -> None:
        """Chiude la visuale e torna alla schermata precedente."""
        self.dismiss(None)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _header(self) -> str:
        return f"Scuderie {self._career.season.year}  |  esc per chiudere"

    def _show_detail(self, team_id: int) -> None:
        self.query_one("#scuderie-detail", Static).update(self._detail(team_id))

    def _detail(self, team_id: int) -> Text:
        primary, secondary = self._team_colors(team_id)
        position = next(s.position for s in self._standings if s.team_id == team_id)
        points = next(s.points for s in self._standings if s.team_id == team_id)

        text = team_swatches(primary, secondary)
        text.append(f" {self._team_name(team_id)}\n", style="bold")
        text.append(f"Posizione: {position} ({points} punti)\n")
        text.append(f"Motore: {self._engine(team_id)}  |  Telaio: {self._philosophy(team_id)}\n")
        text.append(f"Cassa: {format_usd(self._team_cash(team_id))}\n")

        drivers = self._team_drivers(team_id)
        if drivers:
            text.append("Piloti:\n")
            for name, salary in drivers:
                text.append(f"  - {name} (stipendio {format_usd(salary)})\n")
        else:
            text.append(f"Piloti: {_NO_SETUP}\n")

        estimates = self._car_estimates(team_id)
        if estimates is None:
            text.append(f"Valori auto: {_NO_SETUP}\n")
        else:
            attributes = "  ".join(f"{label} {value}" for label, value in estimates)
            text.append(f"Valori auto (Stime): {attributes}\n")

        text.append(self._developments(team_id))
        return text

    # ------------------------------------------------------------------
    # Per-team data
    # ------------------------------------------------------------------

    def _team_name(self, team_id: int) -> str:
        if team_id == PLAYER_TEAM_ID:
            return (self._career.world.player_slot.name or _PLAYER_TEAM_FALLBACK) + _PLAYER_SUFFIX
        return self._ai_teams[team_id].name

    def _team_colors(self, team_id: int) -> tuple[str | None, str | None]:
        if team_id == PLAYER_TEAM_ID:
            slot = self._career.world.player_slot
            return slot.primary_color, slot.secondary_color
        team = self._ai_teams[team_id]
        return team.primary_color, team.secondary_color

    def _team_cash(self, team_id: int) -> int:
        if team_id == PLAYER_TEAM_ID:
            return self._career.ledger.cash_usd
        return self._ai_teams[team_id].cash_usd

    def _team_drivers(self, team_id: int) -> list[tuple[str, int]]:
        return [
            (
                self._driver_names.get(contract.driver_id, str(contract.driver_id)),
                contract.salary_usd,
            )
            for contract in self._career.world.contracts_of(team_id)
        ]

    def _car_estimates(self, team_id: int) -> list[tuple[str, str]] | None:
        if team_id == PLAYER_TEAM_ID:
            slot = self._career.world.player_slot
            if not slot.is_set_up:
                return None
            values = slot.car_attributes
        else:
            team = self._ai_teams[team_id]
            values = {attribute: getattr(team, attribute) for attribute in CAR_ATTRIBUTES}
        knowledge = self._career.knowledge
        subject = car_subject(team_id)
        return [
            (
                _CAR_ATTRIBUTE_LABELS[attribute],
                format_estimate(knowledge.estimate_for(subject, values[attribute])),
            )
            for attribute in CAR_ATTRIBUTES
        ]

    def _engine(self, team_id: int) -> str:
        if team_id == PLAYER_TEAM_ID:
            slot = self._career.world.player_slot
            if not slot.is_set_up:
                return _EMPTY_CELL
            supplier_id = slot.engine_supplier_id
        else:
            supplier_id = self._ai_teams[team_id].engine_supplier_id
        if supplier_id is None:
            return "in proprio"
        return self._supplier_names.get(supplier_id, str(supplier_id))

    def _philosophy(self, team_id: int) -> str:
        if team_id == PLAYER_TEAM_ID:
            philosophy = self._career.world.player_slot.chassis_philosophy
        else:
            philosophy = self._ai_teams[team_id].chassis_philosophy
        if philosophy is None:
            return _EMPTY_CELL
        return _PHILOSOPHY_LABELS.get(philosophy, philosophy)

    def _developments(self, team_id: int) -> str:
        if team_id != PLAYER_TEAM_ID:
            return _AI_DEVELOPMENTS
        projects = self._career.projects
        if not projects:
            return "Sviluppi: nessuno in corso."
        lines = ["Sviluppi:"]
        for project in projects:
            label = _CAR_ATTRIBUTE_LABELS.get(project.attribute, project.attribute)
            if project.in_progress:
                lines.append(f"  - {label}: in corso (consegna {project.delivery_date:%d/%m/%Y})")
            else:
                outcome = "" if project.outcome is None else f", +{project.outcome}"
                lines.append(f"  - {label}: completato{outcome}")
        return "\n".join(lines)
