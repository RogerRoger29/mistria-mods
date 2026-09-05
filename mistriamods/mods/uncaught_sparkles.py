"""Sparkles on insects the museum still needs.

An accessibility mod: every insect whose species is not yet on display in the
museum's Insect wing carries a looping white twinkle, so it can be told apart
from the rest by luminance and motion alone - no colour vision required.
Toggleable in Settings > Accessibility ("Uncaught Insect Sparkles"), on by
default.

Donation state, not catch state: `MUSEUM_PROGRESS[item_id]` is the very flag
the museum reads, so a species you have caught but not yet handed in keeps
sparkling until it is on display - which is the moment it stops mattering.

The art is the game's own. `spr_fx_twinkle_1/2/3` ship in the atlas but are
referenced by no GML at all - dormant assets, 18x18, pure white four-point
stars, the strongest luminance signal in the fx set (the bug-pheromone fx,
also dormant, are faint drifting specks that vanish in greyscale). Each bug
picks one of the three at random and starts on a random frame so a crowd
never twinkles in lockstep.

The effect is an `obj_animation_effect` following the bug, the same follower
Guardian's Shield uses on Ari. Two things it does not do on its own: it only
loops if `live_on_anim_end` is set (otherwise it dies at the end of the first
cycle), and when its target is destroyed it merely stops following - it never
dies. So the bug's own destroy handler puts it down, covering catch, flee and
despawn alike. Height and alpha are mirrored every step, which makes fliers'
hover, jumpers' arcs, canopy drop-ins, the flee fade and cutscene hiding all
fall out of one assignment each.
"""

from ..patcher import Markers

SLUG = "uncaught_sparkles"
NAME = "Uncaught Sparkles"
SUMMARY = "Insects the museum still needs carry a white twinkle, readable without colour vision."
DETAILS = """Every insect whose species is not yet on display in the museum's Insect wing carries a looping white twinkle, so you can tell it apart by brightness and motion alone - built for players with little or no colour vision. It tracks what is actually donated, not what you have caught, so a species you have caught but not handed in keeps sparkling until it is on display. The twinkles are the game's own unused star effects. Toggle under Settings > Accessibility; a command-line option raises the twinkle if it sits too low on a species."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "lift": (int, 0, "pixels to raise the twinkle above the insect"),
}


def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}


OBJ_BUG = "assets/gml/objects/characters/obj_bug.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
MENU = "assets/gml/scripts/UI/Anchor/Menus/SettingsMenu.gml"
LOCAL = "assets/fiddle/misc_local.toml"

# --- obj_bug -----------------------------------------------------------------

# The field must exist before setup() can run: setup() destroys the bug on
# unacceptable terrain, and the destroy handler below reads it.
CREATE_ANCHOR = "            self.shadow_caster = SHADOW_GRID.caster_create(x, y);\n"

CREATE_EFFECT = """//
// Uncaught Sparkles: the follower effect, if this bug earns one.
//
self.sparkle = undefined;
"""

# The end of setup(): past the terrain check that can destroy the bug, past
# the state choice, before the cutscene hide (which the per-step alpha mirror
# covers anyway).
SETUP_ANCHOR = """                if MIST.is_running() {
                    self.cutscene_started();
                }
"""

SETUP_EFFECT = """//
// Uncaught Sparkles: a species the Insect wing still lacks gets a twinkle.
// MUSEUM_PROGRESS is what the museum itself reads, so this tracks what is
// on display, not what has ever been caught.
//
if SETTINGS.get("uncaught_sparkles")
    && self.item_id != undefined
    && MUSEUM_DATA != undefined
    && MUSEUM_DATA.is_museum_item(self.item_id)
    && MUSEUM_PROGRESS[self.item_id] != true
{
    var twinkle = choose(spr_fx_twinkle_1, spr_fx_twinkle_2, spr_fx_twinkle_3);
    self.sparkle = create_animation_effect_on_object(self, twinkle, -1, self.z);
    self.sparkle.live_on_anim_end = true;
    self.sparkle.image_index = irandom(self.sparkle.image_number - 1);
}
"""

STEP_ANCHOR = "            depth = get_instance_depth(y, z);\n"

# Bugs draw at y + z; the follower only knows y. Mirroring z each step keeps
# the twinkle on the insect through hover, jump arc and canopy drop-in, and
# mirroring alpha covers the flee fade-out and cutscene hiding for free.
STEP_EFFECT = """//
// Uncaught Sparkles: ride the bug's height and share its alpha.
//
if self.sparkle != undefined && instance_exists(self.sparkle) {
    self.sparkle.y_offset = self.z - %d;
    self.sparkle.image_alpha = self.image_alpha;
}
"""

DESTROY_ANCHOR = """                instance_destroy(self.light);
                self.light = undefined;
            }
"""

DESTROY_EFFECT = """//
// Uncaught Sparkles: the follower would outlive the bug - it only stops
// following when its target goes, it never dies - so it is put down here,
// on catch, flee and despawn alike.
//
if self.sparkle != undefined {
    if instance_exists(self.sparkle) {
        instance_destroy(self.sparkle);
    }
    self.sparkle = undefined;
}
"""

# --- settings ----------------------------------------------------------------
#
# The same shared single-line anchors every toggle-bearing mod uses; each
# inserts beside them and they survive one another in any order.

SETTINGS_ANCHOR = "        can_burn_fruit_trees: true,\n"

MENU_ANCHOR = ('        self.checkbox("screenshake");\n'
               '        self.checkbox("screen_flash");\n')

LABELS = 'uncaught_sparkles = "Uncaught Insect Sparkles"'


# The player-visible text this mod adds; the framework mirrors it into every
# language's table so it never renders as MISSING.
TRANSLATE = {"misc_local": LABELS}


def patches(mk, opt):
    return {
        OBJ_BUG: [
            (CREATE_ANCHOR,
             CREATE_ANCHOR + mk.block(CREATE_EFFECT, " " * 12)),
            (SETUP_ANCHOR,
             mk.block(SETUP_EFFECT, " " * 16) + SETUP_ANCHOR),
            (STEP_ANCHOR,
             STEP_ANCHOR + mk.block(STEP_EFFECT % opt["lift"], " " * 12)),
            (DESTROY_ANCHOR,
             DESTROY_ANCHOR + mk.block(DESTROY_EFFECT, " " * 12)),
        ],
        SETTINGS: [
            (SETTINGS_ANCHOR,
             SETTINGS_ANCHOR + mk.block("uncaught_sparkles: true,", " " * 8)),
        ],
        MENU: [
            (MENU_ANCHOR,
             mk.block('self.checkbox("uncaught_sparkles");', " " * 8)
             + MENU_ANCHOR),
        ],
        LOCAL: [(mk.APPEND, mk.block(LABELS, toml=True))],
    }
