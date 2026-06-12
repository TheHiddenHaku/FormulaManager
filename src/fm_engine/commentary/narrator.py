"""Resa testuale degli eventi: selezione varianti e parametri (FOR-16).

La funzione pura narrate trasforma una sequenza di eventi del motore in
righe di Telecronaca in italiano. La scelta della variante e' affidata
all'RNG ricevuto (stesso seed, stesso testo) con una regola
anti-ripetizione: una variante gia' usata nelle ultime
REPETITION_WINDOW righe non viene riproposta.
"""

from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from random import Random

from fm_engine import events
from fm_engine.commentary.templates import TEMPLATES

# A template variant never reappears within this many subsequent lines.
# Every family in TEMPLATES has more variants than the window, so a free
# variant always exists.
REPETITION_WINDOW = 4

# Italian labels for the structured payload values coming from the
# engine. Fallback is the raw value, so an unmapped payload never breaks
# the commentary.
_COMPONENT_LABELS: dict[str, str] = {
    "engine": "il motore",
    "gearbox": "il cambio",
    "hydraulics": "l'impianto idraulico",
    "brakes": "l'impianto frenante",
    "electronics": "l'elettronica",
    "suspension": "la sospensione",
}

_ERROR_CAUSE_LABELS: dict[str, str] = {
    "braking_too_deep": "una staccata troppo profonda",
    "kerb_ride": "un cordolo preso male",
    "cold_tyres": "le gomme ancora fredde",
    "traffic_misjudged": "una valutazione sbagliata nel traffico",
}

_DNF_CAUSE_LABELS: dict[events.DnfCause, str] = {
    events.DnfCause.FAILURE: "un guasto meccanico",
    events.DnfCause.DRIVER_ERROR: "un errore di guida",
    events.DnfCause.ACCIDENT: "un incidente",
}

_SEVERITY_LABELS: dict[events.AccidentSeverity, str] = {
    events.AccidentSeverity.MINOR: "un contatto lieve",
    events.AccidentSeverity.MAJOR: "un incidente pesante",
}

# Tyre category of the Crossover events ("slick", "intermediate", "wet").
_TYRE_CATEGORY_LABELS: dict[str, str] = {
    "slick": "slick",
    "intermediate": "intermedie",
    "wet": "da bagnato",
}

# Order payload values of OrderConfirmed: enum values of Aggression,
# TeamOrder and DuelInstruction, plus the lifted-team-order marker.
_ORDER_LABELS: dict[str, str] = {
    "push": "spingere al massimo",
    "normal": "tornare al passo normale",
    "conserve": "conservare gomme e vettura",
    "swap_positions": "scambiare le posizioni con il compagno",
    "hold_positions": "congelare le posizioni in squadra",
    "no_attack": "non attaccare il compagno",
    "standard": "duellare senza istruzioni particolari",
    "defend_hard": "difendere duro la posizione",
    "no_risk": "non rischiare nei duelli",
    events.TEAM_ORDER_LIFTED: "tornare a correre liberi in squadra",
}

# Compound values of fm_engine.tyres.Compound, serialized as str.
_COMPOUND_LABELS: dict[str, str] = {
    "c1": "C1",
    "c2": "C2",
    "c3": "C3",
    "c4": "C4",
    "c5": "C5",
    "intermediate": "intermedie",
    "wet": "da bagnato",
}


@dataclass(frozen=True)
class CommentaryContext:
    """I nomi che la Telecronaca usa al posto degli id del motore."""

    driver_names: Mapping[int, str]
    team_names: Mapping[int, str] = field(default_factory=dict)
    circuit_names: Mapping[str, str] = field(default_factory=dict)

    def driver_name(self, driver_id: int) -> str:
        """Il nome del pilota, o un ripiego neutro se sconosciuto."""
        return self.driver_names.get(driver_id, f"il pilota {driver_id}")

    def team_name(self, team_id: int) -> str:
        """Il nome della squadra, o un ripiego neutro se sconosciuto."""
        return self.team_names.get(team_id, f"la squadra {team_id}")

    def circuit_name(self, circuit_code: str) -> str:
        """Il nome del circuito, o il codice stesso se sconosciuto."""
        return self.circuit_names.get(circuit_code, circuit_code)


def _format_lap_time(seconds: float) -> str:
    """Un tempo sul giro in stile cronometraggio: 1:23.456."""
    minutes, remainder = divmod(seconds, 60.0)
    if minutes >= 1.0:
        return f"{int(minutes)}:{remainder:06.3f}"
    return f"{remainder:.3f}"


def _format_seconds(seconds: float) -> str:
    """Una quantita' di secondi senza zeri inutili: 2.5, 10."""
    return f"{seconds:g}"


def _format_usd(amount_usd: int) -> str:
    """Un importo in dollari con separatore delle migliaia: 120.000."""
    return f"{amount_usd:,} dollari".replace(",", ".")


def _rain_intensity_label(intensity: float) -> str:
    """L'aggettivo per l'intensita' di pioggia, scala 0-1."""
    if intensity < 0.34:
        return "leggera"
    if intensity < 0.67:
        return "moderata"
    return "battente"


def _join_names(names: Iterable[str]) -> str:
    """Elenco in italiano: 'A', 'A e B', 'A, B e C'."""
    listed = list(names)
    if len(listed) <= 1:
        return "".join(listed)
    return ", ".join(listed[:-1]) + " e " + listed[-1]


def _race_started(event: events.RaceStarted, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "circuit": context.circuit_name(event.circuit_code),
        "total_laps": event.total_laps,
    }


def _overtake(event: events.Overtake, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "driver": context.driver_name(event.driver_id),
        "overtaken": context.driver_name(event.overtaken_driver_id),
        "position": event.position,
    }


def _team_order_swap(event: events.TeamOrderSwap, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "team": context.team_name(event.team_id),
        "promoted": context.driver_name(event.promoted_driver_id),
        "demoted": context.driver_name(event.demoted_driver_id),
        "position": event.position,
    }


def _fastest_lap(event: events.FastestLap, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "driver": context.driver_name(event.driver_id),
        "time": _format_lap_time(event.time_seconds),
    }


def _car_failure(event: events.CarFailure, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "driver": context.driver_name(event.driver_id),
        "component": _COMPONENT_LABELS.get(event.component, event.component),
    }


def _driver_error(event: events.DriverError, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "driver": context.driver_name(event.driver_id),
        "cause": _ERROR_CAUSE_LABELS.get(event.cause, event.cause),
        "time_lost": _format_seconds(event.time_lost_seconds),
    }


def _accident(event: events.Accident, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "drivers": _join_names(context.driver_name(d) for d in event.driver_ids),
        "severity_phrase": _SEVERITY_LABELS[event.severity],
    }


def _car_damage(event: events.CarDamage, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "driver": context.driver_name(event.driver_id),
        "amount": _format_usd(event.amount_usd),
    }


def _dnf(event: events.Dnf, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "driver": context.driver_name(event.driver_id),
        "cause": _DNF_CAUSE_LABELS[event.cause],
    }


def _lap_only(event: object, context: CommentaryContext) -> dict[str, object]:
    return {"lap": event.lap}  # type: ignore[attr-defined]


def _rain_started(event: events.RainStarted, context: CommentaryContext) -> dict[str, object]:
    return {"lap": event.lap, "intensity": _rain_intensity_label(event.intensity)}


def _crossover(event: events.Crossover, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "from_category": _TYRE_CATEGORY_LABELS.get(event.from_category, event.from_category),
        "to_category": _TYRE_CATEGORY_LABELS.get(event.to_category, event.to_category),
    }


def _undercut_window(event: events.UndercutWindow, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "driver": context.driver_name(event.driver_id),
        "target": context.driver_name(event.target_driver_id),
        "gap": f"{event.gap_seconds:.1f}",
    }


def _pit_entry(event: events.PitEntry, context: CommentaryContext) -> dict[str, object]:
    return {"lap": event.lap, "driver": context.driver_name(event.driver_id)}


def _tyre_change(event: events.TyreChange, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "driver": context.driver_name(event.driver_id),
        "old_compound": _COMPOUND_LABELS.get(event.old_compound, event.old_compound),
        "new_compound": _COMPOUND_LABELS.get(event.new_compound, event.new_compound),
    }


def _pit_exit(event: events.PitExit, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "driver": context.driver_name(event.driver_id),
        "time_lost": _format_seconds(event.time_lost_seconds),
    }


def _bi_compound_penalty(
    event: events.BiCompoundPenalty, context: CommentaryContext
) -> dict[str, object]:
    return {
        "lap": event.lap,
        "driver": context.driver_name(event.driver_id),
        "penalty": _format_seconds(event.penalty_seconds),
    }


def _order_confirmed(event: events.OrderConfirmed, context: CommentaryContext) -> dict[str, object]:
    return {
        "lap": event.lap,
        "driver": context.driver_name(event.driver_id),
        "order": _ORDER_LABELS.get(event.order, event.order),
    }


def _chequered_flag(event: events.ChequeredFlag, context: CommentaryContext) -> dict[str, object]:
    if event.classification:
        winner = context.driver_name(event.classification[0].driver_id)
    else:
        winner = "nessuno"
    return {"lap": event.lap, "winner": winner}


def _qualifying_time_set(
    event: events.QualifyingTimeSet, context: CommentaryContext
) -> dict[str, object]:
    return {
        "driver": context.driver_name(event.driver_id),
        "time": _format_lap_time(event.time_seconds),
        "segment": event.segment.value.upper(),
    }


def _qualifying_elimination(
    event: events.QualifyingElimination, context: CommentaryContext
) -> dict[str, object]:
    return {
        "driver": context.driver_name(event.driver_id),
        "segment": event.segment.value.upper(),
        "position": event.position,
    }


def _pole_position(event: events.PolePosition, context: CommentaryContext) -> dict[str, object]:
    return {
        "driver": context.driver_name(event.driver_id),
        "time": _format_lap_time(event.time_seconds),
    }


# Parameter builder per event type: same keys as TEMPLATES.
_PARAM_BUILDERS: dict[type, Callable[..., dict[str, object]]] = {
    events.RaceStarted: _race_started,
    events.Overtake: _overtake,
    events.TeamOrderSwap: _team_order_swap,
    events.FastestLap: _fastest_lap,
    events.CarFailure: _car_failure,
    events.DriverError: _driver_error,
    events.Accident: _accident,
    events.CarDamage: _car_damage,
    events.Dnf: _dnf,
    events.SafetyCarDeployed: _lap_only,
    events.SafetyCarEnding: _lap_only,
    events.VscDeployed: _lap_only,
    events.VscEnding: _lap_only,
    events.RainStarted: _rain_started,
    events.RainStopped: _lap_only,
    events.Crossover: _crossover,
    events.UndercutWindow: _undercut_window,
    events.PitEntry: _pit_entry,
    events.TyreChange: _tyre_change,
    events.PitExit: _pit_exit,
    events.BiCompoundPenalty: _bi_compound_penalty,
    events.OrderConfirmed: _order_confirmed,
    events.ChequeredFlag: _chequered_flag,
    events.QualifyingTimeSet: _qualifying_time_set,
    events.QualifyingElimination: _qualifying_elimination,
    events.PolePosition: _pole_position,
}


def _params(event: object, context: CommentaryContext) -> dict[str, object]:
    """I parametri di formattazione per l'evento dato."""
    builder = _PARAM_BUILDERS.get(type(event))
    if builder is None:
        raise ValueError(f"nessun template di Telecronaca per l'evento {type(event).__name__}")
    return builder(event, context)


def render_variants(event: object, context: CommentaryContext) -> tuple[str, ...]:
    """Tutte le varianti della famiglia dell'evento, gia' renderizzate.

    Esposta per ispezione e per i test di copertura: garantisce che ogni
    variante formatti senza errori con i parametri reali dell'evento.
    """
    family = type(event)
    variants = TEMPLATES.get(family)
    if variants is None:
        raise ValueError(f"nessun template di Telecronaca per l'evento {family.__name__}")
    params = _params(event, context)
    return tuple(variant.format(**params) for variant in variants)


def narrate(
    event_stream: Iterable[object],
    context: CommentaryContext,
    rng: Random,
) -> tuple[str, ...]:
    """Una riga di Telecronaca in italiano per ogni evento ricevuto.

    Funzione pura a meno dell'avanzamento dell'RNG: stessa sequenza di
    eventi e stesso seed producono esattamente lo stesso testo. Una
    variante usata nelle ultime REPETITION_WINDOW righe non viene
    riproposta.
    """
    recent: deque[tuple[type, int]] = deque(maxlen=REPETITION_WINDOW)
    lines: list[str] = []
    for event in event_stream:
        family = type(event)
        variants = TEMPLATES.get(family)
        if variants is None:
            raise ValueError(f"nessun template di Telecronaca per l'evento {family.__name__}")
        candidates = [index for index in range(len(variants)) if (family, index) not in recent]
        chosen = candidates[rng.randrange(len(candidates))]
        lines.append(variants[chosen].format(**_params(event, context)))
        recent.append((family, chosen))
    return tuple(lines)
