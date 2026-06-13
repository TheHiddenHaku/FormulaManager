"""Telecronaca a template parametrici (FOR-16, ADR 0003).

L'output primario della simulazione verso il giocatore: gli eventi
tipizzati del motore diventano righe di cronaca in italiano, tono
radiofonico. Nessun LLM nel loop di gioco: solo template con molte
varianti, regole anti-ripetizione e determinismo dato l'RNG.
"""

from fm_engine.commentary.narrator import (
    REPETITION_WINDOW,
    CommentaryContext,
    narrate,
    render_variants,
)
from fm_engine.commentary.templates import TEMPLATES

__all__ = [
    "REPETITION_WINDOW",
    "TEMPLATES",
    "CommentaryContext",
    "narrate",
    "render_variants",
]
