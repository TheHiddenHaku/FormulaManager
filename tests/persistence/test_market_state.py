"""Round-trip dello stato di Mercato nel Checkpoint (T5.2.1, sub-issue M4).

Su un database SQLite temporaneo: lo stato di partenza torna a
NULL e ricarica al default; una fase di Mercato aperta (pool, liberi e
richieste salariali transitorie, sedili vacanti, firme, log mosse) round-
trippa identica; le mutazioni del roster prodotte dal Mercato viaggiano
nella tabella contracts via world_from_rows; un World del giocatore con i 2
Contratti post-mercato conserva is_set_up e gli Attributi vettura (landmine
player_set_up).
"""

from dataclasses import replace
from random import Random

from fm_engine.career import Career
from fm_engine.market import (
    AiMove,
    AiMoveKind,
    ExpiringContract,
    MarketPhase,
    MarketState,
    open_market,
    resolve_market,
)
from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
from fm_persistence import load_career, save_career
from fm_persistence.mapping import persistable_projection

SEED = 42
CONCLUDED_YEAR = 2026


def _populated_market() -> MarketState:
    """Un MarketState con tutti i tipi di campo valorizzati, anche le mosse."""
    return MarketState(
        phase=MarketPhase.OPEN,
        concluded_year=CONCLUDED_YEAR,
        seats_per_team=2,
        pool=(
            ExpiringContract(driver_id=3, team_id=2, salary_usd=9_000_000, last_season=2026),
            ExpiringContract(driver_id=7, team_id=4, salary_usd=5_000_000, last_season=2026),
        ),
        free_agent_ids=(21, 22),
        salary_demands={21: 4_000_000, 22: 6_500_000},
        vacant_seats={0: 1, 2: 1, 4: 1},
        signings={0: (3,), 2: (21,)},
        ai_moves=(
            AiMove(
                team_id=2,
                driver_id=3,
                kind=AiMoveKind.OFFER,
                salary_usd=9_000_000,
                duration_seasons=2,
            ),
            AiMove(
                team_id=2,
                driver_id=21,
                kind=AiMoveKind.SIGNING,
                salary_usd=4_000_000,
                duration_seasons=1,
            ),
            AiMove(
                team_id=4,
                driver_id=22,
                kind=AiMoveKind.FORCED_ASSIGNMENT,
                salary_usd=3_000_000,
                duration_seasons=1,
            ),
            AiMove(
                team_id=0,
                driver_id=3,
                kind=AiMoveKind.SIGNING,
                salary_usd=10_000_000,
                duration_seasons=3,
            ),
        ),
    )


def test_starting_market_round_trips_to_default(conn):
    career = Career(name="Mercato chiuso", world=generate(SEED))
    saved = save_career(conn, career)
    loaded = load_career(conn, saved.id)
    assert loaded.market == MarketState()
    # Stato di partenza: la colonna resta NULL.
    column = conn.execute("select market_state from careers where id = ?", (saved.id,)).fetchone()[
        0
    ]
    assert column is None


def test_open_market_round_trips_structurally_identical(conn):
    world = generate(SEED)
    resolved = resolve_market(world, open_market(world, CONCLUDED_YEAR), Random(SEED))
    # Precondizione: lo stato di Mercato non e' quello di partenza.
    assert resolved != MarketState()
    saved = save_career(conn, Career(name="Mercato risolto", world=world, market=resolved))
    loaded = load_career(conn, saved.id)
    assert loaded.market == resolved


def test_market_payload_carries_pool_signings_and_log(conn):
    market = _populated_market()
    saved = save_career(conn, Career(name="Mercato completo", world=generate(SEED), market=market))
    loaded = load_career(conn, saved.id)
    assert loaded.market == market
    # Le richieste salariali transitorie dei liberi vivono nel payload.
    assert loaded.market.salary_demands == {21: 4_000_000, 22: 6_500_000}
    assert loaded.market.signings == {0: (3,), 2: (21,)}
    assert len(loaded.market.ai_moves) == 4


def test_next_checkpoint_overwrites_then_clears_the_market(conn):
    world = generate(SEED)
    saved = save_career(
        conn, Career(name="Mercato aperto", world=world, market=_populated_market())
    )
    loaded = load_career(conn, saved.id)
    assert loaded.market.phase is MarketPhase.OPEN
    # Chiusa la finestra lo stato torna al default: la colonna torna NULL.
    saved = save_career(conn, replace(loaded, market=MarketState()))
    assert load_career(conn, saved.id).market == MarketState()
    column = conn.execute("select market_state from careers where id = ?", (saved.id,)).fetchone()[
        0
    ]
    assert column is None


def test_market_roster_mutations_round_trip_via_world_from_rows(conn):
    """Un Contratto che cambia squadra (esito del Mercato) sopravvive al round-trip."""
    world = generate(SEED)
    other_team_id = world.ai_teams[1].id
    moved = replace(world.contracts[0], team_id=other_team_id, salary_usd=11_000_000)
    mutated = replace(world, contracts=(moved, *world.contracts[1:]))
    saved = save_career(conn, Career(name="Roster mutato", world=mutated))
    loaded = load_career(conn, saved.id)
    assert loaded.world.contracts == mutated.contracts
    assert loaded.world == persistable_projection(mutated)


def test_player_two_contracts_round_trip_keeps_set_up_and_car(conn):
    """Landmine player_set_up: i 2 Contratti del giocatore tengono is_set_up e vettura."""
    world = generate(SEED)
    named = replace(world, player_slot=PlayerSlot(name="Scuderia Alessio"))
    choices = TeamSetupChoices(
        driver_ids=(world.contracts[0].driver_id, world.contracts[1].driver_id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="fast",
    )
    set_up = apply_team_setup(named, choices)
    assert set_up.player_slot.is_set_up

    saved = save_career(
        conn, Career(name="Giocatore post-mercato", world=set_up, market=_populated_market())
    )
    loaded = load_career(conn, saved.id)

    assert loaded.world.player_slot.is_set_up
    assert loaded.world.player_slot == set_up.player_slot
    assert loaded.world.player_slot.car_attributes == set_up.player_slot.car_attributes
    # Il Mercato aperto coesiste e round-trippa insieme allo stato del giocatore.
    assert loaded.market == _populated_market()
