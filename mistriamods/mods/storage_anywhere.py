"""Reach every chest in the world from anywhere.

Press a key for a scrollable list of all your storage, grouped by location -
name, how full it is, a preview of what is inside, and whether it feeds
crafting. Pick one and the game's own storage screen opens on it.

The mod adds no registry of its own. `STORAGE_NODES` is already a global List
holding every node with an inventory, pushed in `setup_furniture_node()` and
spliced out in `GridUtils` on destroy - the crafting system uses it to pull
ingredients out of chests. Every location's grid is built and loaded at startup
(`LoadGame.gml` walks all of LocationId except the Dungeon), so that list
already spans the whole map at all times. All this mod does is show it to you -
after checking each entry is still real, because nine locations reset nightly
and the list accumulates stale copies the game itself never notices.

The key is a real, rebindable control and shows up in Settings > Controls. It
defaults to B. Toggleable in Settings > Accessibility ("Storage Anywhere").

Every row carries a pin icon on its left edge - click it to pin or unpin that
chest with the mouse, or press the pin key (default P, a real rebindable
control) on the highlighted row. Pinned chests form their own group at the
very top of the list, each row naming the place it lives, in the order they
were pinned. Pins are remembered in settings.json next to the key bindings -
the save file stays untouched.
"""

from ..patcher import Markers

SLUG = "storage_anywhere"
NAME = "Storage Anywhere"
SUMMARY = "Press B for a list of every chest in the world and open any of them from where you stand; pin favourites with P."
DETAILS = """Press B for a list of every chest in the world, grouped by location, and open any of them from wherever you stand. Chests in your current room come first, the one you opened last is pre-selected, and each row shows the chest's name, how full it is, a preview of what is inside, and whether it feeds crafting. Pin your favourites so they always sit at the top: click the pin icon on a row, or press P on it. Fridges, the stable chest, miners' crates, the shipping bin and turn-in boxes are all included, with no range limit. Both keys are real controls, rebindable under Settings > Controls, and pins are remembered in your settings file, never in your save."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "chest_key": (str, "B", "DEFAULT key only; rebind in game afterwards"),
    "pin_key": (str, "P", "DEFAULT pin/unpin key; rebind in game afterwards"),
}


def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}


MENUS = "assets/fiddle/ui/menus/standard_menus.toml"
ANCHOR = "assets/gml/scripts/UI/Anchor/Anchor.gml"
STORAGEMENU = "assets/gml/scripts/UI/Anchor/Menus/StorageMenu.gml"
INPUTUTILS = "assets/gml/scripts/GameplaySystems/Input/InputUtils.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
MENU = "assets/gml/scripts/UI/Anchor/Menus/SettingsMenu.gml"
ARI = "assets/gml/objects/characters/obj_ari.gml"
LOCAL = "assets/fiddle/misc_local.toml"

# --- anchors -----------------------------------------------------------------
#
# Crop Labels and Daily Checklist also register controls, so these three are the
# shared single-line anchors: each survives the others' inserted blocks whichever
# order the mods are applied in, and every one of them inserts immediately after.

ENUM_ANCHOR = "    ResetControls,\n"
CATEGORY_ANCHOR = "        case InputId.Ride:\n"
DEFAULTS_ANCHOR = ('        case InputId.ConfirmTextInput: return '
                   '["enter", undefined, "start", undefined];\n')

SETTINGS_ANCHOR = "        can_burn_fruit_trees: true,\n"

MENU_ANCHOR = ('        self.checkbox("screenshake");\n'
               '        self.checkbox("screen_flash");\n')

SPAWN_ANCHOR = ("                case Menu.Storage: return new StorageMenu"
                "(arg1, arg2, arg3, arg4, arg5, arg6);\n")

# Guarded by game_paused() already, and every branch returns true after opening,
# which is exactly the contract a new branch needs to honour.
OPENS_ANCHOR = """            function check_for_menu_opens() {
                if game_paused() {
                    return false;
                }

"""

OPENS_EFFECT = """//
// Storage Anywhere: open the chest picker.
//
if SETTINGS.get("storage_anywhere")
    && INPUT.take_press(InputId.OpenChestPicker)
{
    chest_picker_ensure_stats();
    ANCHOR.spawn_menu(Menu.ChestPicker);
    return true;
}

"""

# `Menu` is generated from these keys, so this entry is what mints
# Menu.ChestPicker. Fields are from ui/menus/default.toml.
MENU_ENTRY = '''# The menu listing every chest in the world.
[chest_picker]
\tcanvas_kind = "minspec"
\tbackplate_name = "backplate"
\tlisten_for_exit = true
\thas_background = true
\tpause = "main"
'''

HELPER = """
//
// Storage Anywhere.
//

//
// The chest opened last, so reopening the picker lands on it. Held as the node
// itself rather than an index: chests can be built and broken between openings,
// and a stale index would point at someone else's crate.
//
#macro CHEST_PICKER_LAST global.__chest_picker_last
CHEST_PICKER_LAST = undefined;

//
// object id -> the item that places it, built once and kept. Chest prototypes
// carry no name of their own; the name belongs to the furniture item, which
// points the other way (`item.prototype.object`), so the map has to be inverted.
//
#macro CHEST_PICKER_ITEM_MAP global.__chest_picker_item_map
CHEST_PICKER_ITEM_MAP = undefined;

function chest_picker_item_for_object(object_id) {
    if CHEST_PICKER_ITEM_MAP == undefined {
        CHEST_PICKER_ITEM_MAP = {};

        for (var i = 0; i < ItemId.LEN; i++) {
            var proto = ITEM_PROTOTYPES[i];
            if proto == undefined {
                continue;
            }

            var obj = proto[$ "object"];
            if obj == undefined {
                continue;
            }

            //
            // Several recolours place the same object; first one wins, and they
            // share a display name anyway.
            //
            var key = string(obj);
            if !struct_exists(CHEST_PICKER_ITEM_MAP, key) {
                CHEST_PICKER_ITEM_MAP[$ key] = i;
            }
        }
    }

    if object_id == undefined {
        return undefined;
    }

    var key = string(object_id);
    return struct_exists(CHEST_PICKER_ITEM_MAP, key)
        ? CHEST_PICKER_ITEM_MAP[$ key]
        : undefined;
}

//
// spawn_menu() counts every open into GAME_STATS.menu_opens, keyed by menu name,
// and it does that BEFORE it builds anything:
//
//     GAME_STATS.menu_opens[$ menu_to_string(menu_id)] += 1;
//
// A key that was never created reads as undefined, and `+= 1` on undefined is a
// hard crash - "bad unary op inc undefined" - so a brand new menu id dies there
// on its first open, before its constructor ever runs.
//
// The keys are created by patch_game_stats(), which walks Menu.LEN and fills in
// whatever is missing. But that only runs on a NEW GAME, or from
// apply_save_patches() when a save is migrated between versions. An existing
// save already at the current version never gets patched, so it never learns
// about a menu added afterwards. Hence: create it ourselves, once, on demand.
//
function chest_picker_ensure_stats() {
    if GAME_STATS == undefined {
        return;
    }

    var key = menu_to_string(Menu.ChestPicker);
    if GAME_STATS.menu_opens[$ key] == undefined {
        GAME_STATS.menu_opens[$ key] = 0;
    }
}

//
// Pinned chests - the favourites, shown in their own group at the top of the
// picker. Stored in settings.json next to the key bindings, never in the
// save. Identity is location + cell rather than a node reference, which
// survives restarts; a chest that gets moved or broken simply stops matching
// until it is pinned again, and its orphaned entry sits harmlessly in the
// string. Static locations key by LocationId, so renaming the farm keeps its
// pins; building interiors have no id and key by their (user-typed) name,
// with the separators laundered out of it.
//
function chest_picker_pin_id(place, node) {
    var where = place.loc != undefined
        ? "loc" + string(place.loc)
        : "dyn" + string_replace_all(
            string_replace_all(string(place.label), ";", "_"), "@", "_");
    return where + "@" + string(node.top_left_x)
        + "," + string(node.top_left_y);
}

function chest_picker_pins() {
    var raw = SETTINGS.get("chest_picker_pins");
    if raw == undefined || !is_string(raw) || raw == "" {
        return [];
    }
    return string_split(raw, ";");
}

function chest_picker_toggle_pin(pin_id) {
    var pins = chest_picker_pins();
    var out = "";
    var removed = false;

    for (var i = 0; i < array_length(pins); i++) {
        if pins[i] == pin_id {
            removed = true;
            continue;
        }
        if pins[i] == "" {
            continue;
        }
        out += (out == "" ? "" : ";") + pins[i];
    }

    if !removed {
        out += (out == "" ? "" : ";") + pin_id;
    }

    SETTINGS.set("chest_picker_pins", out);
    save_settings();
}

//
// The first keyboard binding for the pin control, for the footer hint - so a
// rebind shows up in the hint too. Anything unprintable (a cleared binding, a
// keycode that will not name itself) falls back to the shipped default.
//
function chest_picker_pin_key_name() {
    var raw = undefined;

    var bindings = SETTINGS.get("bindings");
    if bindings != undefined {
        var entry = bindings[$ input_id_to_string(InputId.PinChest)];
        if entry != undefined && array_length(entry) > 0 {
            raw = entry[0];
        }
    }

    if raw != undefined && !is_string(raw) {
        raw = gm_keycode_to_string(raw);
    }
    if raw == undefined || !is_string(raw) || string_length(raw) == 0
        || string_length(raw) > 9
    {
        raw = default_bindings_for_input_id(InputId.PinChest)[0];
    }

    return string_upper(raw);
}

//
// "small_coop" -> "Small Coop". Forty-one locations define no display name at
// all - every coop, barn and greenhouse interior among them - so a prettified
// id beats both a raw key and a shrugging "Elsewhere".
//
function chest_picker_prettify(key) {
    var out = "";
    var cap = true;

    for (var i = 1; i <= string_length(key); i++) {
        var ch = string_char_at(key, i);
        if ch == "_" {
            out += " ";
            cap = true;
            continue;
        }
        out += cap ? string_upper(ch) : ch;
        cap = false;
    }

    return out;
}

//
// A location's display name.
//
// `LOCATIONS[i].name` is a localization KEY, not a string - printing it raw
// gives you "locations/player_home/name". It is also absent on some locations,
// the farm among them, which is why show_room_title() special-cases the farm to
// ARI.farm_name rather than reading the location at all. Same chain here.
//
function chest_picker_place_name(loc) {
    if loc == undefined {
        return local_get("misc_local/chest_picker_elsewhere");
    }

    if loc == LocationId.Farm {
        return ARI.farm_name;
    }

    var location = LOCATIONS[loc];
    if location != undefined && location[$ "name"] != undefined {
        return local_get(location.name);
    }

    return chest_picker_prettify(location_id_to_string(loc));
}

//
// Where is this chest, really?
//
// Identity, not stored fields: a grid is only current if it IS the grid the
// world holds for some location - `GRIDS[l] == grid` - or a registered dynamic
// grid (a building interior, labelled with the building's own name, the same
// source show_room_title() uses). Stale nodes from the nightly resets carry
// grids that fail every identity test, so this doubles as the liveness check
// the stored-field walk could never quite be.
//
function chest_picker_where(node) {
    var grid = node[$ "parent_grid"];
    var guard = 0;

    while grid != undefined && guard < 8 {
        guard += 1;

        for (var l = 0; l < LocationId.LEN; l++) {
            if GRIDS[l] == grid {
                return { live: true, loc: l, label: chest_picker_place_name(l) };
            }
        }

        if grid[$ "dyn_index"] != undefined
            && grid.dyn_index < DYNAMIC_GRIDS.count()
            && DYNAMIC_GRIDS.get(grid.dyn_index) == grid
        {
            var buildings = get_buildings();
            for (var b = 0, bc = buildings.count(); b < bc; b++) {
                var building = buildings.get(b);
                if building.dyn_index == grid.dyn_index
                    && building[$ "name"] != undefined
                {
                    return { live: true, loc: undefined, label: string(building.name) };
                }
            }
        }

        var pn = grid[$ "parent_node"];
        grid = pn == undefined ? undefined : pn[$ "parent_grid"];
    }

    return { live: false, loc: undefined, label: "" };
}

function chest_picker_name_of(node) {
    var item = chest_picker_item_for_object(node.object_id);
    if item != undefined {
        return local_get(ITEM_PROTOTYPES[item].name_key);
    }

    //
    // Fixed containers - the stable chest, miners' crates - are placed by the
    // map rather than by an item, so they have no furniture item to name them.
    //
    return local_get("misc_local/chest_picker_generic");
}

//
// Clip a string to a pixel width, with an ellipsis.
//
// NOT set_max_width() - that one turns line breaking back ON and wraps, which is
// what made an earlier mod's labels render one character per line. Measuring is
// safe: string_width_font defaults to ANCHOR.get_text_font(), the same font the
// text nodes draw with.
//
function chest_picker_fit(text, max_px) {
    if string_width_font(text) <= max_px {
        return text;
    }

    var out = text;
    while string_length(out) > 1 && string_width_font(out + "..") > max_px {
        out = string_copy(out, 1, string_length(out) - 1);
    }

    return out + "..";
}

//
// Is this node still on its own grid? Guards against a reset overwriting the
// cells in place. chest_picker_where() handles the other staleness - a node
// whose whole grid was retired.
//
function chest_picker_is_live(node) {
    var grid = node[$ "parent_grid"];
    if grid == undefined {
        return false;
    }

    var ni = grid.try_node_index_for_cell(node.top_left_x, node.top_left_y);
    if ni == undefined {
        return false;
    }

    return grid.node_parent[ni] == node;
}

//
// Every real chest: pinned favourites first, then your current location's
// groups, then everywhere else; within a place, fuller chests come before
// empty ones, so the working storage floats up and untouched shipping bins
// sink. A pinned row keeps its home in its name, since the group header no
// longer says it.
//
// STORAGE_NODES also holds factories and the auto-feeder - anything with an
// inventory - so the interaction_chest test is what keeps furnaces and looms
// out of the list. It also accumulates stale entries: nine locations are
// reset_every_night, and rewriting those grids pushes fresh nodes without
// retiring the old ones. The game never notices - the stale copies are empty,
// so shipping and crafting walk straight past them - but a picker that lists
// the array notices very much. Hence the two liveness tests.
//
function chest_picker_entries() {
    var here = CURRENT_LOCATION_ID;
    var buckets = [];
    var pinned = [];
    var seen = {};
    var pins = chest_picker_pins();
    var pinned_label = local_get("misc_local/chest_picker_pinned");

    for (var i = 0, c = STORAGE_NODES.count(); i < c; i++) {
        var node = STORAGE_NODES.get(i);
        if node == undefined || node[$ "inventory"] == undefined {
            continue;
        }
        if node.prototype[$ "interaction_chest"] == undefined {
            continue;
        }
        if !chest_picker_is_live(node) {
            continue;
        }

        var place = chest_picker_where(node);
        if !place.live {
            continue;
        }

        //
        // One chest per cell. Two entries describing the same physical chest
        // can only ever be a bookkeeping artefact.
        //
        var key = place.label + ":" + string(node.top_left_x)
            + ":" + string(node.top_left_y);
        if struct_exists(seen, key) {
            continue;
        }
        seen[$ key] = true;

        var inv = node.inventory;
        var used = 0;
        for (var s = 0, sc = inv.size(); s < sc; s++) {
            if inv.slot(s).count > 0 {
                used += 1;
            }
        }

        var pin_id = chest_picker_pin_id(place, node);
        var pin_index = -1;
        for (var p = 0; p < array_length(pins); p++) {
            if pins[p] == pin_id {
                pin_index = p;
                break;
            }
        }

        var entry = {
            node: node,
            used: used,
            size: inv.size(),
            name: chest_picker_name_of(node),
            place: place.label,
            pin: pin_id,
            is_pinned: pin_index >= 0,
        };

        if pin_index >= 0 {
            entry.place = pinned_label;
            entry.name = entry.name + " - " + place.label;
            entry.order = pin_index;
            array_push(pinned, entry);
            continue;
        }

        var bucket = undefined;
        for (var b = 0; b < array_length(buckets); b++) {
            if buckets[b].label == place.label {
                bucket = buckets[b];
            }
        }
        if bucket == undefined {
            bucket = {
                label: place.label,
                here: place.loc != undefined && place.loc == here,
                entries: [],
            };
            array_push(buckets, bucket);
        }
        array_push(bucket.entries, entry);
    }

    //
    // Fuller chests first within each place. Selection sort - a bucket holds a
    // handful of chests, not a warehouse.
    //
    for (var b = 0; b < array_length(buckets); b++) {
        var list = buckets[b].entries;
        for (var a = 0; a < array_length(list); a++) {
            var best = a;
            for (var j = a + 1; j < array_length(list); j++) {
                if list[j].used > list[best].used {
                    best = j;
                }
            }
            if best != a {
                var tmp = list[a];
                list[a] = list[best];
                list[best] = tmp;
            }
        }
    }

    //
    // Pinned chests keep the order they were pinned in - unpin and re-pin to
    // reshuffle - so the group never rearranges itself under your feet.
    //
    for (var a = 0; a < array_length(pinned); a++) {
        var best = a;
        for (var j = a + 1; j < array_length(pinned); j++) {
            if pinned[j].order < pinned[best].order {
                best = j;
            }
        }
        if best != a {
            var tmp = pinned[a];
            pinned[a] = pinned[best];
            pinned[best] = tmp;
        }
    }

    var out = [];
    for (var p = 0; p < array_length(pinned); p++) {
        array_push(out, pinned[p]);
    }
    for (var pass = 0; pass < 2; pass++) {
        for (var b = 0; b < array_length(buckets); b++) {
            if buckets[b].here == (pass == 0) {
                for (var e = 0; e < array_length(buckets[b].entries); e++) {
                    array_push(out, buckets[b].entries[e]);
                }
            }
        }
    }

    return out;
}

//
// Open one chest on the game's own storage screen. This mirrors the interaction
// in Interact.gml, minus the turn-in box's quest recipe, and skips the lid
// animation for a chest in another room - `renderer` only exists for the
// location you are actually standing in.
//
function chest_picker_open(node) {
    var chest = node.prototype.interaction_chest;

    //
    // A chest visited earlier holds a DEAD renderer: leaving a location
    // destroys its renderer instances, but the node keeps the reference, and
    // touching any variable on it is the "expired instance" crash. Every guard
    // downstream - ours below, and the game's own in StorageMenu.on_close() -
    // only tests `!= undefined`, which an expired instance passes. Normalize it
    // to undefined here so all of those guards work as written. Harmless:
    // re-entering the location reassigns the renderer anyway.
    //
    if node[$ "renderer"] != undefined && !instance_exists(node.renderer) {
        node.renderer = undefined;
    }

    if instance_exists(obj_ari) {
        obj_ari.set_idle_simple();
    }

    var menu = ANCHOR.spawn_menu(Menu.Storage, node)
        .set_inventories(node.inventory, ARI.inventory)
        .with_right_help_button()
        .with_right_banner();

    //
    // Mirror Interact.gml's branches exactly. A turn-in box is a quest dropbox,
    // not storage: it gets the quest's recipe checklist and alt-stack behaviour
    // instead of a left banner - whose pull button would let you toggle a quest
    // box into a crafting source, and whose trash button has no business there.
    //
    if node.object_id == ObjectId.TurnInBox {
        menu.with_alt_stack_behavior();

        var recipe_for_box = undefined;
        if node[$ "building_box"] != undefined {
            recipe_for_box = BLUEPRINT_PROTOTYPES[node.blueprint_id].turn_in_box_recipe;
        } else {
            var q = QUEST_LOG.active.get(node.quest_id);
            var data = q.quest.tasks.get(q.current_stage).requirements[Requirement.SuppliedItems][0].items;

            recipe_for_box = {};
            for (var i = 0; i < array_length(data); i++) {
                if data[i] != 0 {
                    recipe_for_box[$ i] = data[i];
                }
            }
        }

        menu.with_recipe(recipe_for_box);
    } else if !chest.shipping_bin {
        menu.with_left_banner();
    }

    menu.with_chest_node(node);

    //
    // The open sound plays at Ari, exactly where the interaction path plays it,
    // so a remote open is not eerily silent. Only the lid animation needs the
    // renderer, and only a same-room chest has a live one.
    //
    if instance_exists(obj_ari) {
        TANGO.play(chest.open_sfx, obj_ari.x, obj_ari.y);
    }

    if node[$ "renderer"] != undefined {
        node.renderer.sprite_index = chest.opening_sprite;
        node.renderer.image_speed = 1;
        node.renderer.image_index = 0.0;
    }

    menu.build();
}

//
// The picker itself. Built on the engine's scroller + pilot, the same pair the
// settings pages use, so keyboard, controller and mouse all navigate it without
// any input handling here.
//
function ChestPickerMenu() : AnchorMenu(Menu.ChestPicker) constructor {
    //
    // The same key closes the picker, so B is a toggle. This cannot live in
    // check_for_menu_opens - that path is gated behind game_paused(), and this
    // menu pauses - but on_think runs every frame the menu is open.
    //
    // The pin key works on the row under the cursor when there is one - in
    // directional control hover IS the selection, courtesy of hover_node -
    // and falls back to the pilot's row when the mouse is parked elsewhere.
    //
    function on_think() {
        if INPUT.take_press(InputId.OpenChestPicker) {
            self.close();
            return;
        }

        if !INPUT.take_press(InputId.PinChest) {
            return;
        }

        var target = undefined;
        for (var i = 0; i < array_length(self.rows); i++) {
            if self.rows[i].element.is_hovered() {
                target = self.rows[i];
                break;
            }
        }
        if target == undefined && self[$ "pilot"] != undefined {
            var sel = self.pilot.get();
            for (var i = 0; i < array_length(self.rows); i++) {
                if self.rows[i].element == sel {
                    target = self.rows[i];
                    break;
                }
            }
        }
        if target == undefined {
            return;
        }

        chest_picker_toggle_pin(target.entry.pin);

        //
        // Rebuild so the row changes group right away, landing focus back on
        // the same chest - the same close-then-spawn the tap callback rides.
        //
        CHEST_PICKER_LAST = target.entry.node;
        self.close();
        chest_picker_ensure_stats();
        ANCHOR.spawn_menu(Menu.ChestPicker);
    }

    //
    // Rows are two REAL lines: item icons are 16px sprites, so the row must
    // clear a ~12px text line plus a 16px icon line or the two print over each
    // other - which is exactly what the first draft did.
    //
    static PANEL_W = 300;
    static PANEL_H = 256;
    static PAD = 8;
    static LIST_W = PANEL_W - (PAD * 2);
    static ROW_H = 36;
    static HEAD_H = 14;
    static FOOT_H = 14;

    self.entries = chest_picker_entries();
    self.rows = [];

    self.backplate = ANCHOR.nine_slice(self.canvas)
        .set_align(Align.Center, Align.Middle)
        .set_sprite(spr_ui_generic_box_main)
        .set_size(PANEL_W, PANEL_H)

    ANCHOR.text(self.backplate)
        .set_lut(COMMON_LUT, CommonLutIndex.Header)
        .set_align(Align.Center, Align.TopIn)
        .set_y(7)
        .allow_line_breaks(false)
        .prevent_spillover(false)
        .set_text(local_get("misc_local/chest_picker_title"))

    //
    // An empty box reads as a broken menu, so say so instead.
    //
    if array_length(self.entries) == 0 {
        ANCHOR.text(self.backplate)
            .set_lut(COMMON_LUT, CommonLutIndex.Gray)
            .set_align(Align.Center, Align.Middle)
            .allow_line_breaks(false)
            .prevent_spillover(false)
            .set_text(local_get("misc_local/chest_picker_empty"))
        return;
    }

    self.pilot = self.new_pilot()
        .allow_vertical_wrapping()

    self.scroller = create_scroller(
        self.backplate,
        Vec2(PAD, 22),
        Vec2(LIST_W, PANEL_H - 30 - FOOT_H)
    );
    self.scroller.subscribe_to_pilot(self.pilot);

    var focus_node = undefined;
    var last_place = undefined;
    var first_row = true;

    for (var i = 0; i < array_length(self.entries); i++) {
        var entry = self.entries[i];

        //
        // A category strip whenever the place changes. Entries arrive grouped,
        // so each place is one contiguous run and this emits exactly one header
        // per group. Headers are deliberately NOT added to the pilot - drawn
        // and scrolled past, never selectable.
        //
        if first_row || entry.place != last_place {
            var header = self.scroller.new_element(HEAD_H);
            header.set_sprites_from_key("spr_ui_generic_box_category");

            ANCHOR.text(header)
                .set_lut(COMMON_LUT, CommonLutIndex.Header)
                .set_align(Align.LeftIn, Align.Middle)
                .set_x(6)
                .allow_line_breaks(false)
                .prevent_spillover(false)
                .set_text(chest_picker_fit(entry.place, LIST_W - 16))

            last_place = entry.place;
            first_row = false;
        }

        //
        // The second argument is `newline_after`, not "is this one focused" -
        // so it has to be true on every row. Without it the whole list lands in
        // a single pilot row and up/down has nothing to move between.
        //
        var element = self.scroller.new_element(ROW_H)
            .add_to_pilot(self.pilot, true);

        //
        // The pin toggle, settings-checkbox style: a strip down the left edge
        // of the row, faint until pinned. Deliberately NOT a second tap
        // listener - the row's own callback routes by mouse position instead,
        // so each row has exactly one listener and nothing rides on which of
        // two overlapping nodes the engine's newest-first hover scan pays out
        // to. (The game's own menus never nest tappables either - the spell
        // list's checkbox is visual-only, with the toggle on a separate
        // button.) The widened bbox makes the whole strip clickable, not just
        // the icon's own pixels - the same set_bbox_offset + point_in_node
        // combination the scroller uses for its range clicks.
        //
        var pin_icon = ANCHOR.sprite(element)
            .set_align(Align.LeftIn, Align.Middle)
            .set_x(4)
            .set_sprite(spr_ui_journal_magic_pin_icon)
            .set_bbox_offset(-4, -14, 5, 14)
            .set_alpha(entry.is_pinned ? 1 : 0.3)

        element.set_tap_callback(function(entry, pin_icon) {
            //
            // Route to the pin only in point control: a directional Interact
            // lands wherever the mouse was last parked, which is nowhere the
            // player is looking. Controller and keyboard pin with the key.
            //
            if ANCHOR.in_point_control()
                && ANCHOR.point_in_node(pin_icon, MOUSE_GUI_X, MOUSE_GUI_Y)
            {
                chest_picker_toggle_pin(entry.pin);
                CHEST_PICKER_LAST = entry.node;
                self.close();
                chest_picker_ensure_stats();
                ANCHOR.spawn_menu(Menu.ChestPicker);
                return;
            }

            CHEST_PICKER_LAST = entry.node;
            self.close();
            chest_picker_open(entry.node);
        }, [entry, pin_icon]);

        array_push(self.rows, { element: element, entry: entry });

        if entry.node == CHEST_PICKER_LAST {
            focus_node = element;
        }

        //
        // Top line: slot count on the right, name filling whatever is left. An
        // empty chest greys its count rather than shouting a zero.
        //
        var count_text = string(entry.used) + " / " + string(entry.size);

        ANCHOR.text(element)
            .set_lut(COMMON_LUT,
                entry.used == 0 ? CommonLutIndex.Gray : CommonLutIndex.Standard)
            .set_align(Align.RightIn, Align.TopIn)
            .set_xy(-6, 3)
            .allow_line_breaks(false)
            .prevent_spillover(false)
            .set_text(count_text)

        ANCHOR.text(element)
            .set_lut(COMMON_LUT, CommonLutIndex.Standard)
            .set_align(Align.LeftIn, Align.TopIn)
            .set_xy(18, 3)
            .allow_line_breaks(false)
            .prevent_spillover(false)
            .set_text(chest_picker_fit(
                entry.name,
                LIST_W - 36 - string_width_font(count_text)))

        //
        // Bottom line: what is inside, spaced by each icon's REAL width -
        // sprites are not all one size, and a fixed step is how the first
        // draft ended up printing icons over text. Budget leaves room for the
        // crafting crate on the right.
        //
        var ix = 18;
        var icon_budget = LIST_W - 44;
        for (var t = 0, tc = entry.size; t < tc; t++) {
            var slot = entry.node.inventory.slot(t);
            if slot.count <= 0 || slot.item == undefined {
                continue;
            }

            var icon = slot.item.prototype.icon_sprite;
            var iw = sprite_get_width(icon);
            if ix + iw > icon_budget {
                break;
            }

            ANCHOR.sprite(element)
                .set_align(Align.LeftIn, Align.BottomIn)
                .set_xy(ix, -3)
                .set_sprite(icon)

            ix += iw + 2;
        }

        //
        // A chest with use_in_crafting on is one the crafting menu pulls
        // ingredients from. Worth seeing at a glance - the game only exposes
        // it as a button buried inside each chest's own screen.
        //
        if entry.node[$ "use_in_crafting"] {
            ANCHOR.sprite(element)
                .set_align(Align.RightIn, Align.BottomIn)
                .set_xy(-6, -3)
                .set_sprites_from_key("spr_ui_inventory_storage_pull_button_open")
        }
    }

    //
    // Footer: the pin control, spelled with whatever key it is bound to.
    //
    var foot = ANCHOR.sprite(self.backplate)
        .set_align(Align.LeftIn, Align.BottomIn)
        .set_xy(PAD, -5)
        .set_sprite(spr_ui_journal_magic_pin_icon)

    ANCHOR.text(foot)
        .set_lut(COMMON_LUT, CommonLutIndex.Gray)
        .set_align(Align.RightOut, Align.Middle)
        .set_x(3)
        .allow_line_breaks(false)
        .prevent_spillover(false)
        .set_text(chest_picker_pin_key_name() + " - "
            + local_get("misc_local/chest_picker_pin_hint"))

    ANCHOR.set_active_pilot(self.pilot);

    //
    // Land on the chest you opened last. try_force_select is the pilot's own
    // mechanism for this; the pilot keeps its default first row when there is
    // nothing to return to. The scroller, though, only follows the selection
    // during directional control, so scroll to it here as well - without this
    // a mouse user opens onto the top of the list with the selection somewhere
    // below the fold, which is exactly the trip this menu exists to save. The
    // -2 mirrors the pilot padding the scroller's own follow logic uses.
    //
    if focus_node != undefined {
        self.pilot.try_force_select(focus_node);

        var view_h = PANEL_H - 30 - FOOT_H;
        var node_y = ANCHOR.get_relative_position(focus_node, self.scroller.canvas).y;
        var base = node_y + focus_node.get_height();
        if base - 2 > view_h {
            self.scroller.scroll_by_amount(base - view_h - 2);
        }
    }
}
"""

LABELS = '''chest_picker_title = "Storage"
chest_picker_empty = "No storage found."
chest_picker_generic = "Storage"
chest_picker_elsewhere = "Elsewhere"
chest_picker_pinned = "Pinned"
chest_picker_pin_hint = "Pin / Unpin"
storage_anywhere = "Storage Anywhere"
input_open_chest_picker = "Open Chest Picker"
input_pin_chest = "Pin Chest"'''


# The player-visible text this mod adds; the framework mirrors it into every
# language's table so it never renders as MISSING.
TRANSLATE = {"misc_local": LABELS}


def patches(mk, opt):
    key = opt["chest_key"].lower()
    pin = opt["pin_key"].lower()
    default = '["%s", undefined, undefined, undefined]' % key
    # west_face is free in this menu: UseToolCharged is paused out and
    # PickUpOne is only consumed by inventory-style screens.
    pin_default = '["%s", undefined, "west_face", undefined]' % pin

    return {
        MENUS: [(mk.APPEND, mk.block(MENU_ENTRY, toml=True))],
        STORAGEMENU: [(mk.APPEND, mk.block(HELPER))],
        ANCHOR: [
            (SPAWN_ANCHOR,
             SPAWN_ANCHOR
             + mk.block("case Menu.ChestPicker: return new ChestPickerMenu"
                        "(arg1, arg2, arg3, arg4, arg5, arg6);", " " * 16)),
        ],
        INPUTUTILS: [
            # Inserted after ResetControls and so before LEN - nothing shifts.
            (ENUM_ANCHOR,
             ENUM_ANCHOR + mk.block("OpenChestPicker,\nPinChest,", " " * 4)),
            # input_id_to_input_category() ends in impossible(), so an
            # uncategorised id crashes the game on lookup.
            (CATEGORY_ANCHOR,
             CATEGORY_ANCHOR + mk.block(
                 "case InputId.OpenChestPicker:\ncase InputId.PinChest:",
                 " " * 8)),
        ],
        SETTINGS: [
            # Missing bindings and missing settings both fall back to these, so
            # an existing settings.json needs no migration.
            (DEFAULTS_ANCHOR,
             DEFAULTS_ANCHOR
             + mk.block("case InputId.OpenChestPicker: return %s;\n"
                        "case InputId.PinChest: return %s;"
                        % (default, pin_default),
                        " " * 8)),
            (SETTINGS_ANCHOR,
             SETTINGS_ANCHOR + mk.block(
                 'storage_anywhere: true,\nchest_picker_pins: "",', " " * 8)),
        ],
        MENU: [
            (MENU_ANCHOR,
             mk.block('self.checkbox("storage_anywhere");', " " * 8)
             + MENU_ANCHOR),
        ],
        LOCAL: [(mk.APPEND, mk.block(LABELS, toml=True))],
        ARI: [(OPENS_ANCHOR, OPENS_ANCHOR + mk.block(OPENS_EFFECT, " " * 16))],
    }
