"""Review del pool degli Eventi extra-gara (FOR-27).

Almeno 10 eventi con pesi positivi, i quattro tipi coperti, template
parametrici reali e solo effetti automatici: nessun evento richiede una
scelta del giocatore.
"""

from dataclasses import fields

from fm_engine.events_extra import EXTRA_EVENT_POOL, ExtraEvent, ExtraEventKind


def test_pool_has_at_least_ten_weighted_events():
    assert len(EXTRA_EVENT_POOL) >= 10
    assert all(event.weight > 0 for event in EXTRA_EVENT_POOL)
    codes = [event.code for event in EXTRA_EVENT_POOL]
    assert len(codes) == len(set(codes))


def test_pool_covers_the_four_kinds():
    kinds = {event.kind for event in EXTRA_EVENT_POOL}
    assert kinds == set(ExtraEventKind)


def test_templates_are_real_and_parametric():
    for event in EXTRA_EVENT_POOL:
        assert event.headline_template.strip()
        if event.kind is ExtraEventKind.ONE_OFF_SPONSOR:
            assert "{amount}" in event.headline_template
            assert event.amount_usd > 0
        elif event.kind in (
            ExtraEventKind.PROJECT_DELAYED,
            ExtraEventKind.PROJECT_ACCELERATED,
        ):
            assert "{attribute}" in event.headline_template
            assert "{days}" in event.headline_template
            assert event.shift_days > 0
        else:
            assert "{rival}" in event.headline_template


def test_no_event_requires_a_player_choice():
    """Solo effetti automatici: il modello non ha campi di decisione."""
    field_names = {field.name for field in fields(ExtraEvent)}
    assert field_names == {
        "code",
        "kind",
        "weight",
        "headline_template",
        "amount_usd",
        "shift_days",
    }
