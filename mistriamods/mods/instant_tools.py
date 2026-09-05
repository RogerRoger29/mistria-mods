"""Instant Tools - a small Fields of Mistria mod."""

from ..patcher import Markers

SLUG = "instant_tools"
NAME = "Instant Tools"
SUMMARY = "Trees and rocks break in one swing, still charging the full stamina."
DETAILS = """Your axe fells a tree and your pickaxe breaks a rock in a single swing, but you still pay the stamina for every swing it would normally have taken. If you cannot afford the whole job, you get an ordinary single hit instead, so you are never surprised by a faint. Tool-tier requirements are untouched, and explosions, monsters and cutscenes still work the old way. One side effect to know about: essence is granted per swing in the game, so fewer swings means a little less essence. Toggle under Settings > Accessibility."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
}

def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}

#!/usr/bin/env python3
"""
Instant Tools - a small Fields of Mistria mod.

Axe fells a tree in one swing; pickaxe breaks a rock in one swing - but you pay
the stamina you would have spent doing it the long way. The grind goes, the cost
stays.

If you can't afford the whole break, you get a normal single hit instead, so it
never faints you by surprise.

Tool quality gating is untouched: a starter axe still can't fell a hardwood tree.

Like the other mods here, this edits the GML the game compiles out of
assets.zip at startup. Insertions are wrapped in INSTANT_TOOLS markers, so the
patch is idempotent, removable, and composes with the other mods.

Usage:
    python instant_tools.py --apply
    python instant_tools.py --remove
    python instant_tools.py --status
"""



CHOP = "assets/gml/scripts/GameplaySystems/Data/Grid/GridActions/Chop.gml"
PICK = "assets/gml/scripts/GameplaySystems/Data/Grid/GridActions/Pick.gml"
FSM = "assets/gml/scripts/Player/AriFsm.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
MENU = "assets/gml/scripts/UI/Anchor/Menus/SettingsMenu.gml"
LOCAL = "assets/fiddle/misc_local.toml"



# chop_node() and pick_node() are also called by tarball explosions, monsters and
# cutscene scripts. Only the player should be billed for stamina, so the player's
# two call sites raise this flag around their call and nothing else does.
# Leading \n? because misc_local.toml has no trailing newline of its own.

SETTINGS_ANCHOR = "        can_burn_fruit_trees: true,\n"
MENU_ANCHOR = ('        self.checkbox("screenshake");\n'
               '        self.checkbox("screen_flash");\n')

CHOP_HP = "            node.hitpoints -= min(damage, node.hitpoints);\n"
PICK_HP = "                node.hitpoints -= min(damage, node.hitpoints);\n"

CHOP_CALL = ("                var success = chop_node(GRID, target_pos.x, target_pos.y,"
             " self.live_item.prototype, self.range_pattern == RangePattern.One ? 0 : -1,"
             " doppel);\n")
PICK_CALL = ("                var pick_result = pick_node(GRID, target_pos.x, target_pos.y,"
             " self.live_item.prototype, self.range_pattern == RangePattern.One ? 0 : -1,"
             " undefined, doppel);\n")

HELPER = """
//
// Instant Tools. Follows the MAP_HUBS idiom: a global declared at file scope.
//
#macro INSTANT_TOOLS_ACTIVE global.__instant_tools_active
INSTANT_TOOLS_ACTIVE = false;

//
// Boost damage so a node breaks in one swing, charging the stamina the long
// way would have cost. Returns the damage to actually apply.
//
// The caller charges one swing itself, immediately after chop_node/pick_node
// returns, so we only bill the OTHER swings here. If the full cost would drop
// her below zero we leave the damage alone and let it take another hit - that
// keeps the economics honest without fainting her without warning.
//
function instant_break_damage(node, damage, item) {
    if INSTANT_TOOLS_ACTIVE && SETTINGS.get("instant_tools")
        && damage > 0 && node.hitpoints > damage
    {
        var swings = ceil(node.hitpoints / damage);

        //
        var total = item.stamina_cost * swings * ARI.stamina_costs_modifier;
        if ARI.get_stamina() + total >= 0 {
            ARI.modify_stamina(item.stamina_cost * (swings - 1));
            damage = node.hitpoints;
        }
    }

    return damage;
}
"""




def guarded(call, indent):
    """Raise the player flag around a call site, then lower it."""
    return (block("INSTANT_TOOLS_ACTIVE = true;", indent)
            + call
            + block("INSTANT_TOOLS_ACTIVE = false;", indent))


def _patches():
    # (anchor, replacement, expected_count)
    return {
        CHOP: [
            (CHOP_HP, block("damage = instant_break_damage(node, damage, item);", " " * 12)
             + CHOP_HP, 2),
            # Wrapped here, like every other mod. The original script wrapped
            # this at apply time instead, which meant the helper went in
            # unmarked and removal could not find it again.
            (APPEND, block(HELPER), 1),
        ],
        PICK: [
            (PICK_HP, block("damage = instant_break_damage(node, damage, item);", " " * 16)
             + PICK_HP, 1),
        ],
        FSM: [
            (CHOP_CALL, guarded(CHOP_CALL, " " * 16), 1),
            (PICK_CALL, guarded(PICK_CALL, " " * 16), 1),
        ],
        SETTINGS: [(SETTINGS_ANCHOR,
                    SETTINGS_ANCHOR + block("instant_tools: true,", " " * 8), 1)],
        MENU: [(MENU_ANCHOR,
                block('self.checkbox("instant_tools");', " " * 8) + MENU_ANCHOR, 1)],
        LOCAL: [(APPEND, block('instant_tools = "Instant Tools"', toml=True), 1)],
    }




def patches(mk, opt):
    return _patches()
