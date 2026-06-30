"""Test della Telecronaca di rientro tra due GP (tempo-tra-i-gran-premi).

La riga di raccordo all'inizio del weekend successivo da' voce ai giorni
di pausa dall'ultimo Gran Premio. Funzione pura: niente RNG, la variante
si sceglie dai giorni di pausa, e singolare e plurale dei giorni sono
corretti. Una pausa non positiva non e' un rientro: e' un errore.
"""

import pytest

from fm_engine.commentary import return_to_track_commentary


def test_return_line_names_the_circuit_and_the_pause():
    line = return_to_track_commentary(21, "Monza")
    assert "Monza" in line
    assert "21 giorni" in line


def test_single_day_uses_the_singular():
    line = return_to_track_commentary(1, "Imola")
    assert "1 giorno" in line
    assert "giorni" not in line


def test_line_is_deterministic_for_the_same_pause():
    assert return_to_track_commentary(14, "Spa") == return_to_track_commentary(14, "Spa")


def test_different_pause_lengths_can_vary_the_phrasing():
    # Le varianti si scelgono dai giorni di pausa: pause di durata diversa
    # possono produrre frasi diverse, cosi' il rientro non e' sempre uguale.
    lines = {return_to_track_commentary(days, "Suzuka") for days in (10, 11, 12)}
    assert len(lines) > 1


def test_non_positive_pause_is_rejected():
    with pytest.raises(ValueError):
        return_to_track_commentary(0, "Monaco")
    with pytest.raises(ValueError):
        return_to_track_commentary(-3, "Monaco")
