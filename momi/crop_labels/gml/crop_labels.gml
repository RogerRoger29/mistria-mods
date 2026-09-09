//
// Crop Labels - hold a key and the crop you are pointing at tells you what it
// is and how many days until it is ready, from any distance. Regrowing crops
// count against their shorter schedule after the first harvest.
//
// MOMI edition of the Mistria Mods framework mod of the same name. The key is
// an MMAPI hotkey read from mod_data/crop_labels/crop_labels.json (default F;
// an optional gamepad button too) rather than an entry in Settings > Controls.
// Do not install both editions at once.
//
#macro CROP_LABELS_VERSION "1.0.0"
#macro CROP_LABELS_CONFIG_VERSION 1

function __crop_labels_runtime() {
    if (global[$ "__crop_labels"] == undefined) {
        global.__crop_labels = {
            registered: false, cfg: undefined, nodes: undefined,
            bound: false, key_binding: undefined, pad_binding: undefined
        };
    }
    return global.__crop_labels;
}

function crop_labels_config() {
    var _rt = __crop_labels_runtime();
    if (_rt.cfg != undefined) { return _rt.cfg; }
    var _src = mmapi_config_read_valid("crop_labels", CROP_LABELS_CONFIG_VERSION);
    var _key = mmapi_config_get(_src, "key", "F");
    if (!is_string(_key) || _key == "") { _key = "F"; }
    var _pad = mmapi_config_get(_src, "gamepad", "");
    if (!is_string(_pad)) { _pad = ""; }
    var _cfg = {
        enabled: mmapi_config_bool(_src, "enabled", true),
        key: _key,
        gamepad: _pad
    };
    _cfg[$ "__friendly_names"] = {
        enabled: "Enabled",
        key: "Hold key (F, V, F5, HOME ...)",
        gamepad: "Hold gamepad button (GAMEPAD_LEFT_TRIGGER ..., blank for none)"
    };
    mmapi_config_write("crop_labels", CROP_LABELS_CONFIG_VERSION, _cfg);
    _rt.cfg = _cfg;
    return _cfg;
}

//
// Bindings resolve once, after the first frame, when the config is readable.
//
function crop_labels_bind(_rt, _cfg) {
    if (_rt.bound) { return; }
    _rt.bound = true;
    _rt.key_binding = mmapi_hotkey_binding_from_name(_cfg.key);
    if (_rt.key_binding == undefined) {
        mmapi_log_warn("crop_labels", "crop_labels: '" + string(_cfg.key) + "' is not a supported key name; using F");
        _rt.key_binding = mmapi_hotkey_binding_from_name("F");
    }
    if (_cfg.gamepad != "") {
        _rt.pad_binding = mmapi_hotkey_binding_from_name(_cfg.gamepad);
        if (_rt.pad_binding == undefined) {
            mmapi_log_warn("crop_labels", "crop_labels: '" + string(_cfg.gamepad) + "' is not a supported gamepad button name");
        }
    }
}

function crop_labels_held(_rt) {
    if (_rt.key_binding != undefined && mmapi_hotkey_binding_held(_rt.key_binding)) { return true; }
    if (_rt.pad_binding != undefined && mmapi_hotkey_binding_held(_rt.pad_binding)) { return true; }
    return false;
}

//
// The card: Anchor nodes on the vitals HUD. Raw world-space text inherits
// whatever LUT the previous shader pass left bound; Anchor owns that state.
//
function crop_labels_nodes() {
    var _menu = ANCHOR.get_menu(Menu.Vitals);
    if (_menu == undefined) { return undefined; }

    var _rt = __crop_labels_runtime();
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
        .allow_line_breaks(false)
        .prevent_spillover(false)
        .set_alpha(0);

    _rt.nodes = { card: _card, text: _text };
    return _rt.nodes;
}

//
// What is planted at this cell, and how long until it is ready?
//
function crop_labels_label_for(_xx, _yy) {
    if (_xx < 0 || _yy < 0 || _xx >= GRID.dims.x || _yy >= GRID.dims.y) { return undefined; }

    var _ni = GRID.node_index_for_cell(_xx, _yy);
    var _object_id = GRID.node_object_id[_ni];
    if (_object_id == undefined) { return undefined; }
    if (object_id_to_object_category(_object_id) != ObjectCategory.Crop) { return undefined; }

    var _node = GRID.node_parent[_ni];
    var _proto = _node.prototype;
    if (_proto.harvest == undefined) { return undefined; }

    // A crop that has already fruited once regrows on a shorter schedule.
    var _stages = _proto.day_to_stage;
    if (_node.regrow_cycle && _proto.post_harvest_day_to_stage != undefined) {
        _stages = _proto.post_harvest_day_to_stage;
    }

    // Forageables define no schedule and inherit the default [0]; a crop with
    // no real schedule gets its name and nothing else.
    var _total = _stages.count() - 1;
    var _left = _total - _node.day_count;
    var _name = local_get(ITEM_PROTOTYPES[_proto.harvest].name_key);

    var _label = _name;
    if (_total > 0) {
        _label = _left <= 0 ? _name + " - ready" : _name + " - " + string(_left) + "d";
    }

    return {
        text: _label,
        x: GRID.node_top_left_x[_ni],
        y: GRID.node_top_left_y[_ni]
    };
}

function crop_labels_tick() {
    var _nodes = crop_labels_nodes();
    if (_nodes == undefined) { return; }

    var _rt = __crop_labels_runtime();
    var _cfg = crop_labels_config();
    crop_labels_bind(_rt, _cfg);

    var _label = undefined;
    if (_cfg.enabled && !non_cutscene_pause() && instance_exists(obj_ari) && crop_labels_held(_rt)) {
        // With a mouse read the pointer, anywhere on screen; on a controller
        // there is no pointer, so fall back to the tool cursor.
        if (obj_ari.using_mouse) {
            _label = crop_labels_label_for(mouse_x() div 8, mouse_y() div 8);
        } else {
            _label = crop_labels_label_for(obj_ari.cell_select.x, obj_ari.cell_select.y);
        }
    }

    if (_label == undefined) {
        _nodes.card.set_alpha(0);
        _nodes.text.set_alpha(0);
        return;
    }

    _nodes.text.set_text(_label.text);

    var _size = _nodes.text.measure();
    var _card_w = _size.x + 10;
    var _card_h = max(_size.y + 6, 16);
    _nodes.card.set_size(_card_w, _card_h);

    // Anchor lays out in GUI space, 1:1 with the camera view.
    var _gx = (_label.x * 8) + 8 - CAMERA.left();
    var _gy = (_label.y * 8) - CAMERA.top();
    _nodes.card.set_xy(_gx - (_card_w / 2), _gy - _card_h - 2);

    _nodes.card.set_alpha(1);
    _nodes.text.set_alpha(1);
}

function crop_labels_register() {
    var _rt = __crop_labels_runtime();
    if (_rt.registered) { return; }
    _rt.registered = true;
    mmapi_register(crop_labels_tick);
}

mmapi_mod_declare("crop_labels", CROP_LABELS_VERSION);
crop_labels_register();
