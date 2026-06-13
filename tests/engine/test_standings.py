"""Classifiche piloti e costruttori con tie-break a piazzamenti (T5.1.1).

I punti si sommano dai GP disputati; a parita' di punti vince chi ha i
piazzamenti migliori (countback); i piloti e le squadre a zero punti
restano in classifica in un ordine stabile, mai una vista vuota.
"""

from fm_engine.events import ClassifiedResult
from fm_engine.season import (
    RoundResult,
    constructor_standings,
    driver_standings,
)


def _result(position: int, driver_id: int, team_id: int, points: int) -> ClassifiedResult:
    return ClassifiedResult(
        position=position,
        driver_id=driver_id,
        team_id=team_id,
        total_time_seconds=5400.0 + position,
        gap_to_winner_seconds=float(position - 1),
        points=points,
    )


def test_empty_season_lists_everyone_at_zero_in_stable_order():
    standings = driver_standings([], driver_ids=[3, 1, 2])
    assert [s.driver_id for s in standings] == [1, 2, 3]
    assert all(s.points == 0 for s in standings)
    assert [s.position for s in standings] == [1, 2, 3]


def test_points_accumulate_across_rounds():
    round1 = RoundResult(
        round=1,
        circuit_code="albert_park",
        classification=(_result(1, 1, 0, 25), _result(2, 2, 1, 18)),
    )
    round2 = RoundResult(
        round=3,
        circuit_code="suzuka",
        classification=(_result(1, 2, 1, 25), _result(2, 1, 0, 18)),
    )
    standings = driver_standings([round1, round2], driver_ids=[1, 2])
    by_id = {s.driver_id: s for s in standings}
    assert by_id[1].points == 43
    assert by_id[2].points == 43
    # Pari punti e pari piazzamenti (una vittoria a testa): ordine stabile per id.
    assert standings[0].driver_id == 1
    assert by_id[1].wins == 1
    assert by_id[2].wins == 1


def test_countback_breaks_ties_by_best_finishes():
    # A: una vittoria e un dodicesimo posto (25 punti, 1 vittoria).
    # B: un terzo e un quinto (25 punti, nessuna vittoria).
    round1 = RoundResult(
        round=1,
        circuit_code="albert_park",
        classification=(_result(1, 10, 0, 25), _result(3, 20, 1, 15)),
    )
    round2 = RoundResult(
        round=3,
        circuit_code="suzuka",
        classification=(_result(12, 10, 0, 0), _result(5, 20, 1, 10)),
    )
    standings = driver_standings([round1, round2], driver_ids=[10, 20, 30])
    assert standings[0].driver_id == 10  # la vittoria batte i piazzamenti regolari
    assert standings[1].driver_id == 20
    assert standings[2].driver_id == 30  # zero punti, in coda
    assert standings[0].points == standings[1].points == 25


def test_constructor_standings_sum_both_cars():
    round1 = RoundResult(
        round=1,
        circuit_code="albert_park",
        classification=(
            _result(1, 1, 0, 25),
            _result(2, 2, 0, 18),
            _result(3, 3, 1, 15),
            _result(4, 4, 1, 12),
        ),
    )
    standings = constructor_standings([round1], team_ids=[0, 1, 2])
    by_id = {s.team_id: s for s in standings}
    assert by_id[0].points == 43
    assert by_id[1].points == 27
    assert by_id[2].points == 0
    assert standings[0].team_id == 0
    assert standings[0].wins == 1
    assert standings[-1].team_id == 2
