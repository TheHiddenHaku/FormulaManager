"""Serializzazione della conoscenza degli attributi (Stime, T5.1.2).

Il KnowledgeState del motore viaggia nella colonna careers.knowledge_state
come documento JSON: il livello di conoscenza per ogni soggetto (vettura o
pilota). Stato di partenza (nessuna conoscenza) non scritto: colonna NULL e
load al canonico KnowledgeState().
"""

from typing import Any

from fm_engine.info import KnowledgeState


def knowledge_state_payload(knowledge: KnowledgeState) -> dict[str, Any] | None:
    """Il documento JSON della conoscenza, None se nessuna conoscenza accumulata."""
    if knowledge == KnowledgeState():
        return None
    return {"levels": dict(knowledge.levels)}


def knowledge_state_from_payload(payload: dict[str, Any] | None) -> KnowledgeState:
    """Ricostruisce la conoscenza dal documento JSON, o il default."""
    if payload is None:
        return KnowledgeState()
    return KnowledgeState(levels={key: int(value) for key, value in payload["levels"].items()})
