"""Ladder Progress - a small Fields of Mistria mod."""

from ..patcher import Markers

SLUG = "ladder_progress"
NAME = "Ladder Progress"
SUMMARY = "A mine HUD readout of how close the floor is to revealing its ladder."
DETAILS = """A small readout on the mine HUD showing your progress toward revealing the floor's ladder, as a number like 7 / 14. The game hides this: the ladder only appears after you have cleared a random 25 to 75 percent of the floor, rerolled every floor, so without a readout there is no way to tell an unlucky floor from one you have barely started. Monsters count the same as rocks and cost no stamina, so the readout will often tell you to go fight something. Toggle under Settings > Accessibility; the position can be moved from the command line."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "x": (int, 3, 'readout x, in GUI pixels'),
    "y": (int, 46, 'readout y, in GUI pixels'),
}

def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}

#!/usr/bin/env python3
"""
Ladder Progress - a small Fields of Mistria mod.

Shows how close you are to revealing the ladder down, while you're in the mines.

The ladder isn't hidden somewhere waiting to be found - it does not exist until
you've cleared enough of the floor, and then it spawns wherever you made the
final break. The threshold is a fresh random 25-75% of the floor every time, so
without a readout there's no way to tell a slow floor from an unlucky one. This
puts the number on screen.

Counts the same things the game counts: small rocks, dirt rocks, ore nodes and
seams, barrels, crates and monsters. Large rocks and boulders are not ladder
candidates and are deliberately excluded by the game, so they never move it.

Toggleable in Settings > Accessibility ("Ladder Progress").

Usage:
    python ladder_progress.py --apply
    python ladder_progress.py --apply --x 3 --y 60
    python ladder_progress.py --remove
    python ladder_progress.py --status
"""



DUNGEON = "assets/gml/scripts/GameplaySystems/Dungeon/dungeon_utils.gml"
ARI = "assets/gml/objects/characters/obj_ari.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
MENU = "assets/gml/scripts/UI/Anchor/Menus/SettingsMenu.gml"
LOCAL = "assets/fiddle/misc_local.toml"

# Leading \n? because misc_local.toml has no trailing newline of its own.


# Shared with Crop Labels, which inserts after this same anchor. Both mods
# append their own call, so they interleave rather than collide.
STEP_ANCHOR = """        step_end: function() {
            if !non_cutscene_pause() {
                self.fsm.end_step();
                ARI.update();
"""

SETTINGS_ANCHOR = "        can_burn_fruit_trees: true,\n"
MENU_ANCHOR = ('        self.checkbox("screenshake");\n'
               '        self.checkbox("screen_flash");\n')

HELPER = """
//
// Ladder Progress: a HUD readout of how close the floor is to revealing its
// ladder down.
//
// Styled as a HUD element, not a tooltip: spr_ui_hud_info_backplate_middle is
// the same nine-slice the info HUD stacks for essence and gold, and the game's
// convention for a persistent readout is icon + number with no words. A tooltip
// box would have been the idiom for a transient hover popup instead.
//
// Anchor nodes rather than raw drawing - raw drawing inherits whatever shader
// LUT was last bound and comes out mistinted.
//
#macro LADDER_PROGRESS_NODES global.__ladder_progress_nodes
LADDER_PROGRESS_NODES = undefined;

function ladder_progress_nodes() {
    var menu = ANCHOR.get_menu(Menu.Vitals);
    if menu == undefined {
        return undefined;
    }

    var existing = LADDER_PROGRESS_NODES;
    if existing != undefined && !existing.card.freed && !existing.text.freed {
        return existing;
    }

    var card = ANCHOR.nine_slice(menu.canvas)
        .set_sprite(spr_ui_hud_info_backplate_middle)
        .set_align(Align.LeftIn, Align.TopIn)
        .set_alpha(0);

    //
    var icon = ANCHOR.sprite(card)
        .set_sprite(spr_ui_skill_icon_mining)
        .set_align(Align.LeftIn, Align.Middle)
        .set_x(4)
        .set_alpha(0);

    var text = ANCHOR.text(icon)
        .set_lut(COMMON_LUT, CommonLutIndex.Standard)
        .set_align(Align.RightOut, Align.Middle)
        .set_x(3)
        .allow_line_breaks(false)
        .prevent_spillover(false)
        .set_alpha(0);

    LADDER_PROGRESS_NODES = { card: card, icon: icon, text: text };
    return LADDER_PROGRESS_NODES;
}

//
// The readout text, or undefined when there is nothing worth showing.
//
function ladder_progress_text() {
    if SETTINGS.get("ladder_progress") == false {
        return undefined;
    }
    if !is_dungeon_room(room()) || is_special_dungeon_room(room()) {
        return undefined;
    }
    if DUNGEON_RUNNER == undefined {
        return undefined;
    }

    //
    // Once the ladder is out there is nothing left to track.
    //
    if instance_exists(obj_dungeon_ladder_down) {
        return undefined;
    }

    var needed = DUNGEON_RUNNER.ladder_score_needed;
    if needed == undefined || needed <= 0 {
        return undefined;
    }

    var score = min(DUNGEON_RUNNER.ladder_score, needed);
    return string(score) + " / " + string(needed);
}

function ladder_progress_update() {
    var nodes = ladder_progress_nodes();
    if nodes == undefined {
        return;
    }

    var label = ladder_progress_text();
    if label == undefined {
        nodes.card.set_alpha(0);
        nodes.icon.set_alpha(0);
        nodes.text.set_alpha(0);
        return;
    }

    nodes.text.set_text(label);

    //
    // 4px lead-in, 8px icon, 3px gap, text, 5px tail. The backplate nine-slice
    // has 7x7 corners, so keep it at least 16 tall for them to render cleanly.
    //
    var size = nodes.text.measure();
    nodes.card.set_size(size.x + 20, max(size.y + 6, 16));
    nodes.card.set_xy(__X__, __Y__);

    nodes.card.set_alpha(1);
    nodes.icon.set_alpha(1);
    nodes.text.set_alpha(1);
}
"""




def _patches(x, y):
    helper = HELPER.replace("__X__", str(x)).replace("__Y__", str(y))
    return {
        DUNGEON: [(APPEND, block(helper))],
        ARI: [(STEP_ANCHOR, STEP_ANCHOR + block("ladder_progress_update();", " " * 16))],
        SETTINGS: [(SETTINGS_ANCHOR,
                    SETTINGS_ANCHOR + block("ladder_progress: true,", " " * 8))],
        MENU: [(MENU_ANCHOR,
                block('self.checkbox("ladder_progress");', " " * 8) + MENU_ANCHOR)],
        LOCAL: [(APPEND, block('ladder_progress = "Ladder Progress"', toml=True))],
    }




def patches(mk, opt):
    return _patches(opt["x"], opt["y"])
