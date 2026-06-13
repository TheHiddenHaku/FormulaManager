"""Finestra di undercut come evento del motore (FOR-38).

Gare a 2 vetture curate (Sfiga spenta, pilota dietro in NO_RISK cosi'
la coppia resta stabile): la finestra si apre quando le condizioni
maturano e l'evento esce una volta sola per apertura. La sosta del
rivale chiude la finestra; la coppia ribaltata e' una finestra nuova.
"""

from collections import defaultdict
from dataclasses import replace
from random import Random

from test_race_base import _entry

from fm_engine.balance.simulate import build_grid
from fm_engine.circuits import circuit_by_code
from fm_engine.events import UndercutWindow
from fm_engine.misfortune import MisfortuneConfig
from fm_engine.race import (
    UNDERCUT_ATTACKER_COOLDOWN_LAPS,
    UNDERCUT_MAX_GAP_SECONDS,
    UNDERCUT_MIN_ATTACKER_TYRE_AGE_LAPS,
    UNDERCUT_MIN_LAPS_REMAINING,
    UNDERCUT_MIN_RIVAL_DEGRADATION_SECONDS,
    _undercut_window_open,
    start_race,
    step,
)
from fm_engine.state import CarRaceState, DriverOrders, DuelInstruction, Orders, PitOrder
from fm_engine.strategy import build_plans, lap_orders
from fm_engine.tyres import Compound, CompoundSlot, TyreState, nominated_compounds

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
    # The rival rejoins on the medium: it wears fast enough that, once he
    # is the one chasing on aged rubber, a second stop repays the pit
    # loss and the convenience gate (FOR-40) lets the flipped window
    # mature within the race.
    medium = nominated_compounds(state.circuit)[CompoundSlot.MEDIUM]

    def orders_for(lap: int) -> Orders:
        drivers = {2: NO_RISK}
        if lap == 15:
            drivers[1] = DriverOrders(pit=PitOrder(compound=medium))
        return Orders(drivers=drivers)

    state, windows = _windows_until(state, 15, orders_for)
    assert [(w.driver_id, w.target_driver_id) for w in windows] == [(2, 1)]
    # The rival's stop puts him behind on fresh tyres: conditions gone,
    # registry empty, the original window is closed.
    assert state.active_undercut_windows == ()
    # On worn rubber the rival hunts down the leader: the flipped pair
    # matures a brand new window, emitted once.
    state, reopened = _windows_until(state, 38, orders_for)
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


def _car(driver_id: int, team_id: int, total_time: float, age: int, degradation: float):
    """Una vettura su misura per provare la sola condizione di convenienza."""
    return CarRaceState(
        entry=_entry(driver_id, team_id=team_id, strength=70),
        position=1,
        total_time_seconds=total_time,
        last_lap_seconds=90.0,
        gap_to_leader_seconds=0.0,
        tyres=TyreState(compound=Compound.C2, age_laps=age, degradation_seconds=degradation),
        compounds_used=(Compound.C2,),
    )


def test_convenience_gate_needs_the_stop_to_repay():
    """La finestra si apre solo se il guadagno gomma fresca ripaga il pit (FOR-40)."""
    ahead = _car(1, 1, total_time=100.0, age=9, degradation=0.5)
    # Gap 1.0, rivale usurato, attaccante con eta' gomme oltre la soglia:
    # tutto in regola tranne, eventualmente, la convenienza.
    behind = _car(2, 2, total_time=101.0, age=9, degradation=0.5)
    # 12 giri restano, oltre il minimo, ma 0.5 * 12 = 6 < perdita pit:
    # restare in pista fino alla bandiera e' piu' veloce.
    assert 12 >= UNDERCUT_MIN_LAPS_REMAINING
    assert not _undercut_window_open(behind, ahead, laps_remaining=12)
    # Con tanti giri davanti la sosta si ripaga: 0.5 * 48 = 24 > perdita pit.
    assert _undercut_window_open(behind, ahead, laps_remaining=48)
    # Stessi pochi giri, ma gomme cosi' andate che la sosta torna utile.
    very_worn = _car(2, 2, total_time=101.0, age=20, degradation=2.0)
    assert _undercut_window_open(very_worn, ahead, laps_remaining=12)


def test_attacker_cooldown_spaces_out_repeated_windows():
    """Per ogni attaccante due finestre distano almeno il cooldown (FOR-40)."""
    entries = build_grid(7)
    circuit = circuit_by_code("sakhir")
    state, _ = start_race(entries, circuit, seed=7)
    plans = build_plans(entries, circuit, Random(7))
    laps_by_attacker: dict[int, list[int]] = defaultdict(list)
    while not state.finished:
        state, events = step(state, lap_orders(state, plans))
        for event in events:
            if isinstance(event, UndercutWindow):
                laps_by_attacker[event.driver_id].append(event.lap)
    assert any(len(laps) > 1 for laps in laps_by_attacker.values()), (
        "lo scenario deve produrre attaccanti con piu' di una finestra"
    )
    for laps in laps_by_attacker.values():
        for earlier, later in zip(laps, laps[1:], strict=False):
            assert later - earlier >= UNDERCUT_ATTACKER_COOLDOWN_LAPS, (earlier, later)
