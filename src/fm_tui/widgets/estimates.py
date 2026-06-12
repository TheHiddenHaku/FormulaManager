"""Rendering delle Stime: intervalli, MAI valori esatti (CONTEXT.md).

Sistema provvisorio in attesa del fog of war vero (T5.1.2): qui ogni
attributo (vettura o pilota) viene reso come banda fissa di ampiezza
BAND_WIDTH che contiene il valore vero, ottenuta arrotondando il valore
per difetto al multiplo della banda (es. 63 -> "60-70"). Le schermate
passano SOLO da questo modulo per mostrare attributi: T5.1.2 sostituira'
la logica (margini che si stringono con test e sessioni) senza toccarle.
Il valore esatto e il Potenziale non escono mai da qui.
"""

# Fixed width of the band shown to the player. Documented margin: the
# true value always falls within the rendered interval.
BAND_WIDTH = 10

# Game attributes are on a 0-100 scale (DB schema and WorldConfig).
_MAX_VALUE = 100


def format_estimate(value: float) -> str:
    """La Stima di un attributo come intervallo testuale, es. "60-70".

    Il limite inferiore e' il valore arrotondato per difetto al multiplo
    di BAND_WIDTH, agganciato in alto perche' l'intervallo resti dentro
    la scala 0-100 (100 -> "90-100").
    """
    if not 0 <= value <= _MAX_VALUE:
        raise ValueError(f"value outside the 0-{_MAX_VALUE} scale: {value}")
    lower = int(value) // BAND_WIDTH * BAND_WIDTH
    lower = min(lower, _MAX_VALUE - BAND_WIDTH)
    return f"{lower}-{lower + BAND_WIDTH}"
