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
from random import Random

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from fm_engine.career import Career
from fm_engine.circuits import CALENDAR_2026, Circuit, circuit_by_code
from fm_engine.development import advance_projects, apply_delivery
from fm_engine.economy import (
    EconomicStatus,
    economic_status,
    optional_spending_blocked,
    start_next_season,
)
from fm_engine.events_extra import draw_extra_event
from fm_engine.info import car_subject, driver_subject, format_estimate
from fm_engine.preseason import PreseasonState
from fm_engine.season import INITIAL_SEASON_YEAR, advance_to_next_season, season_start_date
from fm_engine.weekend import start_weekend
from fm_engine.world.models import (
    CAR_ATTRIBUTES,
    DRIVER_ATTRIBUTES,
    PLAYER_TEAM_ID,
    Driver,
)
from fm_tui.screens.calendar import CalendarScreen
from fm_tui.screens.development import DevelopmentScreen, current_game_date
from fm_tui.screens.finances import FinancesScreen
from fm_tui.screens.news import NewsScreen
from fm_tui.screens.preseason import PreseasonScreen
from fm_tui.screens.standings import StandingsScreen
from fm_tui.screens.weekend import WeekendScreen
from fm_tui.widgets.balance_bar import BalanceBar
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
        Binding("c", "open_calendar", "Calendario"),
        Binding("l", "open_standings", "Classifiche"),
        Binding("f", "open_finances", "Finanze"),
        Binding("s", "open_development", "Sviluppo"),
        Binding("escape", "back", "Elenco Carriere"),
    ]

    def __init__(self, career: Career) -> None:
        super().__init__(name=self.NAME)
        self._career = career

    def compose(self) -> ComposeResult:
        yield Static(self._header(), id="grid-header")
        yield BalanceBar(self._career.ledger, self._career.solvency)
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
        """Apre il weekend del prossimo GP del Calendario (FOR-21, FOR-25).

        Percorso canonico del Gran Premio: FP1 -> FP2 -> FP3 ->
        Qualifiche -> Gara -> risultato, con Checkpoint a fine di ogni
        sessione. Un weekend gia' in corso (ripreso da un Checkpoint)
        continua dalla sessione giusta; un weekend concluso apre il GP
        successivo del Calendario, attraversando l'intervallo (i
        Progetti avanzano, FOR-25). Il seed deriva da (Mondo, GP):
        stessa Carriera, stesso weekend.
        """
        world = self._career.world
        if not world.player_slot.is_set_up:
            self.notify(
                "Completa il Setup squadra prima di scendere in pista.",
                severity="warning",
            )
            return
        status = economic_status(self._career.ledger, self._career.solvency)
        if status is EconomicStatus.BANKRUPT:
            self.notify(
                "Carriera fallita: la squadra non scende piu' in pista.",
                severity="error",
            )
            return
        # Pre-season test at the start of the season, before the first GP (T5.1.2).
        if self._needs_preseason():
            self.app.push_screen(PreseasonScreen(self._career), self._on_preseason_closed)
            return
        weekend = self._career.weekend
        if weekend is None:
            self._begin_weekend(CALENDAR_2026[0])
        elif weekend.finished:
            previous = circuit_by_code(weekend.circuit_code)
            next_circuit = self._next_playable_circuit(previous)
            if next_circuit is None:
                # Season over: advance the year (standings reset, calendar
                # replicated, economy rollover, T5.1.1), then run the new
                # season's pre-season test before its first GP (T5.1.2). The
                # winter phase (carry-over, projects, market) comes later.
                self._advance_to_next_season()
                self.notify(
                    f"Nuova stagione {self._career.season.year}: classifiche azzerate, "
                    "Calendario replicato.",
                    severity="information",
                )
                self.app.push_screen(PreseasonScreen(self._career), self._on_preseason_closed)
                return
            news = self._cross_the_interval(previous, next_circuit)
            self._begin_weekend(next_circuit)
            if news:
                # La rassegna stampa prima del weekend (FOR-27): si
                # prosegue verso la hub alla chiusura.
                self.app.push_screen(
                    NewsScreen(tuple(news)),
                    lambda _: self.app.push_screen(
                        WeekendScreen(self._career), self._on_weekend_closed
                    ),
                )
                return
        self.app.push_screen(WeekendScreen(self._career), self._on_weekend_closed)

    def _next_playable_circuit(self, previous: Circuit) -> Circuit | None:
        """Il prossimo GP in formato Standard, saltando gli Sprint (post-MVP).

        I GP Sprint del Calendario 2026 sono previsti dal modello ma non
        giocabili nel MVP (FOR-21): la stagione prosegue dal successivo
        GP Standard, segnalando il salto.
        """
        for circuit in CALENDAR_2026[previous.calendar_order :]:
            if circuit.weekend_format_2026 == "standard":
                return circuit
            self.notify(
                f"GP di {circuit.name} saltato: weekend Sprint, post-MVP.",
                severity="warning",
            )
        return None

    def _needs_preseason(self) -> bool:
        """True a inizio stagione, prima del primo GP, coi Test ancora da fare."""
        return (
            self._career.weekend is None
            and not self._career.season.results
            and not self._career.preseason.completed
        )

    def _begin_weekend(self, circuit: Circuit) -> None:
        # The seed varies per Career, season year and GP: a replayed
        # calendar produces a different season every year (T5.1.1). Year
        # 2026 keeps its original seed, so single-season behaviour is intact.
        year_offset = (self._career.season.year - INITIAL_SEASON_YEAR) * 100_000
        seed = self._career.world.seed * 1_000 + year_offset + circuit.calendar_order
        self._career = replace(self._career, weekend=start_weekend(circuit, seed))

    def _cross_the_interval(self, previous: Circuit, next_circuit: Circuit) -> list[str]:
        """L'intervallo tra due GP: Progetti ed Eventi extra-gara (FOR-25, FOR-27).

        Squadra non sana (FOR-24): Progetti sospesi, le consegne
        slittano dell'intervallo. Le consegne mature applicano l'esito
        all'Attributo vettura del giocatore; al piu' un Evento
        extra-gara tocca Cassa, Progetti o un rivale. Ritorna le
        Notizie dell'intervallo (vuoto = silenzio, nessuna rassegna).
        """
        career = self._career
        news: list[str] = []
        suspended = optional_spending_blocked(career.ledger, career.solvency)
        rng = Random(f"development:{career.world.seed}:{next_circuit.code}")
        projects, deliveries = advance_projects(
            career.projects,
            previous.race_date_2026,
            next_circuit.race_date_2026,
            rng,
            suspended=suspended,
        )
        world = career.world
        slot = world.player_slot
        for delivery in deliveries:
            attribute = delivery.project.attribute
            value = getattr(slot, attribute)
            slot = replace(slot, **{attribute: apply_delivery(value, delivery)})
            news.append(delivery.news)
        if deliveries:
            world = replace(world, player_slot=slot)
        if suspended and any(project.in_progress for project in career.projects):
            self.notify(
                "Squadra non sana: Progetti sospesi, le consegne slittano.",
                severity="warning",
            )
        ledger = career.ledger
        outcome = draw_extra_event(
            world,
            ledger,
            projects,
            next_circuit.race_date_2026,
            Random(f"extra:{career.world.seed}:{next_circuit.code}"),
        )
        if outcome is not None:
            news.append(outcome.news)
            world, ledger, projects = outcome.world, outcome.ledger, outcome.projects
        self._career = replace(career, world=world, ledger=ledger, projects=projects)
        self.query_one(BalanceBar).update_ledger(ledger, career.solvency)
        return news

    def _advance_to_next_season(self) -> None:
        """Passaggio di stagione: anno +1, classifiche azzerate, rollover economico.

        Replica il Calendario per l'anno nuovo (T5.1.1) e fa il rollover
        del registro (Cassa riportata, eventuale penalita' da Sforamento).
        La fase inverno vera e propria (Carry-over della vettura, Progetti
        invernali, Mercato piloti) arrivera' con le issue dedicate.
        """
        season = advance_to_next_season(self._career.season)
        ledger = start_next_season(self._career.ledger, season_start_date(season.year))
        self._career = replace(
            self._career,
            season=season,
            ledger=ledger,
            weekend=None,
            preseason=PreseasonState(),
        )
        self.query_one(BalanceBar).update_ledger(ledger, self._career.solvency)

    def _on_preseason_closed(self, career: Career | None) -> None:
        """Riporta in griglia la Carriera dopo i Test pre-season (Stime aggiornate)."""
        if career is not None:
            self._career = career

    def action_open_calendar(self) -> None:
        """Apre il Calendario della stagione (T5.1.1)."""
        self.app.push_screen(CalendarScreen(self._career))

    def action_open_standings(self) -> None:
        """Apre le classifiche piloti e costruttori (T5.1.1)."""
        self.app.push_screen(StandingsScreen(self._career))

    def action_open_development(self) -> None:
        """Apre la schermata sviluppo della vettura (FOR-25)."""
        if not self._career.world.player_slot.is_set_up:
            self.notify(
                "Completa il Setup squadra prima di sviluppare la vettura.",
                severity="warning",
            )
            return
        screen = DevelopmentScreen(self._career, current_game_date(self._career))
        self.app.push_screen(screen, self._on_development_closed)

    def _on_development_closed(self, career: Career | None) -> None:
        """Riporta in griglia registro e Progetti aggiornati."""
        if career is not None:
            self._career = career
            self.query_one(BalanceBar).update_ledger(career.ledger, career.solvency)

    def action_open_finances(self) -> None:
        """Apre la schermata finanze sul registro della Carriera (FOR-15)."""
        self.app.push_screen(FinancesScreen(self._career))

    def _on_weekend_closed(self, career: Career | None) -> None:
        """Aggiorna la Carriera in memoria con lo stato weekend piu' recente."""
        if career is not None:
            self._career = career
            self.query_one(BalanceBar).update_ledger(career.ledger, career.solvency)

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

    def _band(self, subject: str, value: float) -> str:
        """La Stima di un attributo col margine del livello di conoscenza (T5.1.2)."""
        return format_estimate(self._career.knowledge.estimate_for(subject, value))

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
                *(
                    self._band(car_subject(PLAYER_TEAM_ID), value)
                    for value in slot.car_attributes.values()
                ),
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
                *(self._band(car_subject(team.id), getattr(team, name)) for name in CAR_ATTRIBUTES),
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

    def _add_driver_row(self, table: DataTable, driver: Driver, team: str) -> None:
        subject = driver_subject(driver.id)
        table.add_row(
            driver.name,
            flag(driver.nationality),
            str(driver.age),
            team,
            *(self._band(subject, value) for value in driver.visible_attributes.values()),
        )
