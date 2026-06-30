"""Schermata sviluppo: i Progetti in-season della vettura (FOR-25).

Mostra i due slot Progetto con data di consegna stimata ed esiti, e
permette di avviarne uno nuovo da tastiera: attributo dall'elenco,
investimento dal selettore, avvio con a. I rifiuti del motore arrivano
a schermo con messaggi chiari: terzo Progetto, vincolo Cliente sulla
Potenza motore, doppio vincolo di spesa (Cassa o Cap), spese facoltative
bloccate (FOR-24). Nessuna query qui (ADR 0001): lo stato vive in
memoria e si persiste al prossimo Checkpoint.

Alla chiusura restituisce la Carriera aggiornata (registro e Progetti).
"""

from dataclasses import replace
from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, OptionList, Select, Static
from textual.widgets.option_list import Option

from fm_engine.career import Career
from fm_engine.circuits import circuit_by_code
from fm_engine.development import (
    MAX_PARALLEL_PROJECTS,
    CustomerEngineLocked,
    ProjectLimitReached,
    ProjectStatus,
    expected_gain_points,
    start_project,
)
from fm_engine.economy import SpendingBlocked, optional_spending_blocked
from fm_engine.world.models import CAR_ATTRIBUTES
from fm_tui.widgets.balance_bar import BalanceBar, format_usd
from fm_tui.widgets.date_bar import DateBar

EMPTY_STATE_LABEL = "Nessun Progetto attivo"

# Italian labels of the car attributes, in CAR_ATTRIBUTES order.
ATTRIBUTE_LABELS = {
    "engine_power": "Potenza motore",
    "downforce": "Carico aerodinamico",
    "aero_efficiency": "Efficienza aerodinamica",
    "mechanical_grip": "Meccanica",
    "tyre_management": "Gestione gomme",
    "reliability": "Affidabilita'",
}

# Preset investment amounts offered by the select.
INVESTMENT_CHOICES = (4_000_000, 8_000_000, 12_000_000, 20_000_000, 32_000_000)

_STATUS_LABELS = {
    ProjectStatus.IN_PROGRESS: "in corso",
    ProjectStatus.COMPLETED: "consegnato",
}


class DevelopmentScreen(Screen[Career]):
    """I due slot Progetto: stato, consegne e avvio di nuovi sviluppi."""

    NAME = "development"

    DEFAULT_CSS = """
    DevelopmentScreen #development-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    DevelopmentScreen .table-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    DevelopmentScreen DataTable {
        height: auto;
        margin: 0 1;
    }

    DevelopmentScreen #development-empty {
        padding: 1 2;
        color: $text-muted;
    }

    DevelopmentScreen #attribute-list {
        margin: 0 1;
        height: auto;
    }

    DevelopmentScreen #investment-select {
        margin: 0 1;
        width: 40;
    }

    DevelopmentScreen #development-error {
        padding: 0 2;
        color: $error;
    }
    """

    BINDINGS = [
        Binding("a", "start_project", "Avvia il Progetto"),
        Binding("escape", "back", "Indietro"),
    ]

    def __init__(self, career: Career, game_date: date) -> None:
        super().__init__(name=self.NAME)
        self._career = career
        self._game_date = game_date

    @property
    def career(self) -> Career:
        """La Carriera con registro e Progetti piu' recenti in memoria."""
        return self._career

    def compose(self) -> ComposeResult:
        team_name = self._career.world.player_slot.name or "(slot vuoto)"
        yield DateBar(self._career.season)
        yield Static(f"Sviluppo: {team_name}", id="development-header")
        yield BalanceBar(self._career.ledger, self._career.solvency)
        with VerticalScroll():
            yield Static(
                f"Progetti (massimo {MAX_PARALLEL_PROJECTS} paralleli)",
                classes="table-title",
            )
            yield DataTable(id="projects-table", cursor_type="row", zebra_stripes=True)
            yield Static(EMPTY_STATE_LABEL, id="development-empty")
            yield Static(
                "Nuovo Progetto: attributo, investimento, a per avviare", classes="table-title"
            )
            yield OptionList(*self._attribute_options(), id="attribute-list")
            yield Select(
                (
                    (f"{format_usd(amount)} (atteso +{expected_gain_points(amount)})", amount)
                    for amount in INVESTMENT_CHOICES
                ),
                id="investment-select",
                value=INVESTMENT_CHOICES[1],
                allow_blank=False,
            )
            yield Static("", id="development-error")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_projects()
        self.query_one("#attribute-list", OptionList).highlighted = 0

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_start_project(self) -> None:
        """Avvia il Progetto sull'attributo evidenziato (FOR-25)."""
        attribute = self._highlighted_attribute()
        if attribute is None:
            self._set_error("Seleziona un Attributo vettura.")
            return
        if optional_spending_blocked(self._career.ledger, self._career.solvency):
            self._set_error(
                "Spese facoltative bloccate: la squadra non e' sana "
                "(Progetti sospesi finche' la Cassa non si riprende)."
            )
            return
        investment = self.query_one("#investment-select", Select).value
        slot = self._career.world.player_slot
        try:
            ledger, projects = start_project(
                self._career.ledger,
                self._career.projects,
                attribute,
                int(investment),
                self._game_date,
                is_engine_customer=slot.engine_supplier_id is not None,
            )
        except ProjectLimitReached:
            self._set_error(
                f"Gia' {MAX_PARALLEL_PROJECTS} Progetti in corso: "
                "attendi una consegna prima di avviarne un altro."
            )
            return
        except CustomerEngineLocked:
            self._set_error(
                "Sei Cliente di un Motorista: la Potenza motore la sviluppa "
                "il fornitore, non puoi avviare Progetti su di essa."
            )
            return
        except SpendingBlocked as blocked:
            side = "la Cassa" if blocked.constraint == "cash" else "il Cap residuo"
            self._set_error(
                f"Spesa rifiutata: {side} non basta (consentiti {format_usd(blocked.allowed_usd)})."
            )
            return
        self._career = replace(self._career, ledger=ledger, projects=projects)
        self._set_error("")
        self.query_one(BalanceBar).update_ledger(ledger, self._career.solvency)
        self._refresh_projects()

    def action_back(self) -> None:
        """Torna alla griglia con la Carriera aggiornata."""
        self.dismiss(self._career)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _attribute_options(self) -> list[Option]:
        slot = self._career.world.player_slot
        is_customer = slot.engine_supplier_id is not None
        options = []
        for attribute in CAR_ATTRIBUTES:
            label = ATTRIBUTE_LABELS[attribute]
            if attribute == "engine_power" and is_customer:
                supplier = self._supplier_name(slot.engine_supplier_id)
                label += f" (non disponibile: la sviluppa {supplier})"
                options.append(Option(label, id=attribute, disabled=True))
            else:
                options.append(Option(label, id=attribute))
        return options

    def _supplier_name(self, supplier_id: int | None) -> str:
        for supplier in self._career.world.engine_suppliers:
            if supplier.id == supplier_id:
                return supplier.name
        return "il Motorista"

    def _highlighted_attribute(self) -> str | None:
        option_list = self.query_one("#attribute-list", OptionList)
        if option_list.highlighted is None:
            return None
        option = option_list.get_option_at_index(option_list.highlighted)
        return option.id

    def _refresh_projects(self) -> None:
        table = self.query_one("#projects-table", DataTable)
        table.clear(columns=True)
        projects = self._career.projects
        self.query_one("#development-empty", Static).display = not projects
        table.display = bool(projects)
        if not projects:
            return
        table.add_columns("Attributo", "Stato", "Costo", "Avvio", "Consegna stimata", "Esito")
        for project in projects:
            outcome = "-" if project.outcome is None else f"+{project.outcome}"
            table.add_row(
                ATTRIBUTE_LABELS[project.attribute],
                _STATUS_LABELS[project.status],
                format_usd(project.cost_usd),
                project.start_date.strftime("%d/%m/%Y"),
                project.delivery_date.strftime("%d/%m/%Y"),
                outcome,
            )

    def _set_error(self, message: str) -> None:
        self.query_one("#development-error", Static).update(message)


def current_game_date(career: Career) -> date:
    """La data di gioco corrente: la gara del weekend in corso o l'ultima.

    Senza weekend aperto si usa il 1 gennaio della stagione del registro:
    succede solo prima del primo GP.
    """
    if career.weekend is not None:
        return circuit_by_code(career.weekend.circuit_code).race_date_2026
    return date(career.ledger.season_year, 1, 1)
