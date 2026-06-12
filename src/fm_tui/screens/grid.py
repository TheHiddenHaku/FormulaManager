"""Schermata griglia: le 11 squadre e i 22 piloti della Carriera (FOR-6).

Due tabelle: la Griglia (slot del giocatore piu' 10 squadre AI, con
motore, Filosofia telaio e i 6 Attributi vettura) e il roster dei 22
piloti (bandiera di nazionalita', eta', squadra e i 6 Attributi pilota).
Tutti gli attributi sono resi come Stime (intervalli, mai valori esatti)
via fm_tui.widgets.estimates; il Potenziale non compare mai. L'eta' e i
nomi sono informazione pubblica e restano esatti.

La squadra del giocatore e' onesta sul suo stato: prima del wizard di
Setup squadra (FOR-7) gli slot piloti sono vuoti e gli attributi sono
trattini; a Setup completato la riga mostra motore, Filosofia telaio e
Stime come per le squadre AI, e i 2 piloti del giocatore compaiono nel
roster con la sua squadra.

Nessuna query qui (ADR 0001): la schermata riceve la Carriera gia'
caricata in memoria e la presenta soltanto.
"""

from dataclasses import replace

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from fm_engine.career import Career
from fm_engine.circuits import CALENDAR_2026
from fm_engine.weekend import start_weekend
from fm_engine.world.models import (
    CAR_ATTRIBUTES,
    DRIVER_ATTRIBUTES,
    PLAYER_TEAM_ID,
    Driver,
)
from fm_tui.screens.weekend import WeekendScreen
from fm_tui.widgets.estimates import format_estimate
from fm_tui.widgets.flags import FLAG_PLACEHOLDER, flag

# Column labels for the 6 car attributes, in CAR_ATTRIBUTES order.
_CAR_ATTRIBUTE_COLUMNS = (
    "Potenza",
    "Carico",
    "Efficienza",
    "Meccanica",
    "G. gomme",
    "Affidabilita'",
)

# Column labels for the 6 driver attributes, in DRIVER_ATTRIBUTES order.
_DRIVER_ATTRIBUTE_COLUMNS = (
    "Giro secco",
    "Passo gara",
    "Duelli",
    "G. gomme",
    "Bagnato",
    "Costanza",
)

# Cell for data that does not exist yet (player slot before the wizard).
_EMPTY_CELL = "-"

# Labels for the player team rows.
_EMPTY_SLOT_LABEL = "(slot vuoto)"
_PLAYER_SUFFIX = " (tu)"


class Grid(Screen):
    """La griglia di partenza della Carriera, ad attributi a Stime."""

    NAME = "grid"

    DEFAULT_CSS = """
    Grid #grid-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    Grid .table-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    Grid DataTable {
        height: auto;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("g", "open_weekend", "Weekend di gara"),
        Binding("escape", "back", "Elenco Carriere"),
    ]

    def __init__(self, career: Career) -> None:
        super().__init__(name=self.NAME)
        self._career = career

    def compose(self) -> ComposeResult:
        yield Static(self._header(), id="grid-header")
        with VerticalScroll():
            yield Static("Griglia: 11 squadre", classes="table-title")
            yield DataTable(id="teams-table", cursor_type="row", zebra_stripes=True)
            yield Static("Roster: 22 piloti", classes="table-title")
            yield DataTable(id="drivers-table", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self._populate_teams_table()
        self._populate_drivers_table()

    def action_back(self) -> None:
        """Torna all'elenco delle Carriere."""
        self.app.pop_screen()

    def action_open_weekend(self) -> None:
        """Apre il weekend del primo GP del Calendario (FOR-21).

        Percorso canonico del Gran Premio: FP1 -> FP2 -> FP3 ->
        Qualifiche -> Gara -> risultato, con Checkpoint a fine di ogni
        sessione. Un weekend gia' in corso (ripreso da un Checkpoint)
        continua dalla sessione giusta. Il seed deriva da (Mondo, GP):
        stessa Carriera, stesso weekend.
        """
        world = self._career.world
        if not world.player_slot.is_set_up:
            self.notify(
                "Completa il Setup squadra prima di scendere in pista.",
                severity="warning",
            )
            return
        if self._career.weekend is None:
            circuit = CALENDAR_2026[0]
            seed = world.seed * 1_000 + circuit.calendar_order
            self._career = replace(self._career, weekend=start_weekend(circuit, seed))
        self.app.push_screen(WeekendScreen(self._career), self._on_weekend_closed)

    def _on_weekend_closed(self, career: Career | None) -> None:
        """Aggiorna la Carriera in memoria con lo stato weekend piu' recente."""
        if career is not None:
            self._career = career

    def _header(self) -> str:
        slot = self._career.world.player_slot
        primary = slot.primary_color or _EMPTY_CELL
        secondary = slot.secondary_color or _EMPTY_CELL
        livery = f"{primary} / {secondary}"
        return (
            f"Carriera: {self._career.name}  |  "
            f"Squadra: {self._player_team_name()}  |  Livrea: {livery}"
        )

    def _player_team_name(self) -> str:
        return self._career.world.player_slot.name or _EMPTY_SLOT_LABEL

    def _populate_teams_table(self) -> None:
        world = self._career.world
        table = self.query_one("#teams-table", DataTable)
        table.add_columns("Squadra", "Motore", "Filosofia", *_CAR_ATTRIBUTE_COLUMNS)
        supplier_names = {supplier.id: supplier.name for supplier in world.engine_suppliers}

        # The player slot opens the grid. Before the team setup wizard
        # (FOR-7) it is honestly empty; afterwards it shows engine,
        # chassis philosophy and the initial car attributes as estimates.
        slot = world.player_slot
        if slot.is_set_up:
            engine = (
                "in proprio"
                if slot.engine_supplier_id is None
                else supplier_names[slot.engine_supplier_id]
            )
            table.add_row(
                self._player_team_name() + _PLAYER_SUFFIX,
                engine,
                slot.chassis_philosophy,
                *(format_estimate(value) for value in slot.car_attributes.values()),
            )
        else:
            table.add_row(
                self._player_team_name() + _PLAYER_SUFFIX,
                _EMPTY_CELL,
                _EMPTY_CELL,
                *([_EMPTY_CELL] * len(CAR_ATTRIBUTES)),
            )

        for team in world.ai_teams:
            engine = (
                "in proprio"
                if team.engine_supplier_id is None
                else supplier_names[team.engine_supplier_id]
            )
            table.add_row(
                team.name,
                engine,
                team.chassis_philosophy,
                *(format_estimate(getattr(team, name)) for name in CAR_ATTRIBUTES),
            )

    def _populate_drivers_table(self) -> None:
        world = self._career.world
        table = self.query_one("#drivers-table", DataTable)
        table.add_columns("Pilota", "Naz.", "Eta'", "Squadra", *_DRIVER_ATTRIBUTE_COLUMNS)
        drivers_by_id = {driver.id: driver for driver in world.drivers}

        # The player driver slots: filled by the team setup wizard
        # (FOR-7), honestly empty before it.
        player_team = self._player_team_name() + _PLAYER_SUFFIX
        player_contracts = world.contracts_of(PLAYER_TEAM_ID)
        for contract in player_contracts:
            self._add_driver_row(table, drivers_by_id[contract.driver_id], player_team)
        for _ in range(world.config.drivers_per_team - len(player_contracts)):
            table.add_row(
                _EMPTY_SLOT_LABEL,
                FLAG_PLACEHOLDER,
                _EMPTY_CELL,
                player_team,
                *([_EMPTY_CELL] * len(DRIVER_ATTRIBUTES)),
            )

        for team in world.ai_teams:
            for contract in world.contracts_of(team.id):
                self._add_driver_row(table, drivers_by_id[contract.driver_id], team.name)
        for driver in world.drivers_without_contract:
            self._add_driver_row(table, driver, "senza Contratto")

    @staticmethod
    def _add_driver_row(table: DataTable, driver: Driver, team: str) -> None:
        table.add_row(
            driver.name,
            flag(driver.nationality),
            str(driver.age),
            team,
            *(format_estimate(value) for value in driver.visible_attributes.values()),
        )
