"""Homeward - a sixth spell that carries Ari home. The day goes on.

The walk back from floor 55 at one in the morning is the least interesting
part of a mine run. Homeward is a real spell in the spell menu, pinnable
like any other: cast it and Ari is delivered to her own doorstep by the same
taxi system every door in the game uses, from anywhere - the mines included,
which clean up after themselves on any room change. It does not end the day,
touch the clock, or save; it only moves her.

It is learned, not given. With Magic Skill installed it arrives when Magic
reaches a level (20 by default); without it, it comes with the first spell
the Mist teaches. Either way the check runs when a spell is learned and each
morning, and a toast says so.

Spells are minted from spells.toml the way perks and skills are, so a sixth
entry is a real Spell.Homeward. The spell menu lists learned spells
dynamically and prices a card in whole mana orbs (cost / 4), so the default
cost of 8 reads as two orbs. The list icon and card icon are existing
sprites: the button-sprite loader falls back to a plain sprite name when a
family has no _main variant.

    python install.py apply homeward
    python install.py apply homeward --cost 12 --level 30
    python install.py remove homeward
"""

from ..patcher import Markers

SLUG = "homeward"
NAME = "Homeward"
SUMMARY = "A sixth spell: cast it anywhere and Ari is carried to her own doorstep. The day goes on."
DETAILS = """A sixth spell, Homeward. Cast it anywhere, the mines included, and Ari is carried home to her doorstep the way walking through a door would take her, for eight mana. It does not end the day or touch the clock; it just saves the walk. It is learned rather than given: with Magic Skill installed it arrives when Magic reaches level 20, and without Magic Skill it comes along with the first spell the Mist teaches. The check runs whenever a spell is learned and each morning, with a message when it happens. A save that has learned it keeps a homeward entry in its spell list, so as with Magic Skill, test on a throwaway save before removing this mod from a playthrough that learned it."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "cost": (int, 8, "mana cost; multiples of 4 show as whole orbs"),
    "level": (int, 20, "Magic level that teaches it, when Magic Skill is installed"),
}


def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}


# --- files -------------------------------------------------------------------

SPELLS_TOML = "assets/fiddle/spells.toml"
SPELLS_GML = "assets/gml/scripts/Spells.gml"
ARI = "assets/gml/scripts/GameplaySystems/Player/Ari.gml"
NEWDAY = "assets/gml/scripts/GameplaySystems/Cycle/NewDay.gml"
LOADGAME = "assets/gml/scripts/GameplaySystems/Cycle/LoadGame.gml"
LOCAL = "assets/fiddle/misc_local.toml"

# --- the spell ---------------------------------------------------------------
#
# Appended at the end of spells.toml so the existing Spell indices hold; the
# learned-spell list in saves is keyed by name, so position never matters on
# disk. Every sprite here already ships: the list icon is the farmhouse from
# the map screen's tabs (a plain sprite the button loader accepts as-is),
# the card icon is the store's little house, and the ribbon is Full Restore's.

SPELL_DEF = '''[homeward]
	name = "Homeward"
	description = "Carries you home to your own doorstep from wherever you stand. The day goes on."
	type = "Utility"
	cost = @COST@
	icon_key = "spr_ui_map_tab_icon_farm"
	upper_icon = "spr_ui_store_category_icon_buildings"
	ribbon = "spr_ui_journal_magic_card_ribbon_restore"'''

# --- Spells.gml: the gate and the cast ----------------------------------------
#
# Both switches end in an impossible() default, so a new spell must have a
# case in each. Each case is inserted BEFORE an existing line, leaving that
# line intact - Magic Skill inserts AFTER the lines it anchors on, so the two
# compose in either order.
#
# The gate's case cannot anchor on one of its case lines: Magic Skill mirrors
# the whole switch inside its own block, at a deeper indent, and a shallower
# indent is a substring of a deeper one. The default line plus the function
# boundary that follows it exists exactly once, mirror or no mirror.

CAN_CAST_ANCHOR = ('        default: impossible("Unexpected Spell: {Spell}", spell);\n'
                   "    }\n"
                   "}\n"
                   "\n"
                   "function cast_spell(spell) {\n")

CAN_CAST_CASE = "case Spell.Homeward: return homeward_can_cast();"

CAST_ANCHOR = "        case Spell.FullRestore:\n"

CAST_CASE = """case Spell.Homeward:
    homeward_cast();
    break;"""

HELPERS = """
//
// Homeward: a sixth spell that carries Ari home. The day goes on.
//
// The cast is the taxi itinerary a door into the house would make - the
// same destination tag, so Ari arrives on her own doormat - and works from
// any room; leaving the mines this way runs the dungeon's own exit hook,
// since that fires on every change of room. Nothing here ends the day.
//
function homeward_can_cast() {
    return !TAXI.is_traveling()
        && !MIST.is_running()
        && ARI.end_of_day_status == undefined
        && CURRENT_LOCATION_ID != LocationId.PlayerHome;
}

function homeward_cast() {
    TANGO.play("SoundEffects/Ari/MagicGeneric", obj_ari.x, obj_ari.y);
    goto_location_id(LocationId.PlayerHome)
        .set_specific_location_tag(DECOR.player_home_room_transition());
}

//
// Learned, not given. With the Magic skill present (Magic Skill mod) it
// arrives at a Magic level; without it, alongside the first spell the Mist
// teaches. Called when any spell is learned and each morning. The skill is
// looked up by name at run time, so this never names Skill.Magic and is
// safe with or without that mod.
//
function homeward_try_learn(quiet = false) {
    if ARI.spells_learned[Spell.Homeward] {
        return;
    }
    var magic = try_string_to_skill("magic");
    var ready = false;
    if magic != undefined {
        ready = skill_xp_to_level(magic, ARI.skill_xp[magic] ?? 0) >= @LEVEL@;
    } else {
        ready = array_contains(ARI.spells_learned, true);
    }
    if ready {
        ARI.learn_spell(Spell.Homeward);
        if !quiet {
            create_notification("misc_local/homeward_learned");
        }
    }
}
"""

# --- LoadGame.gml: a save that already qualifies gets it at load ------------
#
# Right after the learned spells (and, earlier, the skill XP) are read back.
# Quietly: the toast menu does not exist yet at this point.

LOAD_ANCHOR = ("    ARI.set_pinned_spell(opt_and_then(files.player.pinned_spell, "
               "string_to_spell));\n")

# --- Ari.gml: after any spell is learned ------------------------------------

LEARN_ANCHOR = "        self.spells_learned[spell] = true;\n"

# --- NewDay.gml: each morning, right after the vanilla +1 mana --------------
#
# The same line Magic Skill's Dreamer's Well hangs off; both insert after it.

WAKE_ANCHOR = "    ARI.modify_mana(1);\n"

LABELS = 'homeward_learned = "You feel the way home. Homeward has been added to your spells."'


# The player-visible text this mod adds; the framework mirrors it into every
# language's table so it never renders as MISSING.
TRANSLATE = {"misc_local": LABELS, "spells": SPELL_DEF.replace("@COST@", "8")}


def patches(mk, opt):
    cost = max(1, int(opt["cost"]))
    level = max(1, int(opt["level"]))
    return {
        SPELLS_TOML: [(mk.APPEND, mk.block(SPELL_DEF.replace("@COST@", str(cost)), toml=True))],
        SPELLS_GML: [
            (CAN_CAST_ANCHOR, mk.block(CAN_CAST_CASE, " " * 8) + CAN_CAST_ANCHOR),
            (CAST_ANCHOR, mk.block(CAST_CASE, " " * 8) + CAST_ANCHOR),
            (mk.APPEND, mk.block(HELPERS.replace("@LEVEL@", str(level)))),
        ],
        ARI: [(LEARN_ANCHOR, LEARN_ANCHOR + mk.block("homeward_try_learn();", " " * 8))],
        NEWDAY: [(WAKE_ANCHOR, WAKE_ANCHOR + mk.block("homeward_try_learn();", " " * 4))],
        LOADGAME: [(LOAD_ANCHOR, LOAD_ANCHOR + mk.block("homeward_try_learn(true);", " " * 4))],
        LOCAL: [(mk.APPEND, mk.block(LABELS, toml=True))],
    }
