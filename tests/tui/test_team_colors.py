"""Test dello stile di evidenziazione dei piloti del giocatore (B02).

I colori della livrea sono stringhe libere: esadecimale, nome colore, vuoto o
non interpretabile. Lo stile deve sempre risultare leggibile e non sollevare
eccezioni.
"""

from rich.style import Style

from fm_tui.widgets.team_colors import player_highlight_style


def test_valid_hex_colour_becomes_bold_coloured_style():
    style = player_highlight_style("#ff2800")
    assert style.bold is True
    assert style.color is not None
    assert style.color.name == "#ff2800"


def test_named_colour_is_accepted():
    style = player_highlight_style("red")
    assert style.bold is True
    assert style.color is not None


def test_missing_colour_falls_back_to_bold():
    style = player_highlight_style(None)
    assert style == Style(bold=True)
    assert style.color is None


def test_empty_colour_falls_back_to_bold():
    style = player_highlight_style("")
    assert style.color is None
    assert style.bold is True


def test_unparseable_colour_falls_back_without_raising():
    style = player_highlight_style("non-un-colore")
    assert style.color is None
    assert style.bold is True
