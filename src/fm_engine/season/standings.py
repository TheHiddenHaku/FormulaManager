"""Classifiche piloti e costruttori con tie-break a piazzamenti (T5.1.1).

Le classifiche si ricostruiscono per somma dai risultati dei GP disputati
(RoundResult). A parita' di punti vige il countback: conta chi ha i
piazzamenti migliori (piu' vittorie, poi piu' secondi posti, e cosi'
via), come nella F1 reale. L'ultimo discrimine e' l'id (stabile e
deterministico), cosi' l'ordine non oscilla mai e i piloti a zero punti
prima del primo GP compaiono comunque in un ordine fisso.

Le funzioni ricevono l'elenco completo degli id da classificare (tutti
i 22 piloti, tutte le 11 squadre): chi non ha ancora corso resta in
classifica a zero punti, mai una vista vuota.

Motore puro (ADR 0002): nessun import di TUI o database.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from fm_engine.events import ClassifiedResult

# Highest finishing position used as countback depth (full grid of 22).
_MAX_POSITION = 22


@dataclass(frozen=True)
class RoundResult:
    """Il risultato di un GP disputato: round, circuito e ordine d'arrivo.

    classification e' la classifica finale del motore (ClassifiedResult
    per ogni iscritta, coi punti 2026 gia' attribuiti).
    sprint_classification e' la classifica della Gara sprint (coi punti
    sprint) nei Weekend sprint, tupla vuota negli altri: i suoi punti si
    sommano in classifica, ma i piazzamenti sprint non entrano nel
    countback (il tie-break resta sui piazzamenti di gara, come in F1).
    """

    round: int
    circuit_code: str
    classification: tuple[ClassifiedResult, ...]
    sprint_classification: tuple[ClassifiedResult, ...] = ()


@dataclass(frozen=True)
class DriverStanding:
    """Una riga della classifica piloti: posizione, pilota, punti, vittorie."""

    position: int
    driver_id: int
    points: int
    wins: int


@dataclass(frozen=True)
class ConstructorStanding:
    """Una riga della classifica costruttori: posizione, squadra, punti, vittorie."""

    position: int
    team_id: int
    points: int
    wins: int


def _position_counts(positions: Sequence[int]) -> dict[int, int]:
    """Quante volte ogni posizione d'arrivo ricorre (istogramma dei piazzamenti)."""
    counts: dict[int, int] = {}
    for position in positions:
        counts[position] = counts.get(position, 0) + 1
    return counts


def _countback_key(positions: Sequence[int]) -> tuple[int, ...]:
    """Chiave di tie-break: piu' piazzamenti migliori vengono prima.

    Per ogni posizione da 1 a 22 il conteggio negato: l'ordinamento
    crescente mette davanti chi ha piu' vittorie, poi piu' secondi posti,
    e cosi' via (countback F1).
    """
    counts = _position_counts(positions)
    return tuple(-counts.get(position, 0) for position in range(1, _MAX_POSITION + 1))


def _accumulate(
    results: Sequence[RoundResult], entity_ids: Sequence[int], key: str
) -> tuple[dict[int, int], dict[int, list[int]]]:
    """Somma punti e raccoglie i piazzamenti per ogni id (driver_id o team_id)."""
    points: dict[int, int] = {entity_id: 0 for entity_id in entity_ids}
    positions: dict[int, list[int]] = {entity_id: [] for entity_id in entity_ids}
    for round_result in results:
        for result in round_result.classification:
            entity_id = getattr(result, key)
            if entity_id not in points:
                continue
            points[entity_id] += result.points
            positions[entity_id].append(result.position)
        # Sprint points add to the totals; sprint placings stay out of the
        # countback (the GP race results decide ties, as in F1).
        for result in round_result.sprint_classification:
            entity_id = getattr(result, key)
            if entity_id not in points:
                continue
            points[entity_id] += result.points
    return points, positions


def driver_standings(
    results: Sequence[RoundResult], driver_ids: Sequence[int]
) -> tuple[DriverStanding, ...]:
    """La classifica piloti aggiornata, tutti i piloti inclusi (zero compresi)."""
    points, positions = _accumulate(results, driver_ids, "driver_id")
    ordered = sorted(
        driver_ids,
        key=lambda driver_id: (-points[driver_id], _countback_key(positions[driver_id]), driver_id),
    )
    return tuple(
        DriverStanding(
            position=index,
            driver_id=driver_id,
            points=points[driver_id],
            wins=_position_counts(positions[driver_id]).get(1, 0),
        )
        for index, driver_id in enumerate(ordered, start=1)
    )


def constructor_standings(
    results: Sequence[RoundResult], team_ids: Sequence[int]
) -> tuple[ConstructorStanding, ...]:
    """La classifica costruttori aggiornata, tutte le squadre incluse."""
    points, positions = _accumulate(results, team_ids, "team_id")
    ordered = sorted(
        team_ids,
        key=lambda team_id: (-points[team_id], _countback_key(positions[team_id]), team_id),
    )
    return tuple(
        ConstructorStanding(
            position=index,
            team_id=team_id,
            points=points[team_id],
            wins=_position_counts(positions[team_id]).get(1, 0),
        )
        for index, team_id in enumerate(ordered, start=1)
    )
