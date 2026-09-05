"""Big rocks in the Mines count toward revealing the ladder.

By default they count for nothing at all. Every large rock and boulder ships
with `ladder_candidate = false`, so breaking one - the most expensive thing on
the floor to break - moves the ladder not one point. Small rocks, ore nodes,
seams, barrels, crates and monsters all count; the big ones don't.

This makes them count, and counts them by **size**: a 4x4 rock occupies the
space of four small ones and is worth four, a 6x6 boulder is worth nine. The
floor's threshold still counts each rock as one, so clearing big rocks now
genuinely accelerates the descent instead of taxing it.

Toggleable in Settings > Accessibility ("Big Rock Credit").
"""

from ..patcher import Markers

SLUG = "big_rock_credit"
NAME = "Big Rock Credit"
SUMMARY = "Large rocks and boulders count toward the mine ladder, weighted by their size."
DETAILS = """Large rocks and boulders in the Mines count toward revealing the ladder, weighted by their size - a large rock is worth 4 and a boulder 9. In the unmodded game they are worth nothing, so the most expensive objects on the floor moved the ladder not at all and clearing one actively cost you progress. Toggle under Settings > Accessibility."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {}


def defaults():
    return {}


ROCKS = "assets/gml/scripts/GameplaySystems/Data/Grid/Rocks.gml"
GRIDUTILS = "assets/gml/scripts/GameplaySystems/Data/Grid/__GridGeneral/GridUtils.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
MENU = "assets/gml/scripts/UI/Anchor/Menus/SettingsMenu.gml"
LOCAL = "assets/fiddle/misc_local.toml"

SETTINGS_ANCHOR = "        can_burn_fruit_trees: true,\n"
MENU_ANCHOR = ('        self.checkbox("screenshake");\n'
               '        self.checkbox("screen_flash");\n')

# Where a rock's candidacy is copied off its prototype.
ROCKS_ANCHOR = "    node.ladder_candidate = node.prototype.ladder_candidate;\n"

ROCKS_EFFECT = """
//
// Big Rock Credit. Large rocks and boulders ship as non-candidates, so this
// opts every rock in. Scoring only ever happens inside the Mines, so rocks
// elsewhere are unaffected by the change.
//
if SETTINGS.get("big_rock_credit") {
    node.ladder_candidate = true;
}
"""

# The award site. The node has already been cleared out of the grid by this
# point, but the local `node` is still in scope - the very next statement uses
# it - so its prototype is still readable here.
AWARD_ANCHOR = """    if grid.location_id == LocationId.Dungeon
        && (cat == ObjectCategory.Rock || cat == ObjectCategory.Breakable)
        && ladder_candidate
    {
        DUNGEON_RUNNER.on_object_destroy(_x, _y);
    }
"""

AWARD_EFFECT = """
//
// Pay for the rest of a big rock's footprint. on_object_destroy() below awards
// the single base point every object gets, so this adds the difference: a 4x4
// rock covers four 2x2 cells and ends up worth four, a 6x6 boulder nine.
//
if SETTINGS.get("big_rock_credit")
    && grid.location_id == LocationId.Dungeon
    && cat == ObjectCategory.Rock
    && ladder_candidate
{
    var rock_cells = (node.prototype.size.x div 2) * (node.prototype.size.y div 2);
    if rock_cells > 1 {
        DUNGEON_RUNNER.ladder_score +=
            DUNGEON.biomes[DUNGEON_BIOME].object_element_points * (rock_cells - 1);
    }
}
"""


def patches(mk, opt):
    return {
        ROCKS: [(ROCKS_ANCHOR, ROCKS_ANCHOR + mk.block(ROCKS_EFFECT, " " * 4))],
        GRIDUTILS: [(AWARD_ANCHOR, mk.block(AWARD_EFFECT, " " * 4) + AWARD_ANCHOR)],
        SETTINGS: [(SETTINGS_ANCHOR,
                    SETTINGS_ANCHOR + mk.block("big_rock_credit: true,", " " * 8))],
        MENU: [(MENU_ANCHOR,
                mk.block('self.checkbox("big_rock_credit");', " " * 8) + MENU_ANCHOR)],
        LOCAL: [(mk.APPEND,
                 mk.block('big_rock_credit = "Big Rock Credit"', toml=True))],
    }
