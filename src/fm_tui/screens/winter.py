"""Schermata inverno: Carry-over, rinegoziazione e Progetti invernali (FOR-32).

Guscio TUI sopra fm_engine.winter (ADR 0002): la logica di Carry-over,
rinegoziazione, Progetti invernali e rollover economico vive nel motore;
la schermata raccoglie le scelte del giocatore e chiama advance_winter alla
conferma. Compare alla fine della stagione, dopo il Mercato piloti, dentro
la transizione di stagione (grid._advance_to_next_season).

Tre passi navigabili da tastiera, piu' riepilogo:

1. Carry-over (informativo): mostra come la vettura nuova erediti gli
   Attributi regrediti verso la media di griglia. Niente scelte: il
   Carry-over e' automatico, qui se ne vede l'effetto.
2. Rinegoziazione: motore in proprio o Cliente di un Motorista, e Filosofia
   telaio. Default: scelte di fondo invariate.
3. Progetti invernali: alloca i punti del budget dedicato sugli Attributi
   vettura (frecce su/giu' sull'attributo evidenziato). Default: nessuno.

Alla conferma (Ctrl+S) le scelte passano da advance_winter: la vettura e
l'economia della stagione nuova cambiano DAVVERO, e si salva al Checkpoint.
Lasciando tutto a default (escape dal primo passo o conferma senza scelte)
l'inverno applica comunque Carry-over e rollover con i DEFAULT dichiarati.

Stati UI dichiarati: nessuno Sforamento (Cap pieno), Sforamento con
penalita' (Cap ridotto), scelte lasciate a default. Tutti visibili nel
passo di riepilogo, che legge il nuovo Cap dal motore.
"""

import sqlite3
from dataclasses import replace
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, OptionList, Static
from textual.widgets.option_list import Option

from fm_engine.career import Career
from fm_engine.economy import SEASON_CAP_USD, overspend_penalty_usd
from fm_engine.economy.damages import MINIMUM_CAP_USD
from fm_engine.winter import (
    RenegotiationChoices,
    WinterBudgetExceeded,
    WinterConfig,
    WinterDecisions,
    WinterProject,
    advance_winter,
)
from fm_engine.winter.carryover import carried_over_attributes, grid_attribute_means
from fm_engine.winter.projects import ATTRIBUTE_LABELS, CustomerEngineLocked
from fm_engine.world.models import CAR_ATTRIBUTES
from fm_persistence import connect, save_career
from fm_tui.widgets.balance_bar import format_usd
from fm_tui.widgets.date_bar import DateBar

# Passi del wizard, in ordine.
_STEP_CARRYOVER = 0
_STEP_RENEGOTIATION = 1
_STEP_PROJECTS = 2
_STEP_SUMMARY = 3

_STEP_CONTAINERS = (
    "#step-carryover",
    "#step-renegotiation",
    "#step-projects",
    "#step-summary",
)

# Option id del motore in proprio nel passo rinegoziazione.
_OWN_ENGINE_OPTION = "own"

_PHILOSOPHY_LABELS = {"fast": "veloce", "balanced": "equilibrata", "technical": "tecnica"}
_PHILOSOPHY_ORDER = ("balanced", "fast", "technical")


class WinterScreen(Screen[Career]):
    """La fase inverno: Carry-over visibile, scelte di fondo e Progetti."""

    NAME = "winter"

    DEFAULT_CSS = """
    WinterScreen #winter-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    WinterScreen .step-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    WinterScreen .step-hint {
        padding: 0 1;
        color: $text-muted;
    }

    WinterScreen #budget-status {
        padding: 0 1;
        text-style: bold;
    }

    WinterScreen DataTable {
        height: auto;
        margin: 0 1;
    }

    WinterScreen OptionList {
        height: auto;
        margin: 0 1;
    }

    WinterScreen #carryover-text, WinterScreen #summary-text {
        padding: 1;
    }

    WinterScreen #winter-error {
        padding: 0 1;
        color: $error;
    }
    """

    BINDINGS = [
        Binding("a", "next_step", "Avanti"),
        Binding("up", "add_point", "Piu' punti", show=False),
        Binding("down", "remove_point", "Meno punti", show=False),
        Binding("plus", "add_point", "Piu' punti"),
        Binding("minus", "remove_point", "Meno punti"),
        Binding("escape", "back", "Indietro"),
        Binding("ctrl+s", "confirm", "Conferma e salva"),
    ]

    def __init__(
        self,
        career: Career,
        concluded_year: int,
        config: WinterConfig | None = None,
    ) -> None:
        super().__init__(name=self.NAME)
        self._career = career
        self._concluded_year = concluded_year
        self._config = config if config is not None else WinterConfig()
        self._step = _STEP_CARRYOVER
        slot = career.world.player_slot
        self._engine_choice: int | None = slot.engine_supplier_id
        self._philosophy: str = slot.chassis_philosophy
        # Punti invernali allocati per Attributo vettura (id -> punti).
        self._points: dict[str, int] = dict.fromkeys(CAR_ATTRIBUTES, 0)
        self._save_failed = False

    @property
    def career(self) -> Career:
        """La Carriera con lo stato piu' recente in memoria."""
        return self._career

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield DateBar(self._career.season)
        yield Static(self._header_text(), id="winter-header")
        with Vertical(id="step-carryover"):
            yield Static("Passo 1 di 3: Carry-over della vettura", classes="step-title")
            yield Static(
                "La vettura nuova eredita una quota degli Attributi con regressione "
                "verso la media di griglia: i distacchi si comprimono. E' automatico.",
                classes="step-hint",
            )
            yield Static("", id="carryover-text")
        with Vertical(id="step-renegotiation"):
            yield Static("Passo 2 di 3: motore e Filosofia telaio", classes="step-title")
            yield Static(
                "Rinegozia le scelte di fondo per la stagione nuova. "
                "Default: restano quelle dell'anno concluso.",
                classes="step-hint",
            )
            yield Static("Motore", classes="step-title")
            yield OptionList(id="engine-options")
            yield Static("Filosofia telaio", classes="step-title")
            yield OptionList(id="philosophy-options")
        with VerticalScroll(id="step-projects"):
            yield Static("Passo 3 di 3: Progetti invernali", classes="step-title")
            yield Static(
                "Alloca i punti del budget dedicato sugli Attributi vettura: "
                "+ aggiunge, - toglie sull'attributo evidenziato.",
                classes="step-hint",
            )
            yield Static("", id="budget-status")
            yield DataTable(id="projects-table", cursor_type="row", zebra_stripes=True)
        with VerticalScroll(id="step-summary"):
            yield Static("Riepilogo inverno", classes="step-title")
            yield Static("", id="summary-text")
        yield Static("", id="winter-error")
        yield Footer()

    def on_mount(self) -> None:
        self._populate_engine_options()
        self._populate_philosophy_options()
        self._populate_projects_table()
        self._refresh_carryover_text()
        self._show_step(_STEP_CARRYOVER)

    # ------------------------------------------------------------------
    # Helpers di stato vettura
    # ------------------------------------------------------------------

    def _carried_over_attributes(self) -> dict[str, int]:
        """Gli Attributi vettura del giocatore dopo il solo Carry-over."""
        world = self._career.world
        means = grid_attribute_means(world)
        return carried_over_attributes(
            world.player_slot.car_attributes, means, self._config.carryover
        )

    def _is_engine_customer(self) -> bool:
        return self._engine_choice is not None

    def _winter_projects(self) -> tuple[WinterProject, ...]:
        """La selezione di Progetti invernali dai punti allocati (punti > 0)."""
        return tuple(
            WinterProject(attribute=name, points=points)
            for name, points in self._points.items()
            if points > 0
        )

    def _winter_spend_usd(self) -> int:
        return sum(p.cost_usd(self._config.projects) for p in self._winter_projects())

    def _budget_remaining_usd(self) -> int:
        return self._config.projects.budget_usd - self._winter_spend_usd()

    # ------------------------------------------------------------------
    # Rendering dei passi
    # ------------------------------------------------------------------

    def _header_text(self) -> str:
        team = self._career.world.player_slot.name or ""
        return f"Inverno {self._concluded_year} -> {self._concluded_year + 1}  |  Squadra: {team}"

    def _refresh_carryover_text(self) -> None:
        before = self._career.world.player_slot.car_attributes
        after = self._carried_over_attributes()
        lines = ["Attributi vettura: stagione conclusa -> stagione nuova"]
        for name in CAR_ATTRIBUTES:
            arrow = "->"
            lines.append(f"  {ATTRIBUTE_LABELS[name]}: {before[name]} {arrow} {after[name]}")
        self.query_one("#carryover-text", Static).update("\n".join(lines))

    def _populate_engine_options(self) -> None:
        world = self._career.world
        options = self.query_one("#engine-options", OptionList)
        options.add_option(Option("Motore in proprio (sviluppo libero)", id=_OWN_ENGINE_OPTION))
        for supplier in world.engine_suppliers:
            options.add_option(
                Option(
                    f"Cliente di {supplier.name} "
                    f"(canone {format_usd(supplier.customer_fee_usd)} l'anno)",
                    id=str(supplier.id),
                )
            )
        options.highlighted = self._engine_option_index()

    def _engine_option_index(self) -> int:
        if self._engine_choice is None:
            return 0
        for index, supplier in enumerate(self._career.world.engine_suppliers, start=1):
            if supplier.id == self._engine_choice:
                return index
        return 0

    def _populate_philosophy_options(self) -> None:
        options = self.query_one("#philosophy-options", OptionList)
        for philosophy in _PHILOSOPHY_ORDER:
            options.add_option(Option(_PHILOSOPHY_LABELS[philosophy], id=philosophy))
        options.highlighted = _PHILOSOPHY_ORDER.index(self._philosophy)

    def _populate_projects_table(self) -> None:
        table = self.query_one("#projects-table", DataTable)
        table.add_column("Attributo", key="attribute")
        table.add_column("Punti", key="points")
        table.add_column("Costo", key="cost")
        for name in CAR_ATTRIBUTES:
            table.add_row(ATTRIBUTE_LABELS[name], "0", format_usd(0), key=name)
        self._refresh_budget_status()

    def _refresh_projects_table(self) -> None:
        table = self.query_one("#projects-table", DataTable)
        for name in CAR_ATTRIBUTES:
            points = self._points[name]
            cost = points * self._config.projects.cost_per_point_usd
            table.update_cell(name, "points", str(points))
            table.update_cell(name, "cost", format_usd(cost))

    def _refresh_budget_status(self) -> None:
        remaining = self._budget_remaining_usd()
        self.query_one("#budget-status", Static).update(
            f"Budget invernale: speso {format_usd(self._winter_spend_usd())} / "
            f"{format_usd(self._config.projects.budget_usd)}  |  residuo {format_usd(remaining)}"
        )

    # ------------------------------------------------------------------
    # Navigazione tra i passi
    # ------------------------------------------------------------------

    def _show_step(self, step: int) -> None:
        self._step = step
        self._clear_error()
        for index, selector in enumerate(_STEP_CONTAINERS):
            self.query_one(selector).display = index == step
        if step == _STEP_CARRYOVER:
            self.query_one("#carryover-text", Static).focus()
        elif step == _STEP_RENEGOTIATION:
            self.query_one("#engine-options", OptionList).focus()
        elif step == _STEP_PROJECTS:
            self.query_one("#projects-table", DataTable).focus()
        else:
            self._refresh_summary()
            self.query_one("#step-summary", VerticalScroll).focus()
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Mostra nel Footer solo i binding sensati per il passo corrente."""
        if action in ("add_point", "remove_point"):
            return True if self._step == _STEP_PROJECTS else None
        if action == "next_step":
            return True if self._step != _STEP_SUMMARY else None
        if action == "confirm":
            return True if self._step == _STEP_SUMMARY else None
        return True

    def action_next_step(self) -> None:
        if self._step == _STEP_CARRYOVER:
            self._show_step(_STEP_RENEGOTIATION)
        elif self._step == _STEP_RENEGOTIATION:
            self._adopt_highlighted_choices()
            self._show_step(_STEP_PROJECTS)
        elif self._step == _STEP_PROJECTS:
            self._show_step(_STEP_SUMMARY)

    def action_back(self) -> None:
        """Torna al passo precedente; dal primo conferma comunque l'inverno.

        Default dichiarato: uscire dal primo passo applica Carry-over e
        rollover con le scelte di fondo invariate e nessun Progetto.
        """
        if self._step > _STEP_CARRYOVER:
            self._show_step(self._step - 1)
        else:
            self._confirm_winter()

    # ------------------------------------------------------------------
    # Passo 2: rinegoziazione
    # ------------------------------------------------------------------

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_list.id == "engine-options":
            self._engine_choice = self._engine_id_from_option(event.option.id)
        elif event.option_list.id == "philosophy-options":
            self._philosophy = event.option.id

    @staticmethod
    def _engine_id_from_option(option_id: str | None) -> int | None:
        return None if option_id == _OWN_ENGINE_OPTION else int(option_id)

    def _adopt_highlighted_choices(self) -> None:
        engine = self.query_one("#engine-options", OptionList)
        engine_index = engine.highlighted or 0
        self._engine_choice = self._engine_id_from_option(
            engine.get_option_at_index(engine_index).id
        )
        philosophy = self.query_one("#philosophy-options", OptionList)
        philosophy_index = philosophy.highlighted or 0
        self._philosophy = philosophy.get_option_at_index(philosophy_index).id

    # ------------------------------------------------------------------
    # Passo 3: Progetti invernali
    # ------------------------------------------------------------------

    def _highlighted_attribute(self) -> str | None:
        table = self.query_one("#projects-table", DataTable)
        if table.row_count == 0:
            return None
        return table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value

    def action_add_point(self) -> None:
        if self._step != _STEP_PROJECTS:
            return
        attribute = self._highlighted_attribute()
        if attribute is None:
            return
        if self._is_engine_customer() and attribute == "engine_power":
            self._set_error("Da Cliente non puoi sviluppare la Potenza motore: arriva dal motore.")
            return
        max_points = self._config.projects.max_points_per_project
        if self._points[attribute] >= max_points:
            self._set_error(f"Massimo {max_points} punti per Attributo in un inverno.")
            return
        cost = self._config.projects.cost_per_point_usd
        if cost > self._budget_remaining_usd():
            self._set_error("Budget invernale esaurito: togli punti altrove per aggiungerne qui.")
            return
        self._clear_error()
        self._points[attribute] += 1
        self._refresh_projects_table()
        self._refresh_budget_status()

    def action_remove_point(self) -> None:
        if self._step != _STEP_PROJECTS:
            return
        attribute = self._highlighted_attribute()
        if attribute is None or self._points[attribute] <= 0:
            return
        self._clear_error()
        self._points[attribute] -= 1
        self._refresh_projects_table()
        self._refresh_budget_status()

    # ------------------------------------------------------------------
    # Riepilogo e conferma
    # ------------------------------------------------------------------

    def _projected_cap_usd(self) -> int:
        """Il Cap della stagione nuova dopo l'eventuale penalita' di Sforamento."""
        penalty = overspend_penalty_usd(self._career.ledger.overspend_usd)
        return max(SEASON_CAP_USD - penalty, MINIMUM_CAP_USD)

    def _refresh_summary(self) -> None:
        carried = self._carried_over_attributes()
        decisions = self._build_decisions()
        # Anteprima della vettura nuova dal motore: la stessa che applichera'
        # advance_winter (Carry-over, rinegoziazione, Progetti).
        try:
            preview = advance_winter(
                self._career.world,
                self._career.ledger,
                self._concluded_year,
                decisions,
                self._config,
            )
            preview_car = preview.world.player_slot.car_attributes
            preview_cap = preview.ledger.cap_usd
        except (WinterBudgetExceeded, CustomerEngineLocked, ValueError) as error:
            self._set_error(f"Scelte non valide: {error}")
            preview_car = carried
            preview_cap = self._projected_cap_usd()

        lines = []
        engine = (
            "in proprio"
            if self._engine_choice is None
            else next(
                s.name for s in self._career.world.engine_suppliers if s.id == self._engine_choice
            )
        )
        lines.append(f"Motore: {engine}")
        lines.append(f"Filosofia telaio: {_PHILOSOPHY_LABELS[self._philosophy]}")
        lines.append("")
        lines.append("Vettura della stagione nuova (Carry-over + scelte):")
        for name in CAR_ATTRIBUTES:
            lines.append(f"  {ATTRIBUTE_LABELS[name]}: {preview_car[name]}")
        lines.append("")
        overspend = self._career.ledger.overspend_usd
        if overspend > 0:
            lines.append(
                f"Sforamento {format_usd(overspend)}: Cap della stagione nuova ridotto a "
                f"{format_usd(preview_cap)}."
            )
        else:
            lines.append(f"Nessuno Sforamento: Cap pieno {format_usd(preview_cap)}.")
        lines.append(
            f"Budget invernale speso: {format_usd(self._winter_spend_usd())} / "
            f"{format_usd(self._config.projects.budget_usd)}."
        )
        lines.append("")
        lines.append("Ctrl+S conferma e salva al Checkpoint; Escape torna indietro.")
        self.query_one("#summary-text", Static).update("\n".join(lines))

    def _build_decisions(self) -> WinterDecisions:
        slot = self._career.world.player_slot
        unchanged = (
            self._engine_choice == slot.engine_supplier_id
            and self._philosophy == slot.chassis_philosophy
        )
        renegotiation = (
            None
            if unchanged
            else RenegotiationChoices(
                engine_supplier_id=self._engine_choice,
                chassis_philosophy=self._philosophy,
            )
        )
        return WinterDecisions(
            renegotiation=renegotiation,
            winter_projects=self._winter_projects(),
        )

    def action_confirm(self) -> None:
        if self._step != _STEP_SUMMARY:
            return
        self._confirm_winter()

    def _confirm_winter(self) -> None:
        """Applica la fase inverno nel motore e salva il Checkpoint."""
        decisions = self._build_decisions()
        try:
            outcome = advance_winter(
                self._career.world,
                self._career.ledger,
                self._concluded_year,
                decisions,
                self._config,
            )
        except (WinterBudgetExceeded, CustomerEngineLocked, ValueError) as error:
            self._set_error(f"Inverno non valido: {error}")
            return
        self._career = replace(
            self._career,
            world=outcome.world,
            ledger=outcome.ledger,
        )
        self._checkpoint()
        self.dismiss(self._career)

    def _checkpoint(self) -> None:
        """Salva l'intera Carriera; in caso di errore lo stato resta in memoria."""
        try:
            with connect() as connection:
                self._career = save_career(connection, self._career)
            self._save_failed = False
        except (RuntimeError, sqlite3.Error) as error:
            self._save_failed = True
            self.notify(
                f"Checkpoint dell'inverno fallito: {error}.",
                severity="error",
                timeout=10,
            )

    # ------------------------------------------------------------------
    # Riga di errore
    # ------------------------------------------------------------------

    def _set_error(self, message: str) -> None:
        self.query_one("#winter-error", Static).update(message)

    def _clear_error(self) -> None:
        self.query_one("#winter-error", Static).update("")


def winter_start_date(concluded_year: int) -> date:
    """La data di gioco dell'inverno: inizio della stagione nuova (1 gennaio)."""
    return date(concluded_year + 1, 1, 1)
