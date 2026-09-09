"""Hold a key for a checklist of what's left to do today, and what's coming.

The game tracks all of this and never puts it in one place: which crops still
need water, who you haven't greeted, who can still take a gift, and which
birthday or festival is next. This gathers it into one panel.

The key is a real, rebindable control, so it shows up in Settings > Controls
next to everything else. It defaults to V.
"""

from ..patcher import Markers

SLUG = "daily_checklist"
NAME = "Daily Checklist"
SUMMARY = "Hold V for today's unwatered crops, ungreeted villagers, gifts, birthdays and festivals."
DETAILS = """Hold V for a panel of what is left today and what is coming up: crops that still need watering, villagers you have not greeted, gifts you can still give, and once you keep animals, how many are still unfed, unpetted, or (from five o'clock) still outside, then the next birthday and the next festival. It only counts villagers you have actually met, so it never hints at someone you have not been introduced to. The key is a real control called Show Checklist and can be rebound under Settings > Controls."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "checklist_key": (str, "V", "DEFAULT key only; rebind in game afterwards"),
}


def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}


CROPS = "assets/gml/scripts/GameplaySystems/Data/Grid/Crops.gml"
ARI = "assets/gml/objects/characters/obj_ari.gml"
INPUTUTILS = "assets/gml/scripts/GameplaySystems/Input/InputUtils.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
LOCAL = "assets/fiddle/misc_local.toml"

# --- anchors -----------------------------------------------------------------
#
# Crop Labels registers a control too, so these anchors are chosen to survive
# its blocks: each is a single line that stays intact whichever mod goes first,
# and both insert immediately after it.

ENUM_ANCHOR = "    ResetControls,\n"
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
// Daily Checklist: one panel gathering what the game already knows but never
// shows together.
//
// Anchor nodes on the Vitals canvas, the same construction as the crop label
// card. The whole list is one text node with newlines rather than a node per
// line - simpler, and measure() then sizes the card to fit.
//
#macro CHECKLIST_NODES global.__checklist_nodes
#macro CHECKLIST_CACHE global.__checklist_cache
CHECKLIST_NODES = undefined;
CHECKLIST_CACHE = undefined;

function checklist_nodes() {
    var menu = ANCHOR.get_menu(Menu.Vitals);
    if menu == undefined {
        return undefined;
    }

    var existing = CHECKLIST_NODES;
    if existing != undefined && !existing.card.freed && !existing.text.freed {
        return existing;
    }

    var card = ANCHOR.nine_slice(menu.canvas)
        .set_sprite(spr_ui_tooltip_box)
        .set_align(Align.Center, Align.Middle)
        .set_alpha(0);

    var text = ANCHOR.text(card)
        .set_lut(COMMON_LUT, CommonLutIndex.Standard)
        .set_align(Align.Center, Align.Middle)
        .prevent_spillover(false)
        .set_alpha(0);

    CHECKLIST_NODES = { card: card, text: text };
    return CHECKLIST_NODES;
}

//
// How many planted crops on the farm still want watering. Crops sit on 2x2
// cells aligned to even coordinates, so stepping by 2 counts each one once.
//
function checklist_dry_crops() {
    var grid = GRIDS[LocationId.Farm];
    if grid == undefined {
        return 0;
    }

    var dry = 0;
    for (var xx = 0; xx < grid.dims.x; xx += 2) {
        for (var yy = 0; yy < grid.dims.y; yy += 2) {
            var ni = grid.node_index_for_cell(xx, yy);
            if grid.node_object_id[ni] == undefined {
                continue;
            }
            if object_id_to_object_category(grid.node_object_id[ni]) != ObjectCategory.Crop {
                continue;
            }
            // The game's own test: tilled soil, dry, no rug - so farm forage and
            // anything not on soil never count as thirsty.
            if can_water_node(grid, ni) {
                dry += 1;
            }
        }
    }

    return dry;
}

//
// Build the whole panel text. Called once when the key goes down, not every
// frame - the farm sweep above is too big to repeat while the key is held.
//
function checklist_build() {
    var season = CALENDAR.season();
    var today = CALENDAR.day();

    var to_greet = 0;
    var to_gift = 0;
    var next_birthday = undefined;
    var next_birthday_day = 999;

    for (var i = 0; i < NpcId.LEN; i++) {
        var npc = NPCS[i];
        if !npc.has_met() || !npc_is_unlocked(i) {
            continue;
        }

        if npc.times_spoken_today == 0 {
            to_greet += 1;
        }
        if npc.gift_flag {
            to_gift += 1;
        }

        //
        // birthday.day is 1-based while CALENDAR.day() is 0-based, which is why
        // the game's own calendar compares against `birthday.day - 1`.
        //
        if npc.prototype.birthday.season == season {
            var bday = npc.prototype.birthday.day - 1;
            if bday >= today && bday < next_birthday_day {
                next_birthday_day = bday;
                next_birthday = npc.prototype.name;
            }
        }
    }

    var next_festival = undefined;
    var next_festival_day = 999;
    for (var i = 0; i < FestivalId.LEN; i++) {
        var festival = FESTIVALS[i];
        if !festival.prototype.implemented {
            continue;
        }
        if festival.prototype.date.season != season {
            continue;
        }

        var fday = festival.prototype.date.day - 1;
        if fday >= today && fday < next_festival_day {
            next_festival_day = fday;
            next_festival = festival.prototype.name;
        }
    }

    var out = local_get("misc_local/checklist_title") + "  "
        + string(today + 1) + " / 28";

    out += "\\n\\n" + local_get("misc_local/checklist_today");
    out += "\\n" + string(checklist_dry_crops()) + " "
        + local_get("misc_local/checklist_dry");
    out += "\\n" + string(to_greet) + " " + local_get("misc_local/checklist_greet");
    out += "\\n" + string(to_gift) + " " + local_get("misc_local/checklist_gift");

    //
    // The animals, once there are any. The same three things the nightly
    // check in Stable.gml judges them on: fed, petted, and home. "Outside"
    // only matters toward evening, so it appears from five o'clock.
    //
    var animals = get_all_animals();
    if animals.count() > 0 {
        var not_fed = 0;
        var not_pet = 0;
        var outside = 0;
        for (var i = 0; i < animals.count(); i++) {
            var animal = animals.get(i);
            if !animal.has_eaten {
                not_fed += 1;
            }
            if !animal.has_been_pat {
                not_pet += 1;
            }
            if !animal.is_home() {
                outside += 1;
            }
        }
        out += "\\n" + string(not_fed) + " " + local_get("misc_local/checklist_unfed");
        out += "\\n" + string(not_pet) + " " + local_get("misc_local/checklist_unpet");
        if CLOCK.time >= hours(17) {
            out += "\\n" + string(outside) + " " + local_get("misc_local/checklist_outside");
        }
    }

    out += "\\n\\n" + local_get("misc_local/checklist_ahead");
    if next_birthday != undefined {
        out += "\\n" + local_get("misc_local/checklist_birthday") + " "
            + local_get(next_birthday) + ", " + string(next_birthday_day + 1);
    }
    if next_festival != undefined {
        out += "\\n" + local_get("misc_local/checklist_festival") + " "
            + local_get(next_festival) + ", " + string(next_festival_day + 1);
    }

    return out;
}

function checklist_update() {
    var nodes = checklist_nodes();
    if nodes == undefined {
        return;
    }

    if !INPUT.check(InputId.ShowChecklist) || !instance_exists(obj_ari) {
        CHECKLIST_CACHE = undefined;
        nodes.card.set_alpha(0);
        nodes.text.set_alpha(0);
        return;
    }

    //
    if CHECKLIST_CACHE == undefined {
        CHECKLIST_CACHE = checklist_build();
        nodes.text.set_text(CHECKLIST_CACHE);

        var size = nodes.text.measure();
        nodes.card.set_size(size.x + 20, size.y + 16);
    }

    nodes.card.set_alpha(1);
    nodes.text.set_alpha(1);
}
"""

LABELS = '''checklist_title = "Day"
checklist_today = "TODAY"
checklist_dry = "crops need water"
checklist_greet = "villagers not greeted"
checklist_gift = "gifts still available"
checklist_unfed = "animals not fed"
checklist_unpet = "animals not petted"
checklist_outside = "animals still outside"
checklist_ahead = "COMING UP"
checklist_birthday = "Birthday:"
checklist_festival = "Festival:"
input_show_checklist = "Show Checklist"'''


# The player-visible text this mod adds; the framework mirrors it into every
# language's table so it never renders as MISSING.
TRANSLATE = {"misc_local": LABELS}


def patches(mk, opt):
    key = opt["checklist_key"].lower()
    default = '["%s", undefined, undefined, undefined]' % key

    return {
        INPUTUTILS: [
            # Immediately before LEN, so no existing input id shifts.
            (ENUM_ANCHOR, ENUM_ANCHOR + mk.block("ShowChecklist,", " " * 4)),
            # input_id_to_input_category() ends in impossible(), so every id
            # must be categorised or the game crashes on lookup.
            (CATEGORY_ANCHOR,
             CATEGORY_ANCHOR + mk.block("case InputId.ShowChecklist:", " " * 8)),
        ],
        SETTINGS: [
            # Missing bindings fall back to this, so no settings migration.
            (DEFAULTS_ANCHOR,
             DEFAULTS_ANCHOR
             + mk.block("case InputId.ShowChecklist: return %s;" % default, " " * 8)),
        ],
        LOCAL: [(mk.APPEND, mk.block(LABELS, toml=True))],
        CROPS: [(mk.APPEND, mk.block(HELPER))],
        ARI: [(STEP_ANCHOR, STEP_ANCHOR + mk.block("checklist_update();", " " * 16))],
    }
