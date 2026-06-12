"""Crossover: curve di prestazione per condizioni e soste emergenti (FOR-13)."""

from dataclasses import replace

from test_race_base import _entry

from fm_engine.circuits import circuit_by_code
from fm_engine.events import Crossover, is_key_event
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.race import start_race, step
from fm_engine.state import DriverOrders, Orders, PitOrder
from fm_engine.tyres import Compound
from fm_engine.weather import condition_loss_seconds, optimal_category

NO_MISFORTUNE = MisfortuneConfig.disabled()


def test_condition_curves_cross_over():
    """Slick regina sull'asciutto, Intermedia in mezzo, Bagnato nel diluvio."""
    assert optimal_category(0.0) == "slick"
    assert optimal_category(0.5) == "intermediate"
    assert optimal_category(0.95) == "wet"
    dry_losses = (
        condition_loss_seconds(Compound.C3, 0.0),
        condition_loss_seconds(Compound.INTERMEDIATE, 0.0),
        condition_loss_seconds(Compound.WET, 0.0),
    )
    assert dry_losses[0] < dry_losses[1] < dry_losses[2]
    soaked_losses = (
        condition_loss_seconds(Compound.C3, 1.0),
        condition_loss_seconds(Compound.INTERMEDIATE, 1.0),
        condition_loss_seconds(Compound.WET, 1.0),
    )
    assert soaked_losses[2] < soaked_losses[1] < soaked_losses[0]


def test_slick_gets_slower_as_the_track_gets_wetter():
    losses = [condition_loss_seconds(Compound.C3, wetness) for wetness in (0.0, 0.3, 0.6, 0.9)]
    assert losses == sorted(losses)
    assert losses[-1] > 5.0


def test_crossover_event_fires_when_the_optimal_tyre_changes(entry_factory):
    """Una pioggia forzata fa scattare l'Evento chiave di Crossover."""
    entries = entry_factory()
    circuit = circuit_by_code("spa")
    state, _ = start_race(entries, circuit, seed=4, misfortune=NO_MISFORTUNE)
    # Pioggia gia' in corso: la pista si bagna fino al Crossover.
    state = replace(state, rain_intensity=0.9)
    crossovers = []
    for _ in range(6):
        state, events = step(state)
        crossovers.extend(e for e in events if isinstance(e, Crossover))
        state = replace(state, rain_intensity=max(state.rain_intensity, 0.9))
    assert crossovers, "con pioggia battente il Crossover deve scattare"
    first = crossovers[0]
    assert is_key_event(first)
    assert first.from_category == "slick" and first.to_category == "intermediate"


def test_crossover_stop_pays_off_in_the_rain(entry_factory):
    """Chi monta l'Intermedia al Crossover guadagna su chi resta su slick."""
    circuit = circuit_by_code("spa")
    entries = (_entry(1, team_id=1, strength=70), _entry(2, team_id=2, strength=70))

    def run_with_strategy(switcher_pits: bool) -> tuple[float, float]:
        state, _ = start_race(entries, circuit, seed=11, misfortune=NO_MISFORTUNE)
        state = replace(state, rain_intensity=0.9)
        pitted = False
        for _ in range(12):
            orders = None
            if (
                switcher_pits
                and not pitted
                and optimal_category(state.track_wetness) == "intermediate"
            ):
                orders = Orders(
                    drivers={2: DriverOrders(pit=PitOrder(compound=Compound.INTERMEDIATE))}
                )
                pitted = True
            state, _ = step(state, orders)
            state = replace(state, rain_intensity=max(state.rain_intensity, 0.9))
        return (
            state.car_of(1).total_time_seconds,
            state.car_of(2).total_time_seconds,
        )

    stay_out_1, stay_out_2 = run_with_strategy(switcher_pits=False)
    slick_1, inter_2 = run_with_strategy(switcher_pits=True)
    # Senza sosta i due restano vicini; con la sosta al Crossover il
    # pilota 2 stacca nettamente il pilota 1 rimasto su slick.
    gap_without_stop = stay_out_2 - stay_out_1
    gap_with_stop = inter_2 - slick_1
    assert gap_with_stop < gap_without_stop - 5.0, (gap_without_stop, gap_with_stop)
    assert inter_2 < slick_1, "al Crossover la sosta deve pagare"
