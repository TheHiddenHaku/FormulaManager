"""Stile condiviso per evidenziare i piloti del giocatore con i colori squadra.

I colori della livrea del giocatore (PlayerSlot.primary_color) sono stringhe
libere: esadecimale #rrggbb o nome colore, oppure None se non scelti. Questo
helper li trasforma in uno stile Rich riusabile dalla Telecronaca e dalle
tabelle (classifiche, risultati, monitor tempi), con un ripiego leggibile
quando il colore manca o non e' interpretabile.
"""

from collections.abc import Iterable

from rich.color import ColorParseError
from rich.errors import StyleSyntaxError
from rich.style import Style
from rich.text import Text

# Ripiego quando la squadra non ha un colore valido: grassetto, sempre
# leggibile su qualunque tema, senza markup rotto.
_FALLBACK_STYLE = Style(bold=True)


def player_highlight_style(primary_color: str | None) -> Style:
    """Lo stile con cui evidenziare un pilota del giocatore.

    Grassetto piu' il colore primario della livrea quando e' valido (il
    grassetto aiuta il contrasto su tema scuro); solo grassetto se il colore
    manca o non e' interpretabile, senza sollevare eccezioni.
    """
    if not primary_color:
        return _FALLBACK_STYLE
    try:
        return Style.parse(f"bold {primary_color}")
    except (StyleSyntaxError, ColorParseError):
        return _FALLBACK_STYLE


def highlighted_row(values: Iterable[object], style: Style) -> list[Text]:
    """Le celle di una riga di tabella evidenziate con lo stile del giocatore.

    Ogni valore diventa un Text con lo stile dato, cosi' l'intera riga di una
    DataTable (classifiche, risultati, monitor tempi) risulta colorata. I valori
    sono convertiti a stringa: la tabella mostra gia' celle testuali.
    """
    return [Text(str(value), style=style) for value in values]
