"""Wizard di Setup squadra: piloti, motore, Filosofia telaio (FOR-7).

Parte subito dopo la creazione della Carriera (new_career) e guida il
giocatore in 3 passi piu' riepilogo, tutti navigabili da tastiera con i
binding nel Footer:

1. Piloti: il roster completo dei 22 (contrattualizzati nelle squadre AI
   e svincolati) con Stime sui 6 Attributi pilota, eta' e ingaggio
   richiesto; selezione di esattamente 2 piloti (vincolo verificato).
2. Motore: interno (costo alto, sviluppo libero) oppure Cliente di un
   Motorista (canone piu' basso, Potenza motore condivisa, a Stima).
   Costi informativi: nessuna Cassa o Cap runtime (T4.x).
3. Filosofia telaio: veloce o tecnico, con anteprima degli attributi
   vettura iniziali mostrati come Stime.

Alla conferma del riepilogo le scelte passano dal motore puro
(fm_engine.world.team_setup.apply_team_setup) e si salvano al Checkpoint;
si atterra sulla griglia con la squadra del giocatore completa.

Edge accettato per il MVP: uscendo a meta' wizard (escape dal passo 1)
la Carriera resta senza Setup squadra; riaprendola si vede la griglia
con gli slot vuoti e il wizard NON riparte.

Accesso al database: una connessione per il solo Checkpoint di conferma,
aperta e chiusa nell'azione (ADR 0001).
"""

from dataclasses import replace
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, OptionList, Static
from textual.widgets.option_list import Option

from fm_engine.career import Career
from fm_engine.economy import DEFAULT_PLAYER_PRESTIGE, credit_annual_sponsor
from fm_engine.world.models import CAR_ATTRIBUTES, Driver
from fm_engine.world.team_setup import (
    TeamSetupChoices,
    TeamSetupConfig,
    apply_team_setup,
    baseline_car_attribute,
    initial_car_attributes,
)
from fm_persistence import connect, save_career
from fm_tui.screens.grid import Grid
from fm_tui.widgets.estimates import format_estimate
from fm_tui.widgets.flags import flag

# Wizard steps, in order.
_STEP_DRIVERS = 0
_STEP_ENGINE = 1
_STEP_CHASSIS = 2
_STEP_SUMMARY = 3

_STEP_CONTAINERS = ("#step-drivers", "#step-engine", "#step-chassis", "#step-summary")

# Option id of the in-house engine in the engine step.
_OWN_ENGINE_OPTION = "own"

# Selection markers in the roster table.
_MARK_SELECTED = "[x]"
_MARK_FREE = "[ ]"

# Label for the drivers without an initial contract.
_FREE_AGENT_LABEL = "svincolato"

# Italian labels of the 6 car attributes, keyed by identifier.
_CAR_ATTRIBUTE_LABELS = {
    "engine_power": "Potenza motore",
    "downforce": "Carico aerodinamico",
    "aero_efficiency": "Efficienza aerodinamica",
    "mechanical_grip": "Meccanica",
    "tyre_management": "Gestione gomme",
    "reliability": "Affidabilita'",
}

_PHILOSOPHY_LABELS = {"fast": "veloce", "technical": "tecnico"}


def _millions(amount_usd: int) -> str:
    """Importo leggibile in milioni di dollari, es. 13500000 -> '13,5 M$'."""
    text = f"{amount_usd / 1_000_000:.1f}".replace(".", ",")
    return f"{text} M$"


class TeamSetup(Screen):
    """Il wizard in 3 passi piu' riepilogo con cui nasce la squadra."""

    NAME = "team_setup"

    DEFAULT_CSS = """
    TeamSetup #wizard-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    TeamSetup .step-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    TeamSetup .step-hint {
        padding: 0 1;
        color: $text-muted;
    }

    TeamSetup #selection-status {
        padding: 0 1;
    }

    TeamSetup DataTable {
        height: 1fr;
        margin: 0 1;
    }

    TeamSetup OptionList {
        height: auto;
        margin: 0 1;
    }

    TeamSetup #chassis-preview, TeamSetup #summary-text {
        padding: 1;
    }

    TeamSetup #wizard-error {
        padding: 0 1;
        color: $error;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_driver", "Seleziona/Deseleziona"),
        Binding("a", "next_step", "Avanti"),
        Binding("escape", "back", "Indietro"),
        Binding("ctrl+s", "confirm", "Conferma e salva"),
    ]

    def __init__(self, career: Career, config: TeamSetupConfig | None = None) -> None:
        super().__init__(name=self.NAME)
        self._career = career
        self._config = config if config is not None else TeamSetupConfig()
        self._step = _STEP_DRIVERS
        # Ordered ids of the chosen drivers (at most 2).
        self._selected: list[int] = []
        self._engine_choice: int | None = None
        self._philosophy: str | None = None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="wizard-header")
        with Vertical(id="step-drivers"):
            yield Static("Passo 1 di 3: scegli 2 piloti dal roster", classes="step-title")
            yield Static(
                "Spazio o Invio seleziona; gli attributi sono Stime, "
                "eta' e ingaggio richiesto sono esatti. "
                "Escape esce dal wizard (squadra da completare).",
                classes="step-hint",
            )
            yield Static("", id="selection-status")
            yield DataTable(id="roster-table", cursor_type="row", zebra_stripes=True)
        with Vertical(id="step-engine"):
            yield Static("Passo 2 di 3: il motore", classes="step-title")
            yield Static(
                "Interno: costo alto ma sviluppo libero. Cliente: canone piu' "
                "basso ma Potenza motore condivisa col Motorista. "
                "Costi informativi, senza effetto sulla Cassa.",
                classes="step-hint",
            )
            yield OptionList(id="engine-options")
        with Vertical(id="step-chassis"):
            yield Static("Passo 3 di 3: la Filosofia telaio", classes="step-title")
            yield Static(
                "La scelta sbilancia gli attributi vettura iniziali (anteprima a Stime qui sotto).",
                classes="step-hint",
            )
            yield OptionList(
                Option(self._chassis_prompt("fast"), id="fast"),
                Option(self._chassis_prompt("technical"), id="technical"),
                id="chassis-options",
            )
            yield Static("", id="chassis-preview")
        with VerticalScroll(id="step-summary"):
            yield Static("Riepilogo squadra", classes="step-title")
            yield Static("", id="summary-text")
        yield Static("", id="wizard-error")
        yield Footer()

    def on_mount(self) -> None:
        self._populate_roster_table()
        self._populate_engine_options()
        self._refresh_selection_status()
        self._show_step(_STEP_DRIVERS)

    def _header_text(self) -> str:
        team = self._career.world.player_slot.name or ""
        return f"Setup squadra: {team}  |  Carriera: {self._career.name}"

    def _populate_roster_table(self) -> None:
        world = self._career.world
        table = self.query_one("#roster-table", DataTable)
        table.add_column("Sel.", key="selected")
        table.add_columns(
            "Pilota",
            "Naz.",
            "Eta'",
            "Squadra",
            "Ingaggio",
            "Giro secco",
            "Passo gara",
            "Duelli",
            "G. gomme",
            "Bagnato",
            "Costanza",
        )
        team_names = {team.id: team.name for team in world.ai_teams}
        team_of = {contract.driver_id: team_names[contract.team_id] for contract in world.contracts}
        for driver in world.drivers:
            table.add_row(
                _MARK_FREE,
                driver.name,
                flag(driver.nationality),
                str(driver.age),
                team_of.get(driver.id, _FREE_AGENT_LABEL),
                _millions(driver.salary_demand_usd),
                *(format_estimate(value) for value in driver.visible_attributes.values()),
                key=str(driver.id),
            )

    def _populate_engine_options(self) -> None:
        world = self._career.world
        options = self.query_one("#engine-options", OptionList)
        baseline = format_estimate(baseline_car_attribute(world.config))
        options.add_option(
            Option(
                f"Motore interno  |  costo {_millions(self._config.in_house_engine_cost_usd)} "
                f"l'anno  |  sviluppo libero  |  Potenza motore {baseline}",
                id=_OWN_ENGINE_OPTION,
            )
        )
        for supplier in world.engine_suppliers:
            options.add_option(
                Option(
                    f"Cliente di {supplier.name}  |  canone "
                    f"{_millions(supplier.customer_fee_usd)} l'anno  |  Potenza motore "
                    f"{format_estimate(supplier.engine_power)} condivisa col fornitore",
                    id=str(supplier.id),
                )
            )

    def _chassis_prompt(self, philosophy: str) -> str:
        if philosophy == "fast":
            return (
                "Telaio veloce  |  bonus Efficienza aerodinamica, "
                "malus Carico aerodinamico e Meccanica"
            )
        return (
            "Telaio tecnico  |  bonus Carico aerodinamico e Meccanica, "
            "malus Efficienza aerodinamica"
        )

    # ------------------------------------------------------------------
    # Step navigation
    # ------------------------------------------------------------------

    def _show_step(self, step: int) -> None:
        """Mostra il passo richiesto, nasconde gli altri, aggiorna i binding."""
        self._step = step
        self._clear_error()
        for index, selector in enumerate(_STEP_CONTAINERS):
            self.query_one(selector).display = index == step
        if step == _STEP_DRIVERS:
            self.query_one("#roster-table", DataTable).focus()
        elif step == _STEP_ENGINE:
            self.query_one("#engine-options", OptionList).focus()
        elif step == _STEP_CHASSIS:
            self.query_one("#chassis-options", OptionList).focus()
            self._refresh_chassis_preview()
        else:
            self._refresh_summary()
            self.query_one("#step-summary", VerticalScroll).focus()
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Mostra nel Footer solo i binding sensati per il passo corrente."""
        if action == "toggle_driver":
            return True if self._step == _STEP_DRIVERS else None
        if action == "next_step":
            return True if self._step != _STEP_SUMMARY else None
        if action == "confirm":
            return True if self._step == _STEP_SUMMARY else None
        return True

    def action_next_step(self) -> None:
        """Avanza di un passo, validando il vincolo dei 2 piloti."""
        if self._step == _STEP_DRIVERS:
            if len(self._selected) != 2:
                self._set_error(
                    f"Seleziona esattamente 2 piloti per continuare "
                    f"(selezionati: {len(self._selected)})."
                )
                return
            self._show_step(_STEP_ENGINE)
        elif self._step == _STEP_ENGINE:
            self._adopt_highlighted_engine()
            self._show_step(_STEP_CHASSIS)
        elif self._step == _STEP_CHASSIS:
            self._adopt_highlighted_philosophy()
            self._show_step(_STEP_SUMMARY)

    def action_back(self) -> None:
        """Torna al passo precedente; dal primo passo esce dal wizard.

        Edge accettato per il MVP: uscendo qui la Carriera resta senza
        Setup squadra (griglia con slot vuoti, il wizard non riparte).
        """
        if self._step > _STEP_DRIVERS:
            self._show_step(self._step - 1)
        else:
            self.app.pop_screen()

    # ------------------------------------------------------------------
    # Step 1: drivers
    # ------------------------------------------------------------------

    def action_toggle_driver(self) -> None:
        if self._step != _STEP_DRIVERS:
            return
        table = self.query_one("#roster-table", DataTable)
        if table.row_count == 0:
            return
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        self._toggle_driver(row_key.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Invio (o click) su una riga del roster: stessa logica dello spazio."""
        if event.row_key.value is not None:
            self._toggle_driver(event.row_key.value)

    def _toggle_driver(self, row_value: str) -> None:
        driver_id = int(row_value)
        if driver_id in self._selected:
            self._selected.remove(driver_id)
        elif len(self._selected) >= 2:
            self._set_error("Hai gia' selezionato 2 piloti: deselezionane uno prima.")
            return
        else:
            self._selected.append(driver_id)
        self._clear_error()
        table = self.query_one("#roster-table", DataTable)
        mark = _MARK_SELECTED if driver_id in self._selected else _MARK_FREE
        table.update_cell(row_value, "selected", mark)
        self._refresh_selection_status()

    def _refresh_selection_status(self) -> None:
        names = ", ".join(driver.name for driver in self._selected_drivers())
        suffix = f": {names}" if names else ""
        self.query_one("#selection-status", Static).update(
            f"Selezionati {len(self._selected)}/2{suffix}"
        )

    def _selected_drivers(self) -> list[Driver]:
        by_id = {driver.id: driver for driver in self._career.world.drivers}
        return [by_id[driver_id] for driver_id in self._selected]

    # ------------------------------------------------------------------
    # Steps 2 and 3: engine and chassis philosophy
    # ------------------------------------------------------------------

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Invio su un'opzione: adotta la scelta e avanza."""
        if event.option_list.id == "engine-options":
            self._engine_choice = self._engine_id_from_option(event.option.id)
            self._show_step(_STEP_CHASSIS)
        elif event.option_list.id == "chassis-options":
            self._philosophy = event.option.id
            self._show_step(_STEP_SUMMARY)

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """L'anteprima della vettura segue la Filosofia evidenziata."""
        if event.option_list.id == "chassis-options" and self._step == _STEP_CHASSIS:
            self._refresh_chassis_preview()

    @staticmethod
    def _engine_id_from_option(option_id: str | None) -> int | None:
        return None if option_id == _OWN_ENGINE_OPTION else int(option_id)

    def _adopt_highlighted_engine(self) -> None:
        options = self.query_one("#engine-options", OptionList)
        highlighted = options.highlighted or 0
        self._engine_choice = self._engine_id_from_option(
            options.get_option_at_index(highlighted).id
        )

    def _adopt_highlighted_philosophy(self) -> None:
        options = self.query_one("#chassis-options", OptionList)
        highlighted = options.highlighted or 0
        self._philosophy = options.get_option_at_index(highlighted).id

    def _highlighted_philosophy(self) -> str:
        options = self.query_one("#chassis-options", OptionList)
        highlighted = options.highlighted or 0
        return options.get_option_at_index(highlighted).id

    def _refresh_chassis_preview(self) -> None:
        attributes = initial_car_attributes(
            self._career.world,
            self._engine_choice,
            self._highlighted_philosophy(),
            self._config,
        )
        lines = ["Attributi vettura iniziali (Stime):"]
        lines += [
            f"  {_CAR_ATTRIBUTE_LABELS[name]}: {format_estimate(attributes[name])}"
            for name in CAR_ATTRIBUTES
        ]
        self.query_one("#chassis-preview", Static).update("\n".join(lines))

    # ------------------------------------------------------------------
    # Summary and confirmation
    # ------------------------------------------------------------------

    def _engine_summary(self) -> str:
        if self._engine_choice is None:
            return (
                f"Motore interno (costo {_millions(self._config.in_house_engine_cost_usd)} "
                "l'anno, sviluppo libero)"
            )
        supplier = next(
            s for s in self._career.world.engine_suppliers if s.id == self._engine_choice
        )
        return (
            f"Cliente di {supplier.name} (canone {_millions(supplier.customer_fee_usd)} "
            "l'anno, Potenza motore condivisa)"
        )

    def _refresh_summary(self) -> None:
        attributes = initial_car_attributes(
            self._career.world, self._engine_choice, self._philosophy, self._config
        )
        duration = self._config.player_contract_duration_seasons
        lines = ["Piloti (Contratto di " + str(duration) + " stagioni):"]
        lines += [
            f"  {driver.name} ({flag(driver.nationality)}, eta' {driver.age}, "
            f"ingaggio {_millions(driver.salary_demand_usd)} l'anno)"
            for driver in self._selected_drivers()
        ]
        lines.append(f"Motore: {self._engine_summary()}")
        lines.append(f"Filosofia telaio: {_PHILOSOPHY_LABELS.get(self._philosophy, '?')}")
        lines.append("Attributi vettura iniziali (Stime):")
        lines += [
            f"  {_CAR_ATTRIBUTE_LABELS[name]}: {format_estimate(attributes[name])}"
            for name in CAR_ATTRIBUTES
        ]
        lines.append("")
        lines.append("Ctrl+S conferma e salva al Checkpoint; Escape torna indietro.")
        self.query_one("#summary-text", Static).update("\n".join(lines))

    def action_confirm(self) -> None:
        """Applica le scelte nel motore puro e salva il Checkpoint."""
        if self._step != _STEP_SUMMARY:
            return
        choices = TeamSetupChoices(
            driver_ids=(self._selected[0], self._selected[1]),
            engine_supplier_id=self._engine_choice,
            chassis_philosophy=self._philosophy,
        )
        try:
            world = apply_team_setup(self._career.world, choices, self._config)
        except ValueError as error:
            self._set_error(f"Setup non valido: {error}")
            return
        # La squadra entra nel campionato: lo Sponsor annuale di inizio
        # stagione arriva qui, col Prestigio di partenza (FOR-22).
        ledger = credit_annual_sponsor(
            self._career.ledger,
            DEFAULT_PLAYER_PRESTIGE,
            date(self._career.ledger.season_year, 1, 1),
        )
        career = replace(self._career, world=world, ledger=ledger)
        with connect() as connection:
            saved = save_career(connection, career)
        self.app.switch_screen(Grid(saved))

    # ------------------------------------------------------------------
    # Error line
    # ------------------------------------------------------------------

    def _set_error(self, message: str) -> None:
        self.query_one("#wizard-error", Static).update(message)

    def _clear_error(self) -> None:
        self.query_one("#wizard-error", Static).update("")
