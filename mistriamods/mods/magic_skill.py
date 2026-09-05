"""A tenth skill: Magic.

Cast spells to earn Magic XP, level from 1 to 60, and buy perks from a
five-tier Magic tree on Seridia's shrine, gated at levels 1/15/30/45/60 like
every other skill.

The engine mints `Skill` from skills.toml keys, so appending [magic] creates
Skill.Magic; XP, levels, the level-up toast, and save/load are all generic
over Skill.LEN, keyed by name in the save. The shrine's category screen and
the journal's skill tiles both read their layouts from fiddle data at
runtime, so Magic joins them through guarded array pushes rather than by
editing the data lines - every insertion here is pure addition, nothing is
modified in place.

The tree itself is injected as a prototype into load_dragon_shrine_data()
rather than shipped as a new ui/skill_menu/magic.toml, because the archive
writer only rewrites members that already exist. The loader applies the same
defaults and perk resolution to it as to the real files, and its own
`try_string_to_skill(key)` line resolves the category to Skill.Magic.

XP is a flat per-spell constant, deliberately NOT scaled by mana cost so the
MOMI cost mods don't distort leveling. The curve is bespoke (see XP_EFFECT):
roughly 800 casts to level 60.

19 perks, 4/4/4/4/3, mining-tree costs. Icons are reused - the atlases are
prebuilt. Vanilla notes that shaped the design: mana does NOT refill on sleep
(mornings grant just +1), and Dragon's Breath already destroys rocks and
trees (its tarball has chop/pick/destroy flags at 999 damage), so its perks
extend duration instead.

Uninstall caveat: a save that has earned Magic XP keeps a `magic` key in
skill_xp. On load without the mod, apply_struct_to_array feeds it to the
strict string_to_skill; the release-build guard appears to skip non-numeric
results, but this is unverified against the native converter - test on a
throwaway save before uninstalling mid-playthrough. Purchased perks and the
mana_max bumps from Attunement/Grand Wellspring survive uninstall harmlessly.
"""

from ..patcher import Alternatives, Markers

SLUG = "magic_skill"
NAME = "Magic Skill"
SUMMARY = "A tenth skill: casting spells earns XP, and a 19-perk Magic tree opens on Seridia's shrine."
DETAILS = """A tenth skill, Magic. Every spell you cast earns Magic XP, you level from 1 to 60 exactly like the other skills, and a Magic tree appears on Seridia's shrine beside Mining and Combat. Nineteen perks across five tiers unlock at levels 1, 15, 30, 45 and 60: extra mana orbs, cheaper spells, a longer Dragon's Breath, a wider Growth that can also water, a longer Sacred Light that speeds you up, waking with full mana, refund chances, double XP, and essence from casting. Existing saves simply start at level 1. One caveat: a save that has earned Magic XP keeps a Magic entry, so test on a throwaway save before removing this mod from a leveled playthrough."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {}


def defaults():
    return {}


SKILLS = "assets/fiddle/skills.toml"
PERKS = "assets/fiddle/perks.toml"
XP = "assets/gml/scripts/Xp.gml"
SPELLS_GML = "assets/gml/scripts/Spells.gml"
ARIFSM = "assets/gml/scripts/Player/AriFsm.gml"
ARI = "assets/gml/scripts/GameplaySystems/Player/Ari.gml"
OBJ_ARI = "assets/gml/objects/characters/obj_ari.gml"
NEWDAY = "assets/gml/scripts/GameplaySystems/Cycle/NewDay.gml"
SHRINE = "assets/gml/scripts/UI/Anchor/Menus/DragonshrineMenu.gml"
PLAYERMENU = "assets/gml/scripts/UI/Anchor/Menus/PlayerMenu.gml"
LOCAL = "assets/fiddle/misc_local.toml"

# The category name goes through local_get()/set_key(), which answer
# "MISSING" for anything that is not a real localization key - a raw "Magic"
# string is not the fallback it looks like. Same shared-append file the other
# mods use for their labels.
LABELS = 'magic_skill_category = "Magic"'

# --- the skill ---------------------------------------------------------------
#
# Appended at the END of skills.toml so the existing Skill indices are stable.

SKILL_DEF = '''[magic]
\tsprite = "spr_ui_hud_health_mana_bar_icon"'''

# --- perk definitions --------------------------------------------------------
#
# Numbers are hardcoded in the descriptions, as every vanilla perk does. The
# shrine loader DOES have a {field}-interpolation pass, but zero vanilla
# perks use it and in practice it hands the pattern through unreplaced -
# dead code, learned the hard way. Keep the text in sync with the value
# fields by hand when tuning.

PERK_DEFS = '''[attunement]
\tname = "Attunement"
\tdescription = "Open yourself to the realm's flow. Increases maximum mana by 4."
\tvalue = 4

[apprentices_thrift]
\tname = "Apprentice's Thrift"
\tdescription = "Waste not a drop of the realm's gift. All spells cost 1 less mana."
\tvalue = 1

[deep_roots]
\tname = "Deep Roots"
\tdescription = "The Growth spell advances trees by an extra stage."
\tvalue = 1

[kindled_focus]
\tname = "Kindled Focus"
\tdescription = "Dragon's Breath burns half again as long."
\tvalue = 1.5

[second_wind]
\tname = "Second Wind"
\tdescription = "Full Restore also leaves a restorative glow that mends you over time."
\tduration_minutes = 90

[stormcaller]
\tname = "Stormcaller"
\tdescription = "Rain summoned indoors lingers twice as long."
\tvalue = 2

[alchemists_draught]
\tname = "Alchemist's Draught"
\tdescription = "Mana restoratives restore double."
\tvalue = 2

[luminous_stride]
\tname = "Luminous Stride"
\tdescription = "Sacred Light also quickens your step while it shines."
\tvalue = 1.25

[wide_growth]
\tname = "Wide Growth"
\tdescription = "The Growth spell reaches a full tile further in every direction."
\tvalue = 1

[dreamers_well]
\tname = "Dreamer's Well"
\tdescription = "Wake each morning with your mana fully restored."
\tvalue = 1

[sunlit_depths]
\tname = "Sunlit Depths"
\tdescription = "Sacred Light shines twice as long."
\tvalue = 2

[arcane_economy]
\tname = "Arcane Economy"
\tdescription = "Casting has a 15% chance to refund the spell's full cost."
\tvalue = 15

[grand_wellspring]
\tname = "Grand Wellspring"
\tdescription = "Deepen the well within. Increases maximum mana by another 4."
\tvalue = 4

[verdant_rain]
\tname = "Verdant Rain"
\tdescription = "The Growth spell also waters every tile it touches."
\tvalue = 1

[guardian_flame]
\tname = "Guardian Flame"
\tdescription = "Casting Dragon's Breath kindles a shield charge if you have none. The first hit after the breath is absorbed."
\tvalue = 1

[ritualist]
\tname = "Ritualist"
\tdescription = "Every cast teaches you double the Magic experience."
\tvalue = 2

[twinflow]
\tname = "Twinflow"
\tdescription = "The realm answers you in kind. All spell costs are halved."
\tvalue = 0.5

[eternal_flame]
\tname = "Eternal Flame"
\tdescription = "Dragon's Breath burns twice as long again."
\tvalue = 2

[mistrias_bounty]
\tname = "Mistria's Bounty"
\tdescription = "Each cast has a 25% chance to draw 5 essence from the realm."
\tvalue = 25
\tamount = 5'''

# --- the tree ----------------------------------------------------------------
#
# Injected into load_dragon_shrine_data() right after it reads the directory,
# and before it takes the defaults - so this prototype flows through the same
# apply_defaults / string_to_perk / description-interpolation path as the real
# tree files, and `prototype.skill = try_string_to_skill("magic")` resolves it
# to Skill.Magic. LUT rows 31/32/33 are the Mistmare tree's, a known-good
# triplet; the crafting domain icon family exists in the atlas but is placed
# in no vanilla tree.

LOAD_ANCHOR = ('    var toml_data = MapWrap('
               'fiddle_get_directory("ui/skill_menu"));\n')

LOAD_EFFECT = '''//
// Magic Skill: the tenth tree, injected beside the nine the directory holds.
//
toml_data.set("magic", {
    name: "misc_local/magic_skill_category",
    icon_sprite_key: "spr_ui_skills_domain_icon_crafting",
    default_lut_index: 31,
    hovered_lut_index: 32,
    disabled_lut_index: 33,
    tier_1: [
        { perk: "attunement", essence: 25, icon: "spr_ui_hud_health_mana_ball_on" },
        { perk: "apprentices_thrift", essence: 25, icon: "spr_item_mana_small" },
        { perk: "deep_roots", essence: 20, icon: "spr_ui_journal_magic_growth_spell_icon_main" },
        { perk: "kindled_focus", essence: 20, icon: "spr_ui_journal_magic_fire_spell_icon_main" },
    ],
    tier_2: [
        { perk: "second_wind", essence: 45, icon: "spr_ui_journal_magic_restore_spell_icon_main" },
        { perk: "stormcaller", essence: 50, icon: "spr_ui_journal_magic_rain_spell_icon_main" },
        { perk: "alchemists_draught", essence: 45, icon: "spr_ui_item_mana_potion" },
        { perk: "luminous_stride", essence: 50, icon: "spr_ui_journal_magic_sacred_light_spell_icon_main" },
    ],
    tier_3: [
        { perk: "wide_growth", essence: 85, icon: "spr_ui_journal_magic_growth_spell_icon_main" },
        { perk: "dreamers_well", essence: 80, icon: "spr_item_mana_big" },
        { perk: "sunlit_depths", essence: 80, icon: "spr_ui_journal_magic_sacred_light_spell_icon_main" },
        { perk: "arcane_economy", essence: 75, icon: "spr_ui_hud_info_essence_icon" },
    ],
    tier_4: [
        { perk: "grand_wellspring", essence: 150, icon: "spr_ui_hud_health_mana_ball_on" },
        { perk: "verdant_rain", essence: 155, icon: "spr_ui_journal_magic_rain_spell_icon_main" },
        { perk: "guardian_flame", essence: 150, icon: "spr_ui_journal_magic_fire_spell_icon_main" },
        { perk: "ritualist", essence: 150, icon: "spr_item_mana_medium" },
    ],
    tier_5: [
        { perk: "twinflow", essence: 210, icon: "spr_item_mana_medium" },
        { perk: "eternal_flame", essence: 205, icon: "spr_ui_journal_magic_fire_spell_icon_main" },
        { perk: "mistrias_bounty", essence: 200, icon: "spr_ui_hud_info_essence_icon" },
    ],
});
'''

# The category screen builds its rows from fiddle data; a guarded push keeps
# the mutation of the cached array idempotent across menu opens.
ROW_ANCHOR = ('        var order = fiddle_get(format('
              '"ui/misc/shrine_categories/{ShrineMenuVariant}", '
              'self.variant));\n')

ROW_EFFECT = '''//
// Magic Skill: Magic stands beside Mining and Combat on Seridia's shrine.
//
if self.variant == ShrineMenuVariant.Seridia {
    var magic_row = order[array_length(order) - 1];
    if !array_contains(magic_row, "magic") {
        array_push(magic_row, "magic");
    }
}
'''

# The borrowed crafting tile carries a baked-in tool glyph; the shrine's own
# blank slot (same Gemstone Menu sprite set, same rounded shape) blanks it
# out and the game's magic sparkle goes on top. Both are children of the
# tile, so they ride its position and hover motion; hover feedback stays the
# name bubble, which keys off tile.is_hovered and is unaffected.
TILE_ANCHOR = "                }, [cat_key])\n"

TILE_EFFECT = '''//
// Magic Skill: blank the borrowed tile and stamp the arcane sparkle on it.
//
if cat_key == "magic" {
    var magic_cover = ANCHOR.sprite(tile)
        .set_align(Align.Center, Align.Middle)
        .set_sprite(spr_ui_skills_skill_slot_white)
    ANCHOR.sprite(magic_cover)
        .set_align(Align.Center, Align.Middle)
        .set_y(-1)
        .set_sprite(spr_ui_journal_magic_header_icon)
}
'''

# --- XP ----------------------------------------------------------------------
#
# The outer switch's default would hand Magic a curve built for nothing in
# particular; this case sits in front of it. Small early steps so the first
# tiers arrive at a farming-skill pace, then a gentle linear climb - about
# 8,000 XP (~800 casts) to level 60.

XP_ANCHOR = """        default:
            //
            return ((level - 1) * 60) - 30;
"""

XP_EFFECT = """case Skill.Magic:
    //
    // ~800 casts to max: levels below 10 cost (level-1)*6, then a
    // linear 54 + 4/level. Tier gates land at ~330 / ~2,100 / ~4,600 /
    // ~8,100 XP.
    //
    if level < 10 {
        return (level - 1) * 6;
    }
    return 54 + ((level - 10) * 4);
"""

# --- casting: XP, costs, and the spell perks ---------------------------------

# Two forms of the same site. With MOMI's MMAPI layer installed: after its
# `spells.can_cast` override hook (which returns early when a mod answers),
# so an override still wins over the cost mirror. On a bare game: right after
# the function's opening line. Alternatives tries them in that order.
CAN_CAST_ANCHOR_MMAPI = ('    if (typeof(__mmapi_can_cast_spell) != "undefined") '
                         '{ return __mmapi_can_cast_spell; }\n')
CAN_CAST_ANCHOR_VANILLA = "function can_cast_spell(spell) {\n"

# The vanilla gate below this insertion tests the UNdiscounted cost, which
# undercounts what Ari can afford once cost perks are owned. With any of them
# active, mirror the whole gate at the discounted price and answer early;
# without them this block never runs. The mirrored per-spell cases fall
# through to the vanilla body for any spell added by a future game update.
CAN_CAST_EFFECT = '''//
// Magic Skill: with cost-reducing perks owned, answer from the discounted
// price; the vanilla gate below would refuse casts Ari can now afford.
//
if ARI.perk_active(Perk.ApprenticesThrift) || ARI.perk_active(Perk.Twinflow) {
    if !instance_exists(obj_ari)
        || obj_ari.is_mounted()
        || ARI.get_mana() < magic_spell_cost(spell, @COST@)
        || ARI.held_animal_id != undefined
    {
        return false;
    }
    switch spell {
        case Spell.FullRestore: return ARI.get_health() < ARI.get_max_health() || ARI.get_stamina() < ARI.get_max_stamina();
        case Spell.SummonRain: return (CURRENT_LOCATION_ID == LocationId.Farm && !WEATHER.is_inclement())
            || is_rain_spell_target(CURRENT_LOCATION_ID);
        case Spell.Growth: return LOCATIONS[CURRENT_LOCATION_ID].outdoor || LOCATIONS[CURRENT_LOCATION_ID].farm;
        case Spell.FireBreath: return ARI.fire_breath_time == 0;
        case Spell.SacredLight: return in_dark_mines() && ARI.status_effects.effects.get(StatusEffectId.SacredLight) == undefined;
        default: break;
    }
}
'''

# The base price each form hands the helper: MMAPI's `spells.cost` filter
# is a first-class hook other mods may register on, so with MOMI's layer
# present the mirror reads the filtered price exactly as the vanilla gate
# beside it does; on a bare game that function does not exist.
COST_MMAPI = 'mmapi_apply_filters("spells.cost", SPELLS[spell].cost, spell)'
COST_VANILLA = "SPELLS[spell].cost"
CAN_CAST_EFFECT_MMAPI = CAN_CAST_EFFECT.replace("@COST@", COST_MMAPI)
CAN_CAST_EFFECT_VANILLA = CAN_CAST_EFFECT.replace("@COST@", COST_VANILLA)

CAST_ANCHOR = "function cast_spell(spell) {\n"

CAST_EFFECT = '''//
// Magic Skill: every cast teaches. At the top, before any per-spell early
// return (Growth bails out at the map edge), so XP always lands.
//
magic_skill_on_cast(spell);
'''

RESTORE_ANCHOR = """        case Spell.FullRestore:
            ARI.set_health(ARI.get_max_health());
            if ARI.get_stamina() < ARI.get_max_stamina() {
                ARI.set_stamina(ARI.get_max_stamina());
            }
"""

RESTORE_EFFECT = '''//
// Second Wind: a restorative afterglow, the same status the game's own
// regen food applies (undefined amount = the standard +5 tick).
//
if ARI.perk_active(Perk.SecondWind) {
    var magic_t = CALENDAR.unified_time();
    ARI.status_effects.register(
        StatusEffectId.Restorative,
        undefined,
        magic_t,
        magic_t + minutes(ARI.perk_value(Perk.SecondWind, "duration_minutes")),
    );
}
'''

INDOOR_ANCHOR = ('                WEATHER.spell_timer = '
                 'fiddle_get("spells/summon_rain").indoor_duration;\n')

INDOOR_EFFECT = '''//
// Stormcaller.
//
if ARI.perk_active(Perk.Stormcaller) {
    WEATHER.spell_timer *= ARI.perk_value(Perk.Stormcaller);
}
'''

FIRECAP_ANCHOR = ('            ARI.fire_breath_time = '
                  'fiddle_get("player").fire_breath_time_cap;\n')

# fire_breath_time doubles as the recast lock, so extending it IS the perk;
# the FlameBreath status registered just below reads the extended value.
FIRECAP_EFFECT = '''//
// Kindled Focus / Eternal Flame: the breath burns longer.
//
if ARI.perk_active(Perk.KindledFocus) {
    ARI.fire_breath_time = round(ARI.fire_breath_time * ARI.perk_value(Perk.KindledFocus));
}
if ARI.perk_active(Perk.EternalFlame) {
    ARI.fire_breath_time = round(ARI.fire_breath_time * ARI.perk_value(Perk.EternalFlame));
}
//
// Guardian Flame: the breath kindles a shield charge if none is banked.
// Vanilla already ignores every hit while the breath burns (obj_ari breaks
// out of its damage loop on fire_breath_time > 0), so the charge matters
// the moment it ends: its own counter absorbs the first hit after the
// breath and plays the shield-break effect. Registering the status puts
// the shield icon on the HUD, as entering the mines does for Guardian's
// Shield. Not in cutscenes, which breathe fire through this same case.
//
if ARI.perk_active(Perk.GuardianFlame)
    && ARI.invulnerable_hits <= 0
    && !MIST.is_running()
{
    ARI.invulnerable_hits = 1;
    if ARI.status_effects.effects.get(StatusEffectId.GuardiansShield) == undefined {
        ARI.status_effects.register(
            StatusEffectId.GuardiansShield,
            undefined,
            CALENDAR.unified_time(),
            I32_MAX,
        );
    }
}
'''

SL_ANCHOR = """                time + fiddle_get("misc/sacred_light_duration") * 60,
            )
"""

# Stretching the effect's own finish after registration doubles the duration
# without touching the multi-line register call; Speedy borrows the same
# window so the two perks always agree on when the light goes out.
SL_EFFECT = '''var magic_sl = ARI.status_effects.effects.get(StatusEffectId.SacredLight);
if magic_sl != undefined {
    //
    // Sunlit Depths.
    //
    if ARI.perk_active(Perk.SunlitDepths) {
        magic_sl.finish = magic_sl.start
            + (magic_sl.finish - magic_sl.start) * ARI.perk_value(Perk.SunlitDepths);
    }

    //
    // Luminous Stride: the same multiplicative Speedy the food buffs use.
    //
    if ARI.perk_active(Perk.LuminousStride) {
        ARI.status_effects.register(
            StatusEffectId.Speedy,
            ARI.perk_value(Perk.LuminousStride),
            magic_sl.start,
            magic_sl.finish,
        );
    }
}
'''

GROWTH_ANCHOR = "            if max_ding_count > 0 {\n"

GROWTH_EFFECT = '''//
// Magic Skill: Wide Growth's outer ring, Deep Roots' extra tree stage,
// Verdant Rain's watering pass.
//
max_ding_count = max(max_ding_count,
    magic_growth_extras(x_pos, y_pos, cast_id, ignore_season));
'''

HELPERS = '''
//
// Magic Skill.
//

//
// A spell's cost after Apprentice's Thrift and Twinflow. A spell that is
// already free stays free; a paid spell never drops below 1.
//
function magic_spell_cost(spell, cost) {
    // `cost` is the base price the call site read - MMAPI's filtered price
    // when MOMI's layer is present, SPELLS[spell].cost on a bare game.
    if cost <= 0 {
        return cost;
    }
    if ARI.perk_active(Perk.ApprenticesThrift) {
        cost = max(1, cost - ARI.perk_value(Perk.ApprenticesThrift));
    }
    if ARI.perk_active(Perk.Twinflow) {
        cost = max(1, ceil(cost * ARI.perk_value(Perk.Twinflow)));
    }
    return cost;
}

//
// XP per cast - flat constants, deliberately not scaled by mana cost so cost
// mods and cost perks cannot distort leveling. Ritualist doubles, Mistria's
// Bounty rolls its essence here so every cast path pays out once.
//
function magic_skill_on_cast(spell) {
    // Cutscenes breathe fire through cast_spell too; a scripted breath
    // teaches nothing and conjures nothing.
    if MIST.is_running() {
        return;
    }
    var xp = 8;
    switch spell {
        case Spell.FireBreath: xp = 6; break;
        case Spell.FullRestore: xp = 8; break;
        case Spell.Growth: xp = 10; break;
        case Spell.SummonRain: xp = 12; break;
        case Spell.SacredLight: xp = 15; break;
        default: break;
    }

    if ARI.perk_active(Perk.Ritualist) {
        xp *= ARI.perk_value(Perk.Ritualist);
    }
    ARI.gain_xp(Skill.Magic, xp);

    if ARI.perk_active(Perk.MistriasBounty)
        && chance_percent(ARI.perk_value(Perk.MistriasBounty))
    {
        ARI.modify_essence(ARI.perk_value(Perk.MistriasBounty, "amount"));
    }
}

//
// One Growth cell, a faithful mirror of the loop body in cast_spell - same
// category switch, same last_update stamp, same season gates - except a
// missing node index is a `return 0`, not the vanilla loop's whole-cast
// abort, because the ring runs nearer the map edge than the vanilla square.
//
function magic_growth_cell(xx, yy, cast_id, ignore_season) {
    var ni = GRID.try_node_index_for_cell(xx, yy);
    if ni == undefined {
        return 0;
    }

    var cat = object_id_to_object_category(GRID.node_object_id[ni]);
    if cat == undefined || GRID.node_parent[ni].last_update == cast_id {
        return 0;
    }

    switch cat {
        case ObjectCategory.Crop:
            GRID.node_parent[ni].last_update = cast_id;
            if ignore_season == false && GRID.node_parent[ni].prototype.seasons[CALENDAR.season()] == false {
                return 0;
            }
            return level_up_crop(GRID.node_parent[ni], false);
        case ObjectCategory.Grass:
            GRID.node_parent[ni].last_update = cast_id;
            return level_up_grass(GRID.node_parent[ni]);
        case ObjectCategory.Tree:
            var center_stump_x = GRID.node_top_left_x[ni] + 3;
            var center_stump_y = GRID.node_top_left_y[ni] + 3;
            if xx == center_stump_x && yy == center_stump_y {
                GRID.node_parent[ni].last_update = cast_id;
                level_up_tree(GRID.node_parent[ni], ignore_season);
            }
            return 0;
        case ObjectCategory.Bush:
            GRID.node_parent[ni].last_update = cast_id;
            if ignore_season == false && GRID.node_parent[ni].prototype.seasons[CALENDAR.season()] == false {
                return 0;
            }
            level_up_bush(GRID.node_parent[ni]);
            return 0;
        default:
            return 0;
    }
}

//
// The three Growth perks, as passes ADDED to the vanilla cast rather than a
// rewrite of it. The grid here is half-tile cells, so one tile of perk reach
// is two cells. last_update == cast_id marks "grown by this cast", which is
// how Deep Roots finds every tree the cast touched - vanilla square and
// perk ring alike - exactly once.
//
function magic_growth_extras(x_pos, y_pos, cast_id, ignore_season) {
    var dings = 0;
    var r = 0;

    if ARI.perk_active(Perk.WideGrowth) {
        r = ARI.perk_value(Perk.WideGrowth) * 2;
        for (var xx = x_pos - 2 - r; xx < (x_pos + 4 + r); xx++) {
            for (var yy = y_pos - 2 - r; yy < (y_pos + 4 + r); yy++) {
                if xx >= (x_pos - 2) && xx < (x_pos + 4)
                    && yy >= (y_pos - 2) && yy < (y_pos + 4)
                {
                    continue;
                }
                dings = max(dings, magic_growth_cell(xx, yy, cast_id, ignore_season));
            }
        }
    }

    if ARI.perk_active(Perk.DeepRoots) {
        for (var xx = x_pos - 2 - r; xx < (x_pos + 4 + r); xx++) {
            for (var yy = y_pos - 2 - r; yy < (y_pos + 4 + r); yy++) {
                var ni = GRID.try_node_index_for_cell(xx, yy);
                if ni == undefined {
                    continue;
                }
                if object_id_to_object_category(GRID.node_object_id[ni]) != ObjectCategory.Tree {
                    continue;
                }
                if GRID.node_parent[ni].last_update != cast_id {
                    continue;
                }
                if xx == GRID.node_top_left_x[ni] + 3 && yy == GRID.node_top_left_y[ni] + 3 {
                    level_up_tree(GRID.node_parent[ni], ignore_season);
                }
            }
        }
    }

    if ARI.perk_active(Perk.VerdantRain) {
        for (var xx = x_pos - 2 - r; xx < (x_pos + 4 + r); xx++) {
            for (var yy = y_pos - 2 - r; yy < (y_pos + 4 + r); yy++) {
                var ni = GRID.try_node_index_for_cell(xx, yy);
                if ni == undefined {
                    continue;
                }
                if can_water_node(GRID, ni) {
                    water_node(GRID, xx, yy);
                }
            }
        }
    }

    return dings;
}
'''

# --- mana economy in the cast state ------------------------------------------
#
# The vanilla line charges the UNdiscounted cost through set_mana, which
# clamps at zero - so a flat "refund the discount" after it can hand back
# mana that was never taken. Cast at exactly 1 mana with a 2-cost spell
# discounted to 1: the clamp eats only the 1 that exists, the refund adds 1,
# and the pool never empties (the "stuck at a quarter orb" bug). The fix
# brackets the vanilla line: remember the pre-cast mana, then set the exact
# discounted remainder. Without cost perks that lands on precisely the value
# the vanilla line just wrote, so this is inert until a discount exists.

# Two forms of the same two sites. With MOMI's MMAPI layer the cost passes
# through the `spells.cost` filter and each site carries its own trailing seam
# comment; anchoring on the shared part up to the semicolon matches both, and
# the post-block lands between the code and that comment - which the strip
# regex restores byte-exactly, since it consumes the block's own leading
# whitespace and trailing newline only. On a bare game it is the plain line.
DEDUCT_ANCHOR_MMAPI = ('                            ARI.modify_mana(-mmapi_apply_filters('
                       '"spells.cost", SPELLS[self.spell].cost, self.spell));')
DEDUCT_ANCHOR_VANILLA = ("                            "
                         "ARI.modify_mana(-SPELLS[self.spell].cost);\n")

DEDUCT_PRE = '''//
// Magic Skill: the pre-cast mana, for the exact charge below.
//
var magic_before = ARI.get_mana();
'''

DEDUCT_POST = '''//
// Magic Skill: charge exactly the discounted cost - correct at every
// boundary, an empty pool included - then roll Arcane Economy.
//
var magic_due = magic_spell_cost(self.spell, @COST@);
ARI.set_mana(magic_before - magic_due);
if ARI.perk_active(Perk.ArcaneEconomy)
    && chance_percent(ARI.perk_value(Perk.ArcaneEconomy))
{
    ARI.modify_mana(magic_due);
}
'''

# The cast state names the spell `self.spell`; same two prices as the mirror.
COST_MMAPI_SELF = 'mmapi_apply_filters("spells.cost", SPELLS[self.spell].cost, self.spell)'
COST_VANILLA_SELF = "SPELLS[self.spell].cost"
DEDUCT_POST_MMAPI = DEDUCT_POST.replace("@COST@", COST_MMAPI_SELF)
DEDUCT_POST_VANILLA = DEDUCT_POST.replace("@COST@", COST_VANILLA_SELF)

# Two forms: MMAPI reroutes the potion through modify_mana (its
# player_mana_item_delta seam); vanilla adds through set_mana. The bonus
# below is a modify_mana either way.
POTION_ANCHOR_MMAPI = ("                            "
                       "ARI.modify_mana(self.live_item.prototype.mana_modifier); "
                       "// mmapi_player_mana_item_delta\n")
POTION_ANCHOR_VANILLA = ("                            "
                         "ARI.set_mana(ARI.mana_current + "
                         "self.live_item.prototype.mana_modifier);\n")

POTION_EFFECT = '''//
// Alchemist's Draught: the modifier again, once, for double.
//
if ARI.perk_active(Perk.AlchemistsDraught) {
    ARI.modify_mana(self.live_item.prototype.mana_modifier
        * (ARI.perk_value(Perk.AlchemistsDraught) - 1));
}
'''

# --- permanent stat bumps on purchase ----------------------------------------
#
# The Guardian's Shield idiom: acquire_perk() is the one place a purchase can
# adjust a serialized stat. mana_max is saved raw, so the orbs persist - and
# survive uninstall as a harmless leftover.

ACQUIRE_ANCHOR = """        switch perk {
            case Perk.GuardiansShield:
                ARI.invulnerable_hits += 1;
                break;
"""

ACQUIRE_EFFECT = '''case Perk.Attunement:
    self.mana_max += ARI.perk_value(Perk.Attunement);
    self.set_mana(self.mana_current + ARI.perk_value(Perk.Attunement));
    break;
case Perk.GrandWellspring:
    self.mana_max += ARI.perk_value(Perk.GrandWellspring);
    self.set_mana(self.mana_current + ARI.perk_value(Perk.GrandWellspring));
    break;
'''

# --- the tier-5 achievement --------------------------------------------------
#
# "One tier-5 perk in every category" is computed from DRAGON_SHRINE_DATA's
# keys, so a tenth tree would silently become a tenth requirement - and a
# player midway through the achievement would see it un-tick. Skip ours.

ACHIEVEMENT_ANCHOR = ("    var keys = DRAGON_SHRINE_DATA.keys();\n"
                      "    for (var i = 0; i < array_length(keys); i++) {\n")

ACHIEVEMENT_EFFECT = '''//
// Magic Skill: the vanilla "one tier-5 perk per category" achievement stays
// a nine-category achievement - the Magic tree is extra, not a requirement.
//
if keys[i] == "magic" {
    continue;
}
'''

# Versions 1.0-1.1 wrote a Guardian Flame block into obj_ari's damage gate.
# It was unreachable (vanilla breaks out of that loop while the breath burns)
# and is gone; the file stays listed with no edits so re-applying over an
# older install still strips it.

# --- Dreamer's Well ----------------------------------------------------------
#
# Vanilla mornings grant exactly +1 mana; this line runs right after it.

WAKE_ANCHOR = "    ARI.modify_mana(1);\n"

WAKE_EFFECT = '''//
// Dreamer's Well.
//
if ARI.perk_active(Perk.DreamersWell) {
    ARI.set_mana(ARI.mana_max);
}
'''

# --- the journal -------------------------------------------------------------

FRONT_ANCHOR = ('        static ORDER = '
                'fiddle_get("ui/misc/player_menu_skill_category_order");\n')

FRONT_EFFECT = '''//
// Magic Skill: a tenth tile on the journal's skill grid. Guarded - the
// fiddle data is cached, so the push must be idempotent.
//
if !array_contains(ORDER[array_length(ORDER) - 1], "magic") {
    array_push(ORDER[array_length(ORDER) - 1], "magic");
}
'''

BACKPLATE_ANCHOR = "                popup.backplate.set_size(216, 237);\n"

BACKPLATE_EFFECT = '''//
// Magic Skill: room for a tenth row.
//
popup.backplate.set_size(216, 258);
'''

POPUP_ORDER_ANCHOR = """                    Skill.Woodcrafting,
                ];
"""

POPUP_ORDER_EFFECT = '''//
// Magic Skill: the tenth row, and the plate grown to hold it - nine rows
// at 19px exactly filled the old 178.
//
popup.sub_plate.set_height(198);
if !array_contains(ORDER, Skill.Magic) {
    array_push(ORDER, Skill.Magic);
}
'''

COLOR_ANCHOR = """                        case Skill.Cooking:
                        case Skill.Blacksmithing:
                        case Skill.Woodcrafting:
                            plate_sprite = spr_ui_journal_skill_progress_bar_pink;
                            break;
"""

COLOR_EFFECT = '''case Skill.Magic:
    plate_sprite = spr_ui_journal_skill_progress_bar_blue;
    break;
'''


# The player-visible text this mod adds; the framework mirrors it into every
# language's table so it never renders as MISSING.
TRANSLATE = {"misc_local": LABELS, "perks": PERK_DEFS}


def patches(mk, opt):
    return {
        # Appended at the end: existing Skill indices stay stable, and the
        # name-keyed save format makes position irrelevant on disk.
        SKILLS: [(mk.APPEND, mk.block(SKILL_DEF, toml=True))],

        # Declaring the perks is what mints the Perk.X constants.
        PERKS: [(mk.APPEND, mk.block(PERK_DEFS, toml=True))],

        XP: [(XP_ANCHOR, mk.block(XP_EFFECT, " " * 8) + XP_ANCHOR)],

        SPELLS_GML: [
            Alternatives(
                (CAN_CAST_ANCHOR_MMAPI,
                 CAN_CAST_ANCHOR_MMAPI + mk.block(CAN_CAST_EFFECT_MMAPI, " " * 4)),
                (CAN_CAST_ANCHOR_VANILLA,
                 CAN_CAST_ANCHOR_VANILLA + mk.block(CAN_CAST_EFFECT_VANILLA, " " * 4))),
            (CAST_ANCHOR, CAST_ANCHOR + mk.block(CAST_EFFECT, " " * 4)),
            (RESTORE_ANCHOR,
             RESTORE_ANCHOR + mk.block(RESTORE_EFFECT, " " * 12)),
            (INDOOR_ANCHOR,
             INDOOR_ANCHOR + mk.block(INDOOR_EFFECT, " " * 16)),
            (FIRECAP_ANCHOR,
             FIRECAP_ANCHOR + mk.block(FIRECAP_EFFECT, " " * 12)),
            (SL_ANCHOR, SL_ANCHOR + mk.block(SL_EFFECT, " " * 12)),
            (GROWTH_ANCHOR,
             mk.block(GROWTH_EFFECT, " " * 12) + GROWTH_ANCHOR),
            (mk.APPEND, mk.block(HELPERS)),
        ],

        # The same deduction line appears in both cast states; one patch
        # covers both, and the count check keeps it honest.
        # Both deduction sites in one edit (expected 2), in whichever form the
        # archive has; the potion and the gate likewise pick their form.
        ARIFSM: [
            Alternatives(
                (DEDUCT_ANCHOR_MMAPI,
                 mk.block(DEDUCT_PRE, " " * 28)
                 + DEDUCT_ANCHOR_MMAPI
                 + mk.block(DEDUCT_POST_MMAPI, " " * 28), 2),
                (DEDUCT_ANCHOR_VANILLA,
                 mk.block(DEDUCT_PRE, " " * 28)
                 + DEDUCT_ANCHOR_VANILLA
                 + mk.block(DEDUCT_POST_VANILLA, " " * 28), 2)),
            Alternatives(
                (POTION_ANCHOR_MMAPI,
                 POTION_ANCHOR_MMAPI + mk.block(POTION_EFFECT, " " * 28)),
                (POTION_ANCHOR_VANILLA,
                 POTION_ANCHOR_VANILLA + mk.block(POTION_EFFECT, " " * 28))),
        ],

        ARI: [(ACQUIRE_ANCHOR,
               ACQUIRE_ANCHOR + mk.block(ACQUIRE_EFFECT, " " * 12))],

        # No edits since 1.2.0 - listed so the 1.0-1.1 block is stripped.
        OBJ_ARI: [],

        NEWDAY: [(WAKE_ANCHOR, WAKE_ANCHOR + mk.block(WAKE_EFFECT, " " * 4))],

        SHRINE: [
            (LOAD_ANCHOR, LOAD_ANCHOR + mk.block(LOAD_EFFECT, " " * 4)),
            (ROW_ANCHOR, ROW_ANCHOR + mk.block(ROW_EFFECT, " " * 8)),
            (TILE_ANCHOR, TILE_ANCHOR + mk.block(TILE_EFFECT, " " * 12)),
            (ACHIEVEMENT_ANCHOR,
             ACHIEVEMENT_ANCHOR + mk.block(ACHIEVEMENT_EFFECT, " " * 8)),
        ],

        LOCAL: [(mk.APPEND, mk.block(LABELS, toml=True))],

        PLAYERMENU: [
            (FRONT_ANCHOR, FRONT_ANCHOR + mk.block(FRONT_EFFECT, " " * 8)),
            (BACKPLATE_ANCHOR,
             BACKPLATE_ANCHOR + mk.block(BACKPLATE_EFFECT, " " * 16)),
            (POPUP_ORDER_ANCHOR,
             POPUP_ORDER_ANCHOR + mk.block(POPUP_ORDER_EFFECT, " " * 16)),
            (COLOR_ANCHOR,
             COLOR_ANCHOR + mk.block(COLOR_EFFECT, " " * 24)),
        ],
    }
