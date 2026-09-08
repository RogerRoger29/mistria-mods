"""Field Notes - the museum's missing items, with where and when to look.

Uncaught Sparkles and Uncaught Flora tell you the thing in front of you is
still needed. Field Notes tells you where to go. Four new categories join
the journal's Almanac - Notes: Artifacts, Fish, Flora, Insects - and each
opens a list of everything that wing still lacks, grouped the way the
museum groups it, with a line under every name: "Fall / Pond / Rain",
"Mines 41-60 / Uncommon", "Summer / Beach / Night". Items you have never
held show the lock icon, as the Almanac's own pages do; the name shows
regardless, since the point is to hunt it.

The lines are computed when the page opens, from the game's own tables
(fish, bugs, forageables, artifacts, the museum's set order), so they stay
right under data mods and game updates. The Almanac's category builder is
data-driven; the four entries carry a `field_notes` field the mod's branch
in create_category() recognises, and the vanilla builder never sees them.

    python install.py apply field-notes
    python install.py remove field-notes
"""

from ..patcher import Markers

SLUG = "field_notes"
NAME = "Field Notes"
SUMMARY = "Four Almanac pages listing what the museum still lacks, each item with where and when to find it."
DETAILS = """The journal's Almanac gains four pages, one per museum wing, listing everything that wing still lacks, grouped the way the museum groups it, with a line under each name saying where and when it turns up: the season, the water, the weather, the mine floors, the location's dig sites, the perk that unlocks it. The lines are worked out from the game's own tables when the page opens, so they stay right under data mods. Items you have never held show the lock icon, as the Almanac does, but the name shows regardless, since the point is to go and find it. No toggle; remove the mod to take the pages away."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {}


def defaults():
    return {}


# --- files -------------------------------------------------------------------

SUB_MENUS = "assets/fiddle/ui/menus/sub_menus.toml"
ALMANAC = "assets/gml/scripts/UI/Anchor/Menus/AlmanacMenu.gml"
MUSEUM = "assets/gml/scripts/Museum.gml"
LOCAL = "assets/fiddle/misc_local.toml"

# --- the categories ----------------------------------------------------------
#
# Appended inside the Almanac's `categories` array, after its last entry.
# The engine's TOML reader accepts comments between array elements (misc.toml
# ships one), so the marker lines are fine there. `tags = []` keeps the
# vanilla builder's shape; the `field_notes` field is what our branch keys on.
# Icons reuse the Almanac's own category glyphs.

CATEGORIES_ANCHOR = ('\t\t{ key = "song_crystal", tags = ["song_crystal"], '
                     'icon_sprite = "spr_ui_journal_almanac_icon_song_crystals" },\n')

CATEGORIES = '''{ key = "field_notes_archaeology", tags = [], icon_sprite = "spr_ui_journal_almanac_icon_artifacts", field_notes = "archaeology" },
{ key = "field_notes_fish", tags = [], icon_sprite = "spr_ui_journal_almanac_icon_fish", field_notes = "fish" },
{ key = "field_notes_flora", tags = [], icon_sprite = "spr_ui_journal_almanac_icon_forageables", field_notes = "flora" },
{ key = "field_notes_insect", tags = [], icon_sprite = "spr_ui_journal_almanac_icon_bugs", field_notes = "insect" },'''

# --- AlmanacMenu.gml ---------------------------------------------------------
#
# Two insertions inside the constructor: a branch at the top of the vanilla
# category builder, and the two methods it calls, placed after the last
# field the constructor initialises and before the loop that builds the
# categories - functions declared in a constructor are methods once that
# statement runs, so they must precede their first use.

BRANCH_ANCHOR = "    function create_category(data) {\n"

BRANCH = """//
// Field Notes: a museum wing's missing items, each with where and when.
//
if data[$ "field_notes"] != undefined {
    return self.create_field_notes_category(data);
}
"""

# Not "self.tooltip = undefined;": it appears three times at deeper indents,
# and a shallower indent is a substring of a deeper one. The categories list
# is built exactly once, and the methods land just before that.
METHODS_ANCHOR = "    self.categories = List();\n"

METHODS = """//
// Field Notes. The left-page entry mirrors the vanilla category exactly
// (label, icon, a donated/total count in the small font); the right page
// is a list rather than a grid: one row per missing item, the set's name
// above each group, and a where-and-when line under every name.
//
function create_field_notes_category(data) {
    var local_key = data[$ "local_key"] ?? "misc_local/" + data.key;
    var icon = string_to_asset(data.icon_sprite);
    var wing = string_to_museum_wing(data.field_notes);

    var total = 0;
    var donated = 0;
    var set_keys = MUSEUM_DATA.data[wing].sets.keys();
    for (var i = 0; i < array_length(set_keys); i++) {
        total += museum_set_size(wing, set_keys[i]);
        donated += museum_set_progress(wing, set_keys[i]);
    }

    var element = self.category_scroller.new_element()
        .add_text_label(local_key)
        .add_to_pilot(self.left_pilot, true)
        .set_tap_callback(function(wing, icon, local_key, key) {
            self.open_field_notes(wing, icon, local_key);
            self.active_page = key;
        }, [wing, icon, local_key, data.key])
        .set_selected_getter(function(key) {
            return self.active_page == key;
        }, [data.key]);

    element.text_label
        .set_align(Align.LeftIn, Align.TopIn)
        .set_xy(21, 3)

    ANCHOR.sprite(element.text_label)
        .set_sprite(icon)
        .set_align(Align.LeftOut, Align.Middle)
        .set_x(-4)

    ANCHOR.text(element)
        .set_sprite_font("player_level")
        .set_text(fmt("{}/{}", donated, total))
        .set_xy(21, 20)
        .mirror_node_lut(element.text_label)

    return element;
}

function open_field_notes(wing, icon, title) {
    if self.item_scroller != undefined {
        self.item_scroller.free();
    }
    self.item_scroller = create_scroller(self.journal.right_full_body)
        .subscribe_to_pilot(self.right_pilot);
    if self.tooltip != undefined {
        self.tooltip.close();
        self.tooltip = undefined;
    }
    self.right_pilot.reset();

    var header = self.item_scroller.new_element(23);
    var icon_node = ANCHOR.sprite(header)
        .set_sprite(icon)
        .set_xy(5, 9)
    ANCHOR.text(icon_node)
        .set_lut(COMMON_LUT)
        .set_key(title)
        .set_align(Align.RightOut, Align.Middle)
        .set_x(3)

    var order = MENUS.get_unwrap(Menu.Museum)[$ museum_wing_to_string(wing) + "_order"];
    var listed = 0;
    for (var i = 0; i < array_length(order); i++) {
        var set = MUSEUM_DATA.data[wing].sets.get(order[i]);
        if set == undefined {
            continue;
        }
        var missing = [];
        for (var k = 0; k < array_length(set.items); k++) {
            if MUSEUM_PROGRESS[set.items[k]] != true {
                array_push(missing, set.items[k]);
            }
        }
        if array_length(missing) == 0 {
            continue;
        }

        var head = self.item_scroller.new_element(16);
        ANCHOR.text(head)
            .set_lut(COMMON_LUT)
            .set_key(set.display_name)
            .set_xy(5, 4)

        for (var k = 0; k < array_length(missing); k++) {
            var item_id = missing[k];
            var row = self.item_scroller.new_element(27)
                .add_to_pilot(self.right_pilot);

            var square = common_slice(row, 24, 24)
                .set_xy(3, 1);
            ANCHOR.sprite(square)
                .set_sprite(ARI.items_acquired[item_id]
                    ? ITEM_PROTOTYPES[item_id].icon_sprite
                    : spr_ui_generic_lock_icon)
                .set_align(Align.Center, Align.Middle)

            ANCHOR.text(row)
                .set_lut(COMMON_LUT)
                .set_key(ITEM_PROTOTYPES[item_id].name_key)
                .set_xy(31, 2)

            //
            // The hint wraps at the page's width; a two-line hint grows its
            // row, and everything below it shifts down.
            //
            var hint = ANCHOR.text(row)
                .set_lut(COMMON_LUT)
                .set_max_width(138)
                .set_text(field_notes_hint(wing, order[i], item_id))
                .set_xy(31, 13)
            var overflow = 13 + hint.measure().y + 2 - 27;
            if overflow > 0 {
                self.item_scroller.add_height_to_element(row, overflow);
            }

            listed += 1;
        }
    }

    if listed == 0 {
        var done = self.item_scroller.new_element(23);
        ANCHOR.text(done)
            .set_lut(COMMON_LUT)
            .set_key("misc_local/field_notes_complete")
            .set_xy(5, 6)
    }

    ANCHOR.set_active_pilot(self.right_pilot);
}
"""

# --- Museum.gml: the where-and-when lines ------------------------------------
#
# Global helpers appended to the museum script. Everything they say comes
# from the game's tables at call time: fiddle_get("fish"), ("bugs"),
# ("forageables"), ("artifacts"), and the museum's own set names. Words are
# localization keys of this mod's (mirrored into every language table), the
# seasons and location names the game's own.

HINTS = """
//
// Field Notes: one short line per missing museum item saying where and when
// it turns up. Built from the raw tables so data mods and updates are
// honoured; every word is a localization key.
//
function field_notes_word(key) {
    return local_get("misc_local/fn_" + key);
}

function field_notes_join(parts) {
    var out = "";
    for (var i = 0; i < array_length(parts); i++) {
        if parts[i] == undefined || parts[i] == "" {
            continue;
        }
        out += (out == "" ? "" : " - ") + parts[i];
    }
    return out;
}

function field_notes_season_word(season) {
    return local_get("misc_local/" + season);
}

//
// A seasons array from a raw table entry: all four (or none given) reads
// as "any season"; otherwise the season names joined with slashes.
//
function field_notes_seasons(seasons) {
    if !is_array(seasons) || array_length(seasons) >= 4 {
        return field_notes_word("any_season");
    }
    var out = "";
    for (var i = 0; i < array_length(seasons); i++) {
        out += (i > 0 ? "/" : "") + field_notes_season_word(seasons[i]);
    }
    return out;
}

//
// The mine biome a museum set name refers to, as a floor-range word.
//
function field_notes_mine_word(set_key) {
    switch set_key {
        case "upper_mines":
        case "upper_mines_artifacts": return field_notes_word("mines_1_20");
        case "tide_caverns": return field_notes_word("mines_21_40");
        case "deep_earth": return field_notes_word("mines_41_60");
        case "lava_caves": return field_notes_word("mines_61_80");
        case "ruins":
        case "dragon": return field_notes_word("ruins_81");
        default: return undefined;
    }
}

function field_notes_biome_word(biome) {
    switch biome {
        case "upper": return field_notes_word("mines_1_20");
        case "tide_caverns": return field_notes_word("mines_21_40");
        case "deep_earth": return field_notes_word("mines_41_60");
        case "lava_caves": return field_notes_word("mines_61_80");
        case "ruins": return field_notes_word("ruins_81");
        default: return undefined;
    }
}

function field_notes_rarity_word(rarity) {
    switch rarity {
        case "common": return field_notes_word("common");
        case "uncommon": return field_notes_word("uncommon");
        case "rare": return field_notes_word("rare");
        case "very_rare": return field_notes_word("very_rare");
        case "legendary": return field_notes_word("legendary");
        default: return undefined;
    }
}

//
// What the museum's set name already says, so the hint need not repeat
// it: "fall_pond" is the season and the water, "summer" is the season.
//
function field_notes_set_season(set_key) {
    static SEASONS = ["spring", "summer", "fall", "winter"];
    for (var i = 0; i < array_length(SEASONS); i++) {
        if set_key == SEASONS[i] || string_pos(SEASONS[i] + "_", set_key) == 1 {
            return SEASONS[i];
        }
    }
    return undefined;
}

function field_notes_set_water(set_key) {
    static WATERS = ["river", "pond", "ocean"];
    for (var i = 0; i < array_length(WATERS); i++) {
        var w = WATERS[i];
        if string_length(set_key) > string_length(w)
            && string_copy(set_key, string_length(set_key) - string_length(w), string_length(w) + 1) == "_" + w
        {
            return w;
        }
    }
    return undefined;
}

function field_notes_artifact_hint(set_key, item_id) {
    var f = fiddle_get("artifacts");
    var name = item_id_to_string(item_id);
    var source = undefined;

    var mine = field_notes_mine_word(set_key);
    if mine != undefined {
        source = mine + " " + field_notes_word("dig_sites");
    } else {
        switch set_key {
            case "mine": source = field_notes_word("any_mine_floor"); break;
            case "common_finds": source = field_notes_word("any_dig_site"); break;
            case "oopart": source = field_notes_join([field_notes_word("dig_sites"), field_notes_word("well_placed")]); break;
            case "aquatic": source = field_notes_join([field_notes_word("fishing"), field_notes_word("aquatic_antiquities")]); break;
            case "sunken": source = field_notes_join([field_notes_word("dive_spot"), field_notes_word("sunken_secrets")]); break;
            case "fish_trap": source = field_notes_word("fish_trap"); break;
            case "ritual": source = field_notes_join([field_notes_word("ritual_chamber"), field_notes_word("lost_to_history")]); break;
            case "mist": source = field_notes_join([field_notes_word("mist_sights"), field_notes_word("mist_sight")]); break;
            case "vintage_farm_tools": source = field_notes_join([field_notes_word("farm_dig_site"), field_notes_word("former_farmers")]); break;
            case "metals_of_mistria":
            case "gems_of_mistria": source = field_notes_word("mining_rare_drop"); break;
            default:
                //
                // The overworld sets: artifacts.toml maps a location to each.
                //
                var locs = struct_get_names(f.locations);
                for (var i = 0; i < array_length(locs); i++) {
                    if f.locations[$ locs[i]] == set_key {
                        source = local_get("locations/" + locs[i] + "/name") + " " + field_notes_word("dig_sites");
                        break;
                    }
                }
                break;
        }
    }

    var rarity = field_notes_rarity_word(f.loot[$ name]);
    return field_notes_join([source, rarity]);
}

function field_notes_fish_hint(set_key, item_id) {
    var raw = fiddle_get("fish")[$ item_id_to_string(item_id)];
    if raw == undefined {
        return "";
    }
    var parts = [];

    var retrieval = raw[$ "retrieval"];
    var in_mines = retrieval == "mines" || (is_array(retrieval) && array_contains(retrieval, "mines"));
    var dive_only = retrieval == "divespot" || (is_array(retrieval) && array_length(retrieval) == 1 && retrieval[0] == "divespot");
    var trap = retrieval == "fish_trap";
    var set_season = field_notes_set_season(set_key);
    var set_water = field_notes_set_water(set_key);

    if !in_mines && !trap && set_season == undefined && set_key != "multi_season_fish" {
        array_push(parts, field_notes_seasons(raw[$ "seasons"]));
    }

    if in_mines {
        if field_notes_mine_word(set_key) == undefined {
            array_push(parts, field_notes_word("any_mine_floor"));
        }
    } else if trap {
        if set_key != "fish_trap" {
            array_push(parts, field_notes_word("fish_trap"));
        }
    } else {
        var locs = raw[$ "locations"];
        if is_array(locs) && array_length(locs) > 0 && set_key != locs[0] {
            array_push(parts, local_get("locations/" + locs[0] + "/name"));
        }
        var water = raw[$ "water_type"];
        if set_water == undefined {
            if is_string(water) {
                array_push(parts, field_notes_word(water));
            } else if is_array(water) {
                var w = "";
                for (var i = 0; i < array_length(water); i++) {
                    w += (i > 0 ? "/" : "") + field_notes_word(water[i]);
                }
                array_push(parts, w);
            }
        }
        if dive_only {
            array_push(parts, field_notes_word("dive_spot"));
        }
    }

    var weather = raw[$ "weather"];
    if is_array(weather) && array_length(weather) > 0 && !array_contains(weather, "calm") {
        array_push(parts, field_notes_word("rain"));
    }
    if raw[$ "bait_only"] == true && set_key != "fish_bait" {
        array_push(parts, field_notes_word("needs_bait"));
    }
    if raw[$ "legendary"] == true && set_key != "legendary" {
        array_push(parts, field_notes_word("legendary"));
    }
    if array_length(parts) == 0 {
        array_push(parts, field_notes_word("any_weather"));
    }
    return field_notes_join(parts);
}

function field_notes_insect_hint(set_key, item_id) {
    switch set_key {
        case "honey": return field_notes_word("beehives");
        case "bug_pheromone": return field_notes_word("crafted");
        default: break;
    }
    var bugs = fiddle_get("bugs");
    var raw = bugs[$ item_id_to_string(item_id)];
    if raw == undefined {
        return "";
    }
    var def = bugs[$ "default"];
    var parts = [];

    if field_notes_set_season(set_key) == undefined && set_key != "multi_season" {
        array_push(parts, field_notes_seasons(raw[$ "seasons"] ?? def.seasons));
    }

    var tag = raw[$ "tag"] ?? def.tag;
    if !is_array(tag) {
        tag = [tag];
    }
    var place_in_set = set_key == "beach" || set_key == "deep_woods" || set_key == "grass"
        || field_notes_mine_word(set_key) != undefined;
    if place_in_set {
        // the set name says where
    } else if array_contains(tag, "mines") {
        array_push(parts, field_notes_biome_word(raw[$ "dungeon_biome"]) ?? field_notes_word("any_mine_floor"));
    } else if array_contains(tag, "beach") && array_length(tag) == 1 {
        array_push(parts, field_notes_word("beach"));
    } else if array_contains(tag, "deep_woods") && array_length(tag) == 1 {
        array_push(parts, field_notes_word("deep_woods"));
    } else if array_contains(tag, "water_bug") {
        array_push(parts, field_notes_word("near_water"));
    } else {
        array_push(parts, field_notes_word("outdoors"));
    }

    var hours = raw[$ "hours"] ?? def.hours;
    if is_array(hours) && array_length(hours) == 2 {
        if hours[0] >= 20 {
            array_push(parts, field_notes_word("night"));
        } else if hours[1] <= 20 {
            array_push(parts, field_notes_word("day"));
        }
    }

    var weather = raw[$ "weather"] ?? def.weather;
    if is_array(weather) && !array_contains(weather, "calm") {
        array_push(parts, field_notes_word("rain"));
    }

    var spawn = raw[$ "spawn"] ?? def.spawn;
    if !is_array(spawn) {
        spawn = [spawn];
    }
    if array_contains(spawn, "rock") {
        array_push(parts, field_notes_word("on_rocks"));
    } else if array_contains(spawn, "canopy") {
        array_push(parts, field_notes_word("in_trees"));
    } else if array_contains(spawn, "grass") {
        array_push(parts, field_notes_word("in_grass"));
    }

    if raw[$ "pheromones_only"] == true {
        array_push(parts, field_notes_word("pheromones_only"));
    }
    var rarity = raw[$ "rarity"] ?? def.rarity;
    if (rarity == "rare" || rarity == "very_rare" || rarity == "legendary")
        && set_key != "rare" && set_key != "legendary"
    {
        array_push(parts, field_notes_rarity_word(rarity));
    }
    if array_length(parts) == 0 {
        array_push(parts, field_notes_word("any_time"));
    }
    return field_notes_join(parts);
}

//
// Which forage rarity list (this season) holds the item, if any.
//
function field_notes_forage_rarity(season, name) {
    var f = fiddle_get("forageables");
    var table = f[$ season];
    if table == undefined {
        return undefined;
    }
    static RARITIES = ["common", "uncommon", "rare", "legendary"];
    for (var i = 0; i < array_length(RARITIES); i++) {
        var list = table[$ RARITIES[i]];
        if is_array(list) && array_contains(list, name) {
            return RARITIES[i];
        }
    }
    return undefined;
}

function field_notes_flora_hint(set_key, item_id) {
    var name = item_id_to_string(item_id);
    if field_notes_mine_word(set_key) != undefined || set_key == "deep_woods" {
        return field_notes_word("forage");
    }
    if set_key == "void" {
        return field_notes_word("void_sight");
    }

    //
    // The seasonal sets: "<season>_crops", "<season>_flowers", "<season>_forage".
    // The set name carries the season, so the hint says only how.
    //
    var underscore = string_pos("_", set_key);
    if underscore == 0 {
        return "";
    }
    var season = string_copy(set_key, 1, underscore - 1);
    var kind = string_delete(set_key, 1, underscore);

    if kind == "crops" {
        return field_notes_word("store_seeds");
    }

    var sand = fiddle_get("forageables")[$ "sand_forageables"];
    if is_array(sand) && array_contains(sand, name) {
        return field_notes_join([field_notes_word("beach"), field_notes_word("forage")]);
    }
    var rarity = field_notes_forage_rarity(season, name);
    if rarity != undefined {
        return field_notes_join([field_notes_word("forage"), field_notes_rarity_word(rarity)]);
    }
    if kind == "flowers" {
        return field_notes_word("store_seeds");
    }
    return field_notes_word("forage");
}

function field_notes_hint(wing, set_key, item_id) {
    switch wing {
        case MuseumWing.Archaeology: return field_notes_artifact_hint(set_key, item_id);
        case MuseumWing.Fish: return field_notes_fish_hint(set_key, item_id);
        case MuseumWing.Flora: return field_notes_flora_hint(set_key, item_id);
        case MuseumWing.Insect: return field_notes_insect_hint(set_key, item_id);
        default: return "";
    }
}
"""

# --- labels ------------------------------------------------------------------

LABELS = '''field_notes_archaeology = "Notes: Artifacts"
field_notes_fish = "Notes: Fish"
field_notes_flora = "Notes: Flora"
field_notes_insect = "Notes: Insects"
field_notes_complete = "Nothing left to find here."
fn_any_season = "Any season"
fn_any_weather = "Any weather"
fn_any_time = "Any time of day"
fn_day = "Day"
fn_night = "Night"
fn_rain = "Rain"
fn_river = "River"
fn_pond = "Pond"
fn_ocean = "Ocean"
fn_dive_spot = "Dive spot"
fn_fish_trap = "Fish trap"
fn_needs_bait = "Needs bait"
fn_legendary = "Legendary"
fn_common = "Common"
fn_uncommon = "Uncommon"
fn_rare = "Rare"
fn_very_rare = "Very rare"
fn_mines_1_20 = "Mines 1-20"
fn_mines_21_40 = "Mines 21-40"
fn_mines_41_60 = "Mines 41-60"
fn_mines_61_80 = "Mines 61-80"
fn_ruins_81 = "Ruins 81+"
fn_any_mine_floor = "Any mine floor"
fn_any_dig_site = "Any dig site"
fn_dig_sites = "dig sites"
fn_outdoors = "Outdoors"
fn_near_water = "Near water"
fn_beach = "Beach"
fn_deep_woods = "Deep Woods"
fn_on_rocks = "On rocks"
fn_in_trees = "In trees"
fn_in_grass = "In tall grass"
fn_pheromones_only = "Pheromones only"
fn_beehives = "Beehives"
fn_crafted = "Crafted"
fn_store_seeds = "Seeds at the store"
fn_forage = "Forage"
fn_void_sight = "Needs Void Sight"
fn_fishing = "Fishing"
fn_well_placed = "Well Placed perk"
fn_aquatic_antiquities = "Aquatic Antiquities perk"
fn_sunken_secrets = "Sunken Secrets perk"
fn_ritual_chamber = "Ritual chamber"
fn_lost_to_history = "Lost to History perk"
fn_mist_sights = "Mist sights"
fn_mist_sight = "Mist Sight perk"
fn_farm_dig_site = "Farm dig site"
fn_former_farmers = "Former Farmers perk"
fn_mining_rare_drop = "Rare drop while mining"'''


# The player-visible text this mod adds; the framework mirrors it into every
# language's table so it never renders as MISSING.
TRANSLATE = {"misc_local": LABELS}


def patches(mk, opt):
    return {
        SUB_MENUS: [(CATEGORIES_ANCHOR,
                     CATEGORIES_ANCHOR + mk.block(CATEGORIES, "\t\t", toml=True))],
        ALMANAC: [
            (BRANCH_ANCHOR, BRANCH_ANCHOR + mk.block(BRANCH, " " * 8)),
            (METHODS_ANCHOR, mk.block(METHODS, " " * 4) + METHODS_ANCHOR),
        ],
        MUSEUM: [(mk.APPEND, mk.block(HINTS))],
        LOCAL: [(mk.APPEND, mk.block(LABELS, toml=True))],
    }
