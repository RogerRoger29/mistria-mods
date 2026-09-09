//
// Storage Anywhere - press a key for a scrollable list of every chest in the
// world, grouped by location: name, how full it is, a preview of what is
// inside, and whether it feeds crafting. Pick one and the game's own storage
// screen opens on it. Pin favourites so they always sit at the top.
//
// The mod adds no registry of its own. STORAGE_NODES is already a global List
// holding every node with an inventory; every location's grid is built at
// startup, so that list spans the whole map. This only shows it to you, after
// checking each entry is still real.
//
// MOMI edition of the Mistria Mods framework mod of the same name. Menu ids
// are minted from ui/menus/standard_menus.toml, which MOMI merges, so
// Menu.ChestPicker is real; the menu class lives here and is opened by
// pushing it onto the Anchor's open menus the way spawn_menu does. The keys
// are MMAPI hotkeys and the pins are kept in
// mod_data/storage_anywhere/storage_anywhere.json. Do not install both
// editions at once.
//
#macro STORAGE_ANYWHERE_VERSION "1.0.0"
#macro STORAGE_ANYWHERE_CONFIG_VERSION 1
#macro STORAGE_ANYWHERE_TEXT "mods/storage_anywhere/labels/"

function __storage_anywhere_runtime() {
    if (global[$ "__storage_anywhere"] == undefined) {
        global.__storage_anywhere = {
            registered: false, cfg: undefined, bound: false,
            last: undefined, item_map: undefined,
            pin_binding: undefined, pin_pad_binding: undefined, pin_was_down: false
        };
    }
    return global.__storage_anywhere;
}

function storage_anywhere_config() {
    var _rt = __storage_anywhere_runtime();
    if (_rt.cfg != undefined) { return _rt.cfg; }
    var _src = mmapi_config_read_valid("storage_anywhere", STORAGE_ANYWHERE_CONFIG_VERSION);
    var _open_key = mmapi_config_get(_src, "open_key", "B");
    if (!is_string(_open_key) || _open_key == "") { _open_key = "B"; }
    var _open_pad = mmapi_config_get(_src, "open_gamepad", "");
    if (!is_string(_open_pad)) { _open_pad = ""; }
    var _pin_key = mmapi_config_get(_src, "pin_key", "P");
    if (!is_string(_pin_key) || _pin_key == "") { _pin_key = "P"; }
    var _pin_pad = mmapi_config_get(_src, "pin_gamepad", "GAMEPAD_X");
    if (!is_string(_pin_pad)) { _pin_pad = ""; }
    var _pins = mmapi_config_get(_src, "pins", "");
    if (!is_string(_pins)) { _pins = ""; }
    var _cfg = {
        enabled: mmapi_config_bool(_src, "enabled", true),
        open_key: _open_key,
        open_gamepad: _open_pad,
        pin_key: _pin_key,
        pin_gamepad: _pin_pad,
        pins: _pins
    };
    _cfg[$ "__friendly_names"] = {
        enabled: "Enabled",
        open_key: "Open / close key (B, F5, HOME ...)",
        open_gamepad: "Open / close gamepad button (blank for none)",
        pin_key: "Pin / unpin key",
        pin_gamepad: "Pin / unpin gamepad button (blank for none)",
        pins: "Pinned chests (managed in game)"
    };
    mmapi_config_write("storage_anywhere", STORAGE_ANYWHERE_CONFIG_VERSION, _cfg);
    _rt.cfg = _cfg;
    return _cfg;
}

//
// object id -> the item that places it, built once and kept. Chest prototypes
// carry no name of their own; the name belongs to the furniture item, which
// points the other way (item.prototype.object), so the map has to be inverted.
//
function storage_anywhere_item_for_object(_object_id) {
    var _rt = __storage_anywhere_runtime();
    if (_rt.item_map == undefined) {
        _rt.item_map = {};
        for (var _i = 0; _i < ItemId.LEN; _i++) {
            var _proto = ITEM_PROTOTYPES[_i];
            if (_proto == undefined) { continue; }
            var _obj = _proto[$ "object"];
            if (_obj == undefined) { continue; }
            // Several recolours place the same object; first one wins.
            var _k = string(_obj);
            if (!struct_exists(_rt.item_map, _k)) {
                _rt.item_map[$ _k] = _i;
            }
        }
    }
    if (_object_id == undefined) { return undefined; }
    var _key = string(_object_id);
    return struct_exists(_rt.item_map, _key) ? _rt.item_map[$ _key] : undefined;
}

//
// spawn_menu() counts every open into GAME_STATS.menu_opens, keyed by menu
// name, and `+= 1` on a key that was never created is a hard crash. The keys
// are created on a new game or a save migration only, so an existing save
// never learns about a menu added afterwards. Hence: create it, once.
//
function storage_anywhere_ensure_stats() {
    if (GAME_STATS == undefined) { return; }
    var _key = menu_to_string(Menu.ChestPicker);
    if (GAME_STATS.menu_opens[$ _key] == undefined) {
        GAME_STATS.menu_opens[$ _key] = 0;
    }
}

//
// Open the picker the way Anchor.spawn_menu() would, minus its closed switch:
// the stats bump, the construction, the push onto the open menus, the event.
//
function storage_anywhere_spawn() {
    var _rt = __storage_anywhere_runtime();
    storage_anywhere_ensure_stats();
    if (GAME_STATS != undefined) {
        GAME_STATS.menu_opens[$ menu_to_string(Menu.ChestPicker)] += 1;
    }
    _rt.pin_was_down = true;
    var _menu = new storage_anywhere_menu();
    ANCHOR.open_menus.push(_menu);
    try {
        mmapi_emit("ui.menu_opened", { menu: _menu, kind: Menu.ChestPicker });
    } catch (_e) {}
    return _menu;
}

//
// Pinned chests: identity is location + cell rather than a node reference,
// which survives restarts; a chest that gets moved or broken simply stops
// matching until it is pinned again. Static locations key by LocationId;
// building interiors have no id and key by their name.
//
function storage_anywhere_pin_id(_place, _node) {
    var _where = _place.loc != undefined
        ? "loc" + string(_place.loc)
        : "dyn" + string_replace_all(string_replace_all(string(_place.label), ";", "_"), "@", "_");
    return _where + "@" + string(_node.top_left_x) + "," + string(_node.top_left_y);
}

function storage_anywhere_pins() {
    var _raw = storage_anywhere_config().pins;
    if (!is_string(_raw) || _raw == "") { return []; }
    var _parts = string_split(_raw, ";");
    // The shipped engine returns [] when the delimiter never appears.
    if (array_length(_parts) == 0) { _parts = [_raw]; }
    return _parts;
}

function storage_anywhere_toggle_pin(_pin_id) {
    var _pins = storage_anywhere_pins();
    var _out = "";
    var _removed = false;
    for (var _i = 0; _i < array_length(_pins); _i++) {
        if (_pins[_i] == _pin_id) { _removed = true; continue; }
        if (_pins[_i] == "") { continue; }
        _out += (_out == "" ? "" : ";") + _pins[_i];
    }
    if (!_removed) {
        _out += (_out == "" ? "" : ";") + _pin_id;
    }
    var _cfg = storage_anywhere_config();
    _cfg.pins = _out;
    mmapi_config_write("storage_anywhere", STORAGE_ANYWHERE_CONFIG_VERSION, _cfg);
}

function storage_anywhere_pin_key_name() {
    return string_upper(storage_anywhere_config().pin_key);
}

//
// "small_coop" -> "Small Coop". Many locations define no display name at all,
// every coop, barn and greenhouse interior among them.
//
function storage_anywhere_prettify(_key) {
    var _out = "";
    var _cap = true;
    for (var _i = 1; _i <= string_length(_key); _i++) {
        var _ch = string_char_at(_key, _i);
        if (_ch == "_") { _out += " "; _cap = true; continue; }
        _out += _cap ? string_upper(_ch) : _ch;
        _cap = false;
    }
    return _out;
}

//
// A location's display name. LOCATIONS[i].name is a localization key, and it
// is absent on some locations, the farm among them.
//
function storage_anywhere_place_name(_loc) {
    if (_loc == undefined) {
        return local_get(STORAGE_ANYWHERE_TEXT + "chest_picker_elsewhere");
    }
    if (_loc == LocationId.Farm) {
        return ARI.farm_name;
    }
    var _location = LOCATIONS[_loc];
    if (_location != undefined && _location[$ "name"] != undefined) {
        return local_get(_location.name);
    }
    return storage_anywhere_prettify(location_id_to_string(_loc));
}

//
// Where is this chest, really? A grid is only current if it IS the grid the
// world holds for some location, or a registered dynamic grid (a building
// interior). Stale nodes from the nightly resets fail every identity test.
//
function storage_anywhere_where(_node) {
    var _grid = _node[$ "parent_grid"];
    var _guard = 0;

    while (_grid != undefined && _guard < 8) {
        _guard += 1;

        for (var _l = 0; _l < LocationId.LEN; _l++) {
            if (GRIDS[_l] == _grid) {
                return { live: true, loc: _l, label: storage_anywhere_place_name(_l) };
            }
        }

        if (_grid[$ "dyn_index"] != undefined
            && _grid.dyn_index < DYNAMIC_GRIDS.count()
            && DYNAMIC_GRIDS.get(_grid.dyn_index) == _grid)
        {
            var _buildings = get_buildings();
            for (var _b = 0, _bc = _buildings.count(); _b < _bc; _b++) {
                var _building = _buildings.get(_b);
                if (_building.dyn_index == _grid.dyn_index && _building[$ "name"] != undefined) {
                    return { live: true, loc: undefined, label: string(_building.name) };
                }
            }
        }

        var _pn = _grid[$ "parent_node"];
        _grid = _pn == undefined ? undefined : _pn[$ "parent_grid"];
    }

    return { live: false, loc: undefined, label: "" };
}

function storage_anywhere_name_of(_node) {
    var _item = storage_anywhere_item_for_object(_node.object_id);
    if (_item != undefined) {
        return local_get(ITEM_PROTOTYPES[_item].name_key);
    }
    // Fixed containers are placed by the map, not by an item.
    return local_get(STORAGE_ANYWHERE_TEXT + "chest_picker_generic");
}

//
// Clip a string to a pixel width, with an ellipsis. Not set_max_width(), which
// turns line breaking back on.
//
function storage_anywhere_fit(_text, _max_px) {
    if (string_width_font(_text) <= _max_px) { return _text; }
    var _out = _text;
    while (string_length(_out) > 1 && string_width_font(_out + "..") > _max_px) {
        _out = string_copy(_out, 1, string_length(_out) - 1);
    }
    return _out + "..";
}

// Is this node still on its own grid?
function storage_anywhere_is_live(_node) {
    var _grid = _node[$ "parent_grid"];
    if (_grid == undefined) { return false; }
    var _ni = _grid.try_node_index_for_cell(_node.top_left_x, _node.top_left_y);
    if (_ni == undefined) { return false; }
    return _grid.node_parent[_ni] == _node;
}

//
// Every real chest: pinned favourites first, then your current location's
// groups, then everywhere else; within a place, fuller chests first.
//
function storage_anywhere_entries() {
    var _rt = __storage_anywhere_runtime();
    var _here = CURRENT_LOCATION_ID;
    var _buckets = [];
    var _pinned = [];
    var _seen = {};
    var _pins = storage_anywhere_pins();
    var _pinned_label = local_get(STORAGE_ANYWHERE_TEXT + "chest_picker_pinned");

    for (var _i = 0, _c = STORAGE_NODES.count(); _i < _c; _i++) {
        var _node = STORAGE_NODES.get(_i);
        if (_node == undefined || _node[$ "inventory"] == undefined) { continue; }
        if (_node.prototype[$ "interaction_chest"] == undefined) { continue; }
        if (!storage_anywhere_is_live(_node)) { continue; }

        var _place = storage_anywhere_where(_node);
        if (!_place.live) { continue; }

        // One chest per cell.
        var _key = _place.label + ":" + string(_node.top_left_x) + ":" + string(_node.top_left_y);
        if (struct_exists(_seen, _key)) { continue; }
        _seen[$ _key] = true;

        var _inv = _node.inventory;
        var _used = 0;
        for (var _s = 0, _sc = _inv.size(); _s < _sc; _s++) {
            if (_inv.slot(_s).count > 0) { _used += 1; }
        }

        var _pin_id = storage_anywhere_pin_id(_place, _node);
        var _pin_index = -1;
        for (var _p = 0; _p < array_length(_pins); _p++) {
            if (_pins[_p] == _pin_id) { _pin_index = _p; break; }
        }

        var _entry = {
            node: _node,
            used: _used,
            size: _inv.size(),
            name: storage_anywhere_name_of(_node),
            place: _place.label,
            pin: _pin_id,
            is_pinned: _pin_index >= 0
        };

        if (_pin_index >= 0) {
            _entry.place = _pinned_label;
            _entry.name = _entry.name + " - " + _place.label;
            _entry.order = _pin_index;
            array_push(_pinned, _entry);
            continue;
        }

        var _bucket = undefined;
        for (var _b = 0; _b < array_length(_buckets); _b++) {
            if (_buckets[_b].label == _place.label) { _bucket = _buckets[_b]; }
        }
        if (_bucket == undefined) {
            _bucket = {
                label: _place.label,
                here: _place.loc != undefined && _place.loc == _here,
                entries: []
            };
            array_push(_buckets, _bucket);
        }
        array_push(_bucket.entries, _entry);
    }

    // Fuller chests first within each place.
    for (var _b = 0; _b < array_length(_buckets); _b++) {
        var _list = _buckets[_b].entries;
        for (var _a = 0; _a < array_length(_list); _a++) {
            var _best = _a;
            for (var _j = _a + 1; _j < array_length(_list); _j++) {
                if (_list[_j].used > _list[_best].used) { _best = _j; }
            }
            if (_best != _a) {
                var _tmp = _list[_a];
                _list[_a] = _list[_best];
                _list[_best] = _tmp;
            }
        }
    }

    // Pinned chests keep the order they were pinned in.
    for (var _a = 0; _a < array_length(_pinned); _a++) {
        var _best = _a;
        for (var _j = _a + 1; _j < array_length(_pinned); _j++) {
            if (_pinned[_j].order < _pinned[_best].order) { _best = _j; }
        }
        if (_best != _a) {
            var _tmp = _pinned[_a];
            _pinned[_a] = _pinned[_best];
            _pinned[_best] = _tmp;
        }
    }

    var _out = [];
    for (var _p = 0; _p < array_length(_pinned); _p++) {
        array_push(_out, _pinned[_p]);
    }
    for (var _pass = 0; _pass < 2; _pass++) {
        for (var _b = 0; _b < array_length(_buckets); _b++) {
            if (_buckets[_b].here == (_pass == 0)) {
                for (var _e = 0; _e < array_length(_buckets[_b].entries); _e++) {
                    array_push(_out, _buckets[_b].entries[_e]);
                }
            }
        }
    }
    return _out;
}

//
// Open one chest on the game's own storage screen. Mirrors the interaction in
// Interact.gml, and skips the lid animation for a chest in another room:
// `renderer` only exists for the location you are standing in.
//
function storage_anywhere_open(_node) {
    var _chest = _node.prototype.interaction_chest;

    // A chest visited earlier holds a dead renderer; touching any variable on
    // it is the "expired instance" crash. Normalize it so every guard works.
    if (_node[$ "renderer"] != undefined && !instance_exists(_node.renderer)) {
        _node.renderer = undefined;
    }

    if (instance_exists(obj_ari)) {
        obj_ari.set_idle_simple();
    }

    var _menu = ANCHOR.spawn_menu(Menu.Storage, _node)
        .set_inventories(_node.inventory, ARI.inventory)
        .with_right_help_button()
        .with_right_banner();

    // A turn-in box is a quest dropbox, not storage.
    if (_node.object_id == ObjectId.TurnInBox) {
        _menu.with_alt_stack_behavior();

        var _recipe_for_box = undefined;
        if (_node[$ "building_box"] != undefined) {
            _recipe_for_box = BLUEPRINT_PROTOTYPES[_node.blueprint_id].turn_in_box_recipe;
        } else {
            var _q = QUEST_LOG.active.get(_node.quest_id);
            var _data = _q.quest.tasks.get(_q.current_stage).requirements[Requirement.SuppliedItems][0].items;
            _recipe_for_box = {};
            for (var _i = 0; _i < array_length(_data); _i++) {
                if (_data[_i] != 0) {
                    _recipe_for_box[$ _i] = _data[_i];
                }
            }
        }
        _menu.with_recipe(_recipe_for_box);
    } else if (!_chest.shipping_bin) {
        _menu.with_left_banner();
    }

    _menu.with_chest_node(_node);

    if (instance_exists(obj_ari)) {
        TANGO.play(_chest.open_sfx, obj_ari.x, obj_ari.y);
    }

    if (_node[$ "renderer"] != undefined) {
        _node.renderer.sprite_index = _chest.opening_sprite;
        _node.renderer.image_speed = 1;
        _node.renderer.image_index = 0.0;
    }

    _menu.build();
}

//
// The pin key, as a press edge on a held binding: the hotkey registry polls
// once a frame, and this menu pauses the game, so a level check with our own
// edge is the reliable form.
//
function storage_anywhere_pin_pressed() {
    var _rt = __storage_anywhere_runtime();
    var _down = false;
    if (_rt.pin_binding != undefined && mmapi_hotkey_binding_held(_rt.pin_binding)) { _down = true; }
    if (_rt.pin_pad_binding != undefined && mmapi_hotkey_binding_held(_rt.pin_pad_binding)) { _down = true; }
    var _pressed = _down && !_rt.pin_was_down;
    _rt.pin_was_down = _down;
    return _pressed;
}

//
// The picker itself. Built on the engine's scroller and pilot, the same pair
// the settings pages use, so keyboard, controller and mouse all navigate it.
//
function storage_anywhere_menu() : AnchorMenu(Menu.ChestPicker) constructor {
    //
    // The pin key works on the row under the cursor when there is one, and
    // falls back to the pilot's row when the mouse is parked elsewhere.
    //
    function on_think() {
        if (!storage_anywhere_pin_pressed()) { return; }

        var _target = undefined;
        for (var _i = 0; _i < array_length(self.rows); _i++) {
            if (self.rows[_i].element.is_hovered()) {
                _target = self.rows[_i];
                break;
            }
        }
        if (_target == undefined && self[$ "pilot"] != undefined) {
            var _sel = self.pilot.get();
            for (var _i = 0; _i < array_length(self.rows); _i++) {
                if (self.rows[_i].element == _sel) {
                    _target = self.rows[_i];
                    break;
                }
            }
        }
        if (_target == undefined) { return; }

        storage_anywhere_toggle_pin(_target.entry.pin);

        // Rebuild so the row changes group right away, focus back on the same chest.
        __storage_anywhere_runtime().last = _target.entry.node;
        self.close();
        storage_anywhere_spawn();
    }

    // Rows are two real lines: a text line plus a 16px icon line.
    static PANEL_W = 300;
    static PANEL_H = 256;
    static PAD = 8;
    static LIST_W = PANEL_W - (PAD * 2);
    static ROW_H = 36;
    static HEAD_H = 14;
    static FOOT_H = 14;

    self.entries = storage_anywhere_entries();
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
        .set_text(local_get(STORAGE_ANYWHERE_TEXT + "chest_picker_title"))

    // An empty box reads as a broken menu, so say so instead.
    if (array_length(self.entries) == 0) {
        ANCHOR.text(self.backplate)
            .set_lut(COMMON_LUT, CommonLutIndex.Gray)
            .set_align(Align.Center, Align.Middle)
            .allow_line_breaks(false)
            .prevent_spillover(false)
            .set_text(local_get(STORAGE_ANYWHERE_TEXT + "chest_picker_empty"))
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

    var _focus_node = undefined;
    var _last_place = undefined;
    var _first_row = true;
    var _last_opened = __storage_anywhere_runtime().last;

    for (var _i = 0; _i < array_length(self.entries); _i++) {
        var _entry = self.entries[_i];

        // A category strip whenever the place changes; never selectable.
        if (_first_row || _entry.place != _last_place) {
            var _header = self.scroller.new_element(HEAD_H);
            _header.set_sprites_from_key("spr_ui_generic_box_category");

            ANCHOR.text(_header)
                .set_lut(COMMON_LUT, CommonLutIndex.Header)
                .set_align(Align.LeftIn, Align.Middle)
                .set_x(6)
                .allow_line_breaks(false)
                .prevent_spillover(false)
                .set_text(storage_anywhere_fit(_entry.place, LIST_W - 16))

            _last_place = _entry.place;
            _first_row = false;
        }

        // The second argument is newline_after, so it has to be true on every row.
        var _element = self.scroller.new_element(ROW_H)
            .add_to_pilot(self.pilot, true);

        // The pin toggle: a strip down the left edge of the row, faint until
        // pinned. The row's own callback routes by mouse position, so each
        // row has exactly one listener.
        var _pin_icon = ANCHOR.sprite(_element)
            .set_align(Align.LeftIn, Align.Middle)
            .set_x(4)
            .set_sprite(spr_ui_journal_magic_pin_icon)
            .set_bbox_offset(-4, -14, 5, 14)
            .set_alpha(_entry.is_pinned ? 1 : 0.3)

        _element.set_tap_callback(function(entry, pin_icon) {
            // Route to the pin only in point control; controller and keyboard
            // pin with the key.
            if (ANCHOR.in_point_control()
                && ANCHOR.point_in_node(pin_icon, MOUSE_GUI_X, MOUSE_GUI_Y))
            {
                storage_anywhere_toggle_pin(entry.pin);
                __storage_anywhere_runtime().last = entry.node;
                self.close();
                storage_anywhere_spawn();
                return;
            }

            __storage_anywhere_runtime().last = entry.node;
            self.close();
            storage_anywhere_open(entry.node);
        }, [_entry, _pin_icon]);

        array_push(self.rows, { element: _element, entry: _entry });

        if (_entry.node == _last_opened) {
            _focus_node = _element;
        }

        // Top line: slot count on the right, name filling whatever is left.
        var _count_text = string(_entry.used) + " / " + string(_entry.size);

        ANCHOR.text(_element)
            .set_lut(COMMON_LUT,
                _entry.used == 0 ? CommonLutIndex.Gray : CommonLutIndex.Standard)
            .set_align(Align.RightIn, Align.TopIn)
            .set_xy(-6, 3)
            .allow_line_breaks(false)
            .prevent_spillover(false)
            .set_text(_count_text)

        ANCHOR.text(_element)
            .set_lut(COMMON_LUT, CommonLutIndex.Standard)
            .set_align(Align.LeftIn, Align.TopIn)
            .set_xy(18, 3)
            .allow_line_breaks(false)
            .prevent_spillover(false)
            .set_text(storage_anywhere_fit(
                _entry.name,
                LIST_W - 36 - string_width_font(_count_text)))

        // Bottom line: what is inside, spaced by each icon's real width.
        var _ix = 18;
        var _icon_budget = LIST_W - 44;
        for (var _t = 0, _tc = _entry.size; _t < _tc; _t++) {
            var _slot = _entry.node.inventory.slot(_t);
            if (_slot.count <= 0 || _slot.item == undefined) { continue; }

            var _icon = _slot.item.prototype.icon_sprite;
            var _iw = sprite_get_width(_icon);
            if (_ix + _iw > _icon_budget) { break; }

            ANCHOR.sprite(_element)
                .set_align(Align.LeftIn, Align.BottomIn)
                .set_xy(_ix, -3)
                .set_sprite(_icon)

            _ix += _iw + 2;
        }

        // A chest the crafting menu pulls ingredients from.
        if (_entry.node[$ "use_in_crafting"]) {
            ANCHOR.sprite(_element)
                .set_align(Align.RightIn, Align.BottomIn)
                .set_xy(-6, -3)
                .set_sprites_from_key("spr_ui_inventory_storage_pull_button_open")
        }
    }

    // Footer: the pin control, spelled with whatever key it is bound to.
    var _foot = ANCHOR.sprite(self.backplate)
        .set_align(Align.LeftIn, Align.BottomIn)
        .set_xy(PAD, -5)
        .set_sprite(spr_ui_journal_magic_pin_icon)

    ANCHOR.text(_foot)
        .set_lut(COMMON_LUT, CommonLutIndex.Gray)
        .set_align(Align.RightOut, Align.Middle)
        .set_x(3)
        .allow_line_breaks(false)
        .prevent_spillover(false)
        .set_text(storage_anywhere_pin_key_name() + " - "
            + local_get(STORAGE_ANYWHERE_TEXT + "chest_picker_pin_hint"))

    ANCHOR.set_active_pilot(self.pilot);

    // Land on the chest you opened last, and scroll to it: the scroller only
    // follows the selection during directional control.
    if (_focus_node != undefined) {
        self.pilot.try_force_select(_focus_node);

        var _view_h = PANEL_H - 30 - FOOT_H;
        var _node_y = ANCHOR.get_relative_position(_focus_node, self.scroller.canvas).y;
        var _base = _node_y + _focus_node.get_height();
        if (_base - 2 > _view_h) {
            self.scroller.scroll_by_amount(_base - _view_h - 2);
        }
    }
}

//
// The open key: a toggle. Closes the picker when it is up; otherwise opens it
// when the game is not paused, which also rules out dialogue and cutscenes.
//
function storage_anywhere_on_open_key() {
    var _cfg = storage_anywhere_config();
    if (!_cfg.enabled) { return; }
    var _open = ANCHOR.get_menu(Menu.ChestPicker);
    if (_open != undefined) {
        _open.close();
        return;
    }
    if (game_paused() || !instance_exists(obj_ari)) { return; }
    storage_anywhere_spawn();
}

//
// Bindings resolve once, after the first frame, when the config is readable.
//
function storage_anywhere_tick() {
    var _rt = __storage_anywhere_runtime();
    if (_rt.bound) { return; }
    _rt.bound = true;
    var _cfg = storage_anywhere_config();

    var _open = mmapi_hotkey_binding_from_name(_cfg.open_key);
    if (_open == undefined) {
        mmapi_log_warn("storage_anywhere", "storage_anywhere: '" + string(_cfg.open_key) + "' is not a supported key name; using B");
        _open = mmapi_hotkey_binding_from_name("B");
    }
    if (_open != undefined) {
        mmapi_hotkey_register_binding(_open, storage_anywhere_on_open_key);
    }
    if (_cfg.open_gamepad != "") {
        var _open_pad = mmapi_hotkey_binding_from_name(_cfg.open_gamepad);
        if (_open_pad != undefined) {
            mmapi_hotkey_register_binding(_open_pad, storage_anywhere_on_open_key);
        } else {
            mmapi_log_warn("storage_anywhere", "storage_anywhere: '" + string(_cfg.open_gamepad) + "' is not a supported gamepad button name");
        }
    }

    _rt.pin_binding = mmapi_hotkey_binding_from_name(_cfg.pin_key);
    if (_rt.pin_binding == undefined) {
        mmapi_log_warn("storage_anywhere", "storage_anywhere: '" + string(_cfg.pin_key) + "' is not a supported key name; using P");
        _rt.pin_binding = mmapi_hotkey_binding_from_name("P");
    }
    if (_cfg.pin_gamepad != "") {
        _rt.pin_pad_binding = mmapi_hotkey_binding_from_name(_cfg.pin_gamepad);
    }
}

//
// English resolves natively through localization/l10n.meta.toml; a language
// with no entry for a key gets the English source instead of MISSING.
//
function storage_anywhere_local_missing(_value, _ctx) {
    if (_value != undefined || !is_struct(_ctx)) { return undefined; }
    var _key = _ctx[$ "key"];
    var _n = string_length(STORAGE_ANYWHERE_TEXT);
    if (!is_string(_key) || string_copy(_key, 1, _n) != STORAGE_ANYWHERE_TEXT) { return undefined; }
    var _text = undefined;
    try {
        var _table = fiddle_get("mods/storage_anywhere/labels");
        _text = _table[$ string_delete(_key, 1, _n)];
    } catch (_e) {}
    return is_string(_text) ? _text : undefined;
}

function storage_anywhere_register() {
    var _rt = __storage_anywhere_runtime();
    if (_rt.registered) { return; }
    _rt.registered = true;
    mmapi_filter("local.missing", storage_anywhere_local_missing);
    mmapi_register(storage_anywhere_tick);
}

mmapi_mod_declare("storage_anywhere", STORAGE_ANYWHERE_VERSION);
storage_anywhere_register();
