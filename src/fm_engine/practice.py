"""Prove libere con Programmi (FOR-20).

Per ogni sessione di libere (FP1, FP2, FP3) il manager assegna a
ciascun suo pilota un Programma: Setup, Gomme, Focus qualifica, Passo
gara o Strategia. Gli effetti si cumulano nel weekend in PracticeEffects:

- Setup: alza la percentuale di setup del pilota (rendimenti
  decrescenti); il setup mancante costa tempo sul giro, in libere e
  nelle sessioni successive (setup_deficit_seconds).
- Gomme: rivela le curve di Degrado delle Mescole nominate provate,
  dalla piu' morbida, due per sessione (revealed_degradation_rates).
- Focus qualifica / Passo gara: bonus di passo in secondi, con tetto,
  valido per la sessione corrispondente del weekend
  (qualifying_adjustment_seconds, race_adjustment_seconds).
- Strategia: alza il livello di lettura strategica della squadra e
  sblocca il numero di soste consigliato (suggested_stop_count).

Un pilota senza Programma riceve il default (Setup) e il report lo
segnala. La Classifica tempi della sessione e' esatta per tutte le 22
vetture (il cronometro non mente mai); i tempi dei piloti del manager
riflettono il Programma svolto e il setup raggiunto. Motore puro (ADR
0002), deterministico a parita' di seed; costanti tarabili con
l'harness di bilanciamento (T2.4.1). Il cablaggio dei bonus dentro
Qualifiche e gara arriva con la macchina a stati del weekend (FOR-21).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from random import Random

from fm_engine.circuits import Circuit
from fm_engine.laptime import lap_time_seconds
from fm_engine.pitstop import PIT_STOP_BASE_SECONDS
from fm_engine.state import Aggression, RaceEntry, TimesheetRow
from fm_engine.tyres import (
    COMPOUND_DEGRADATION_RATE_SECONDS_PER_LAP,
    Compound,
    CompoundSlot,
    nominated_compounds,
    severity_factor,
)
from fm_engine.weather import SessionForecast, session_forecast


class PracticeProgramme(Enum):
    """Un Programma di prove libere assegnabile a un pilota."""

    SETUP = "setup"
    TYRES = "tyres"
    QUALIFYING_FOCUS = "qualifying_focus"
    RACE_PACE = "race_pace"
    STRATEGY = "strategy"


# Programme applied when the manager launches the session without one.
DEFAULT_PROGRAMME = PracticeProgramme.SETUP


class PracticeSession(Enum):
    """Una sessione di prove libere del Formato weekend standard."""

    FP1 = "fp1"
    FP2 = "fp2"
    FP3 = "fp3"


# The practice sessions of the standard weekend, in running order.
PRACTICE_SESSIONS: tuple[PracticeSession, ...] = (
    PracticeSession.FP1,
    PracticeSession.FP2,
    PracticeSession.FP3,
)

# Offset that separates each session's RNG stream from the race laps
# (seed*1_000_003+lap), qualifying and forecast streams.
_PRACTICE_SEED_OFFSET = 11_000_027

# Setup starts at a workable baseline and every Setup programme closes
# a share of the remaining gap to 100%: diminishing returns.
INITIAL_SETUP_PERCENTAGE = 30.0
SETUP_GAIN_SHARE_RANGE = (0.35, 0.55)
# Missing setup costs lap time: seconds per missing percentage point.
SETUP_PACE_SECONDS_PER_POINT = 0.005

# Weekend pace bonuses, in seconds per lap, stacking up to a cap.
QUALIFYING_FOCUS_BONUS_SECONDS = 0.10
QUALIFYING_BONUS_CAP_SECONDS = 0.20
RACE_PACE_BONUS_SECONDS = 0.06
RACE_PACE_BONUS_CAP_SECONDS = 0.12

# Tyre programme: nominated compounds revealed per session, softest first.
COMPOUNDS_REVEALED_PER_PROGRAMME = 2
# Strategy programme: insight levels, capped.
STRATEGY_INSIGHT_CAP = 2
# Stop counts evaluated by the strategy suggestion (dry race: at least 1).
_SUGGESTED_STOPS_RANGE = (1, 2, 3)

# Best lap attempts per driver per session.
RUNS_PER_SESSION = 3
# Headline time offset of each programme: who chases the lap is faster,
# who runs long stints or experiments leaves time on the table.
PROGRAMME_HEADLINE_OFFSET_SECONDS: dict[PracticeProgramme, float] = {
    PracticeProgramme.SETUP: 0.20,
    PracticeProgramme.TYRES: 0.50,
    PracticeProgramme.QUALIFYING_FOCUS: -0.15,
    PracticeProgramme.RACE_PACE: 0.50,
    PracticeProgramme.STRATEGY: 0.35,
}
# Mixed running assumed for the cars the manager does not control.
AI_HEADLINE_OFFSET_SECONDS = 0.25


@dataclass(frozen=True)
class DriverPracticeEffects:
    """Gli effetti cumulati dei Programmi su un singolo pilota."""

    setup_percentage: float = INITIAL_SETUP_PERCENTAGE
    qualifying_bonus_seconds: float = 0.0
    race_pace_bonus_seconds: float = 0.0


_DEFAULT_DRIVER_EFFECTS = DriverPracticeEffects()


@dataclass(frozen=True)
class PracticeEffects:
    """Gli effetti dei Programmi validi per il weekend, cumulati per sessione.

    Mappatura sparsa come Orders: i piloti assenti partono dai default
    (setup alla baseline, nessun bonus). revealed_compounds e
    strategy_insight sono patrimonio di squadra, non del singolo pilota.
    """

    drivers: Mapping[int, DriverPracticeEffects] = field(default_factory=dict)
    revealed_compounds: frozenset[Compound] = frozenset()
    strategy_insight: int = 0

    def for_driver(self, driver_id: int) -> DriverPracticeEffects:
        """Gli effetti cumulati sul pilota indicato, o i default."""
        return self.drivers.get(driver_id, _DEFAULT_DRIVER_EFFECTS)


@dataclass(frozen=True)
class ProgrammeReport:
    """L'esito del Programma di un pilota a fine sessione.

    defaulted segnala che il Programma e' stato applicato d'ufficio
    perche' il manager ha lanciato la sessione senza assegnarlo. I campi
    di bonus e setup sono i totali cumulati DOPO la sessione.
    """

    driver_id: int
    programme: PracticeProgramme
    defaulted: bool
    setup_percentage: float
    setup_gain: float
    newly_revealed: tuple[Compound, ...]
    qualifying_bonus_seconds: float
    race_pace_bonus_seconds: float
    strategy_insight: int
    suggested_stops: int | None


@dataclass(frozen=True)
class PracticeSessionResult:
    """L'esito completo di una sessione di libere.

    classification e' la Classifica tempi esatta delle 22 vetture;
    reports racconta gli effetti ottenuti dai piloti del manager;
    effects e' lo stato cumulato del weekend dopo la sessione, da
    passare alla sessione successiva.
    """

    session: PracticeSession
    circuit: Circuit
    forecast: SessionForecast
    classification: tuple[TimesheetRow, ...]
    reports: tuple[ProgrammeReport, ...]
    effects: PracticeEffects


def setup_deficit_seconds(effects: PracticeEffects, driver_id: int) -> float:
    """Quanto costa sul giro il setup mancante del pilota indicato."""
    missing = 100.0 - effects.for_driver(driver_id).setup_percentage
    return missing * SETUP_PACE_SECONDS_PER_POINT


def qualifying_adjustment_seconds(effects: PracticeEffects, driver_id: int) -> float:
    """La correzione di passo in Qualifica: deficit di setup meno bonus.

    Negativa = piu' veloce. Il cablaggio dentro simulate_qualifying
    arriva con la macchina a stati del weekend (FOR-21).
    """
    return (
        setup_deficit_seconds(effects, driver_id)
        - effects.for_driver(driver_id).qualifying_bonus_seconds
    )


def race_adjustment_seconds(effects: PracticeEffects, driver_id: int) -> float:
    """La correzione di passo in gara: deficit di setup meno bonus."""
    return (
        setup_deficit_seconds(effects, driver_id)
        - effects.for_driver(driver_id).race_pace_bonus_seconds
    )


def revealed_degradation_rates(effects: PracticeEffects, circuit: Circuit) -> dict[Compound, float]:
    """Le curve di Degrado rivelate: secondi per giro di eta', sul circuito.

    Tasso base della Mescola per la severita' del circuito: la quota
    che dipende da vettura e pilota resta una Stima.
    """
    factor = severity_factor(circuit)
    return {
        compound: COMPOUND_DEGRADATION_RATE_SECONDS_PER_LAP[compound] * factor
        for compound in sorted(effects.revealed_compounds, key=lambda c: c.value)
    }


def suggested_stop_count(circuit: Circuit) -> int:
    """Il numero di soste consigliato dalla lettura strategica.

    Aritmetica pura sulle curve di Degrado della Mescola media nominata:
    per ogni numero di soste, costo = soste per il costo medio del pit
    stop piu' il Degrado cumulato sugli stint uguali. Gara asciutta:
    almeno una sosta (obbligo bi-mescola).
    """
    medium = nominated_compounds(circuit)[CompoundSlot.MEDIUM]
    rate = COMPOUND_DEGRADATION_RATE_SECONDS_PER_LAP[medium] * severity_factor(circuit)
    best_stops, best_cost = 1, float("inf")
    for stops in _SUGGESTED_STOPS_RANGE:
        stints = stops + 1
        stint_laps = circuit.race_laps / stints
        degradation = stints * rate * stint_laps * (stint_laps - 1) / 2
        cost = stops * PIT_STOP_BASE_SECONDS + degradation
        if cost < best_cost:
            best_stops, best_cost = stops, cost
    return best_stops


def _session_rng(session: PracticeSession, seed: int) -> Random:
    """L'RNG della sessione, su uno stream separato da gara e Qualifiche."""
    index = PRACTICE_SESSIONS.index(session) + 1
    return Random(seed * 1_000_003 + _PRACTICE_SEED_OFFSET * index)


def _tyres_to_reveal(circuit: Circuit, revealed: set[Compound]) -> tuple[Compound, ...]:
    """Le prossime Mescole nominate da provare, dalla piu' morbida."""
    nominated = nominated_compounds(circuit)
    softest_first = (
        nominated[CompoundSlot.SOFT],
        nominated[CompoundSlot.MEDIUM],
        nominated[CompoundSlot.HARD],
    )
    pending = [compound for compound in softest_first if compound not in revealed]
    return tuple(pending[:COMPOUNDS_REVEALED_PER_PROGRAMME])


def simulate_practice_session(
    entries: tuple[RaceEntry, ...],
    circuit: Circuit,
    session: PracticeSession,
    assignments: Mapping[int, PracticeProgramme | None],
    seed: int,
    effects: PracticeEffects | None = None,
) -> PracticeSessionResult:
    """Simula una sessione di libere e cumula gli effetti del weekend.

    assignments mappa i piloti del manager al loro Programma; None vale
    Programma di default, segnalato nel report. Gli altri piloti girano
    con programmi misti e fanno solo tempo. Deterministica a parita' di
    seed e assegnazioni: l'RNG deriva da (seed, sessione).
    """
    if effects is None:
        effects = PracticeEffects()
    known_ids = {entry.driver.id for entry in entries}
    unknown = sorted(set(assignments) - known_ids)
    if unknown:
        raise ValueError(f"assignments for drivers not in the session: {unknown}")

    rng = _session_rng(session, seed)
    driver_effects = dict(effects.drivers)
    revealed = set(effects.revealed_compounds)
    insight = effects.strategy_insight
    reports: list[ProgrammeReport] = []
    resolved: dict[int, PracticeProgramme] = {}

    # Programme effects first, in driver id order: the draw sequence
    # stays deterministic for a given seed and set of assignments.
    for driver_id in sorted(assignments):
        assigned = assignments[driver_id]
        defaulted = assigned is None
        programme = assigned or DEFAULT_PROGRAMME
        resolved[driver_id] = programme
        current = effects.for_driver(driver_id)
        setup_percentage = current.setup_percentage
        qualifying_bonus = current.qualifying_bonus_seconds
        race_pace_bonus = current.race_pace_bonus_seconds
        setup_gain = 0.0
        newly_revealed: tuple[Compound, ...] = ()
        if programme is PracticeProgramme.SETUP:
            share = rng.uniform(*SETUP_GAIN_SHARE_RANGE)
            setup_gain = (100.0 - setup_percentage) * share
            setup_percentage = min(setup_percentage + setup_gain, 100.0)
        elif programme is PracticeProgramme.TYRES:
            newly_revealed = _tyres_to_reveal(circuit, revealed)
            revealed.update(newly_revealed)
        elif programme is PracticeProgramme.QUALIFYING_FOCUS:
            qualifying_bonus = min(
                qualifying_bonus + QUALIFYING_FOCUS_BONUS_SECONDS,
                QUALIFYING_BONUS_CAP_SECONDS,
            )
        elif programme is PracticeProgramme.RACE_PACE:
            race_pace_bonus = min(
                race_pace_bonus + RACE_PACE_BONUS_SECONDS,
                RACE_PACE_BONUS_CAP_SECONDS,
            )
        elif programme is PracticeProgramme.STRATEGY:
            insight = min(insight + 1, STRATEGY_INSIGHT_CAP)
        driver_effects[driver_id] = DriverPracticeEffects(
            setup_percentage=setup_percentage,
            qualifying_bonus_seconds=qualifying_bonus,
            race_pace_bonus_seconds=race_pace_bonus,
        )
        reports.append(
            ProgrammeReport(
                driver_id=driver_id,
                programme=programme,
                defaulted=defaulted,
                setup_percentage=setup_percentage,
                setup_gain=setup_gain,
                newly_revealed=newly_revealed,
                qualifying_bonus_seconds=qualifying_bonus,
                race_pace_bonus_seconds=race_pace_bonus,
                strategy_insight=insight,
                suggested_stops=suggested_stop_count(circuit) if insight > 0 else None,
            )
        )

    new_effects = PracticeEffects(
        drivers=driver_effects,
        revealed_compounds=frozenset(revealed),
        strategy_insight=insight,
    )

    # The exact timesheet: best of RUNS_PER_SESSION attempts on the one
    # lap pace, plus the running profile of the programme and, for the
    # manager's drivers, the cost of the setup still missing.
    best_times: dict[int, float] = {}
    for entry in entries:
        best = min(
            lap_time_seconds(
                entry,
                circuit,
                Aggression.NORMAL,
                rng,
                pace_attribute="one_lap_pace",
            )
            for _ in range(RUNS_PER_SESSION)
        )
        driver_id = entry.driver.id
        if driver_id in resolved:
            best += PROGRAMME_HEADLINE_OFFSET_SECONDS[resolved[driver_id]]
            best += setup_deficit_seconds(new_effects, driver_id)
        else:
            best += AI_HEADLINE_OFFSET_SECONDS
        best_times[driver_id] = best

    ranked = sorted(entries, key=lambda entry: best_times[entry.driver.id])
    classification = tuple(
        TimesheetRow(
            position=position,
            driver_id=entry.driver.id,
            time_seconds=best_times[entry.driver.id],
        )
        for position, entry in enumerate(ranked, start=1)
    )

    return PracticeSessionResult(
        session=session,
        circuit=circuit,
        forecast=session_forecast(circuit, seed),
        classification=classification,
        reports=tuple(reports),
        effects=new_effects,
    )
