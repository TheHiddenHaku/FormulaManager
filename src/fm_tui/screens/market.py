"""Schermata Mercato piloti: pool a Stime, offerte rivali, controfferta (T5.2.1, M5).

Guscio TUI sopra il motore (ADR 0002): mostra il pool dei Contratti in
scadenza e dei piloti liberi, gli Attributi pilota SEMPRE come Stime
(intervalli, mai valori esatti), l'offerta rivale visibile e i controlli
per la controfferta del giocatore (ingaggio e durata 1-3 stagioni). Le
controfferte insostenibili o perdenti mostrano il motivo strutturato che
arriva dal motore (NegotiationOutcome), mai una stringa improvvisata. Il
log delle mosse AI e' consultabile.

Nessuna logica di dominio qui: l'apertura, la risoluzione AI e la
negoziazione vivono in fm_engine.market; la schermata si limita a
chiamarle e a presentarne lo stato. Coerente con preseason.py e
development.py: push_screen dal grid e dismiss(Career) alla chiusura, con
Checkpoint a ogni mossa rilevante (le firme del Mercato viaggiano nel
market_state, sub-issue M4).

Default documentati (tuning rimandato a FOR-34):
- Apertura su richiesta dal grid (tasto m) sull'anno della stagione
  corrente: l'aggancio automatico al flusso di fine stagione e' della fase
  inverno (FOR-32).
- Una tornata di controfferta per pilota, come il default del motore (M3).
- Prestigio del giocatore al valore di partenza DEFAULT_PLAYER_PRESTIGE
  (il Prestigio dinamico del giocatore e' post-MVP).
"""

from dataclasses import replace
from datetime import date
from random import Random

import psycopg
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Input, Select, Static

from fm_engine.career import Career
from fm_engine.economy import DEFAULT_PLAYER_PRESTIGE
from fm_engine.info import driver_subject, format_estimate
from fm_engine.market import (
    AiMoveKind,
    NegotiationOutcomeKind,
    best_rival_salary_usd,
    counter_offer,
    open_market,
    resolve_market,
)
from fm_engine.season import INITIAL_SEASON_YEAR
from fm_engine.world.models import PLAYER_TEAM_ID
from fm_persistence import connect, save_career
from fm_tui.screens.development import current_game_date
from fm_tui.widgets.balance_bar import BalanceBar, format_usd
from fm_tui.widgets.flags import flag

# Italian labels of the 6 driver attributes, in DRIVER_ATTRIBUTES order.
_DRIVER_ATTRIBUTE_COLUMNS = (
    "Giro secco",
    "Passo gara",
    "Duelli",
    "G. gomme",
    "Bagnato",
    "Costanza",
)

# Italian labels of the AI move kinds shown in the log.
_MOVE_LABELS = {
    AiMoveKind.OFFER: "Offerta",
    AiMoveKind.SIGNING: "Firma",
    AiMoveKind.FORCED_ASSIGNMENT: "Assegnazione",
}

# Allowed counter-offer durations, in seasons (mirrors the engine 1-3).
_DURATION_CHOICES = (1, 2, 3)

# Seed salt for the AI resolution: keeps the Mercato deterministic per
# Career and season, distinct from the weekend and development draws.
_MARKET_SEED_SALT = 800

_EMPTY_POOL_LABEL = "Nessun pilota in scadenza ne' libero: niente da negoziare."
_EMPTY_CELL = "-"
_PLAYER_SUFFIX = " (tu)"
_FREE_AGENT_LABEL = "libero"


class MarketScreen(Screen[Career]):
    """Il Mercato piloti di fine stagione: pool a Stime, offerte e controfferta."""

    NAME = "market"

    DEFAULT_CSS = """
    MarketScreen #market-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    MarketScreen .table-title {
        padding: 1 1 0 1;
        text-style: bold;
    }

    MarketScreen DataTable {
        height: auto;
        margin: 0 1;
    }

    MarketScreen #market-empty {
        padding: 1 2;
        color: $text-muted;
    }

    MarketScreen #salary-input {
        margin: 0 1;
        width: 40;
    }

    MarketScreen #duration-select {
        margin: 0 1;
        width: 40;
    }

    MarketScreen #counter-offer {
        margin: 1 1 0 1;
    }

    MarketScreen #market-error {
        padding: 0 2;
        color: $error;
    }
    """

    BINDINGS = [
        Binding("o", "counter_offer", "Controfferta"),
        Binding("escape", "back", "Indietro"),
    ]

    def __init__(self, career: Career, game_date: date | None = None) -> None:
        super().__init__(name=self.NAME)
        self._career = career
        self._game_date = game_date or current_game_date(career)
        self._drivers_by_id = {driver.id: driver for driver in career.world.drivers}
        self._team_names = {team.id: team.name for team in career.world.ai_teams}
        # Driver ids in pool-row order: bridges the table cursor to the engine.
        self._row_driver_ids: list[int] = []
        self._save_failed = False

    @property
    def career(self) -> Career:
        """La Carriera con lo stato di Mercato piu' recente in memoria."""
        return self._career

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="market-header")
        yield BalanceBar(self._career.ledger, self._career.solvency)
        with VerticalScroll():
            yield Static("Pool: Contratti in scadenza e piloti liberi", classes="table-title")
            yield DataTable(id="market-pool", cursor_type="row", zebra_stripes=True)
            yield Static(_EMPTY_POOL_LABEL, id="market-empty")
            yield Static(
                "Controfferta: scegli un pilota, l'ingaggio annuale e la durata",
                classes="table-title",
            )
            yield Input(placeholder="Ingaggio annuale in USD", id="salary-input")
            yield Select(
                ((_duration_label(seasons), seasons) for seasons in _DURATION_CHOICES),
                id="duration-select",
                value=_DURATION_CHOICES[1],
                allow_blank=False,
            )
            yield Button("Controfferta", variant="primary", id="counter-offer")
            yield Static("", id="market-error")
            yield Static("Log mosse del Mercato", classes="table-title")
            yield DataTable(id="market-log", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        # The market opens (and the AI resolves) on first entry; a market
        # already open (resumed from a Checkpoint) is presented as-is.
        if not self._career.market.is_open:
            self._open_and_resolve()
        self._populate_pool()
        self._populate_log()
        self._prefill_salary()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_counter_offer(self) -> None:
        """Rilancia sul pilota selezionato con l'ingaggio e la durata scelti."""
        driver_id = self._selected_driver_id()
        if driver_id is None:
            self._set_error("Seleziona un pilota dal pool.")
            return
        if driver_id in self._career.market.signings_for(PLAYER_TEAM_ID):
            self._set_error("Hai gia' ingaggiato questo pilota.")
            return
        salary_usd = self._parsed_salary()
        if salary_usd is None:
            self._set_error("Inserisci un ingaggio annuale valido in USD (solo cifre).")
            return
        duration_seasons = int(self.query_one("#duration-select", Select).value)
        outcome = counter_offer(
            self._career.market,
            self._career.ledger,
            driver_id,
            salary_usd,
            duration_seasons,
            self._game_date,
            player_prestige=DEFAULT_PLAYER_PRESTIGE,
        )
        if outcome.kind is NegotiationOutcomeKind.ACCEPTED:
            self._on_signed(outcome.market, driver_id, duration_seasons)
        elif outcome.kind is NegotiationOutcomeKind.CASH_BLOCKED:
            self._set_error(
                "Controfferta rifiutata: la Cassa non basta (rata per gara massima "
                f"sostenibile {format_usd(outcome.allowed_usd or 0)})."
            )
        elif outcome.kind is NegotiationOutcomeKind.REJECTED_BY_DRIVER:
            self._set_error(
                "Il pilota ha scelto un'offerta rivale piu' alta "
                f"({format_usd(outcome.rival_salary_usd or 0)}). Rilancia ingaggio o durata."
            )
        else:  # INVALID_DURATION: la UI offre solo 1-3, e' una salvaguardia.
            self._set_error("Durata non valida: scegli tra 1 e 3 stagioni.")

    def action_back(self) -> None:
        """Torna alla griglia portando con se' la Carriera aggiornata."""
        self.dismiss(self._career)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "counter-offer":
            self.action_counter_offer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "salary-input":
            self.action_counter_offer()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "market-pool":
            self._prefill_salary()

    # ------------------------------------------------------------------
    # Engine calls
    # ------------------------------------------------------------------

    def _open_and_resolve(self) -> None:
        """Apre il Mercato per l'anno concluso e fa muovere le squadre AI."""
        world = self._career.world
        concluded_year = self._career.season.year
        market = open_market(world, concluded_year)
        seed = (
            world.seed * 1_000
            + (concluded_year - INITIAL_SEASON_YEAR) * 100_000
            + _MARKET_SEED_SALT
        )
        market = resolve_market(world, market, Random(seed))
        self._career = replace(self._career, market=market)
        self._checkpoint()

    def _on_signed(self, market, driver_id: int, duration_seasons: int) -> None:
        self._career = replace(self._career, market=market)
        self._checkpoint()
        self._set_error("")
        driver = self._drivers_by_id[driver_id]
        self.notify(
            f"{driver.name} ha firmato per {_duration_label(duration_seasons)}.",
            severity="information",
        )
        self._populate_pool()
        self._populate_log()
        self.query_one("#market-header", Static).update(self._header_text())

    def _checkpoint(self) -> None:
        """Salva l'intera Carriera; in caso di errore lo stato resta in memoria."""
        try:
            with connect() as connection:
                self._career = save_career(connection, self._career)
            self._save_failed = False
        except (RuntimeError, psycopg.Error) as error:
            self._save_failed = True
            self.notify(
                f"Checkpoint fallito: {error}. Riprova con un'altra mossa o riapri il Mercato.",
                severity="error",
                timeout=10,
            )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _populate_pool(self) -> None:
        table = self.query_one("#market-pool", DataTable)
        table.clear(columns=True)
        market = self._career.market
        self._row_driver_ids = list(market.available_driver_ids)
        has_pool = bool(self._row_driver_ids)
        self.query_one("#market-empty", Static).display = not has_pool
        table.display = has_pool
        if not has_pool:
            return
        table.add_columns(
            "Pilota",
            "Naz",
            "Eta'",
            "Da",
            "Ingaggio rif.",
            "Off. rivale",
            *_DRIVER_ATTRIBUTE_COLUMNS,
            "Esito",
        )
        origins = {contract.driver_id: contract.team_id for contract in market.pool}
        for driver_id in self._row_driver_ids:
            driver = self._drivers_by_id[driver_id]
            subject = driver_subject(driver_id)
            rival = best_rival_salary_usd(market, driver_id)
            table.add_row(
                driver.name,
                flag(driver.nationality),
                str(driver.age),
                self._origin_label(driver_id, origins),
                format_usd(self._reference_salary(driver_id, market)),
                format_usd(rival) if rival else _EMPTY_CELL,
                *(
                    format_estimate(self._career.knowledge.estimate_for(subject, value))
                    for value in driver.visible_attributes.values()
                ),
                self._signing_label(driver_id, market),
            )

    def _populate_log(self) -> None:
        table = self.query_one("#market-log", DataTable)
        table.clear(columns=True)
        table.add_columns("Squadra", "Pilota", "Mossa", "Ingaggio", "Durata")
        for move in self._career.market.ai_moves:
            table.add_row(
                self._team_label(move.team_id),
                self._driver_name(move.driver_id),
                _MOVE_LABELS[move.kind],
                format_usd(move.salary_usd),
                _duration_label(move.duration_seasons),
            )

    def _prefill_salary(self) -> None:
        """Suggerisce un ingaggio per il pilota evidenziato: l'offerta da battere."""
        driver_id = self._selected_driver_id()
        if driver_id is None:
            return
        market = self._career.market
        suggestion = max(
            best_rival_salary_usd(market, driver_id),
            self._reference_salary(driver_id, market),
        )
        self.query_one("#salary-input", Input).value = str(suggestion)

    def _header_text(self) -> str:
        market = self._career.market
        year = (
            market.concluded_year if market.concluded_year is not None else self._career.season.year
        )
        vacant = market.vacant_seats_for(PLAYER_TEAM_ID)
        signed = len(market.signings_for(PLAYER_TEAM_ID))
        return (
            f"Mercato piloti {year}  |  Squadra: {self._player_team_name()}  |  "
            f"Sedili da riempire: {vacant}  |  Ingaggiati: {signed}"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _selected_driver_id(self) -> int | None:
        if not self._row_driver_ids:
            return None
        row = self.query_one("#market-pool", DataTable).cursor_row
        if row is None or not 0 <= row < len(self._row_driver_ids):
            return None
        return self._row_driver_ids[row]

    def _parsed_salary(self) -> int | None:
        raw = self.query_one("#salary-input", Input).value.strip()
        for token in (".", ",", "_", "$", " "):
            raw = raw.replace(token, "")
        if not raw.isdigit():
            return None
        value = int(raw)
        return value if value > 0 else None

    def _reference_salary(self, driver_id: int, market) -> int:
        for contract in market.pool:
            if contract.driver_id == driver_id:
                return contract.salary_usd
        demand = self._drivers_by_id[driver_id].salary_demand_usd
        return market.salary_demands.get(driver_id, demand)

    def _origin_label(self, driver_id: int, origins: dict[int, int]) -> str:
        team_id = origins.get(driver_id)
        if team_id is None:
            return _FREE_AGENT_LABEL
        return self._team_label(team_id)

    def _signing_label(self, driver_id: int, market) -> str:
        if driver_id in market.signings_for(PLAYER_TEAM_ID):
            return "tuo"
        for team_id, signed in market.signings.items():
            if team_id != PLAYER_TEAM_ID and driver_id in signed:
                return self._team_label(team_id)
        return _EMPTY_CELL

    def _team_label(self, team_id: int) -> str:
        if team_id == PLAYER_TEAM_ID:
            return f"{self._player_team_name()}{_PLAYER_SUFFIX}"
        return self._team_names.get(team_id, f"Squadra {team_id}")

    def _driver_name(self, driver_id: int) -> str:
        driver = self._drivers_by_id.get(driver_id)
        return driver.name if driver is not None else f"Pilota {driver_id}"

    def _player_team_name(self) -> str:
        return self._career.world.player_slot.name or "(slot vuoto)"

    def _set_error(self, message: str) -> None:
        self.query_one("#market-error", Static).update(message)


def _duration_label(seasons: int) -> str:
    """La durata come etichetta italiana: '1 stagione' o 'N stagioni'."""
    return "1 stagione" if seasons == 1 else f"{seasons} stagioni"
