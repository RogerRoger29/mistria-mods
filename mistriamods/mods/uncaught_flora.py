"""Sparkles on wild forage, bushes and fruit trees the museum still needs.

The Flora-wing companion to Uncaught Sparkles. Any world plant whose harvest
is a Flora-wing item not yet on display carries a looping white twinkle:
wild forage (mushrooms, herbs, wild flowers), harvestable bushes, and fruit
trees. Luminance and motion only - no colour vision required. Toggleable in
Settings > Accessibility ("Uncaught Forage Sparkles"), on by default.

What is a "plant" here: every world object is a grid node drawn by one
`obj_node_renderer` instance, and every renderer is built through a single
`init(node, ...)`. That one function is the hook, and the node's prototype
says what the plant yields:

  forage   ObjectCategory.Crop with CropFlag.FORAGEABLE, `prototype.harvest`
  bushes   ObjectCategory.Bush, `prototype.harvest` (undefined for the
           plain decorative bush, whose harvest is the sentinel "__none__")
  trees    ObjectCategory.Tree with `prototype.fruit_data.harvest`

Farm crops are deliberately left out: they are ObjectCategory.Crop too, but
without the FORAGEABLE flag - and a field of forty turnips twinkling at once
would drown the signal this mod exists to give. You know what you planted.

The twinkle is the same follower effect Uncaught Sparkles uses, with one
addition: an opt-in `orphan_dies` flag on `obj_animation_effect`, so that a
follower whose target instance is gone destroys itself next step. Renderers
die on harvest, on leaving a location, and en masse in
remake_room_renderers(); the flag covers every path with no teardown code
in the renderer at all, and it is opt-in so no vanilla effect changes.

Bush and tree twinkles reflect the species, not whether fruit is on it right
now - renderers persist across days and are only rebuilt when you re-enter
the area, so a just-picked rose bush keeps its twinkle until then. Wild
forage is single-stage and harvestable on sight, so no such gap exists.
"""

from ..patcher import Markers

SLUG = "uncaught_flora"
NAME = "Uncaught Flora"
SUMMARY = "Wild forage, bushes and fruit trees the museum's Flora wing still needs twinkle too."
DETAILS = """The same twinkle on plants: wild forage such as mushrooms, herbs and wild flowers, harvestable bushes, and fruit trees whose harvest the museum's Flora wing still lacks. Farm crops are deliberately left out, since a field of forty twinkling turnips would drown the signal - you know what you planted. Bush and tree twinkles reflect the species rather than whether fruit is on it right now, and refresh when you re-enter an area. Toggle under Settings > Accessibility."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {}


def defaults():
    return {}


RENDERER = "assets/gml/objects/objects/obj_node_renderer.gml"
EFFECT = "assets/gml/objects/objects/obj_animation_effect.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
MENU = "assets/gml/scripts/UI/Anchor/Menus/SettingsMenu.gml"
LOCAL = "assets/fiddle/misc_local.toml"

# --- the renderer ------------------------------------------------------------
#
# Right after init() learns what it is drawing. node and prototype are set;
# nothing below in init() is needed. The lifts put the twinkle in the body of
# each plant rather than at its feet: forage sprites are ~20px, bushes 32px,
# trees taller still.

INIT_ANCHOR = ("                self.object_category = "
               "object_id_to_object_category(self.object_id);\n")

INIT_EFFECT = """//
// Uncaught Flora: a twinkle on wild forage, bushes and fruit trees whose
// harvest the museum's Flora wing still lacks.
//
self.flora_sparkle = undefined;
if SETTINGS.get("uncaught_flora") {
    var flora_item = undefined;
    var flora_lift = 0;

    switch self.object_category {
        case ObjectCategory.Crop:
            if node[$ "ctx"] != undefined && has_flag(node.ctx, CropFlag.FORAGEABLE) {
                flora_item = node.prototype.harvest;
                flora_lift = 10;
            }
            break;
        case ObjectCategory.Bush:
            flora_item = node.prototype.harvest;
            flora_lift = 18;
            break;
        case ObjectCategory.Tree:
            if node.prototype[$ "fruit_data"] != undefined {
                flora_item = node.prototype.fruit_data.harvest;
                flora_lift = 40;
            }
            break;
        default:
            break;
    }

    if flora_item != undefined
        && MUSEUM_DATA != undefined
        && MUSEUM_DATA.is_museum_item(flora_item)
        && MUSEUM_PROGRESS[flora_item] != true
    {
        var flora_twinkle = choose(spr_fx_twinkle_1, spr_fx_twinkle_2, spr_fx_twinkle_3);
        self.flora_sparkle = create_animation_effect_on_object(self, flora_twinkle, -1, -flora_lift);
        self.flora_sparkle.live_on_anim_end = true;
        self.flora_sparkle.orphan_dies = true;
        self.flora_sparkle.image_index = irandom(self.flora_sparkle.image_number - 1);
    }
}
"""

# --- the effect --------------------------------------------------------------
#
# Vanilla followers stop following when their target goes and otherwise live
# out their lifetime; a looping one would sit at the empty spot forever. The
# flag is opt-in, so nothing vanilla changes.

# Two lines, not one: `self.following_object = undefined;` also appears in
# release_object(), and this must land in the create event.
EFFECT_CREATE_ANCHOR = """            self.following_object = undefined;
            self.relative_depth = 0;
"""

EFFECT_CREATE_EFFECT = """//
// Uncaught Flora: opt-in - die when the followed instance is gone.
//
self.orphan_dies = false;
"""

EFFECT_STEP_ANCHOR = ("            if self.following_object != undefined "
                      "&& instance_exists(self.following_object) {\n")

EFFECT_STEP_EFFECT = """//
// Uncaught Flora: a follower that was told to die with its target.
//
if self.orphan_dies
    && self.following_object != undefined
    && !instance_exists(self.following_object)
{
    instance_destroy();
    return;
}
"""

# --- settings ----------------------------------------------------------------

SETTINGS_ANCHOR = "        can_burn_fruit_trees: true,\n"

MENU_ANCHOR = ('        self.checkbox("screenshake");\n'
               '        self.checkbox("screen_flash");\n')

LABELS = 'uncaught_flora = "Uncaught Forage Sparkles"'


def patches(mk, opt):
    return {
        RENDERER: [
            (INIT_ANCHOR, INIT_ANCHOR + mk.block(INIT_EFFECT, " " * 16)),
        ],
        EFFECT: [
            (EFFECT_CREATE_ANCHOR,
             EFFECT_CREATE_ANCHOR + mk.block(EFFECT_CREATE_EFFECT, " " * 12)),
            (EFFECT_STEP_ANCHOR,
             mk.block(EFFECT_STEP_EFFECT, " " * 12) + EFFECT_STEP_ANCHOR),
        ],
        SETTINGS: [
            (SETTINGS_ANCHOR,
             SETTINGS_ANCHOR + mk.block("uncaught_flora: true,", " " * 8)),
        ],
        MENU: [
            (MENU_ANCHOR,
             mk.block('self.checkbox("uncaught_flora");', " " * 8)
             + MENU_ANCHOR),
        ],
        LOCAL: [(mk.APPEND, mk.block(LABELS, toml=True))],
    }
