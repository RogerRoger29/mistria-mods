//
// Shovel Sense - dig sites give themselves away while the shovel is in hand.
//
// Hold the shovel and every undug dig site within reach lets out an
// occasional puff of settling earth (the game's own dirt effect). The first
// site to come within a few tiles makes Ari think of archaeology: a thought
// bubble, a soft chime, a nudge of rumble, once per site per day. Put the
// shovel away and the ground goes quiet.
//
// This is the MOMI edition of the Mistria Mods framework mod of the same
// name. The per-frame work runs from mmapi_register instead of a patch in
// obj_ari, and the options live in mod_data/shovel_sense/shovel_sense.json.
// Do not install both editions at once.
//
#macro SHOVEL_SENSE_VERSION "1.0.0"
#macro SHOVEL_SENSE_CONFIG_VERSION 1

function __shovel_sense_runtime() {
    if (global[$ "__shovel_sense"] == undefined) {
        global.__shovel_sense = { registered: false, cfg: undefined, tick: 0, seen: {} };
    }
    return global.__shovel_sense;
}

function shovel_sense_config() {
    var _rt = __shovel_sense_runtime();
    if (_rt.cfg != undefined) { return _rt.cfg; }
    var _src = mmapi_config_read_valid("shovel_sense", SHOVEL_SENSE_CONFIG_VERSION);
    var _cfg = {
        enabled: mmapi_config_bool(_src, "enabled", true),
        shovel_only: mmapi_config_bool(_src, "shovel_only", true),
        chime: mmapi_config_bool(_src, "chime", true),
        notice_radius_tiles: mmapi_config_number(_src, "notice_radius_tiles", 5, 1, 30),
        puff_reach_tiles: mmapi_config_number(_src, "puff_reach_tiles", 12, 1, 40)
    };
    _cfg[$ "__friendly_names"] = {
        enabled: "Enabled",
        shovel_only: "Only while the shovel is held",
        chime: "Chime when Ari notices a site",
        notice_radius_tiles: "Notice radius (tiles)",
        puff_reach_tiles: "Puff reach (tiles)"
    };
    mmapi_config_write("shovel_sense", SHOVEL_SENSE_CONFIG_VERSION, _cfg);
    _rt.cfg = _cfg;
    return _cfg;
}

function shovel_sense_active(_cfg) {
    if (!_cfg.enabled || MIST.is_running()) { return false; }
    if (!instance_exists(obj_ari) || GRID == undefined) { return false; }
    if (!_cfg.shovel_only) { return true; }
    var _held = ARI.held_item();
    return _held != undefined && _held.prototype.tags.contains("shovel");
}

//
// A few times a second: scan the cells around Ari for undug dig sites. They
// are 2x2 nodes on even coordinates, so the scan steps by two and counts each
// site once, at its top-left.
//
function shovel_sense_tick() {
    var _rt = __shovel_sense_runtime();
    _rt.tick += 1;
    if (_rt.tick % 15 != 0 || non_cutscene_pause()) { return; }
    var _cfg = shovel_sense_config();
    if (!shovel_sense_active(_cfg)) { return; }

    var _ax = obj_ari.x div 8;
    var _ay = obj_ari.y div 8;
    var _reach = _cfg.puff_reach_tiles * 2;
    var _notice = _cfg.notice_radius_tiles * 2;
    var _floor_key = DUNGEON_RUNNER != undefined ? DUNGEON_RUNNER.current_floor : -1;
    var _noticed = false;

    for (var _cy = ((_ay - _reach) div 2) * 2; _cy <= _ay + _reach; _cy += 2) {
        for (var _cx = ((_ax - _reach) div 2) * 2; _cx <= _ax + _reach; _cx += 2) {
            var _ni = GRID.try_node_index_for_cell(_cx, _cy);
            if (_ni == undefined || GRID.node_object_id[_ni] != ObjectId.DigSite) { continue; }
            var _node = GRID.node_parent[_ni];
            var _tx = _node[$ "top_left_x"] ?? _cx;
            var _ty = _node[$ "top_left_y"] ?? _cy;
            if (_tx != _cx || _ty != _cy) { continue; }
            var _px = _tx * 8 + 8;
            var _py = _ty * 8 + 8;

            // Settling earth, about every two seconds per site.
            if (irandom(7) == 0) {
                create_animation_effect(
                    _px + irandom_range(-4, 4),
                    _py + irandom_range(-2, 2),
                    get_instance_depth(_ty * 8 + 16) - 1,
                    choose(spr_fx_poof1_dirt_once, spr_fx_poof2_dirt_once)
                );
            }

            // The first close one Ari has not noticed yet.
            if (!_noticed && abs(_cx - _ax) <= _notice && abs(_cy - _ay) <= _notice) {
                var _key = string(room()) + ":" + string(_floor_key) + ":"
                    + string(total_days()) + ":" + string(_cx) + ":" + string(_cy);
                if (_rt.seen[$ _key] == undefined) {
                    _rt.seen[$ _key] = true;
                    _noticed = true;
                    if (!obj_ari.bark_emitter.is_barking()) {
                        obj_ari.bark_emitter.emit(BarkId.Archaeology, BarkType.Thought, false);
                    }
                    if (_cfg.chime) {
                        TANGO.play("SoundEffects/NPCs/DialogSparkle", obj_ari.x, obj_ari.y);
                    }
                    set_rumble(RumbleKind.ItemCollect);
                }
            }
        }
    }
}

function shovel_sense_register() {
    var _rt = __shovel_sense_runtime();
    if (_rt.registered) { return; }
    _rt.registered = true;
    mmapi_register(shovel_sense_tick);
}

mmapi_mod_declare("shovel_sense", SHOVEL_SENSE_VERSION);
shovel_sense_register();
