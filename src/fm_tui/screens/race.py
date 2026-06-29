"""Schermata gara: Telecronaca, monitor tempi e Auto-pausa (FOR-17, FOR-18).

La finestra principale del giocatore sulla simulazione: un RichLog
riceve la Telecronaca (fm_engine.commentary) riga per riga in ordine di
Tick, mentre una DataTable mostra la Classifica tempi live (posizione,
pilota, distacco dal leader, distacco dal pilota davanti, Mescola, eta'
gomme) aggiornata cella per cella con throttling del refresh: mai un
ridisegno completo a ogni Tick.

Un worker asyncio avanza il motore Tick dopo Tick senza mai bloccare
l'event loop di Textual: velocita' 1x/2x/4x, pausa/riprendi e
skip-to-event (corsa a vuoto fino al prossimo Evento chiave o alla
bandiera a scacchi).

Auto-pausa (FOR-18): ogni Evento chiave del motore, piu' il Guasto
proprio di una vettura del giocatore e la finestra di undercut che lo
coinvolge (FOR-38), congela la simulazione una sola volta e apre il
pannello di decisione contestuale (PitOrderPanel). Da
li', o in pausa manuale con il tasto box, il manager impartisce
l'Ordine di pit con scelta della Mescola: il motore lo applica al Tick
successivo e la gara riprende fluida. Nessuna scrittura su database
durante la gara (ADR 0001).

Ordini pilota (FOR-19): da qualunque pausa (manuale o Auto-pausa) il
pannello Ordini imposta per ciascun pilota Aggressivita', Ordine di
scuderia e Istruzione sui duelli. Gli Ordini confermati sono persistenti
(consumati dal motore a ogni Tick), producono la conferma radio in
Telecronaca e restano sempre visibili nella barra Ordini della
schermata; il pilota in Abbandono e' disabilitato con motivo visibile.
"""

import asyncio
import re
import time
from dataclasses import dataclass
from random import Random

from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Label,
    RadioButton,
    RadioSet,
    RichLog,
    Static,
)

from fm_engine.circuits import CALENDAR_2026
from fm_engine.commentary import CommentaryContext, narrate
from fm_engine.events import (
    TEAM_ORDER_LIFTED,
    CarDamage,
    CarFailure,
    ChequeredFlag,
    ClassifiedResult,
    Crossover,
    Dnf,
    DriverError,
    OrderConfirmed,
    RaceEvent,
    RainStarted,
    RainStopped,
    SafetyCarDeployed,
    SafetyCarEnding,
    UndercutWindow,
    VscDeployed,
    VscEnding,
    is_key_event,
)
from fm_engine.race import step
from fm_engine.state import (
    Aggression,
    CarAttributes,
    CarRaceState,
    DriverOrders,
    DuelInstruction,
    Orders,
    PitOrder,
    RaceEntry,
    RaceState,
    TeamOrder,
)
from fm_engine.strategy import StrategyPlan, build_plans, lap_orders
from fm_engine.tyres import Compound, CompoundSlot, nominated_compounds
from fm_engine.world.models import PLAYER_TEAM_ID, World
from fm_tui.widgets.team_colors import (
    commentary_color_style,
    player_highlight_style,
    row_with_team_colors,
)

# Seconds of real time between two Ticks, per simulation speed.
TICK_DELAY_SECONDS: dict[int, float] = {1: 1.2, 2: 0.6, 4: 0.3}

# Minimum seconds between two monitor refreshes: during skip-to-event
# the Ticks run much faster than this, and the table is not redrawn for
# every one of them.
MONITOR_REFRESH_INTERVAL_SECONDS = 0.1

# Per-driver undercut auto-pause cooldown (FOR-40): once an undercut
# window has paused the race for one of the player's drivers, that
# driver does not pause it again for this many laps, accepted or
# refused. Stops the panel reopening lap after lap as the rivals around
# him keep churning. Distinct from the engine's per-attacker cooldown:
# this also covers the player as the threatened target.
UNDERCUT_AUTOPAUSE_COOLDOWN_LAPS = 8

# Italian labels for the fitted compound shown in the live monitor.
_COMPOUND_LABELS: dict[str, str] = {
    "c1": "C1",
    "c2": "C2",
    "c3": "C3",
    "c4": "C4",
    "c5": "C5",
    "intermediate": "Inter",
    "wet": "Bagnato",
}

_LEADER_GAP = "-"
_DNF_LABEL = "Abbandono"
_EMPTY_CELL = "-"

# Telecronaca: gli avvenimenti che richiedono attenzione del manager sono
# evidenziati in giallo (testo-giallo-su-problema): meteo in arrivo,
# neutralizzazioni (Safety car, VSC), Crossover, finestra di undercut e forti
# rallentamenti (Errore). Ritiri, guasti e incidenti restano fuori dal giallo.
_ATTENTION_EVENTS: tuple[type, ...] = (
    RainStarted,
    SafetyCarDeployed,
    VscDeployed,
    Crossover,
    UndercutWindow,
    DriverError,
)
_ATTENTION_STYLE = Style(color="yellow")

# I ritiri (Abbandono, sia del giocatore sia degli avversari) sono in rosso:
# qualcosa di grave (testo-rosso-su-ritiro). Vince sul giallo.
_RETIREMENT_STYLE = Style(color="red")


def _commentary_line_style(event: object) -> Style | None:
    """Lo stile di colore di una riga di Telecronaca per categoria di evento.

    Rosso per i ritiri (testo-rosso-su-ritiro), giallo per gli avvenimenti che
    richiedono attenzione (testo-giallo-su-problema), None (colore standard)
    per i messaggi ordinari.
    """
    if isinstance(event, Dnf):
        return _RETIREMENT_STYLE
    if isinstance(event, _ATTENTION_EVENTS):
        return _ATTENTION_STYLE
    return None

# UI labels for the simulation status shown in the header.
_STATUS_RUNNING = "In corsa"
_STATUS_PAUSED = "In pausa"
_STATUS_AUTO_PAUSED = "Auto-pausa"
_STATUS_SKIPPING = "Skip all'evento"
_STATUS_FINISHED = "Bandiera a scacchi"

# Italian labels for the nominated compound slots offered by the panel.
_SLOT_LABELS: dict[CompoundSlot, str] = {
    CompoundSlot.SOFT: "Morbida",
    CompoundSlot.MEDIUM: "Media",
    CompoundSlot.HARD: "Dura",
}

# Italian labels for the Crossover tyre categories.
_TYRE_CATEGORY_LABELS: dict[str, str] = {
    "slick": "le slick",
    "intermediate": "le intermedie",
    "wet": "le gomme da bagnato",
}

_MANUAL_PANEL_DESCRIPTION = "Pausa ai box: ordinare un pit stop?"

# Italian labels for the three order groups (FOR-19), shared by the
# orders panel and the always-visible orders bar.
_AGGRESSION_LABELS: dict[Aggression, str] = {
    Aggression.PUSH: "Push",
    Aggression.NORMAL: "Normale",
    Aggression.CONSERVE: "Conserva",
}
_TEAM_ORDER_LABELS: dict[TeamOrder, str] = {
    TeamOrder.SWAP_POSITIONS: "Scambio posizioni",
    TeamOrder.HOLD_POSITIONS: "Congelamento posizioni",
    TeamOrder.NO_ATTACK: "Divieto di attacco al compagno",
}
_DUEL_LABELS: dict[DuelInstruction, str] = {
    DuelInstruction.STANDARD: "Standard",
    DuelInstruction.DEFEND_HARD: "Difendi duro",
    DuelInstruction.NO_RISK: "Non rischiare",
}
_NO_TEAM_ORDER_LABEL = "Nessun ordine"
_RETIRED_REASON = "Abbandono: vettura fuori gara"

# Default per-driver settings: normal aggression, standard duels.
_DEFAULT_DRIVER_SETTINGS = (Aggression.NORMAL, DuelInstruction.STANDARD)


@dataclass(frozen=True)
class PitDecision:
    """La decisione presa dal pannello: quale pilota e quale Mescola."""

    driver_id: int
    compound: Compound


@dataclass(frozen=True)
class OrdersDecision:
    """La decisione del pannello Ordini: pilota e i tre gruppi (FOR-19)."""

    driver_id: int
    aggression: Aggression
    duel_instruction: DuelInstruction
    team_order: TeamOrder | None


@dataclass(frozen=True)
class OpenOrdersRequest:
    """Richiesta dal pannello pit: aprire il pannello Ordini, pausa intatta."""


class DriverOrdersPanel(ModalScreen[OrdersDecision | None]):
    """Pannello Ordini per pilota (FOR-19): Aggressivita', scuderia, duelli.

    Mostra lo stato corrente degli Ordini del pilota selezionato e
    permette di cambiarli da qualunque pausa; il pilota in Abbandono e'
    disabilitato con il motivo visibile. dismiss(OrdersDecision) =
    Ordini confermati; dismiss(None) = nessun cambiamento.
    """

    NAME = "driver_orders_panel"

    DEFAULT_CSS = """
    DriverOrdersPanel {
        align: center middle;
    }

    DriverOrdersPanel #orders-window {
        width: 70;
        height: auto;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    DriverOrdersPanel #orders-title {
        margin-bottom: 1;
        text-style: bold;
    }

    DriverOrdersPanel RadioSet {
        height: auto;
        margin-bottom: 1;
    }

    DriverOrdersPanel #orders-buttons {
        height: auto;
        align-horizontal: center;
    }

    DriverOrdersPanel #orders-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Chiudi senza ordini"),
    ]

    def __init__(
        self,
        drivers: tuple[tuple[int, str, bool], ...],
        current: dict[int, tuple[Aggression, DuelInstruction]],
        team_order: TeamOrder | None,
    ) -> None:
        """drivers: (id, nome, in Abbandono) per i piloti del giocatore."""
        super().__init__(name=self.NAME)
        self._drivers = drivers
        self._current = current
        self._team_order = team_order

    def compose(self) -> ComposeResult:
        first_active = next(
            (driver_id for driver_id, _, retired in self._drivers if not retired), None
        )
        aggression, duel_instruction = (
            self._current.get(first_active, _DEFAULT_DRIVER_SETTINGS)
            if first_active is not None
            else _DEFAULT_DRIVER_SETTINGS
        )
        all_retired = first_active is None
        with Vertical(id="orders-window"):
            yield Label("Ordini pilota", id="orders-title")
            yield Label("Pilota:")
            with RadioSet(id="orders-drivers"):
                for driver_id, name, retired in self._drivers:
                    yield RadioButton(
                        f"{name} ({_RETIRED_REASON})" if retired else name,
                        value=driver_id == first_active,
                        disabled=retired,
                        id=f"orders-driver-{driver_id}",
                    )
            yield Label("Aggressivita':")
            with RadioSet(id="orders-aggression", disabled=all_retired):
                for option in Aggression:
                    yield RadioButton(
                        _AGGRESSION_LABELS[option],
                        value=option is aggression,
                        id=f"orders-aggression-{option.value}",
                    )
            yield Label("Ordine di scuderia:")
            with RadioSet(id="orders-team", disabled=all_retired):
                yield RadioButton(
                    _NO_TEAM_ORDER_LABEL,
                    value=self._team_order is None,
                    id="orders-team-none",
                )
                for team_option in TeamOrder:
                    yield RadioButton(
                        _TEAM_ORDER_LABELS[team_option],
                        value=team_option is self._team_order,
                        id=f"orders-team-{team_option.value}",
                    )
            yield Label("Istruzione sui duelli:")
            with RadioSet(id="orders-duel", disabled=all_retired):
                for duel_option in DuelInstruction:
                    yield RadioButton(
                        _DUEL_LABELS[duel_option],
                        value=duel_option is duel_instruction,
                        id=f"orders-duel-{duel_option.value}",
                    )
            if all_retired:
                yield Label(
                    "Nessun pilota disponibile: vetture in Abbandono.",
                    id="orders-retired-note",
                )
            with Horizontal(id="orders-buttons"):
                yield Button(
                    "Conferma gli ordini",
                    variant="primary",
                    id="confirm-orders",
                    disabled=all_retired,
                )
                yield Button("Chiudi senza ordini", id="dismiss-orders")
        yield Footer()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Al cambio pilota ricarica i suoi Ordini correnti nei gruppi."""
        if event.radio_set.id != "orders-drivers" or event.pressed.id is None:
            return
        driver_id = int(event.pressed.id.removeprefix("orders-driver-"))
        aggression, duel_instruction = self._current.get(driver_id, _DEFAULT_DRIVER_SETTINGS)
        # Defer the reload past this Changed: setting RadioButton.value from
        # inside the driver-change handler does not reliably switch the
        # pressed button in the other groups, leaving two dots lit (FOR-41).
        # Once the handler returns, Textual's own exclusivity does the swap.
        self.call_after_refresh(self._reload_current_orders, aggression, duel_instruction)

    def _reload_current_orders(
        self, aggression: Aggression, duel_instruction: DuelInstruction
    ) -> None:
        """Porta i gruppi Aggressivita' e duelli sugli Ordini del pilota scelto."""
        self.query_one(f"#orders-aggression-{aggression.value}", RadioButton).value = True
        self.query_one(f"#orders-duel-{duel_instruction.value}", RadioButton).value = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-orders":
            self.dismiss(self._decision())
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _decision(self) -> OrdersDecision | None:
        """Gli Ordini selezionati per il pilota scelto, o None se incompleti."""
        driver_button = self.query_one("#orders-drivers", RadioSet).pressed_button
        aggression_button = self.query_one("#orders-aggression", RadioSet).pressed_button
        team_button = self.query_one("#orders-team", RadioSet).pressed_button
        duel_button = self.query_one("#orders-duel", RadioSet).pressed_button
        buttons = (driver_button, aggression_button, team_button, duel_button)
        if any(button is None or button.id is None for button in buttons):
            return None
        team_value = team_button.id.removeprefix("orders-team-")
        return OrdersDecision(
            driver_id=int(driver_button.id.removeprefix("orders-driver-")),
            aggression=Aggression(aggression_button.id.removeprefix("orders-aggression-")),
            duel_instruction=DuelInstruction(duel_button.id.removeprefix("orders-duel-")),
            team_order=None if team_value == "none" else TeamOrder(team_value),
        )


class PitOrderPanel(ModalScreen[PitDecision | OpenOrdersRequest | None]):
    """Pannello di decisione contestuale dell'Ordine di pit (FOR-18).

    Descrive l'Evento chiave (o la pausa manuale) e offre la scelta di
    pilota e Mescola. dismiss(PitDecision) = pit ordinato;
    dismiss(None) = nessun Ordine; dismiss(OpenOrdersRequest) = il
    manager passa al pannello Ordini pilota senza riprendere (FOR-19).
    """

    NAME = "pit_order_panel"

    DEFAULT_CSS = """
    PitOrderPanel {
        align: center middle;
    }

    PitOrderPanel #pit-window {
        width: 70;
        height: auto;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
    }

    PitOrderPanel #pit-description {
        margin-bottom: 1;
    }

    PitOrderPanel RadioSet {
        height: auto;
        margin-bottom: 1;
    }

    PitOrderPanel #pit-buttons {
        height: auto;
        align-horizontal: center;
    }

    PitOrderPanel #pit-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Riprendi senza ordini"),
    ]

    def __init__(
        self,
        description: str,
        drivers: tuple[tuple[int, str], ...],
        compounds: tuple[tuple[Compound, str], ...],
        preselected: Compound,
        preselected_driver: int | None = None,
    ) -> None:
        super().__init__(name=self.NAME)
        self._description = description
        self._drivers = drivers
        self._compounds = compounds
        self._preselected = preselected
        # The driver the panel opens on. The auto-pause passes the one the
        # trigger is about (undercut window, own failure) so the pit order
        # lands on the right car; the manual flow leaves it None and the
        # first driver stays selected, as before.
        driver_ids = [driver_id for driver_id, _ in drivers]
        self._selected_driver_id = (
            preselected_driver
            if preselected_driver in driver_ids
            else (driver_ids[0] if driver_ids else None)
        )

    @property
    def description(self) -> str:
        """Il testo contestuale mostrato in testa al pannello."""
        return self._description

    def compose(self) -> ComposeResult:
        with Vertical(id="pit-window"):
            yield Label(self._description, id="pit-description")
            yield Label("Pilota da richiamare ai box:")
            with RadioSet(id="pit-drivers"):
                for driver_id, name in self._drivers:
                    yield RadioButton(
                        name,
                        value=driver_id == self._selected_driver_id,
                        id=f"pit-driver-{driver_id}",
                    )
            yield Label("Mescola da montare:")
            with RadioSet(id="pit-compounds"):
                for compound, label in self._compounds:
                    yield RadioButton(
                        label,
                        value=compound is self._preselected,
                        id=f"pit-compound-{compound.value}",
                    )
            with Horizontal(id="pit-buttons"):
                yield Button("Ordina il pit", variant="primary", id="confirm-pit")
                yield Button("Ordini pilota", id="open-orders")
                yield Button("Riprendi senza ordini", id="dismiss-panel")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-pit":
            self.dismiss(self._decision())
        elif event.button.id == "open-orders":
            self.dismiss(OpenOrdersRequest())
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _decision(self) -> PitDecision | None:
        """La coppia (pilota, Mescola) selezionata, o None se incompleta."""
        driver_button = self.query_one("#pit-drivers", RadioSet).pressed_button
        compound_button = self.query_one("#pit-compounds", RadioSet).pressed_button
        if driver_button is None or compound_button is None or driver_button.id is None:
            return None
        if compound_button.id is None:
            return None
        driver_id = int(driver_button.id.removeprefix("pit-driver-"))
        compound = Compound(compound_button.id.removeprefix("pit-compound-"))
        return PitDecision(driver_id=driver_id, compound=compound)


def race_entries(world: World) -> tuple[RaceEntry, ...]:
    """Le 22 iscritte alla gara dal Mondo della Carriera.

    I 2 piloti del giocatore corrono sulla sua vettura iniziale, quindi
    il Setup squadra deve essere completato; le squadre AI schierano i
    loro contrattualizzati. L'ordine e' giocatore prima, poi le AI:
    sara' la Qualifica a decidere la griglia.
    """
    if not world.player_slot.is_set_up:
        raise ValueError("player slot not set up yet: no car to race with")
    drivers_by_id = {driver.id: driver for driver in world.drivers}
    entries: list[RaceEntry] = []
    player_car = CarAttributes.from_player_slot(world.player_slot)
    for contract in world.contracts_of(PLAYER_TEAM_ID):
        entries.append(
            RaceEntry(
                driver=drivers_by_id[contract.driver_id],
                team_id=PLAYER_TEAM_ID,
                car=player_car,
            )
        )
    for team in world.ai_teams:
        car = CarAttributes.from_team(team)
        for contract in world.contracts_of(team.id):
            entries.append(
                RaceEntry(driver=drivers_by_id[contract.driver_id], team_id=team.id, car=car)
            )
    return tuple(entries)


def commentary_context(world: World) -> CommentaryContext:
    """Il contesto della Telecronaca: nomi al posto degli id del motore."""
    team_names = {team.id: team.name for team in world.ai_teams}
    if world.player_slot.name:
        team_names[PLAYER_TEAM_ID] = world.player_slot.name
    return CommentaryContext(
        driver_names={driver.id: driver.name for driver in world.drivers},
        team_names=team_names,
        circuit_names={circuit.code: circuit.name for circuit in CALENDAR_2026},
    )


class RaceScreen(Screen[tuple[ClassifiedResult, ...] | None]):
    """La Gara interattiva: cronaca in streaming e monitor tempi live."""

    NAME = "race"

    DEFAULT_CSS = """
    RaceScreen #race-header {
        padding: 0 1;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    RaceScreen #orders-status {
        padding: 0 1;
        color: $text-muted;
    }

    RaceScreen #race-body {
        height: 1fr;
    }

    RaceScreen #commentary {
        width: 1fr;
        margin: 0 1;
        border: solid $primary;
    }

    RaceScreen #monitor {
        width: auto;
        margin-right: 1;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_pause", "Pausa/Riprendi"),
        Binding("1", "speed('1')", "1x"),
        Binding("2", "speed('2')", "2x"),
        Binding("4", "speed('4')", "4x"),
        Binding("s", "skip_to_event", "Salta all'evento"),
        Binding("b", "pit_order", "Ordine di pit"),
        Binding("o", "driver_orders", "Ordini pilota"),
        Binding("escape", "back", "Lascia la gara"),
    ]

    def __init__(
        self,
        state: RaceState,
        initial_events: tuple[RaceEvent, ...],
        context: CommentaryContext,
        player_color: str | None = None,
        team_colors: dict[int, tuple[str | None, str | None]] | None = None,
    ) -> None:
        super().__init__(name=self.NAME)
        self._state = state
        self._initial_events = initial_events
        self._commentary_context = context
        # driver_id -> (primary, secondary) for the two team colour squares
        # shown next to every driver in the monitor.
        self._team_colors = team_colors or {}
        # Player livery highlight (B02): the player's drivers are evidenced in
        # the Telecronaca with the team colour. The colour lives on the player
        # slot; the names come from the commentary context. Falls back to bold
        # when the colour is missing or unparseable.
        self._player_style = player_highlight_style(player_color)
        # Commentary RNG stream, separate from the engine's (seed, lap)
        # streams: deterministic text for a given race seed.
        self._commentary_rng = Random(state.seed)
        self._speed = 1
        self._skipping = False
        self._resume = asyncio.Event()
        self._resume.set()
        self._classification: tuple[ClassifiedResult, ...] | None = None
        # Auto-pause bookkeeping (FOR-18): the player's drivers, the pit
        # orders queued for the next Tick and the key events already
        # handled (each one pauses exactly once).
        # Retired player cars included: the orders bar and the orders
        # panel keep showing them, marked as DNF (FOR-19).
        self._player_driver_ids = tuple(
            car.entry.driver.id
            for car in state.cars + state.dnfs
            if car.entry.team_id == PLAYER_TEAM_ID
        )
        # Every driver's name is painted in the Telecronaca with the team
        # colour (colori-squadra-in-telecronaca): the player's drivers keep
        # their bold highlight, the rivals get their team colour. Built once
        # for all the cars on the grid, in starting order.
        self._driver_name_styles: list[tuple[str, Style]] = []
        for car in state.cars + state.dnfs:
            driver_id = car.entry.driver.id
            name = self._commentary_context.driver_name(driver_id)
            if not name:
                continue
            if driver_id in self._player_driver_ids:
                self._driver_name_styles.append((name, self._player_style))
                continue
            primary = (team_colors or {}).get(driver_id, (None, None))[0]
            rival_style = commentary_color_style(primary)
            if rival_style is not None:
                self._driver_name_styles.append((name, rival_style))
        self._pending_pits: dict[int, Compound] = {}
        # AI pit strategy (FOR-39): the non-player cars get the same tyre
        # plans the balance harness uses, injected at every Tick alongside
        # the player's orders. The player's own drivers are excluded: their
        # stops stay the manager's call. Built once from the starting grid,
        # deterministic for the race seed.
        ai_entries = tuple(
            car.entry for car in state.cars + state.dnfs if car.entry.team_id != PLAYER_TEAM_ID
        )
        self._ai_plans: dict[int, StrategyPlan] = build_plans(
            ai_entries, state.circuit, Random(state.seed)
        )
        # Persistent driver orders (FOR-19): aggression and duel
        # instruction per player driver, plus the shared team order.
        # They feed the engine at every Tick until changed.
        self._driver_orders: dict[int, tuple[Aggression, DuelInstruction]] = {
            driver_id: _DEFAULT_DRIVER_SETTINGS for driver_id in self._player_driver_ids
        }
        self._team_order: TeamOrder | None = None
        # Damage events of the whole race (FOR-23): the weekend screen
        # turns the player's ones into repair charges at the flag.
        self._damage_events: list[CarDamage] = [
            event for event in initial_events if isinstance(event, CarDamage)
        ]
        # Principal events of the whole race (T5.3.2): Safety car and
        # Abbandoni, archived in the Almanacco at the flag (ADR 0003: no
        # full Telecronaca). Collected lap by lap like the damage events.
        self._principal_events: list[SafetyCarDeployed | Dnf] = [
            event for event in initial_events if isinstance(event, SafetyCarDeployed | Dnf)
        ]
        self._handled_key_events: set[RaceEvent] = set()
        # Undercut auto-pause cooldown (FOR-40): player driver id -> the
        # lap before which no further undercut window pauses for him.
        self._undercut_cooldown_until: dict[int, int] = {}
        self._auto_paused = False
        self._panel_open = False
        # Cell cache for per-cell updates: (row index, column index) -> value.
        self._cells: dict[tuple[int, int], str | Text] = {}
        self._row_keys: list[object] = []
        self._column_keys: list[object] = []
        self._last_monitor_refresh = 0.0

    # ------------------------------------------------------------------
    # Read-only state, for the header and the Pilot tests
    # ------------------------------------------------------------------

    @property
    def race_finished(self) -> bool:
        """True dopo la bandiera a scacchi."""
        return self._state.finished

    @property
    def damage_events(self) -> tuple[CarDamage, ...]:
        """Gli eventi danno della gara, per i Danni su Cassa e Cap (FOR-23)."""
        return tuple(self._damage_events)

    @property
    def principal_events(self) -> tuple[SafetyCarDeployed | Dnf, ...]:
        """Gli eventi principali della gara, per l'Almanacco (T5.3.2)."""
        return tuple(self._principal_events)

    @property
    def current_lap(self) -> int:
        """L'ultimo giro completato."""
        return self._state.lap

    @property
    def is_paused(self) -> bool:
        """True se la simulazione e' congelata in attesa di riprendere."""
        return not self._resume.is_set()

    @property
    def speed_multiplier(self) -> int:
        """La velocita' di simulazione corrente (1, 2 o 4)."""
        return self._speed

    @property
    def is_skipping(self) -> bool:
        """True durante la corsa a vuoto verso il prossimo Evento chiave."""
        return self._skipping

    @property
    def is_auto_paused(self) -> bool:
        """True se la pausa corrente e' un'Auto-pausa da Evento chiave."""
        return self._auto_paused and not self._resume.is_set()

    @property
    def race_state(self) -> RaceState:
        """Lo stato di gara dopo l'ultimo Tick simulato."""
        return self._state

    @property
    def pending_pit_orders(self) -> dict[int, Compound]:
        """Gli Ordini di pit in coda per il prossimo Tick (copia)."""
        return dict(self._pending_pits)

    @property
    def driver_order_settings(self) -> dict[int, tuple[Aggression, DuelInstruction]]:
        """Gli Ordini persistenti correnti per pilota del giocatore (copia)."""
        return dict(self._driver_orders)

    @property
    def team_order(self) -> TeamOrder | None:
        """L'Ordine di scuderia attivo sulla squadra del giocatore."""
        return self._team_order

    # ------------------------------------------------------------------
    # Layout and start-up
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="race-header")
        yield Static(self._orders_status_text(), id="orders-status")
        with Horizontal(id="race-body"):
            yield RichLog(id="commentary", wrap=True, markup=False, highlight=False)
            yield DataTable(id="monitor", cursor_type="none", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#monitor", DataTable)
        self._column_keys = list(
            table.add_columns("Pos", "Pilota", "Distacco", "Dist. prec.", "Mescola", "Eta' gomme")
        )
        for index, row in enumerate(self._monitor_rows()):
            self._row_keys.append(table.add_row(*row, key=f"slot-{index}"))
            for column_index, value in enumerate(row):
                self._cells[(index, column_index)] = value
        self._write_commentary(self._initial_events)
        self.run_worker(self._run_race(), exclusive=True)

    # ------------------------------------------------------------------
    # The asyncio worker: one Tick at a time, never blocking the loop
    # ------------------------------------------------------------------

    async def _run_race(self) -> None:
        """Avanza il motore Tick dopo Tick fino alla bandiera a scacchi.

        Ogni iterazione attende l'eventuale pausa, consuma gli Ordini
        di pit in coda, simula un giro, scrive la cronaca e aggiorna il
        monitor, poi cede il controllo all'event loop: in skip con uno
        sleep(0), altrimenti con il ritardo della velocita' scelta. Gli
        Eventi chiave nuovi del Tick scatenano l'Auto-pausa (FOR-18).
        """
        while not self._state.finished:
            await self._resume.wait()
            self._state, events = step(self._state, self._take_orders())
            self._write_commentary(events)
            for event in events:
                if isinstance(event, ChequeredFlag):
                    self._classification = event.classification
                elif isinstance(event, CarDamage):
                    self._damage_events.append(event)
                if isinstance(event, SafetyCarDeployed | Dnf):
                    self._principal_events.append(event)
            triggers = self._new_triggers(events)
            if self._state.finished:
                self._skipping = False
            elif triggers:
                # Auto-pause: freeze on the spot, then ask the manager.
                self._skipping = False
                self._auto_pause(triggers)
            self._refresh_monitor(force=self._state.finished or self.is_paused)
            self._update_header()
            if self._state.finished:
                break
            if self._skipping:
                await asyncio.sleep(0)
            else:
                await asyncio.sleep(TICK_DELAY_SECONDS[self._speed])
        self._refresh_monitor(force=True)
        self._update_header()

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def action_toggle_pause(self) -> None:
        """Congela o riprende la simulazione; la tabella resta consultabile."""
        if self._state.finished or self._panel_open:
            return
        if self._resume.is_set():
            self._resume.clear()
            self._skipping = False
            self._update_header()
        else:
            self._resume_simulation()

    def action_speed(self, multiplier: str) -> None:
        """Imposta la velocita' di simulazione a 1x, 2x o 4x."""
        if self._state.finished:
            return
        self._speed = int(multiplier)
        self._skipping = False
        self._update_header()

    def action_skip_to_event(self) -> None:
        """Corre a vuoto fino al prossimo Evento chiave o alla bandiera."""
        if self._state.finished or self._panel_open:
            return
        self._skipping = True
        self._resume_simulation()

    def action_pit_order(self) -> None:
        """Apre il pannello dell'Ordine di pit, mettendo in pausa se serve."""
        if self._state.finished or self._panel_open:
            return
        was_running = self._resume.is_set()
        self._resume.clear()
        self._skipping = False
        self._update_header()
        self._open_pit_panel(_MANUAL_PANEL_DESCRIPTION, resume_on_dismiss=was_running)

    def action_driver_orders(self) -> None:
        """Apre il pannello Ordini pilota, mettendo in pausa se serve."""
        if self._state.finished or self._panel_open:
            return
        was_running = self._resume.is_set()
        self._resume.clear()
        self._skipping = False
        self._update_header()
        self._open_orders_panel(resume_on_dismiss=was_running)

    def action_back(self) -> None:
        """Chiude la schermata gara e restituisce l'esito al chiamante.

        A bandiera a scacchi esposta il dismiss porta la classifica
        finale al flusso weekend (FOR-21); lasciare prima della fine
        restituisce None e la Gara resta da giocare.
        """
        self.dismiss(self._classification if self._state.finished else None)

    # ------------------------------------------------------------------
    # Auto-pause and the pit order panel (FOR-18)
    # ------------------------------------------------------------------

    def _take_orders(self) -> Orders:
        """Gli Ordini del prossimo Tick: persistenti piu' i pit in coda.

        Aggressivita', Ordine di scuderia e Istruzione sui duelli sono
        persistenti e viaggiano a ogni Tick; l'Ordine di pit del giocatore
        e' one-shot e la sua coda si svuota. Le squadre AI ricevono i loro
        Ordini di pit dalla strategia del motore (FOR-39): il manager
        decide solo per i propri piloti.
        """
        drivers: dict[int, DriverOrders] = {}
        for driver_id in self._player_driver_ids:
            aggression, duel_instruction = self._driver_orders[driver_id]
            compound = self._pending_pits.get(driver_id)
            drivers[driver_id] = DriverOrders(
                aggression=aggression,
                duel_instruction=duel_instruction,
                pit=PitOrder(compound=compound) if compound is not None else None,
            )
        self._pending_pits.clear()
        # AI pit strategy: lap_orders skips the cars without a plan (the
        # player's) and the retired ones (not in state.cars).
        ai_orders = lap_orders(self._state, self._ai_plans)
        if ai_orders is not None:
            drivers.update(ai_orders.drivers)
        teams = {PLAYER_TEAM_ID: self._team_order} if self._team_order is not None else {}
        return Orders(drivers=drivers, teams=teams)

    def _new_triggers(self, events: tuple[RaceEvent, ...]) -> tuple[RaceEvent, ...]:
        """Gli inneschi di Auto-pausa non ancora gestiti tra gli eventi.

        Eventi chiave del motore (is_key_event) piu' il Guasto proprio e
        la finestra di undercut che coinvolge il giocatore (FOR-38);
        ogni evento entra nel registro dei gestiti alla prima vista,
        cosi' lo stesso Evento chiave non scatena mai due Auto-pause.
        """
        triggers: list[RaceEvent] = []
        for event in events:
            is_undercut = self._is_own_undercut_window(event)
            if not (is_key_event(event) or self._is_own_failure(event) or is_undercut):
                continue
            if event in self._handled_key_events:
                continue
            if is_undercut and self._undercut_on_cooldown(event):
                # Cooldown (FOR-40): the involved player driver was just
                # flagged; mark this window handled and stay silent.
                self._handled_key_events.add(event)
                continue
            self._handled_key_events.add(event)
            if is_undercut:
                self._start_undercut_cooldown(event)
            triggers.append(event)
        return tuple(triggers)

    def _is_own_failure(self, event: RaceEvent) -> bool:
        """True per il Guasto di una vettura del giocatore."""
        return isinstance(event, CarFailure) and event.driver_id in self._player_driver_ids

    def _is_own_undercut_window(self, event: RaceEvent) -> bool:
        """True per una finestra di undercut che coinvolge il giocatore.

        Opportunita' (il pilota del giocatore puo' guadagnare la
        posizione fermandosi) o minaccia subita (il rivale dietro puo'
        scavalcarlo ai box). Il motore non conosce il giocatore: il
        filtro sta qui, come per il Guasto proprio.
        """
        return isinstance(event, UndercutWindow) and (
            event.driver_id in self._player_driver_ids
            or event.target_driver_id in self._player_driver_ids
        )

    def _player_drivers_in_window(self, event: UndercutWindow) -> tuple[int, ...]:
        """I piloti del giocatore coinvolti nella finestra (attaccante o rivale)."""
        return tuple(
            driver_id
            for driver_id in (event.driver_id, event.target_driver_id)
            if driver_id in self._player_driver_ids
        )

    def _undercut_on_cooldown(self, event: UndercutWindow) -> bool:
        """True se ogni pilota del giocatore coinvolto e' ancora in cooldown."""
        return all(
            self._state.lap < self._undercut_cooldown_until.get(driver_id, 0)
            for driver_id in self._player_drivers_in_window(event)
        )

    def _start_undercut_cooldown(self, event: UndercutWindow) -> None:
        """Avvia il cooldown per i piloti del giocatore coinvolti nella finestra."""
        until = self._state.lap + UNDERCUT_AUTOPAUSE_COOLDOWN_LAPS
        for driver_id in self._player_drivers_in_window(event):
            self._undercut_cooldown_until[driver_id] = until

    def _trigger_focus_driver(self, triggers: tuple[RaceEvent, ...]) -> int | None:
        """Il pilota del giocatore al centro degli inneschi, se uno spicca.

        La finestra di undercut e il Guasto riguardano un pilota preciso:
        il pannello di pit deve pre-selezionare quello, non per forza il
        primo della lista. Inneschi non legati a un pilota (Safety car,
        VSC, meteo) non impongono un focus e lasciano il default.
        """
        for event in triggers:
            if isinstance(event, UndercutWindow):
                involved = self._player_drivers_in_window(event)
                if involved:
                    return involved[0]
            elif isinstance(event, CarFailure) and event.driver_id in self._player_driver_ids:
                return event.driver_id
        return None

    def _auto_pause(self, triggers: tuple[RaceEvent, ...]) -> None:
        """Congela la simulazione e apre il pannello di decisione.

        Se gli inneschi puntano a un pilota preciso (finestra di undercut,
        Guasto proprio), il pannello pre-seleziona quel pilota cosi'
        l'Ordine di pit confermato cade sulla vettura giusta.
        """
        self._resume.clear()
        self._auto_paused = True
        description = "\n".join(self._trigger_description(event) for event in triggers)
        self._open_pit_panel(
            description,
            resume_on_dismiss=True,
            preselected_driver=self._trigger_focus_driver(triggers),
        )

    def _open_pit_panel(
        self, description: str, resume_on_dismiss: bool, preselected_driver: int | None = None
    ) -> None:
        """Mostra il PitOrderPanel per i piloti del giocatore in gara.

        Se nessuna vettura del giocatore e' in pista non c'e' niente da
        decidere: la pausa resta, il pannello no. Alla chiusura: con
        una decisione il pit va in coda e la gara riprende; senza
        decisione riprende solo se resume_on_dismiss e' True.
        """
        drivers = tuple(
            (car.entry.driver.id, self._commentary_context.driver_name(car.entry.driver.id))
            for car in self._state.cars
            if car.entry.driver.id in self._player_driver_ids
        )
        if not drivers:
            return
        nominated = nominated_compounds(self._state.circuit)
        compounds = tuple(
            (nominated[slot], f"{_SLOT_LABELS[slot]} ({nominated[slot].value.upper()})")
            for slot in (CompoundSlot.SOFT, CompoundSlot.MEDIUM, CompoundSlot.HARD)
        ) + ((Compound.INTERMEDIATE, "Intermedia"), (Compound.WET, "Bagnato"))
        self._panel_open = True

        def on_close(decision: PitDecision | OpenOrdersRequest | None) -> None:
            self._panel_open = False
            if isinstance(decision, OpenOrdersRequest):
                # FOR-19: switch to the orders panel, the pause stays.
                self._open_orders_panel(resume_on_dismiss=resume_on_dismiss)
                return
            if isinstance(decision, PitDecision):
                self._pending_pits[decision.driver_id] = decision.compound
                self._resume_simulation()
            elif resume_on_dismiss:
                self._resume_simulation()
            else:
                self._update_header()

        panel = PitOrderPanel(
            description=description,
            drivers=drivers,
            compounds=compounds,
            preselected=nominated[CompoundSlot.MEDIUM],
            preselected_driver=preselected_driver,
        )
        self.app.push_screen(panel, on_close)

    def _open_orders_panel(self, resume_on_dismiss: bool) -> None:
        """Mostra il DriverOrdersPanel con lo stato corrente degli Ordini.

        Il pannello elenca entrambi i piloti del giocatore: chi e' in
        Abbandono resta visibile ma disabilitato, con il motivo. Alla
        chiusura: con una decisione gli Ordini diventano effettivi e la
        gara riprende; senza decisione riprende solo se
        resume_on_dismiss e' True.
        """
        if not self._player_driver_ids:
            return
        retired_ids = {car.entry.driver.id for car in self._state.dnfs}
        drivers = tuple(
            (
                driver_id,
                self._commentary_context.driver_name(driver_id),
                driver_id in retired_ids,
            )
            for driver_id in self._player_driver_ids
        )
        self._panel_open = True

        def on_close(decision: OrdersDecision | None) -> None:
            self._panel_open = False
            if decision is not None:
                self._apply_orders_decision(decision)
                self._resume_simulation()
            elif resume_on_dismiss:
                self._resume_simulation()
            else:
                self._update_header()

        panel = DriverOrdersPanel(
            drivers=drivers,
            current=dict(self._driver_orders),
            team_order=self._team_order,
        )
        self.app.push_screen(panel, on_close)

    def _apply_orders_decision(self, decision: OrdersDecision) -> None:
        """Rende effettivi gli Ordini confermati e da' il feedback radio.

        Ogni gruppo cambiato produce una conferma OrderConfirmed in
        Telecronaca; gli Ordini diventano input del motore dal prossimo
        Tick e la barra Ordini si aggiorna subito.
        """
        lap = self._state.lap
        confirmations: list[RaceEvent] = []
        current_aggression, current_duel = self._driver_orders.get(
            decision.driver_id, _DEFAULT_DRIVER_SETTINGS
        )
        if decision.aggression is not current_aggression:
            confirmations.append(
                OrderConfirmed(
                    lap=lap, driver_id=decision.driver_id, order=decision.aggression.value
                )
            )
        if decision.duel_instruction is not current_duel:
            confirmations.append(
                OrderConfirmed(
                    lap=lap, driver_id=decision.driver_id, order=decision.duel_instruction.value
                )
            )
        if decision.team_order is not self._team_order:
            order_value = (
                decision.team_order.value if decision.team_order is not None else TEAM_ORDER_LIFTED
            )
            confirmations.append(
                OrderConfirmed(lap=lap, driver_id=decision.driver_id, order=order_value)
            )
        self._driver_orders[decision.driver_id] = (decision.aggression, decision.duel_instruction)
        self._team_order = decision.team_order
        if confirmations:
            self._write_commentary(tuple(confirmations))
        self._update_orders_status()

    def _resume_simulation(self) -> None:
        """Riprende la simulazione esattamente da dove si era fermata."""
        self._auto_paused = False
        self._resume.set()
        self._update_header()

    def _trigger_description(self, event: RaceEvent) -> str:
        """La descrizione contestuale di un innesco di Auto-pausa."""
        if isinstance(event, SafetyCarDeployed):
            return "Safety car in pista: box ora a costo ridotto? Quale Mescola?"
        if isinstance(event, SafetyCarEnding):
            return "La Safety car rientra: ultima occasione di sosta scontata prima del verde."
        if isinstance(event, VscDeployed):
            return "VSC attivo: pit stop scontato finche' dura. Box ora?"
        if isinstance(event, VscEnding):
            return "Il VSC sta per finire: ultima chance di sosta scontata."
        if isinstance(event, RainStarted):
            return "Pioggia in arrivo: passare a gomme da bagnato?"
        if isinstance(event, RainStopped):
            return "La pioggia e' cessata: la pista si asciuga, valutare il rientro in slick."
        if isinstance(event, Crossover):
            label = _TYRE_CATEGORY_LABELS.get(event.to_category, event.to_category)
            return f"Crossover gomme: ora convengono {label}. Box per il cambio?"
        if isinstance(event, CarFailure):
            name = self._commentary_context.driver_name(event.driver_id)
            return f"Guasto per {name}: la sua vettura si ferma."
        if isinstance(event, UndercutWindow):
            attacker = self._commentary_context.driver_name(event.driver_id)
            target = self._commentary_context.driver_name(event.target_driver_id)
            if event.driver_id in self._player_driver_ids:
                return (
                    f"Finestra di undercut: {attacker} e' a {event.gap_seconds:.1f} secondi"
                    f" da {target}, una sosta immediata puo' valere la posizione. Box ora?"
                )
            return (
                f"Minaccia di undercut: {attacker} puo' fermarsi e scavalcare {target}."
                " Coprirsi con un pit stop?"
            )
        return "Evento chiave in pista: decidere ora."

    # ------------------------------------------------------------------
    # Commentary and live monitor
    # ------------------------------------------------------------------

    def _write_commentary(self, events: tuple[RaceEvent, ...]) -> None:
        """Le righe di Telecronaca degli eventi del Tick, in ordine.

        Ogni riga viene resa come Text. Gli avvenimenti che richiedono
        attenzione sono evidenziati in giallo (testo-giallo-su-problema): in
        quel caso l'intera riga prende il colore. Le righe ordinarie portano i
        nomi dei piloti colorati nei colori della rispettiva scuderia.
        """
        log = self.query_one("#commentary", RichLog)
        lines = narrate(events, self._commentary_context, self._commentary_rng)
        for event, line in zip(events, lines, strict=True):
            style = _commentary_line_style(event)
            if style is not None:
                log.write(Text(line, style=style))
            else:
                log.write(self._highlight_driver_names(line))

    def _highlight_driver_names(self, line: str) -> Text:
        """La riga di Telecronaca coi nomi dei piloti colorati per scuderia.

        Ogni pilota usa i colori della propria squadra (i piloti del giocatore
        restano col grassetto evidenziato). I nomi sono cercati per intero e
        con confine di parola, cosi' da non colorare per sbaglio porzioni di
        altre parole.
        """
        text = Text(line)
        for name, style in self._driver_name_styles:
            text.highlight_regex(rf"\b{re.escape(name)}\b", style)
        return text

    def _monitor_rows(self) -> list[tuple[str | Text, ...]]:
        """Le righe correnti del monitor: in gara prima, Abbandoni in coda.

        Due colonne di distacco: "Distacco" dal leader e "Dist. prec." dal
        pilota immediatamente davanti (la differenza tra righe consecutive,
        per leggere al volo se vale la pena tentare una strategia). Le righe
        delle vetture del giocatore sono evidenziate coi colori squadra (B03).
        A bandiera a scacchi esposta usa la classifica finale (penalita'
        bi-mescola incluse), con il distacco dal vincitore.
        """
        state = self._state
        rows: list[tuple[str | Text, ...]] = []
        if self._classification is not None:
            cars_by_id = {car.entry.driver.id: car for car in state.cars}
            previous_gap = 0.0
            for result in self._classification:
                car = cars_by_id[result.driver_id]
                if result.position == 1:
                    gap = _LEADER_GAP
                    interval = _LEADER_GAP
                else:
                    gap = f"+{result.gap_to_winner_seconds:.3f}"
                    interval = f"+{result.gap_to_winner_seconds - previous_gap:.3f}"
                previous_gap = result.gap_to_winner_seconds
                rows.append(self._car_row(str(result.position), car, gap, interval))
        else:
            previous_gap = 0.0
            for car in state.cars:
                if car.position == 1:
                    gap = _LEADER_GAP
                    interval = _LEADER_GAP
                else:
                    gap = f"+{car.gap_to_leader_seconds:.3f}"
                    interval = f"+{car.gap_to_leader_seconds - previous_gap:.3f}"
                previous_gap = car.gap_to_leader_seconds
                rows.append(self._car_row(str(car.position), car, gap, interval))
        # Retired cars at the bottom, most recent retirement first.
        for car in reversed(state.dnfs):
            rows.append(self._car_row(_EMPTY_CELL, car, _DNF_LABEL, _EMPTY_CELL))
        return rows

    def _car_row(
        self, position: str, car: CarRaceState, gap: str, interval: str
    ) -> tuple[str | Text, ...]:
        """La riga del monitor di una vettura.

        Le vetture del giocatore sono rese con i colori della squadra (B03):
        l'intera riga porta lo stile, le avversarie restano nel default.
        """
        compound = car.tyres.compound.value
        cells = [
            position,
            car.entry.driver.name,
            gap,
            interval,
            _COMPOUND_LABELS.get(compound, compound),
            f"{car.tyres.age_laps} giri",
        ]
        primary, secondary = self._team_colors.get(car.entry.driver.id, (None, None))
        highlight = self._player_style if car.entry.driver.id in self._player_driver_ids else None
        return tuple(
            row_with_team_colors(
                cells,
                name_index=1,
                primary_color=primary,
                secondary_color=secondary,
                highlight_style=highlight,
            )
        )

    def _refresh_monitor(self, force: bool = False) -> None:
        """Aggiorna il monitor cella per cella, con throttling temporale.

        Solo le celle cambiate vengono toccate; sotto l'intervallo
        minimo il refresh viene saltato del tutto (skip-to-event macina
        Tick molto piu' in fretta del limite).
        """
        now = time.monotonic()
        if not force and now - self._last_monitor_refresh < MONITOR_REFRESH_INTERVAL_SECONDS:
            return
        self._last_monitor_refresh = now
        table = self.query_one("#monitor", DataTable)
        for row_index, row in enumerate(self._monitor_rows()):
            for column_index, value in enumerate(row):
                if self._cells.get((row_index, column_index)) == value:
                    continue
                table.update_cell(
                    self._row_keys[row_index],
                    self._column_keys[column_index],
                    value,
                    update_width=True,
                )
                self._cells[(row_index, column_index)] = value

    def _header_text(self) -> str:
        state = self._state
        if state.finished:
            status = _STATUS_FINISHED
        elif self.is_auto_paused:
            status = _STATUS_AUTO_PAUSED
        elif self.is_paused:
            status = _STATUS_PAUSED
        elif self._skipping:
            status = _STATUS_SKIPPING
        else:
            status = f"{_STATUS_RUNNING} {self._speed}x"
        return (
            f"Gara: {self._commentary_context.circuit_name(state.circuit.code)}  |  "
            f"Giro {state.lap}/{state.total_laps}  |  {status}"
        )

    def _orders_status_text(self) -> str:
        """La barra Ordini: lo stato corrente per entrambi i piloti.

        Sempre visibile in gara (FOR-19); il pilota in Abbandono e'
        marcato come tale al posto dei suoi Ordini.
        """
        retired_ids = {car.entry.driver.id for car in self._state.dnfs}
        parts: list[str] = []
        for driver_id in self._player_driver_ids:
            name = self._commentary_context.driver_name(driver_id)
            if driver_id in retired_ids:
                parts.append(f"{name}: {_DNF_LABEL}")
                continue
            aggression, duel_instruction = self._driver_orders[driver_id]
            parts.append(
                f"{name}: {_AGGRESSION_LABELS[aggression]}, duelli"
                f" {_DUEL_LABELS[duel_instruction].lower()}"
            )
        team_label = (
            _TEAM_ORDER_LABELS[self._team_order]
            if self._team_order is not None
            else _NO_TEAM_ORDER_LABEL.lower()
        )
        parts.append(f"Scuderia: {team_label}")
        return "Ordini  |  " + "  |  ".join(parts)

    def _update_orders_status(self) -> None:
        self.query_one("#orders-status", Static).update(self._orders_status_text())

    def _update_header(self) -> None:
        self.query_one("#race-header", Static).update(self._header_text())
        self._update_orders_status()
