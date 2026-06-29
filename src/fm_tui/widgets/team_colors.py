"""Stile e quadratini condivisi per i colori squadra nelle tabelle TUI.

I colori della livrea (PlayerSlot e Team.primary_color/secondary_color) sono
stringhe libere: esadecimale #rrggbb o nome colore, oppure None se non scelti.
Questi helper li trasformano in stili Rich riusabili dalla Telecronaca e dalle
tabelle (classifiche, risultati, monitor tempi, mercato, griglia): i piloti del
giocatore restano evidenziati, e accanto a ogni pilota compaiono i due
quadratini coi colori della sua scuderia, con un ripiego leggibile quando un
colore manca o non e' interpretabile.
"""

from collections.abc import Iterable

from rich.color import ColorParseError
from rich.errors import StyleSyntaxError
from rich.style import Style
from rich.text import Text

from fm_engine.world.models import PLAYER_TEAM_ID, World

# Ripiego quando la squadra non ha un colore valido: grassetto, sempre
# leggibile su qualunque tema, senza markup rotto.
_FALLBACK_STYLE = Style(bold=True)

# Carattere usato come quadratino di livrea accanto al nome di un pilota.
_SWATCH = "■"  # ■


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


def _swatch_style(color: str | None) -> Style:
    """Lo stile di un quadratino: il colore della livrea, o un ripiego visibile."""
    if not color:
        return Style(dim=True)
    try:
        return Style(color=color)
    except (StyleSyntaxError, ColorParseError):
        return Style(dim=True)


def team_swatches(primary_color: str | None, secondary_color: str | None) -> Text:
    """I due quadratini coi colori della scuderia (primario e secondario)."""
    swatches = Text()
    swatches.append(_SWATCH, style=_swatch_style(primary_color))
    swatches.append(_SWATCH, style=_swatch_style(secondary_color))
    return swatches


def name_with_team_swatches(
    name: object,
    primary_color: str | None,
    secondary_color: str | None,
    name_style: Style | None = None,
) -> Text:
    """Il nome di un pilota preceduto dai due quadratini della sua scuderia.

    Lo stile di base del Text (name_style, l'evidenziazione del giocatore se
    presente) si applica al nome; i due quadratini portano i colori della
    livrea come span propri, sopra lo stile di base.
    """
    text = Text(style=name_style if name_style is not None else Style())
    text.append_text(team_swatches(primary_color, secondary_color))
    text.append(" ")
    text.append(str(name))
    return text


def row_with_team_colors(
    cells: list[object],
    name_index: int,
    primary_color: str | None,
    secondary_color: str | None,
    highlight_style: Style | None = None,
) -> list[object]:
    """Le celle di una riga con i quadratini scuderia sul nome.

    Il nome (cella name_index) porta i due quadratini; se highlight_style e'
    dato (riga di un pilota del giocatore) l'intera riga e' evidenziata.
    """
    result: list[object] = []
    for index, value in enumerate(cells):
        if index == name_index:
            if primary_color is None and secondary_color is None:
                # No team colours known: keep the prior look (plain name, or the
                # player highlight). No swatches for free agents or legacy data.
                if highlight_style is not None:
                    result.append(Text(str(value), style=highlight_style))
                else:
                    result.append(value)
            else:
                result.append(
                    name_with_team_swatches(value, primary_color, secondary_color, highlight_style)
                )
        elif highlight_style is not None:
            result.append(Text(str(value), style=highlight_style))
        else:
            result.append(value)
    return result


def driver_team_colors(world: World) -> dict[int, tuple[str | None, str | None]]:
    """Mappa driver_id -> (colore primario, secondario) della sua scuderia.

    Copre i piloti contrattualizzati (i 22 in Griglia): il giocatore dallo
    slot, gli altri dalle squadre AI. I liberi (senza Contratto) non hanno
    scuderia, quindi non compaiono nella mappa.
    """
    by_team: dict[int, tuple[str | None, str | None]] = {
        PLAYER_TEAM_ID: (world.player_slot.primary_color, world.player_slot.secondary_color)
    }
    for team in world.ai_teams:
        by_team[team.id] = (team.primary_color, team.secondary_color)
    colors: dict[int, tuple[str | None, str | None]] = {}
    for contract in world.contracts:
        if contract.team_id in by_team:
            colors[contract.driver_id] = by_team[contract.team_id]
    return colors
