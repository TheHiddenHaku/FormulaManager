"""Finestra di undercut come evento del motore (FOR-38).

Gare a 2 vetture curate (Sfiga spenta, pilota dietro in NO_RISK cosi'
la coppia resta stabile): la finestra si apre quando le condizioni
maturano e l'evento esce una volta sola per apertura. La sosta del
rivale chiude la finestra; la coppia ribaltata e' una finestra nuova.
"""

from dataclasses import replace

from test_race_base import _entry

from fm_engine.circuits import circuit_by_code
from fm_engine.events import UndercutWindow
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.race import (
    UNDERCUT_MAX_GAP_SECONDS,
    UNDERCUT_MIN_ATTACKER_TYRE_AGE_LAPS,
    UNDERCUT_MIN_RIVAL_DEGRADATION_SECONDS,
    start_race,
    step,
)
from fm_engine.state import DriverOrders, DuelInstruction, Orders, PitOrder
from fm_engine.tyres import CompoundSlot, nominated_compounds

NO_MISFORTUNE = MisfortuneConfig.disabled()
SEED = 3

# The trailing driver never attacks on track: the pair stays stable and
# the only way past the rival is the pit lane.
NO_RISK = DriverOrders(duel_instruction=DuelInstruction.NO_RISK)
NO_RISK_ORDERS = Orders(drivers={2: NO_RISK})


def _two_car_start(behind_team_id: int = 2, behind_strength: int = 70, circuit=None):
    """Una gara a 2 in partenza: pilota 1 davanti, pilota 2 dietro."""
    circuit = circuit or circuit_by_code("sakhir")
    entries = (
        _entry(1, team_id=1, strength=70),
        _entry(2, team_id=behind_team_id, strength=behind_strength),
    )
    state, _ = start_race(entries, circuit, seed=SEED, misfortune=NO_MISFORTUNE)
    return state


def _windows_until(state, lap_limit: int, orders_for=None):
    """Gli eventi UndercutWindow emessi fino al giro indicato."""
    windows: list[UndercutWindow] = []
    while state.lap < lap_limit and not state.finished:
        orders = orders_for(state.lap + 1) if orders_for is not None else NO_RISK_ORDERS
        state, events = step(state, orders)
        windows.extend(event for event in events if isinstance(event, UndercutWindow))
    return state, windows


def test_window_opens_once_when_conditions_mature():
    """Una emissione sola per apertura, mai una per giro (anti-spam)."""
    state = _two_car_start()
    state, windows = _windows_until(state, 25)
    assert len(windows) == 1, windows
    event = windows[0]
    assert event.driver_id == 2 and event.target_driver_id == 1
    assert 0 < event.gap_seconds <= UNDERCUT_MAX_GAP_SECONDS
    # The window opened only once the existing models said so: rival
    # tyres worn enough, attacker himself in need of a stop.
    assert event.lap > UNDERCUT_MIN_ATTACKER_TYRE_AGE_LAPS
    assert state.car_of(1).tyres.degradation_seconds >= UNDERCUT_MIN_RIVAL_DEGRADATION_SECONDS
    # The window is still open at lap 25 and stays registered (silent).
    assert state.active_undercut_windows == ((2, 1),)


def test_rival_pit_closes_the_window_and_the_flipped_pair_reopens_it():
    """La finestra si riapre solo se chiusa o se cambia la coppia."""
    state = _two_car_start()
    hard = nominated_compounds(state.circuit)[CompoundSlot.HARD]

    def orders_for(lap: int) -> Orders:
        drivers = {2: NO_RISK}
        if lap == 15:
            drivers[1] = DriverOrders(pit=PitOrder(compound=hard))
        return Orders(drivers=drivers)

    state, windows = _windows_until(state, 15, orders_for)
    assert [(w.driver_id, w.target_driver_id) for w in windows] == [(2, 1)]
    # The rival's stop puts him behind on fresh tyres: conditions gone,
    # registry empty, the original window is closed.
    assert state.active_undercut_windows == ()
    # On fresh rubber the rival hunts down the leader on worn tyres: the
    # flipped pair matures a brand new window, emitted once.
    state, reopened = _windows_until(state, 40, orders_for)
    assert [(w.driver_id, w.target_driver_id) for w in reopened] == [(1, 2)]


def test_same_seed_same_orders_same_windows():
    """Determinismo: stesso seed e stessi Ordini, stessi eventi finestra."""
    _, first = _windows_until(_two_car_start(), 30)
    _, second = _windows_until(_two_car_start(), 30)
    assert first == second
    assert first, "lo scenario deve produrre almeno una finestra"


def test_no_window_when_the_gap_is_wide():
    """Distacchi ampi: nessuna finestra, anche con gomme usurate."""
    state = _two_car_start(behind_strength=40)
    state, windows = _windows_until(state, 25)
    assert windows == []
    assert state.active_undercut_windows == ()
    gap = state.car_of(2).total_time_seconds - state.car_of(1).total_time_seconds
    assert gap > UNDERCUT_MAX_GAP_SECONDS


def test_no_window_between_teammates():
    """In casa propria decide l'Ordine di scuderia, non l'undercut."""
    state = _two_car_start(behind_team_id=1)
    _, windows = _windows_until(state, 25)
    assert windows == []


def test_no_window_without_enough_laps_to_amortise_the_stop():
    """A fine gara la sosta non si ripaga: la finestra non si apre."""
    short_circuit = replace(circuit_by_code("sakhir"), race_laps=14)
    state = _two_car_start(circuit=short_circuit)
    _, windows = _windows_until(state, short_circuit.race_laps)
    assert windows == []
