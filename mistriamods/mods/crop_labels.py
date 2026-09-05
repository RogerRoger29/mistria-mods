"""Crop Labels - a small Fields of Mistria mod."""

from ..patcher import Markers

SLUG = "crop_labels"
NAME = "Crop Labels"
SUMMARY = "Hold F to see what a crop is and how many days until harvest."
DETAILS = """Hold F and the crop you are aiming at shows its name and how many days until harvest, from any distance. It understands regrowing crops, so a strawberry plant that has already fruited tells you the regrowth time rather than the full growth time. The key is a real control called Show Crop Labels and can be rebound under Settings > Controls."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "key": (str, 'F', 'DEFAULT key only; rebind in game afterwards'),
}

def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}

#!/usr/bin/env python3
"""
Crop Labels - a small Fields of Mistria mod.

Hold a key and the crop you're pointing at tells you what it is and how many
days until it's ready. The game has no way to identify a plant already in the
ground - the grow-time tooltip only appears on seeds you're holding - so mystery
stems stay mysteries until they've grown.

The key is a real, rebindable control: it registers a new "Show Crop Labels"
action that appears in Settings > Controls alongside everything else, so you can
change it in game without re-patching. It defaults to F.

Reads regrowing crops correctly - after the first harvest they follow a shorter
schedule, and the countdown uses that one.

Usage:
    python crop_labels.py --apply
    python crop_labels.py --apply --key V
    python crop_labels.py --remove
    python crop_labels.py --status
"""



CROPS = "assets/gml/scripts/GameplaySystems/Data/Grid/Crops.gml"
ARI = "assets/gml/objects/characters/obj_ari.gml"
INPUTUTILS = "assets/gml/scripts/GameplaySystems/Input/InputUtils.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
LOCAL = "assets/fiddle/misc_local.toml"
# Label shown in Settings > Controls; the menu looks up
# misc_local/input_{snake_case_of_enum}.
LABELS = 'input_show_crop_labels = "Show Crop Labels"'

# misc_local.toml is TOML, so it needs hash comments.
# Leading \n? because misc_local.toml has no trailing newline of its own: the
# append supplies one, and removal has to take it back for an exact round-trip.
# Safe here because this file only ever gets the single appended block.


# --- anchors -----------------------------------------------------------------

# Single-line anchors, so this and Daily Checklist can each register a control
# without disturbing the other's anchor whichever order they are applied in.
ENUM_ANCHOR = "    ResetControls,\n"

# Both of these switches end in `impossible(...)`, so a new InputId that isn't
# added to BOTH of them crashes the game the moment it is looked up.
CATEGORY_ANCHOR = "        case InputId.Ride:\n"

DEFAULTS_ANCHOR = ('        case InputId.ConfirmTextInput: return '
                   '["enter", undefined, "start", undefined];\n')

STEP_ANCHOR = """        step_end: function() {
            if !non_cutscene_pause() {
                self.fsm.end_step();
                ARI.update();
"""

HELPER = """
//
// Crop Labels: a tooltip card naming the crop under the cursor.
//
// Built from Anchor nodes rather than raw draw calls. Raw world-space text
// inherits whatever LUT the previous shader pass left bound - which is why the
// first attempt came out red - and Anchor already owns that state, so this also
// gets exactly the same card the map name labels use.
//
#macro CROP_LABEL_NODES global.__crop_label_nodes
CROP_LABEL_NODES = undefined;

function crop_labels_nodes() {
    //
    var menu = ANCHOR.get_menu(Menu.Vitals);
    if menu == undefined {
        return undefined;
    }

    var existing = CROP_LABEL_NODES;
    if existing != undefined && !existing.card.freed && !existing.text.freed {
        return existing;
    }

    var card = ANCHOR.nine_slice(menu.canvas)
        .set_sprite(spr_ui_tooltip_box)
        .set_align(Align.LeftIn, Align.TopIn)
        .set_alpha(0);

    var text = ANCHOR.text(card)
        .set_lut(COMMON_LUT, CommonLutIndex.Standard)
        .set_align(Align.Center, Align.Middle)
        .allow_line_breaks(false)
        .prevent_spillover(false)
        .set_alpha(0);

    CROP_LABEL_NODES = { card: card, text: text };
    return CROP_LABEL_NODES;
}

//
// What is planted at this cell, and how long until it is ready?
//
function crop_label_for(xx, yy) {
    if xx < 0 || yy < 0 || xx >= GRID.dims.x || yy >= GRID.dims.y {
        return undefined;
    }

    var ni = GRID.node_index_for_cell(xx, yy);
    var object_id = GRID.node_object_id[ni];
    if object_id == undefined {
        return undefined;
    }
    if object_id_to_object_category(object_id) != ObjectCategory.Crop {
        return undefined;
    }

    var node = GRID.node_parent[ni];
    var proto = node.prototype;
    if proto.harvest == undefined {
        return undefined;
    }

    //
    // A crop that has already fruited once regrows on a shorter schedule, so
    // count against whichever table it is currently on.
    //
    var stages = proto.day_to_stage;
    if node.regrow_cycle && proto.post_harvest_day_to_stage != undefined {
        stages = proto.post_harvest_day_to_stage;
    }

    //
    // 47 forageables define no day_to_stage and inherit the default [0], so a
    // naive countdown reports every one of them as "ready" forever. A crop with
    // no real schedule gets its name and nothing else.
    //
    var total = stages.count() - 1;
    var left = total - node.day_count;
    var name = local_get(ITEM_PROTOTYPES[proto.harvest].name_key);

    var label = name;
    if total > 0 {
        label = left <= 0 ? name + " - ready" : name + " - " + string(left) + "d";
    }

    return {
        text: label,
        x: GRID.node_top_left_x[ni],
        y: GRID.node_top_left_y[ni],
    };
}

function crop_labels_update() {
    var nodes = crop_labels_nodes();
    if nodes == undefined {
        return;
    }

    var label = undefined;
    if INPUT.check(InputId.ShowCropLabels) && instance_exists(obj_ari) {
        //
        // Point at anything on screen, not just what is in reach. cell_select is
        // the tool cursor and the game clamps it to range, so with a mouse we
        // read the pointer directly. On controller there is no pointer, so fall
        // back to the cursor.
        //
        if obj_ari.using_mouse {
            label = crop_label_for(mouse_x() div 8, mouse_y() div 8);
        } else {
            label = crop_label_for(obj_ari.cell_select.x, obj_ari.cell_select.y);
        }
    }

    if label == undefined {
        nodes.card.set_alpha(0);
        nodes.text.set_alpha(0);
        return;
    }

    nodes.text.set_text(label.text);

    var size = nodes.text.measure();
    var card_w = size.x + 10;
    var card_h = max(size.y + 6, 16);
    nodes.card.set_size(card_w, card_h);

    //
    // Anchor lays out in GUI space, which is 1:1 with the camera view, so a
    // world position converts by subtracting the camera origin.
    //
    var gx = (label.x * 8) + 8 - CAMERA.left();
    var gy = (label.y * 8) - CAMERA.top();
    nodes.card.set_xy(gx - (card_w / 2), gy - card_h - 2);

    nodes.card.set_alpha(1);
    nodes.text.set_alpha(1);
}
"""




def _patches(key):
    default = '["%s", undefined, undefined, undefined]' % key.lower()
    return {
        INPUTUTILS: [
            # New action, inserted after ResetControls and so before LEN - no
            # existing input id shifts.
            (ENUM_ANCHOR, ENUM_ANCHOR + block("ShowCropLabels,", "    ")),
            # Must be categorised, or input_id_to_input_category() hits impossible().
            (CATEGORY_ANCHOR,
             CATEGORY_ANCHOR + block("case InputId.ShowCropLabels:", "        ")),
        ],
        SETTINGS: [
            # Missing bindings fall back to this, so existing settings.json
            # picks the default up without any migration.
            (
                DEFAULTS_ANCHOR,
                DEFAULTS_ANCHOR
                + block("case InputId.ShowCropLabels: return %s;" % default,
                        "        "),
            ),
        ],
        LOCAL: [
            (APPEND, block(LABELS, toml=True)),
        ],
        CROPS: [(APPEND, block(HELPER))],
        ARI: [
            # Driven from step_end, not a draw event: the label is Anchor nodes
            # whose position we update, not something we paint each frame.
            (STEP_ANCHOR, STEP_ANCHOR + block("crop_labels_update();", " " * 16)),
        ],
    }


# The player-visible text this mod adds; the framework mirrors it into every
# language's table so it never renders as MISSING.
TRANSLATE = {"misc_local": LABELS}


def patches(mk, opt):
    return _patches(opt["key"])
