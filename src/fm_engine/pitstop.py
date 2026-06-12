"""Costo in tempo del pit stop (FOR-10).

Tempo medio piu' varianza gaussiana, con un pavimento fisico: anche la
sosta perfetta costa il transito in corsia box. Lo sconto sotto Safety
car e VSC arriva con T2.3.1. Costanti tarabili con l'harness (T2.4.1).
"""

from random import Random

# Average total time lost by pitting under green flag conditions.
PIT_STOP_BASE_SECONDS = 22.0
PIT_STOP_SIGMA_SECONDS = 0.8
# No stop can cost less than the pit lane transit itself.
PIT_STOP_MINIMUM_SECONDS = 18.0


def pit_stop_seconds(rng: Random) -> float:
    """Il tempo perso da una sosta: media piu' varianza, mai sotto il minimo."""
    return max(
        PIT_STOP_BASE_SECONDS + rng.gauss(0.0, PIT_STOP_SIGMA_SECONDS),
        PIT_STOP_MINIMUM_SECONDS,
    )
