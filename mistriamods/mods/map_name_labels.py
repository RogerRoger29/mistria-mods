"""Map Name Labels - a small Fields of Mistria mod."""

from ..patcher import Markers

SLUG = "map_name_labels"
NAME = "Map Name Labels"
SUMMARY = "Hover a villager's head on the map screen to see their name."
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "card": (bool, True, 'tooltip card behind the name'),
}

def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}

#!/usr/bin/env python3
"""
Map Name Labels - a small Fields of Mistria mod.

Hover a villager's head on the map screen and their name appears above it.
The map packs several 11x11 head icons into one grid per location hub, which
makes them genuinely hard to tell apart; hovering disambiguates a cluster that
squinting can't.

Villagers you haven't met read "???", matching how the relationships menu
already treats them, so this reveals nothing you haven't earned.

Like the other mods here, this edits the GML the game compiles out of
assets.zip at startup. Insertions are wrapped in MAP_NAME_LABELS markers, so
the patch is idempotent, removable, and composes with the other mods.

Usage:
    python map_name_labels.py --apply
    python map_name_labels.py --remove
    python map_name_labels.py --status
"""



MAPMENU = "assets/gml/scripts/UI/Anchor/Menus/MapMenu.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
MENU = "assets/gml/scripts/UI/Anchor/Menus/SettingsMenu.gml"
LOCAL = "assets/fiddle/misc_local.toml"



# Leading \n? because misc_local.toml has no trailing newline of its own.

SETTINGS_ANCHOR = "        can_burn_fruit_trees: true,\n"
MENU_ANCHOR = ('        self.checkbox("screenshake");\n'
               '        self.checkbox("screen_flash");\n')

# The block that builds one head icon on the map. We hang the label off the end
# of it, so every icon the map draws gets one.
ICON_BLOCK = """                    node
                        .set_sprite(icon)
                        .set_xy(xx, yy)
                        .set_speed(1)
"""




# ---------------------------------------------------------------- the patches

HELPER = """
//
// Map Name Labels: give one map head icon a name that appears while hovered.
//
// add_text_label() is what makes this cheap: it parents a text node to the
// icon AND is the thing Anchor calls update() on each frame for sprite nodes.
// That update only runs while the node has run_logic set, which is exactly
// what listen_for_hovers() turns on - so one call buys us both the hover
// detection and the per-frame hook, and we never touch Anchor itself.
//
function map_name_label_attach(node, resident) {
    var key;
    if resident == ARI_MAP_SIGNUM {
        key = ANCHOR.wrap_for_local(ARI.name);
    } else if resident == PET_MAP_SIGNUM {
        key = ANCHOR.wrap_for_local(PET.name);
    } else if resident == CHILD_0_MAP_SIGNUM {
        key = ANCHOR.wrap_for_local(ARI.children[0].name);
    } else if resident == CHILD_1_MAP_SIGNUM {
        key = ANCHOR.wrap_for_local(ARI.children[1].name);
    } else if NPCS[resident].has_met() {
        //
        key = NPCS[resident].prototype.name;
    } else {
        //
        key = ANCHOR.wrap_for_local("???");
    }

    node.listen_for_hovers();
    node.add_text_label(key, COMMON_LUT);

    //
    // allow_line_breaks(false) is load-bearing. add_text_label() turns line
    // breaking ON, and a text node infers its wrap width from its PARENT - here
    // an 11px head icon - so the name would wrap after every single character
    // and read vertically. Names are short; never wrap them.
    //
    //
    // Text colour comes from a LUT index. add_text_label() leaves it on Source
    // (raw white glyphs with a dark outline), which is built for drawing over
    // the world - illegible on a pale tooltip card. Standard is what the game's
    // own tooltips use for body text on this very sprite.
    //
    node.text_label
        .set_align(Align.Center, Align.TopOut)
        .set_lut(COMMON_LUT, __LUT__)
        .allow_line_breaks(false)
        .prevent_spillover(false)
        .set_alpha(0);

__CARD__
    //
    //
    node.text_label.update = method(node.text_label, function() {
        //
        var showing = SETTINGS.get("map_name_labels") && self.target.in_hover ? 1 : 0;
        self.set_alpha(showing);

        var card = self.board_get("name_card");
        if card != undefined && !card.freed {
            card.set_alpha(showing);
        }
    });
}
"""

CARD_GML = """
    //
    // A tooltip card behind the name, using the game's own tooltip nine-slice.
    // Its frames are 8x8, so the box needs ~16px of height for the corners to
    // render cleanly - hence the floor on card_h.
    //
    var size = node.text_label.measure();
    var card_w = size.x + 10;
    var card_h = max(size.y + 6, 16);

    var card = ANCHOR.nine_slice(node, node.get_z() - 1)
        .set_sprite(spr_ui_tooltip_box)
        .set_align(Align.Center, Align.TopOut)
        .set_size(card_w, card_h)
        .set_alpha(0);

    //
    // Draw the text in front of the card, and centre it inside the card: both
    // are pinned to the icon's top edge, so the label has to rise by half the
    // difference in their heights.
    //
    node.text_label.set_z(node.get_z() - 2);
    node.text_label.set_y((size.y - card_h) / 2);
    node.text_label.board_set("name_card", card);
"""


def helper_gml(card):
    # On the pale card, dark-on-light. Without a card the name is drawn straight
    # over the map, where the outlined white glyphs are the readable choice.
    lut = "CommonLutIndex.Standard" if card else "CommonLutIndex.Source"
    return (HELPER
            .replace("__CARD__", CARD_GML.strip("\n") if card else "")
            .replace("__LUT__", lut))


def _patches(card):
    return {
        MAPMENU: [
            (
                ICON_BLOCK,
                ICON_BLOCK + block("map_name_label_attach(node, resident);",
                                   "                    "),
            ),
            (APPEND, block(helper_gml(card))),
        ],
        SETTINGS: [(SETTINGS_ANCHOR,
                    SETTINGS_ANCHOR + block("map_name_labels: true,", " " * 8))],
        MENU: [(MENU_ANCHOR,
                block('self.checkbox("map_name_labels");', " " * 8) + MENU_ANCHOR)],
        LOCAL: [(APPEND, block('map_name_labels = "Map Name Labels"', toml=True))],
    }




def patches(mk, opt):
    return _patches(opt["card"])
