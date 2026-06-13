"""Convergenza delle Stime con la conoscenza (T5.1.2).

Il margine di una Stima e' monotono non crescente all'aumentare della
conoscenza, mai negativo, e il valore vero resta sempre dentro
l'intervallo. Osservare piu' weekend (prove libere e gare) stringe le
Stime fino al minimo.
"""

from fm_engine.events import ClassifiedResult
from fm_engine.info import (
    INITIAL_MARGIN,
    MINIMUM_MARGIN,
    KnowledgeState,
    car_subject,
    driver_subject,
    margin_for_level,
    observe_practice,
    observe_race,
)


def test_margin_is_monotone_non_increasing_and_floored():
    margins = [margin_for_level(level) for level in range(10)]
    assert margins[0] == INITIAL_MARGIN
    assert all(margins[i] >= margins[i + 1] for i in range(len(margins) - 1))
    assert all(margin >= MINIMUM_MARGIN for margin in margins)
    assert margins[-1] == MINIMUM_MARGIN


def test_estimate_always_contains_the_true_value_even_at_the_edges():
    knowledge = KnowledgeState()
    subject = driver_subject(1)
    for true_value in (0.0, 1.0, 50.0, 99.0, 100.0):
        for level in range(6):
            state = KnowledgeState(levels={subject: level})
            estimate = state.estimate_for(subject, true_value)
            assert estimate.margin >= 0
            assert estimate.contains(true_value)
        # margin shrinks with knowledge for the same true value
        wide = knowledge.estimate_for(subject, true_value)
        tight = KnowledgeState(levels={subject: 4}).estimate_for(subject, true_value)
        assert tight.margin <= wide.margin


def _classification() -> tuple[ClassifiedResult, ...]:
    return tuple(
        ClassifiedResult(
            position=position,
            driver_id=position,
            team_id=(position - 1) // 2,
            total_time_seconds=5400.0 + position,
            gap_to_winner_seconds=float(position - 1),
            points=0,
        )
        for position in range(1, 11)
    )


def test_races_and_practice_tighten_estimates_over_weekends():
    knowledge = KnowledgeState()
    subject = driver_subject(1)
    margins = [knowledge.estimate_for(subject, 70.0).margin]
    for _ in range(6):
        knowledge = observe_practice(knowledge, [1], team_id=0)
        knowledge = observe_race(knowledge, _classification())
        margins.append(knowledge.estimate_for(subject, 70.0).margin)
    assert all(margins[i] >= margins[i + 1] for i in range(len(margins) - 1))
    assert margins[-1] < margins[0]
    # Convergence: enough weekends bring the margin to the floor.
    assert margins[-1] == MINIMUM_MARGIN


def test_observing_a_race_tightens_every_car_and_driver_seen():
    knowledge = observe_race(KnowledgeState(), _classification())
    # Each driver seen rises one level; team 0 fielded two cars, so its
    # car estimate is observed once per car.
    assert knowledge.level_for(driver_subject(1)) == 1
    assert knowledge.level_for(car_subject(0)) == 2
    # A driver that did not appear stays at level 0 (wide estimate).
    assert knowledge.level_for(driver_subject(99)) == 0
