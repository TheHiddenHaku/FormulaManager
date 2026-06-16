"""La transizione di stagione: orchestrazione della fase inverno (FOR-32).

Mette in fila i cinque pezzi dell'inverno su un World e un TeamLedger
immutabili (motore puro ADR 0002), nell'ordine in cui hanno senso:

1. CARRY-OVER: tutta la Griglia regredisce verso la media (carryover.py).
2. RINEGOZIAZIONE: le scelte di fondo del giocatore (motore, Filosofia
   telaio) cambiano gli effetti sulla vettura della stagione nuova
   (renegotiation.py). Default: invariate.
3. PROGETTI INVERNALI: gli sviluppi scelti dal giocatore col budget
   dedicato si sommano alla vettura (projects.py). Default: nessuno.
4. ROLLOVER ECONOMICO: nuovo Cap (con eventuale penalita' da Sforamento),
   Cassa riportata e Sponsor annuale dal Prestigio (economy esistente).

Il Mercato piloti (apply_market) NON vive qui: e' gia' agganciato nel
flusso TUI di fine stagione, prima della transizione, e muta i Contratti.
La transizione si concentra su vettura ed economia, cosi' i due pezzi
restano disaccoppiati.

WinterDecisions raccoglie le scelte del giocatore; senza decisioni la
transizione applica comunque Carry-over e rollover con i DEFAULT espliciti
(scelte di fondo invariate, nessun Progetto invernale). L'entry point e'
advance_winter(...): ritorna lo stato della stagione nuova (World, ledger).
"""

from dataclasses import dataclass, replace

from fm_engine.economy import (
    DEFAULT_PLAYER_PRESTIGE,
    TeamLedger,
    credit_annual_sponsor,
    start_next_season,
)
from fm_engine.season.clock import season_start_date
from fm_engine.winter.carryover import CarryoverConfig, apply_carryover
from fm_engine.winter.projects import (
    WinterProject,
    WinterProjectConfig,
    apply_winter_projects,
    validate_selection,
)
from fm_engine.winter.renegotiation import (
    RenegotiationChoices,
    apply_renegotiation,
)
from fm_engine.world.models import World
from fm_engine.world.team_setup import TeamSetupConfig


@dataclass(frozen=True)
class WinterConfig:
    """I parametri tarabili della fase inverno, raccolti in un solo posto."""

    carryover: CarryoverConfig = CarryoverConfig()
    projects: WinterProjectConfig = WinterProjectConfig()
    team_setup: TeamSetupConfig = TeamSetupConfig()
    player_prestige: int = DEFAULT_PLAYER_PRESTIGE


@dataclass(frozen=True)
class WinterDecisions:
    """Le scelte del giocatore per l'inverno; tutte facoltative (default sotto).

    renegotiation None = scelte di fondo invariate rispetto all'anno
    concluso. winter_projects vuota = nessun Progetto invernale. Con
    WinterDecisions() (default) l'inverno applica solo Carry-over e rollover.
    """

    renegotiation: RenegotiationChoices | None = None
    winter_projects: tuple[WinterProject, ...] = ()


@dataclass(frozen=True)
class WinterOutcome:
    """Lo stato della stagione nuova prodotto dalla transizione."""

    world: World
    ledger: TeamLedger
    # Spesa dei Progetti invernali (dal budget dedicato), per i testi UI.
    winter_spend_usd: int


def _player_car_after_winter(
    world: World,
    decisions: WinterDecisions,
    config: WinterConfig,
) -> tuple[World, int]:
    """Applica rinegoziazione e Progetti invernali alla vettura del giocatore.

    Opera sulla vettura GIA' regredita dal Carry-over. Ritorna il World con
    lo slot aggiornato (attributi, motore, Filosofia) e la spesa invernale.
    Se la squadra non e' configurata non c'e' nulla da fare (spesa zero).
    """
    slot = world.player_slot
    if not slot.is_set_up:
        return world, 0

    attributes = slot.car_attributes
    engine_supplier_id = slot.engine_supplier_id
    chassis_philosophy = slot.chassis_philosophy
    suppliers = {supplier.id: supplier for supplier in world.engine_suppliers}

    # 2. Rinegoziazione delle scelte di fondo (default: invariate).
    if decisions.renegotiation is not None:
        attributes = apply_renegotiation(
            attributes,
            chassis_philosophy,
            engine_supplier_id,
            decisions.renegotiation,
            suppliers,
            config.team_setup,
        )
        engine_supplier_id = decisions.renegotiation.engine_supplier_id
        chassis_philosophy = decisions.renegotiation.chassis_philosophy

    # 3. Progetti invernali (default: nessuno).
    is_engine_customer = engine_supplier_id is not None
    winter_spend = 0
    if decisions.winter_projects:
        winter_spend = validate_selection(
            decisions.winter_projects, is_engine_customer, config.projects
        )
        attributes = apply_winter_projects(
            attributes, decisions.winter_projects, is_engine_customer, config.projects
        )

    slot = replace(
        slot,
        chassis_philosophy=chassis_philosophy,
        engine_supplier_id=engine_supplier_id,
        **attributes,
    )
    return replace(world, player_slot=slot), winter_spend


def advance_winter(
    world: World,
    ledger: TeamLedger,
    concluded_year: int,
    decisions: WinterDecisions | None = None,
    config: WinterConfig | None = None,
) -> WinterOutcome:
    """Applica la fase inverno e ritorna lo stato della stagione nuova.

    Ordine: Carry-over su tutta la Griglia, poi rinegoziazione e Progetti
    invernali sulla vettura del giocatore, infine rollover economico (nuovo
    Cap con penalita' da Sforamento, Cassa riportata, Sponsor annuale dal
    Prestigio). Senza decisioni (None o default) applica Carry-over e
    rollover con i DEFAULT dichiarati: scelte di fondo invariate, nessun
    Progetto invernale.

    Non tocca i Contratti (il Mercato piloti vive a monte, apply_market): la
    transizione e' su vettura ed economia. World e ledger in ingresso restano
    intatti (frozen). Tutto e' deterministico: nessuna estrazione casuale qui.
    """
    if decisions is None:
        decisions = WinterDecisions()
    if config is None:
        config = WinterConfig()

    # 1. Carry-over: tutta la Griglia regredisce verso la media.
    world = apply_carryover(world, config.carryover)

    # 2-3. Rinegoziazione e Progetti invernali sulla vettura del giocatore.
    world, winter_spend = _player_car_after_winter(world, decisions, config)

    # 4. Rollover economico: nuovo Cap (penalita' da Sforamento), Cassa
    #    riportata, poi Sponsor annuale della stagione nuova.
    next_year = concluded_year + 1
    season_start = season_start_date(next_year)
    new_ledger = start_next_season(ledger, season_start)
    new_ledger = credit_annual_sponsor(new_ledger, config.player_prestige, season_start)

    return WinterOutcome(world=world, ledger=new_ledger, winter_spend_usd=winter_spend)
