"""Test dello stile di evidenziazione dei piloti del giocatore (B02).

I colori della livrea sono stringhe libere: esadecimale, nome colore, vuoto o
non interpretabile. Lo stile deve sempre risultare leggibile e non sollevare
eccezioni.
"""

from dataclasses import replace

from rich.style import Style
from rich.text import Text

from fm_engine.world import PlayerSlot, generate
from fm_engine.world.team_setup import TeamSetupChoices, apply_team_setup
from fm_tui.widgets.team_colors import (
    driver_team_colors,
    name_with_team_swatches,
    player_highlight_style,
    row_with_team_colors,
    team_swatches,
)


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


# ---------------------------------------------------------------------------
# Quadratini di livrea e mappa pilota -> colori (colori-team)
# ---------------------------------------------------------------------------


def test_team_swatches_carry_the_two_livery_colours():
    swatches = team_swatches("#ff0000", "#0000ff")
    assert swatches.plain == "■■"
    assert swatches.spans[0].style.color.name == "#ff0000"
    assert swatches.spans[1].style.color.name == "#0000ff"


def test_name_with_swatches_keeps_the_base_style_on_the_name():
    text = name_with_team_swatches("Rossi", "#ff0000", "#0000ff", Style.parse("bold #00ff00"))
    assert text.plain == "■■ Rossi"
    # The base style (player highlight) sits on the Text; the squares override
    # only their own characters.
    assert text.style.color.name == "#00ff00"


def test_row_without_colours_keeps_the_plain_name():
    cells = ["1", "Rossi", "x"]
    row = row_with_team_colors(cells, name_index=1, primary_color=None, secondary_color=None)
    assert row[1] == "Rossi"


def test_row_with_colours_adds_the_swatches():
    cells = ["1", "Rossi", "x"]
    row = row_with_team_colors(
        cells, name_index=1, primary_color="#ff0000", secondary_color="#0000ff"
    )
    assert isinstance(row[1], Text)
    assert row[1].plain == "■■ Rossi"


def test_driver_team_colors_covers_ai_and_player_drivers():
    world = generate(7)
    # An AI-contracted driver maps to its team's livery colours.
    ai_contract = world.contracts[0]
    team = next(team for team in world.ai_teams if team.id == ai_contract.team_id)
    colors = driver_team_colors(world)
    assert colors[ai_contract.driver_id] == (team.primary_color, team.secondary_color)

    # After the team setup the player's drivers map to the slot colours.
    slot = PlayerSlot(name="Scuderia X", primary_color="#abcdef", secondary_color="#123456")
    with_slot = replace(world, player_slot=slot)
    free_agents = tuple(driver.id for driver in with_slot.drivers_without_contract)
    choices = TeamSetupChoices(
        driver_ids=free_agents[:2],
        engine_supplier_id=with_slot.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    set_up = apply_team_setup(with_slot, choices)
    player_colors = driver_team_colors(set_up)
    for driver_id in free_agents[:2]:
        assert player_colors[driver_id] == ("#abcdef", "#123456")
