"""Barn Labels - hover an animal to see its name, hearts, and today's care.

The journal's Animals tab shows every animal's hearts with a fed tick and a
petted tick, which is exactly what you want to know while you are standing
in the barn, and exactly when you don't want to open the journal. This puts
the same three facts on a card above the animal under the cursor, or the
nearest one on a controller: its name, its hearts out of ten, and whether
it has been fed and petted today - the three things the nightly check in
Stable.gml judges it on. Words rather than ticks, so it reads without
colour.

The card is the Crop Labels card: two Anchor nodes on the vitals HUD,
updated from obj_ari's step_end, sized by measure() and placed in GUI
space just above the animal's sprite.

    python install.py apply barn-labels
    python install.py apply barn-labels --reach 48
    python install.py remove barn-labels
"""

from ..patcher import Markers

SLUG = "barn_labels"
NAME = "Barn Labels"
SUMMARY = "Hover an animal to see its name, hearts, and whether it has been fed and petted today."
DETAILS = """Point at any of your animals and a card above it shows its name, its hearts out of ten, and whether it has been fed and petted today, the same facts the journal's Animals tab keeps, without opening the journal. On a controller the card follows the nearest animal within a couple of tiles. Words rather than coloured ticks, so it reads with no colour vision. Toggle under Settings > Accessibility; a command-line option sets the controller reach."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "reach": (int, 32, "on a controller, pixels from Ari within which the nearest animal shows (8 = 1 tile)"),
}


def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}


# --- files -------------------------------------------------------------------

ANIMAL_UTILS = "assets/gml/scripts/GameplaySystems/Ranching/AnimalUtils.gml"
ARI = "assets/gml/objects/characters/obj_ari.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
MENU = "assets/gml/scripts/UI/Anchor/Menus/SettingsMenu.gml"
LOCAL = "assets/fiddle/misc_local.toml"

# --- the helpers, appended to AnimalUtils.gml --------------------------------

HELPERS = """
//
// Barn Labels: a card over the animal under the cursor - or the nearest one
// on a controller - with its name, its hearts, and whether it has been fed
// and petted today: the three things the nightly check judges it on.
//
// Built from Anchor nodes on the vitals HUD, like the crop labels: raw
// world-space text inherits whatever LUT the last shader pass left bound,
// and Anchor already owns that state.
//
#macro BARN_LABEL_NODES global.__barn_label_nodes
BARN_LABEL_NODES = undefined;

function barn_labels_nodes() {
    var menu = ANCHOR.get_menu(Menu.Vitals);
    if menu == undefined {
        return undefined;
    }

    var existing = BARN_LABEL_NODES;
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
        .prevent_spillover(false)
        .set_alpha(0);

    BARN_LABEL_NODES = { card: card, text: text };
    return BARN_LABEL_NODES;
}

//
// The animal to describe: the one nearest the pointer with a mouse, if the
// pointer is on it; on a controller, the nearest one within reach of Ari.
// instance_nearest() answers undefined when there is none, as the game's
// own callers expect of it.
//
function barn_labels_target() {
    if !instance_exists(obj_ari) {
        return undefined;
    }
    if obj_ari.using_mouse {
        var under = instance_nearest(mouse_x(), mouse_y(), obj_player_animal);
        if under != undefined && point_distance(mouse_x(), mouse_y(), under.x, under.y) <= 20 {
            return under;
        }
        return undefined;
    }
    var near = instance_nearest(obj_ari.x, obj_ari.y, obj_player_animal);
    if near != undefined && point_distance(obj_ari.x, obj_ari.y, near.x, near.y) <= @REACH@ {
        return near;
    }
    return undefined;
}

function barn_labels_update() {
    var nodes = barn_labels_nodes();
    if nodes == undefined {
        return;
    }

    var target = undefined;
    if SETTINGS.get("barn_labels") && !MIST.is_running() {
        target = barn_labels_target();
    }
    if target == undefined || !instance_exists(target) || target.me == undefined {
        nodes.card.set_alpha(0);
        nodes.text.set_alpha(0);
        return;
    }

    var me = target.me;
    var label = me.name + "   " + local_get("misc_local/barn_hearts") + " "
        + string(points_to_animal_heart_level(me.heart_points)) + "/10";
    label += "\\n" + local_get(me.has_eaten ? "misc_local/barn_fed" : "misc_local/barn_unfed")
        + " - " + local_get(me.has_been_pat ? "misc_local/barn_pet" : "misc_local/barn_unpet");
    nodes.text.set_text(label);

    var size = nodes.text.measure();
    var card_w = size.x + 10;
    var card_h = max(size.y + 6, 16);
    nodes.card.set_size(card_w, card_h);

    //
    // Anchor lays out in GUI space, 1:1 with the camera view, so a world
    // position converts by subtracting the camera origin.
    //
    var gx = target.x - CAMERA.left();
    var gy = target.bbox_top - CAMERA.top();
    nodes.card.set_xy(gx - (card_w / 2), gy - card_h - 4);

    nodes.card.set_alpha(1);
    nodes.text.set_alpha(1);
}
"""

# --- obj_ari: the shared step_end site --------------------------------------

STEP_ANCHOR = """        step_end: function() {
            if !non_cutscene_pause() {
                self.fsm.end_step();
                ARI.update();
"""

# --- settings ----------------------------------------------------------------

SETTINGS_ANCHOR = "        can_burn_fruit_trees: true,\n"

MENU_ANCHOR = ('        self.checkbox("screenshake");\n'
               '        self.checkbox("screen_flash");\n')

LABELS = '''barn_labels = "Barn Labels"
barn_hearts = "Hearts"
barn_fed = "Fed"
barn_unfed = "Not fed"
barn_pet = "Petted"
barn_unpet = "Not petted"'''


# The player-visible text this mod adds; the framework mirrors it into every
# language's table so it never renders as MISSING.
TRANSLATE = {"misc_local": LABELS}


def patches(mk, opt):
    gml = HELPERS.replace("@REACH@", str(max(8, int(opt["reach"]))))
    return {
        ANIMAL_UTILS: [(mk.APPEND, mk.block(gml))],
        ARI: [(STEP_ANCHOR, STEP_ANCHOR + mk.block("barn_labels_update();", " " * 16))],
        SETTINGS: [(SETTINGS_ANCHOR,
                    SETTINGS_ANCHOR + mk.block("barn_labels: true,", " " * 8))],
        MENU: [(MENU_ANCHOR,
                MENU_ANCHOR + mk.block('self.checkbox("barn_labels");', " " * 8))],
        LOCAL: [(mk.APPEND, mk.block(LABELS, toml=True))],
    }
