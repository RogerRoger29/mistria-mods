"""Shovel Sense - dig sites give themselves away while the shovel is in hand.

Dig sites are small mounds that vanish into the scenery, and the mines only
offer a few per floor. This gives them a tell that lives in the world rather
than on the HUD: hold the shovel and every undug dig site within reach lets
out a puff of settling earth now and then (the game's own dirt-poof effect),
and the first site to come within a few tiles makes Ari think of archaeology
- a thought bubble with the archaeology icon, a soft chime, and a nudge of
controller rumble - once per site. Put the shovel away and the ground goes
quiet again.

Everything runs from obj_ari's step_end a few times a second: the cells
around Ari are scanned for ObjectId.DigSite nodes (2x2, even-aligned, so the
scan steps by two and counts each site once at its top-left). No renderer
gets a step event, nothing is stored on the node, nothing reaches the save.

    python install.py apply shovel-sense
    python install.py apply shovel-sense --radius 8 --reach 16
    python install.py apply shovel-sense --no-shovel-only
    python install.py remove shovel-sense
"""

from ..patcher import Markers

SLUG = "shovel_sense"
NAME = "Shovel Sense"
SUMMARY = "Hold the shovel: nearby dig sites puff loose earth, and Ari notices the first one that comes close."
DETAILS = """Dig sites are easy to walk past. With the shovel in hand, every undug dig site within reach lets out an occasional puff of settling earth, and the first one to come within a few tiles makes Ari notice it: a thought bubble with the archaeology icon, a soft chime, and a nudge of rumble on a controller, once per site. Put the shovel away and the ground goes quiet. It reads by motion and sound, so it needs no colour vision, and it works in the mines and the overworld alike. Toggle under Settings > Accessibility; command-line options set both radii, let it work without the shovel, and silence the chime."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "radius": (int, 5, "tiles within which Ari notices a dig site"),
    "reach": (int, 12, "tiles within which dig sites puff earth"),
    "shovel_only": (bool, True, "only while the shovel is held"),
    "sound": (bool, True, "the soft chime when Ari notices one"),
}


def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}


# --- files -------------------------------------------------------------------

DIGSITE = "assets/gml/scripts/GameplaySystems/Data/Grid/Digsite.gml"
ARI = "assets/gml/objects/characters/obj_ari.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
MENU = "assets/gml/scripts/UI/Anchor/Menus/SettingsMenu.gml"
LOCAL = "assets/fiddle/misc_local.toml"

# --- the helpers, appended to Digsite.gml ------------------------------------

HELPERS = """
//
// Shovel Sense: dig sites give themselves away while the shovel is in hand.
//
// Driven from obj_ari's step_end a few times a second. The cells around Ari
// are scanned for undug dig sites - 2x2 nodes on even coordinates, so the
// scan steps by two and counts each site once, at its top-left. Sites in
// reach let out a puff of settling earth now and then; the first site to
// come within the notice radius makes Ari think of archaeology, with a soft
// chime and a nudge of rumble - once per site, per floor, per day.
//
#macro SHOVEL_SENSE_SEEN global.__shovel_sense_seen
SHOVEL_SENSE_SEEN = {};
#macro SHOVEL_SENSE_TICK global.__shovel_sense_tick
SHOVEL_SENSE_TICK = 0;

function shovel_sense_active() {
    if !SETTINGS.get("shovel_sense") || MIST.is_running() {
        return false;
    }
    if !instance_exists(obj_ari) || GRID == undefined {
        return false;
    }
    if !@SHOVEL_ONLY@ {
        return true;
    }
    var held = ARI.held_item();
    return held != undefined && held.prototype.tags.contains("shovel");
}

function shovel_sense_update() {
    SHOVEL_SENSE_TICK += 1;
    if SHOVEL_SENSE_TICK % 15 != 0 || !shovel_sense_active() {
        return;
    }

    var ax = obj_ari.x div 8;
    var ay = obj_ari.y div 8;
    var reach = @REACH@;
    var notice = @NOTICE@;
    var floor_key = DUNGEON_RUNNER != undefined ? DUNGEON_RUNNER.current_floor : -1;
    var noticed = false;

    for (var cy = ((ay - reach) div 2) * 2; cy <= ay + reach; cy += 2) {
        for (var cx = ((ax - reach) div 2) * 2; cx <= ax + reach; cx += 2) {
            var ni = GRID.try_node_index_for_cell(cx, cy);
            if ni == undefined || GRID.node_object_id[ni] != ObjectId.DigSite {
                continue;
            }
            var node = GRID.node_parent[ni];
            var tx = node[$ "top_left_x"] ?? cx;
            var ty = node[$ "top_left_y"] ?? cy;
            if tx != cx || ty != cy {
                continue;
            }
            var px = tx * 8 + 8;
            var py = ty * 8 + 8;

            //
            // Settling earth, about every two seconds per site.
            //
            if irandom(7) == 0 {
                create_animation_effect(
                    px + irandom_range(-4, 4),
                    py + irandom_range(-2, 2),
                    get_instance_depth(ty * 8 + 16) - 1,
                    choose(spr_fx_poof1_dirt_once, spr_fx_poof2_dirt_once),
                );
            }

            //
            // The first close one Ari has not noticed yet.
            //
            if !noticed && abs(cx - ax) <= notice && abs(cy - ay) <= notice {
                var key = string(room()) + ":" + string(floor_key) + ":"
                    + string(total_days()) + ":" + string(cx) + ":" + string(cy);
                if SHOVEL_SENSE_SEEN[$ key] == undefined {
                    SHOVEL_SENSE_SEEN[$ key] = true;
                    noticed = true;
                    if !obj_ari.bark_emitter.is_barking() {
                        obj_ari.bark_emitter.emit(BarkId.Archaeology, BarkType.Thought, false);
                    }
                    if @SOUND@ {
                        TANGO.play("SoundEffects/NPCs/DialogSparkle", obj_ari.x, obj_ari.y);
                    }
                    set_rumble(RumbleKind.ItemCollect);
                }
            }
        }
    }
}
"""

# --- obj_ari: the shared step_end site --------------------------------------
#
# The same four lines crop-labels, daily-checklist and ladder-progress hang
# off; each inserts immediately after, so they survive each other in any
# order. Already inside the !non_cutscene_pause() guard.

STEP_ANCHOR = """        step_end: function() {
            if !non_cutscene_pause() {
                self.fsm.end_step();
                ARI.update();
"""

# --- settings ----------------------------------------------------------------

SETTINGS_ANCHOR = "        can_burn_fruit_trees: true,\n"

MENU_ANCHOR = ('        self.checkbox("screenshake");\n'
               '        self.checkbox("screen_flash");\n')

LABELS = 'shovel_sense = "Shovel Sense"'


# The player-visible text this mod adds; the framework mirrors it into every
# language's table so it never renders as MISSING.
TRANSLATE = {"misc_local": LABELS}


def patches(mk, opt):
    gml = (HELPERS
           .replace("@SHOVEL_ONLY@", "true" if opt["shovel_only"] else "false")
           .replace("@SOUND@", "true" if opt["sound"] else "false")
           .replace("@REACH@", str(max(1, int(opt["reach"])) * 2))
           .replace("@NOTICE@", str(max(1, int(opt["radius"])) * 2)))
    return {
        DIGSITE: [(mk.APPEND, mk.block(gml))],
        ARI: [(STEP_ANCHOR, STEP_ANCHOR + mk.block("shovel_sense_update();", " " * 16))],
        SETTINGS: [(SETTINGS_ANCHOR,
                    SETTINGS_ANCHOR + mk.block("shovel_sense: true,", " " * 8))],
        MENU: [(MENU_ANCHOR,
                MENU_ANCHOR + mk.block('self.checkbox("shovel_sense");', " " * 8))],
        LOCAL: [(mk.APPEND, mk.block(LABELS, toml=True))],
    }
