"""Round-trip di conoscenza e fase Test pre-season nel Checkpoint (T5.1.2).

Sul Postgres effimero Docker (mai matilde): i livelli di conoscenza e i
giorni di Test svolti sopravvivono al Checkpoint; lo stato di partenza
torna a NULL e ricarica al default.
"""

from fm_engine.career import Career
from fm_engine.info import KnowledgeState
from fm_engine.preseason import PreseasonDay, PreseasonProgramme, PreseasonState
from fm_engine.world import generate
from fm_persistence import load_career, save_career

SEED = 7


def test_knowledge_and_preseason_round_trip(conn):
    knowledge = KnowledgeState(levels={"driver:1": 2, "car:0": 3, "driver:5": 1})
    preseason = PreseasonState(
        days_done=(
            PreseasonDay(
                day=1,
                programmes={1: PreseasonProgramme.KNOWLEDGE, 5: PreseasonProgramme.DEVELOPMENT},
            ),
            PreseasonDay(
                day=2,
                programmes={1: PreseasonProgramme.RELIABILITY, 5: PreseasonProgramme.KNOWLEDGE},
            ),
        )
    )
    career = Career(name="Stime", world=generate(SEED), knowledge=knowledge, preseason=preseason)
    saved = save_career(conn, career)
    loaded = load_career(conn, saved.id)
    assert loaded.knowledge == knowledge
    assert loaded.preseason == preseason
    assert loaded.preseason.knowledge_days == 2


def test_default_states_round_trip_to_none(conn):
    career = Career(name="Vergine", world=generate(SEED))
    saved = save_career(conn, career)
    loaded = load_career(conn, saved.id)
    assert loaded.knowledge == KnowledgeState()
    assert loaded.preseason == PreseasonState()
    assert not loaded.preseason.completed
