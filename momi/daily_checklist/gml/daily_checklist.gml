//
// Daily Checklist - hold a key for a panel of what is left today and what is
// coming up: crops that still need water, villagers you have not greeted,
// gifts you can still give, your animals' care once you keep any, then the
// next birthday and the next festival. Only villagers you have actually met
// are counted.
//
// MOMI edition of the Mistria Mods framework mod of the same name. The key is
// an MMAPI hotkey read from mod_data/daily_checklist/daily_checklist.json
// (default V; an optional gamepad button too). Do not install both editions
// at once.
//
#macro DAILY_CHECKLIST_VERSION "1.0.0"
#macro DAILY_CHECKLIST_CONFIG_VERSION 1
#macro DAILY_CHECKLIST_TEXT "mods/daily_checklist/labels/"

function __daily_checklist_runtime() {
    if (global[$ "__daily_checklist"] == undefined) {
        global.__daily_checklist = {
            registered: false, cfg: undefined, nodes: undefined, cache: undefined,
            bound: false, key_binding: undefined, pad_binding: undefined
        };
    }
    return global.__daily_checklist;
}

function daily_checklist_config() {
    var _rt = __daily_checklist_runtime();
    if (_rt.cfg != undefined) { return _rt.cfg; }
    var _src = mmapi_config_read_valid("daily_checklist", DAILY_CHECKLIST_CONFIG_VERSION);
    var _key = mmapi_config_get(_src, "key", "V");
    if (!is_string(_key) || _key == "") { _key = "V"; }
    var _pad = mmapi_config_get(_src, "gamepad", "");
    if (!is_string(_pad)) { _pad = ""; }
    var _cfg = {
        enabled: mmapi_config_bool(_src, "enabled", true),
        key: _key,
        gamepad: _pad
    };
    _cfg[$ "__friendly_names"] = {
        enabled: "Enabled",
        key: "Hold key (V, F5, HOME ...)",
        gamepad: "Hold gamepad button (GAMEPAD_RIGHT_TRIGGER ..., blank for none)"
    };
    mmapi_config_write("daily_checklist", DAILY_CHECKLIST_CONFIG_VERSION, _cfg);
    _rt.cfg = _cfg;
    return _cfg;
}

function daily_checklist_bind(_rt, _cfg) {
    if (_rt.bound) { return; }
    _rt.bound = true;
    _rt.key_binding = mmapi_hotkey_binding_from_name(_cfg.key);
    if (_rt.key_binding == undefined) {
        mmapi_log_warn("daily_checklist", "daily_checklist: '" + string(_cfg.key) + "' is not a supported key name; using V");
        _rt.key_binding = mmapi_hotkey_binding_from_name("V");
    }
    if (_cfg.gamepad != "") {
        _rt.pad_binding = mmapi_hotkey_binding_from_name(_cfg.gamepad);
        if (_rt.pad_binding == undefined) {
            mmapi_log_warn("daily_checklist", "daily_checklist: '" + string(_cfg.gamepad) + "' is not a supported gamepad button name");
        }
    }
}

function daily_checklist_held(_rt) {
    if (_rt.key_binding != undefined && mmapi_hotkey_binding_held(_rt.key_binding)) { return true; }
    if (_rt.pad_binding != undefined && mmapi_hotkey_binding_held(_rt.pad_binding)) { return true; }
    return false;
}

//
// Anchor nodes on the Vitals canvas: one text node with newlines, and a card
// sized by measure() to fit.
//
function daily_checklist_nodes() {
    var _menu = ANCHOR.get_menu(Menu.Vitals);
    if (_menu == undefined) { return undefined; }

    var _rt = __daily_checklist_runtime();
    var _existing = _rt.nodes;
    if (_existing != undefined && !_existing.card.freed && !_existing.text.freed) {
        return _existing;
    }

    var _card = ANCHOR.nine_slice(_menu.canvas)
        .set_sprite(spr_ui_tooltip_box)
        .set_align(Align.Center, Align.Middle)
        .set_alpha(0);

    var _text = ANCHOR.text(_card)
        .set_lut(COMMON_LUT, CommonLutIndex.Standard)
        .set_align(Align.Center, Align.Middle)
        .prevent_spillover(false)
        .set_alpha(0);

    _rt.nodes = { card: _card, text: _text };
    return _rt.nodes;
}

//
// How many planted crops on the farm still want watering. Crops sit on 2x2
// cells aligned to even coordinates, so stepping by 2 counts each one once.
//
function daily_checklist_dry_crops() {
    var _grid = GRIDS[LocationId.Farm];
    if (_grid == undefined) { return 0; }

    var _dry = 0;
    for (var _xx = 0; _xx < _grid.dims.x; _xx += 2) {
        for (var _yy = 0; _yy < _grid.dims.y; _yy += 2) {
            var _ni = _grid.node_index_for_cell(_xx, _yy);
            if (_grid.node_object_id[_ni] == undefined) { continue; }
            if (object_id_to_object_category(_grid.node_object_id[_ni]) != ObjectCategory.Crop) { continue; }
            // The game's own test: tilled soil, dry, no rug.
            if (can_water_node(_grid, _ni)) { _dry += 1; }
        }
    }
    return _dry;
}

//
// Build the whole panel text. Called once when the key goes down, not every
// frame: the farm sweep is too big to repeat while the key is held.
//
function daily_checklist_build() {
    var _season = CALENDAR.season();
    var _today = CALENDAR.day();

    var _to_greet = 0;
    var _to_gift = 0;
    var _next_birthday = undefined;
    var _next_birthday_day = 999;

    for (var _i = 0; _i < NpcId.LEN; _i++) {
        var _npc = NPCS[_i];
        if (!_npc.has_met() || !npc_is_unlocked(_i)) { continue; }

        if (_npc.times_spoken_today == 0) { _to_greet += 1; }
        if (_npc.gift_flag) { _to_gift += 1; }

        // birthday.day is 1-based while CALENDAR.day() is 0-based.
        if (_npc.prototype.birthday.season == _season) {
            var _bday = _npc.prototype.birthday.day - 1;
            if (_bday >= _today && _bday < _next_birthday_day) {
                _next_birthday_day = _bday;
                _next_birthday = _npc.prototype.name;
            }
        }
    }

    var _next_festival = undefined;
    var _next_festival_day = 999;
    for (var _f = 0; _f < FestivalId.LEN; _f++) {
        var _festival = FESTIVALS[_f];
        if (!_festival.prototype.implemented) { continue; }
        if (_festival.prototype.date.season != _season) { continue; }

        var _fday = _festival.prototype.date.day - 1;
        if (_fday >= _today && _fday < _next_festival_day) {
            _next_festival_day = _fday;
            _next_festival = _festival.prototype.name;
        }
    }

    var _out = local_get(DAILY_CHECKLIST_TEXT + "checklist_title") + "  "
        + string(_today + 1) + " / 28";

    _out += "\n\n" + local_get(DAILY_CHECKLIST_TEXT + "checklist_today");
    _out += "\n" + string(daily_checklist_dry_crops()) + " " + local_get(DAILY_CHECKLIST_TEXT + "checklist_dry");
    _out += "\n" + string(_to_greet) + " " + local_get(DAILY_CHECKLIST_TEXT + "checklist_greet");
    _out += "\n" + string(_to_gift) + " " + local_get(DAILY_CHECKLIST_TEXT + "checklist_gift");

    // The animals, once there are any: fed, petted, and home. "Outside" only
    // matters toward evening, so it appears from five o'clock.
    var _animals = get_all_animals();
    if (_animals.count() > 0) {
        var _not_fed = 0;
        var _not_pet = 0;
        var _outside = 0;
        for (var _a = 0; _a < _animals.count(); _a++) {
            var _animal = _animals.get(_a);
            if (!_animal.has_eaten) { _not_fed += 1; }
            if (!_animal.has_been_pat) { _not_pet += 1; }
            if (!_animal.is_home()) { _outside += 1; }
        }
        _out += "\n" + string(_not_fed) + " " + local_get(DAILY_CHECKLIST_TEXT + "checklist_unfed");
        _out += "\n" + string(_not_pet) + " " + local_get(DAILY_CHECKLIST_TEXT + "checklist_unpet");
        if (CLOCK.time >= hours(17)) {
            _out += "\n" + string(_outside) + " " + local_get(DAILY_CHECKLIST_TEXT + "checklist_outside");
        }
    }

    _out += "\n\n" + local_get(DAILY_CHECKLIST_TEXT + "checklist_ahead");
    if (_next_birthday != undefined) {
        _out += "\n" + local_get(DAILY_CHECKLIST_TEXT + "checklist_birthday") + " "
            + local_get(_next_birthday) + ", " + string(_next_birthday_day + 1);
    }
    if (_next_festival != undefined) {
        _out += "\n" + local_get(DAILY_CHECKLIST_TEXT + "checklist_festival") + " "
            + local_get(_next_festival) + ", " + string(_next_festival_day + 1);
    }

    return _out;
}

function daily_checklist_tick() {
    var _nodes = daily_checklist_nodes();
    if (_nodes == undefined) { return; }

    var _rt = __daily_checklist_runtime();
    var _cfg = daily_checklist_config();
    daily_checklist_bind(_rt, _cfg);

    if (!_cfg.enabled || non_cutscene_pause() || !instance_exists(obj_ari) || !daily_checklist_held(_rt)) {
        _rt.cache = undefined;
        _nodes.card.set_alpha(0);
        _nodes.text.set_alpha(0);
        return;
    }

    if (_rt.cache == undefined) {
        _rt.cache = daily_checklist_build();
        _nodes.text.set_text(_rt.cache);

        var _size = _nodes.text.measure();
        _nodes.card.set_size(_size.x + 20, _size.y + 16);
    }

    _nodes.card.set_alpha(1);
    _nodes.text.set_alpha(1);
}

//
// English resolves natively through localization/l10n.meta.toml; a language
// with no entry for a key gets the English source instead of MISSING.
//
function daily_checklist_local_missing(_value, _ctx) {
    if (_value != undefined || !is_struct(_ctx)) { return undefined; }
    var _key = _ctx[$ "key"];
    var _n = string_length(DAILY_CHECKLIST_TEXT);
    if (!is_string(_key) || string_copy(_key, 1, _n) != DAILY_CHECKLIST_TEXT) { return undefined; }
    var _text = undefined;
    try {
        var _table = fiddle_get("mods/daily_checklist/labels");
        _text = _table[$ string_delete(_key, 1, _n)];
    } catch (_e) {}
    return is_string(_text) ? _text : undefined;
}

function daily_checklist_register() {
    var _rt = __daily_checklist_runtime();
    if (_rt.registered) { return; }
    _rt.registered = true;
    mmapi_filter("local.missing", daily_checklist_local_missing);
    mmapi_register(daily_checklist_tick);
}

mmapi_mod_declare("daily_checklist", DAILY_CHECKLIST_VERSION);
daily_checklist_register();
