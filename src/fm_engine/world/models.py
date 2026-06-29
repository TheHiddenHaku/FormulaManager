"""Modelli del Mondo di inizio Carriera.

Dataclass immutabili (frozen) che descrivono cio' che produce
fm_engine.world.generation.generate: la Griglia (10 squadre AI piu' lo
slot del giocatore), il roster dei 22 piloti, i Motoristi con i rapporti
di fornitura, i Contratti iniziali e le personalita' di spesa delle AI.

Decisione di modellazione (FOR-4):
- I 22 piloti si distribuiscono cosi': 20 con Contratto iniziale nelle 10
  squadre AI (2 ciascuna) e 2 piloti liberi senza Contratto. Tutti hanno
  un ingaggio richiesto: insieme formano il roster da cui il giocatore
  scegliera' i suoi 2 piloti nel wizard di nuova Carriera (T1.3.2).
- Lo slot del giocatore nella Griglia porta solo l'identita' scelta alla
  creazione (nome e colori, T1.3.1): niente piloti, niente motore,
  niente attributi. Il resto arriva col wizard (T1.3.2).
- Una squadra AI produce il motore in proprio (engine_supplier_id is
  None, coerente con teams.engine_supplier_id NULL dello schema DB)
  oppure e' Cliente di un Motorista e ne condivide la Potenza motore.

Gli id sono interi progressivi per tipo di entita', validi solo dentro al
Mondo generato: la persistenza (T1.2.2) li rimappa su UUID.
"""

from dataclasses import dataclass

from fm_engine.world.nationalities import (
    DRIVER_NAMES,
    ENGINE_SUPPLIER_NAMES,
    NATIONALITY_WEIGHTS,
    TEAM_LIVERY_COLORS,
    TEAM_NAMES,
)

# The 6 visible driver attributes (CONTEXT.md, section Pilota). Potential
# is excluded on purpose: it is a hidden attribute.
DRIVER_ATTRIBUTES: tuple[str, ...] = (
    "one_lap_pace",
    "race_pace",
    "duels",
    "tyre_management",
    "wet_weather",
    "consistency",
)

# The 6 car attributes (CONTEXT.md, section Vettura).
CAR_ATTRIBUTES: tuple[str, ...] = (
    "engine_power",
    "downforce",
    "aero_efficiency",
    "mechanical_grip",
    "tyre_management",
    "reliability",
)

# The chassis philosophies allowed by the DB schema.
CHASSIS_PHILOSOPHIES: tuple[str, ...] = ("fast", "balanced", "technical")

# Development focuses of the AI spending personality (FOR-26).
SPENDING_FOCUSES: tuple[str, ...] = ("aero", "engine", "reliability")

# Internal team id reserved for the player team in Contract.team_id.
# AI teams use ids from 1 up; persistence maps this id onto the is_player
# row of the teams table.
PLAYER_TEAM_ID = 0


@dataclass(frozen=True)
class SpendingPersonality:
    """Profilo di spesa di una squadra AI.

    Le AI giocano con le stesse regole del giocatore: la personalita'
    guidera' le loro decisioni di sviluppo (Progetti, Mercato piloti).
    Parametri su scala 0-1, tarabili via WorldConfig.
    """

    profile: str
    # How much of the available cash the team tends to invest.
    spending_propensity: float
    # How much the team accepts projects with high outcome variance.
    risk_tolerance: float
    # Development focus: the attribute family the team favours (FOR-26).
    focus: str = "aero"


# Tunable starting profiles: generation assigns one to each AI team.
DEFAULT_PERSONALITIES: tuple[SpendingPersonality, ...] = (
    SpendingPersonality(profile="aggressive", spending_propensity=0.8, risk_tolerance=0.75),
    SpendingPersonality(profile="balanced", spending_propensity=0.5, risk_tolerance=0.5),
    SpendingPersonality(profile="cautious", spending_propensity=0.3, risk_tolerance=0.25),
)


@dataclass(frozen=True)
class EngineSupplier:
    """Produttore di motori indipendente, con nome di fantasia editabile.

    La Potenza motore e' condivisa da tutte le squadre Clienti; il canone
    annuale e' il costo della fornitura per ogni Cliente.
    """

    id: int
    name: str
    engine_power: int
    customer_fee_usd: int


@dataclass(frozen=True)
class Driver:
    """Pilota del roster iniziale.

    I 6 Attributi pilota sono su scala 0-100 e sono quelli che la TUI
    mostrera' come Stime. Il Potenziale e' un attributo nascosto, distinto
    dai 6: margine di crescita o declino, mai mostrato al giocatore.
    L'ingaggio richiesto serve al wizard (T1.3.2) e al Mercato piloti;
    per i contrattualizzati coincide con lo stipendio del Contratto.
    """

    id: int
    name: str
    # Lowercase ISO 3166-1 alpha-2 code (see nationalities.NATION_NAMES).
    nationality: str
    age: int
    one_lap_pace: int
    race_pace: int
    duels: int
    tyre_management: int
    wet_weather: int
    consistency: int
    # Hidden attribute: never listed among the visible ones.
    potential: int
    salary_demand_usd: int
    # Career retirement (FOR-31): True after a driver leaves the scene at the
    # end of a season. Ritirato resta nel roster come storia ma esce dal parco
    # attivo: i Contratti non lo selezionano piu' e il pool del Mercato lo
    # ignora (market.pool._is_active, market.roster._is_active).
    retired: bool = False

    @property
    def visible_attributes(self) -> dict[str, int]:
        """I soli 6 Attributi pilota visibili, senza il Potenziale."""
        return {name: getattr(self, name) for name in DRIVER_ATTRIBUTES}


@dataclass(frozen=True)
class Team:
    """Squadra AI della Griglia, con vettura, economia e personalita'.

    engine_supplier_id is None significa motore prodotto in proprio
    (coerente con teams.engine_supplier_id NULL nello schema DB);
    valorizzato significa squadra Cliente: in quel caso engine_power e'
    la copia della Potenza motore del Motorista fornitore.
    """

    id: int
    name: str
    prestige: int
    cash_usd: int
    chassis_philosophy: str
    engine_supplier_id: int | None
    engine_power: int
    downforce: int
    aero_efficiency: int
    mechanical_grip: int
    tyre_management: int
    reliability: int
    personality: SpendingPersonality
    # Livery colours (hex #rrggbb or colour name), shown next to the team
    # drivers in the TUI. Assigned at generation; None only in legacy data.
    primary_color: str | None = None
    secondary_color: str | None = None

    @property
    def builds_own_engine(self) -> bool:
        """True se la squadra non e' Cliente di nessun Motorista."""
        return self.engine_supplier_id is None


@dataclass(frozen=True)
class PlayerSlot:
    """Lo slot del giocatore nella Griglia: identita' piu' Setup squadra.

    Il flusso di nuova Carriera (T1.3.1) valorizza nome e colori della
    livrea; motore, Filosofia telaio e attributi vettura iniziali arrivano
    col wizard di Setup squadra (T1.3.2, fm_engine.world.team_setup) e
    restano None prima del wizard. I piloti del giocatore non vivono qui:
    sono Contratti con team_id = PLAYER_TEAM_ID. E' l'undicesimo slot
    della Griglia (replica della F1 2026, Cadillac come slot concettuale).
    I colori sono stringhe libere (esadecimale #rrggbb o nome colore),
    None se non scelti.
    """

    name: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    # Team setup choices (T1.3.2). chassis_philosophy is the marker:
    # None means the wizard has not completed yet.
    chassis_philosophy: str | None = None
    # None means own engine AFTER the setup; meaningless before (see is_set_up).
    engine_supplier_id: int | None = None
    engine_power: int | None = None
    downforce: int | None = None
    aero_efficiency: int | None = None
    mechanical_grip: int | None = None
    tyre_management: int | None = None
    reliability: int | None = None

    @property
    def is_set_up(self) -> bool:
        """True dopo il wizard di Setup squadra: la vettura iniziale esiste."""
        return self.chassis_philosophy is not None

    @property
    def car_attributes(self) -> dict[str, int]:
        """I 6 Attributi vettura iniziali, solo a Setup squadra completato."""
        if not self.is_set_up:
            raise ValueError("player slot not set up yet: no car attributes")
        return {name: getattr(self, name) for name in CAR_ATTRIBUTES}


@dataclass(frozen=True)
class Contract:
    """Contratto iniziale squadra AI - pilota: durata 1-3 stagioni.

    Lo stipendio pesa solo sulla Cassa, escluso dal Cap (CONTEXT.md).
    """

    driver_id: int
    team_id: int
    start_season: int
    duration_seasons: int
    salary_usd: int


@dataclass(frozen=True)
class WorldConfig:
    """Parametri di generazione del Mondo, con default sensati e tarabili.

    Tutti i valori numerici di partenza (range attributi, distribuzioni,
    pesi nazionalita', pool di nomi) vivono qui: la generazione non
    hardcoda nulla. I range sono tuple (minimo, massimo) inclusive.
    """

    initial_season: int = 2026
    ai_team_count: int = 10
    drivers_per_team: int = 2
    free_agents: int = 2
    min_engine_suppliers: int = 3
    max_engine_suppliers: int = 4
    age_range: tuple[int, int] = (18, 40)
    # Mode of the triangular age distribution: drivers cluster around this
    # age, with tails towards both ends of the range.
    age_mode: int = 26
    # Share of generated drivers that are women (the rest are men). Scelta di
    # gioco esplicita: i piloti possono essere uomini o donne, e il nome
    # generato e' coerente col genere estratto. Tarabile; il default tiene le
    # donne in minoranza ma ben presenti nel roster e nei Giovani.
    female_probability: float = 0.3
    driver_attribute_range: tuple[int, int] = (40, 92)
    potential_range: tuple[int, int] = (20, 95)
    car_attribute_range: tuple[int, int] = (40, 85)
    prestige_range: tuple[int, int] = (30, 80)
    cash_usd_range: tuple[int, int] = (20_000_000, 60_000_000)
    contract_duration_range: tuple[int, int] = (1, 3)
    salary_demand_usd_range: tuple[int, int] = (2_000_000, 25_000_000)
    customer_fee_usd_range: tuple[int, int] = (10_000_000, 18_000_000)
    nationality_weights: tuple[tuple[str, int], ...] = NATIONALITY_WEIGHTS
    team_names: tuple[str, ...] = TEAM_NAMES
    team_livery_colors: tuple[tuple[str, str], ...] = TEAM_LIVERY_COLORS
    engine_supplier_names: tuple[str, ...] = ENGINE_SUPPLIER_NAMES
    chassis_philosophies: tuple[str, ...] = CHASSIS_PHILOSOPHIES
    available_personalities: tuple[SpendingPersonality, ...] = DEFAULT_PERSONALITIES
    spending_focuses: tuple[str, ...] = SPENDING_FOCUSES
    # --- Ricambio generazionale (FOR-31), tarabili (tuning a FOR-34) ---
    # Eta' di picco: sotto si cresce, sopra si declina. La spinta di crescita
    # scala col Potenziale nascosto; il declino col superamento del picco.
    peak_age: int = 28
    # Eta' da cui i Ritiri di carriera diventano possibili (mai obbligatori).
    retirement_age: int = 33
    # Probabilita' base di Ritiro al raggiungimento di retirement_age, piu' un
    # incremento per ogni anno oltre la soglia, con un tetto: gli anziani si
    # ritirano spesso ma mai con certezza (esistono stagioni senza Ritiri).
    retirement_base_probability: float = 0.08
    retirement_probability_per_year: float = 0.06
    retirement_probability_cap: float = 0.6
    # I Giovani entrano nel range eta' basso e con un Potenziale tendenzialmente
    # alto (margine di crescita). Il range eta' dei Giovani e' un sotto-range.
    youngster_age_range: tuple[int, int] = (18, 23)
    youngster_potential_range: tuple[int, int] = (55, 95)
    # Dimensione obiettivo del parco attivo: la Griglia piena piu' una riserva
    # di liberi. La generazione di Giovani riporta il parco a questa soglia.
    active_pool_target: int = 24

    @property
    def total_drivers(self) -> int:
        """Il roster completo: contrattualizzati nelle squadre AI piu' liberi."""
        return self.ai_team_count * self.drivers_per_team + self.free_agents

    def __post_init__(self) -> None:
        if self.ai_team_count < 1:
            raise ValueError("ai_team_count must be at least 1")
        if self.drivers_per_team < 1:
            raise ValueError("drivers_per_team must be at least 1")
        if self.free_agents < 0:
            raise ValueError("free_agents cannot be negative")
        if not 1 <= self.min_engine_suppliers <= self.max_engine_suppliers:
            raise ValueError("requires 1 <= min_engine_suppliers <= max_engine_suppliers")
        # Every engine supplier needs at least one customer, and at least
        # one team must build its own engine.
        if self.ai_team_count < self.max_engine_suppliers + 1:
            raise ValueError(
                "at least max_engine_suppliers + 1 AI teams are required: one "
                "customer per supplier plus one team building its own engine"
            )
        for range_name in (
            "age_range",
            "driver_attribute_range",
            "potential_range",
            "car_attribute_range",
            "prestige_range",
            "cash_usd_range",
            "contract_duration_range",
            "salary_demand_usd_range",
            "customer_fee_usd_range",
            "youngster_age_range",
            "youngster_potential_range",
        ):
            minimum, maximum = getattr(self, range_name)
            if minimum > maximum:
                raise ValueError(f"{range_name}: minimum {minimum} > maximum {maximum}")
        if not self.age_range[0] <= self.age_mode <= self.age_range[1]:
            raise ValueError("age_mode must fall within age_range")
        if not 0.0 <= self.female_probability <= 1.0:
            raise ValueError("female_probability must be a probability in [0, 1]")
        # peak_age e retirement_age sono indipendenti dal range eta' iniziale
        # (descrivono la curva di carriera, non la generazione iniziale): si
        # vincola solo la coerenza interna fra picco e Ritiro.
        if self.retirement_age < self.peak_age:
            raise ValueError("retirement_age must be at least peak_age")
        # Le coorti dei Giovani (FOR-31) hanno range propri, indipendenti dai
        # range di generazione iniziale: basta che siano ben formati (min<=max,
        # gia' controllato sopra).
        if not 0.0 <= self.retirement_base_probability <= 1.0:
            raise ValueError("retirement_base_probability must be a probability in [0, 1]")
        if self.retirement_probability_per_year < 0.0:
            raise ValueError("retirement_probability_per_year cannot be negative")
        if not 0.0 <= self.retirement_probability_cap <= 1.0:
            raise ValueError("retirement_probability_cap must be a probability in [0, 1]")
        if self.active_pool_target < self.ai_team_count * self.drivers_per_team:
            raise ValueError("active_pool_target must cover at least the full grid")
        if len(self.team_names) < self.ai_team_count:
            raise ValueError("not enough team_names for the configured AI teams")
        if len(self.team_livery_colors) < self.ai_team_count:
            raise ValueError("not enough team_livery_colors for the configured AI teams")
        if len(self.engine_supplier_names) < self.max_engine_suppliers:
            raise ValueError("not enough engine_supplier_names for the configured suppliers")
        if not self.nationality_weights:
            raise ValueError("nationality_weights cannot be empty")
        for nation, weight in self.nationality_weights:
            if weight <= 0:
                raise ValueError(f"non-positive weight for nationality {nation}")
            if nation not in DRIVER_NAMES:
                raise ValueError(f"no name pool for nationality {nation}")
        if not self.chassis_philosophies:
            raise ValueError("chassis_philosophies cannot be empty")
        if not self.available_personalities:
            raise ValueError("available_personalities cannot be empty")
        if not self.spending_focuses:
            raise ValueError("spending_focuses cannot be empty")


@dataclass(frozen=True)
class World:
    """Il Mondo completo di inizio Carriera prodotto da generate(seed, config).

    La Griglia e' ai_teams (10) piu' player_slot (vuoto, 11 slot in
    tutto). I contratti legano 20 dei 22 piloti alle squadre AI; i piloti
    senza Contratto sono i liberi del roster.
    """

    seed: int
    config: WorldConfig
    ai_teams: tuple[Team, ...]
    player_slot: PlayerSlot
    drivers: tuple[Driver, ...]
    engine_suppliers: tuple[EngineSupplier, ...]
    contracts: tuple[Contract, ...]

    @property
    def drivers_without_contract(self) -> tuple[Driver, ...]:
        """I piloti liberi del roster, senza Contratto iniziale."""
        contracted = {contract.driver_id for contract in self.contracts}
        return tuple(driver for driver in self.drivers if driver.id not in contracted)

    def contracts_of(self, team_id: int) -> tuple[Contract, ...]:
        """I Contratti della squadra indicata."""
        return tuple(c for c in self.contracts if c.team_id == team_id)
