//
// Ladder Progress - a HUD readout of how close the floor is to revealing its
// ladder down, as a number like 7 / 14.
//
// The ladder does not exist until you have cleared a random 25 to 75 percent
// of the floor, rerolled every floor, so without a readout there is no way to
// tell an unlucky floor from one you have barely started. It counts what the
// game counts: small rocks, ore, seams, barrels, crates and monsters.
//
// MOMI edition of the Mistria Mods framework mod of the same name. Options
// live in mod_data/ladder_progress/ladder_progress.json. Do not install both
// editions at once.
//
#macro LADDER_PROGRESS_VERSION "1.0.0"
#macro LADDER_PROGRESS_CONFIG_VERSION 1

function __ladder_progress_runtime() {
    if (global[$ "__ladder_progress"] == undefined) {
        global.__ladder_progress = { registered: false, cfg: undefined, nodes: undefined };
    }
    return global.__ladder_progress;
}

function ladder_progress_config() {
    var _rt = __ladder_progress_runtime();
    if (_rt.cfg != undefined) { return _rt.cfg; }
    var _src = mmapi_config_read_valid("ladder_progress", LADDER_PROGRESS_CONFIG_VERSION);
    var _cfg = {
        enabled: mmapi_config_bool(_src, "enabled", true),
        x: mmapi_config_number(_src, "x", 3, 0, 640),
        y: mmapi_config_number(_src, "y", 46, 0, 360)
    };
    _cfg[$ "__friendly_names"] = {
        enabled: "Enabled",
        x: "Readout x (GUI pixels)",
        y: "Readout y (GUI pixels)"
    };
    mmapi_config_write("ladder_progress", LADDER_PROGRESS_CONFIG_VERSION, _cfg);
    _rt.cfg = _cfg;
    return _cfg;
}

//
// Styled as a HUD element: the same nine-slice the info HUD stacks for
// essence and gold, icon plus number, no words.
//
function ladder_progress_nodes() {
    var _menu = ANCHOR.get_menu(Menu.Vitals);
    if (_menu == undefined) { return undefined; }

    var _rt = __ladder_progress_runtime();
    var _existing = _rt.nodes;
    if (_existing != undefined && !_existing.card.freed && !_existing.text.freed) {
        return _existing;
    }

    var _card = ANCHOR.nine_slice(_menu.canvas)
        .set_sprite(spr_ui_hud_info_backplate_middle)
        .set_align(Align.LeftIn, Align.TopIn)
        .set_alpha(0);

    var _icon = ANCHOR.sprite(_card)
        .set_sprite(spr_ui_skill_icon_mining)
        .set_align(Align.LeftIn, Align.Middle)
        .set_x(4)
        .set_alpha(0);

    var _text = ANCHOR.text(_icon)
        .set_lut(COMMON_LUT, CommonLutIndex.Standard)
        .set_align(Align.RightOut, Align.Middle)
        .set_x(3)
        .allow_line_breaks(false)
        .prevent_spillover(false)
        .set_alpha(0);

    _rt.nodes = { card: _card, icon: _icon, text: _text };
    return _rt.nodes;
}

//
// The readout text, or undefined when there is nothing worth showing.
//
function ladder_progress_text(_cfg) {
    if (!_cfg.enabled) { return undefined; }
    if (!is_dungeon_room(room()) || is_special_dungeon_room(room())) { return undefined; }
    if (DUNGEON_RUNNER == undefined) { return undefined; }
    if (instance_exists(obj_dungeon_ladder_down)) { return undefined; }

    var _needed = DUNGEON_RUNNER.ladder_score_needed;
    if (_needed == undefined || _needed <= 0) { return undefined; }

    var _score = min(DUNGEON_RUNNER.ladder_score, _needed);
    return string(_score) + " / " + string(_needed);
}

function ladder_progress_tick() {
    var _nodes = ladder_progress_nodes();
    if (_nodes == undefined) { return; }

    var _cfg = ladder_progress_config();
    var _label = ladder_progress_text(_cfg);
    if (_label == undefined) {
        _nodes.card.set_alpha(0);
        _nodes.icon.set_alpha(0);
        _nodes.text.set_alpha(0);
        return;
    }

    _nodes.text.set_text(_label);

    // 4px lead-in, 8px icon, 3px gap, text, 5px tail; at least 16 tall so the
    // nine-slice's 7x7 corners render cleanly.
    var _size = _nodes.text.measure();
    _nodes.card.set_size(_size.x + 20, max(_size.y + 6, 16));
    _nodes.card.set_xy(_cfg.x, _cfg.y);

    _nodes.card.set_alpha(1);
    _nodes.icon.set_alpha(1);
    _nodes.text.set_alpha(1);
}

function ladder_progress_register() {
    var _rt = __ladder_progress_runtime();
    if (_rt.registered) { return; }
    _rt.registered = true;
    mmapi_register(ladder_progress_tick);
}

mmapi_mod_declare("ladder_progress", LADDER_PROGRESS_VERSION);
ladder_progress_register();
