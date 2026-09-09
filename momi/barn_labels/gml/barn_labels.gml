//
// Barn Labels - point at one of your animals and a card above it shows its
// name, its hearts out of ten, and whether it has been fed and petted today,
// the three things the nightly check judges it on. On a controller the card
// follows the nearest animal within reach of Ari. Words rather than coloured
// ticks, so it reads with no colour vision.
//
// MOMI edition of the Mistria Mods framework mod of the same name. The card
// is Anchor nodes on the vitals HUD, updated every frame from mmapi_register.
// Options live in mod_data/barn_labels/barn_labels.json. Do not install both
// editions at once.
//
#macro BARN_LABELS_VERSION "1.0.0"
#macro BARN_LABELS_CONFIG_VERSION 1
#macro BARN_LABELS_TEXT "mods/barn_labels/labels/"

function __barn_labels_runtime() {
    if (global[$ "__barn_labels"] == undefined) {
        global.__barn_labels = { registered: false, cfg: undefined, nodes: undefined };
    }
    return global.__barn_labels;
}

function barn_labels_config() {
    var _rt = __barn_labels_runtime();
    if (_rt.cfg != undefined) { return _rt.cfg; }
    var _src = mmapi_config_read_valid("barn_labels", BARN_LABELS_CONFIG_VERSION);
    var _cfg = {
        enabled: mmapi_config_bool(_src, "enabled", true),
        controller_reach_px: mmapi_config_number(_src, "controller_reach_px", 32, 8, 200)
    };
    _cfg[$ "__friendly_names"] = {
        enabled: "Enabled",
        controller_reach_px: "Controller reach (pixels, 8 per tile)"
    };
    mmapi_config_write("barn_labels", BARN_LABELS_CONFIG_VERSION, _cfg);
    _rt.cfg = _cfg;
    return _cfg;
}

//
// The card: a nine-slice tooltip box and a text node on the vitals HUD's
// canvas. Raw world-space text inherits whatever LUT the last shader pass
// left bound; Anchor owns that state.
//
function barn_labels_nodes() {
    var _menu = ANCHOR.get_menu(Menu.Vitals);
    if (_menu == undefined) { return undefined; }

    var _rt = __barn_labels_runtime();
    var _existing = _rt.nodes;
    if (_existing != undefined && !_existing.card.freed && !_existing.text.freed) {
        return _existing;
    }

    var _card = ANCHOR.nine_slice(_menu.canvas)
        .set_sprite(spr_ui_tooltip_box)
        .set_align(Align.LeftIn, Align.TopIn)
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
// The animal to describe: the nearest to the pointer with a mouse, if the
// pointer is on it; on a controller, the nearest one within reach of Ari.
// instance_nearest() answers undefined when there is none.
//
function barn_labels_target(_cfg) {
    if (!instance_exists(obj_ari)) { return undefined; }
    if (obj_ari.using_mouse) {
        var _under = instance_nearest(mouse_x(), mouse_y(), obj_player_animal);
        if (_under != undefined && point_distance(mouse_x(), mouse_y(), _under.x, _under.y) <= 20) {
            return _under;
        }
        return undefined;
    }
    var _near = instance_nearest(obj_ari.x, obj_ari.y, obj_player_animal);
    if (_near != undefined && point_distance(obj_ari.x, obj_ari.y, _near.x, _near.y) <= _cfg.controller_reach_px) {
        return _near;
    }
    return undefined;
}

function barn_labels_tick() {
    var _nodes = barn_labels_nodes();
    if (_nodes == undefined) { return; }

    var _cfg = barn_labels_config();
    var _target = undefined;
    if (_cfg.enabled && !MIST.is_running() && !non_cutscene_pause()) {
        _target = barn_labels_target(_cfg);
    }
    if (_target == undefined || !instance_exists(_target) || _target.me == undefined) {
        _nodes.card.set_alpha(0);
        _nodes.text.set_alpha(0);
        return;
    }

    var _me = _target.me;
    var _label = _me.name + "   " + local_get(BARN_LABELS_TEXT + "barn_hearts") + " "
        + string(points_to_animal_heart_level(_me.heart_points)) + "/10";
    _label += "\n" + local_get(BARN_LABELS_TEXT + (_me.has_eaten ? "barn_fed" : "barn_unfed"))
        + " - " + local_get(BARN_LABELS_TEXT + (_me.has_been_pat ? "barn_pet" : "barn_unpet"));
    _nodes.text.set_text(_label);

    var _size = _nodes.text.measure();
    var _card_w = _size.x + 10;
    var _card_h = max(_size.y + 6, 16);
    _nodes.card.set_size(_card_w, _card_h);

    // Anchor lays out in GUI space, 1:1 with the camera view.
    var _gx = _target.x - CAMERA.left();
    var _gy = _target.bbox_top - CAMERA.top();
    _nodes.card.set_xy(_gx - (_card_w / 2), _gy - _card_h - 4);

    _nodes.card.set_alpha(1);
    _nodes.text.set_alpha(1);
}

//
// The mod's own text is registered for localization through
// localization/l10n.meta.toml, so English resolves natively. A language whose
// table has no entry for a key gets the English source instead of MISSING.
//
function barn_labels_local_missing(_value, _ctx) {
    if (_value != undefined || !is_struct(_ctx)) { return undefined; }
    var _key = _ctx[$ "key"];
    var _n = string_length(BARN_LABELS_TEXT);
    if (!is_string(_key) || string_copy(_key, 1, _n) != BARN_LABELS_TEXT) { return undefined; }
    var _text = undefined;
    try {
        var _table = fiddle_get("mods/barn_labels/labels");
        _text = _table[$ string_delete(_key, 1, _n)];
    } catch (_e) {}
    return is_string(_text) ? _text : undefined;
}

function barn_labels_register() {
    var _rt = __barn_labels_runtime();
    if (_rt.registered) { return; }
    _rt.registered = true;
    mmapi_filter("local.missing", barn_labels_local_missing);
    mmapi_register(barn_labels_tick);
}

mmapi_mod_declare("barn_labels", BARN_LABELS_VERSION);
barn_labels_register();
