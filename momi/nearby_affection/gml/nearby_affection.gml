//
// Nearby Affection - when a villager gains hearts from you (the day's first
// chat, or a gift), every villager you have met who is standing nearby also
// gains a little, once each per day, with a heart bubble over their head. It
// goes through the game's own heart system, so level-ups and jingles happen
// as they normally would. Caldarus and Seridia are skipped below six hearts,
// matching the game's own rule for them.
//
// MOMI edition of the Mistria Mods framework mod of the same name. The
// trigger is the npc.heart_points filter, which the game runs inside
// add_heart_points(); the bystanders' own gains re-enter that filter and are
// ignored while an award is in progress. Options live in
// mod_data/nearby_affection/nearby_affection.json. Do not install both
// editions at once.
//
#macro NEARBY_AFFECTION_VERSION "1.0.0"
#macro NEARBY_AFFECTION_CONFIG_VERSION 1

function __nearby_affection_runtime() {
    if (global[$ "__nearby_affection"] == undefined) {
        global.__nearby_affection = { registered: false, cfg: undefined, busy: false, awarded: {} };
    }
    return global.__nearby_affection;
}

function nearby_affection_config() {
    var _rt = __nearby_affection_runtime();
    if (_rt.cfg != undefined) { return _rt.cfg; }
    var _src = mmapi_config_read_valid("nearby_affection", NEARBY_AFFECTION_CONFIG_VERSION);
    var _cfg = {
        enabled: mmapi_config_bool(_src, "enabled", true),
        radius_px: mmapi_config_number(_src, "radius_px", 64, 8, 400),
        points: mmapi_config_number(_src, "points", 2, 1, 50),
        popup: mmapi_config_bool(_src, "popup", true)
    };
    _cfg[$ "__friendly_names"] = {
        enabled: "Enabled",
        radius_px: "Bystander distance (pixels, 8 per tile)",
        points: "Heart points per bystander per day",
        popup: "Heart bubble over bystanders"
    };
    mmapi_config_write("nearby_affection", NEARBY_AFFECTION_CONFIG_VERSION, _cfg);
    _rt.cfg = _cfg;
    return _cfg;
}

//
// Award every eligible villager near the one who just gained hearts.
//
function nearby_affection_on_interact(_origin_id, _cfg) {
    var _rt = __nearby_affection_runtime();
    var _origin_obj = npc_id_to_gm_obj_id(_origin_id);
    if (!instance_exists(_origin_obj)) { return; }

    var _ox = _origin_obj.x;
    var _oy = _origin_obj.y;

    for (var _i = 0; _i < NpcId.LEN; _i++) {
        if (_i == _origin_id) { continue; }
        if (_rt.awarded[$ string(_i)] != undefined) { continue; }

        var _bystander = NPCS[_i];
        // Strangers have no opinion of you.
        if (!_bystander.has_met()) { continue; }
        if ((_i == NpcId.Caldarus || _i == NpcId.Seridia) && _bystander.heart_level() < 6) { continue; }

        var _obj = npc_id_to_gm_obj_id(_i);
        if (!instance_exists(_obj)) { continue; }
        if (point_distance(_obj.x, _obj.y, _ox, _oy) > _cfg.radius_px) { continue; }

        _rt.awarded[$ string(_i)] = true;
        _bystander.add_heart_points(_cfg.points);

        // The same bubble pets show when petted. Skipped if the villager is
        // already barking, so it never stomps a chat or cutscene bubble.
        if (_cfg.popup && !_obj.bark_emitter.is_barking()) {
            _obj.bark_emitter.emit(BarkId.Heart, BarkType.Thought);
        }
    }
}

//
// npc.heart_points: value is the amount about to be added, ctx the villager.
// Never changes the value; it only reacts to a real gain.
//
function nearby_affection_heart_filter(_value, _npc) {
    var _rt = __nearby_affection_runtime();
    if (_rt.busy) { return undefined; }
    if (!(is_real(_value) || is_int64(_value)) || _value <= 0) { return undefined; }
    if (!is_struct(_npc) || _npc[$ "id"] == undefined) { return undefined; }
    var _cfg = nearby_affection_config();
    if (!_cfg.enabled) { return undefined; }

    _rt.busy = true;
    try {
        nearby_affection_on_interact(_npc.id, _cfg);
    } catch (_e) {}
    _rt.busy = false;
    return undefined;
}

// A new day, a loaded save, or the title screen: everyone is eligible again.
function nearby_affection_reset(_ctx) {
    __nearby_affection_runtime().awarded = {};
}

function nearby_affection_register() {
    var _rt = __nearby_affection_runtime();
    if (_rt.registered) { return; }
    _rt.registered = true;
    mmapi_filter("npc.heart_points", nearby_affection_heart_filter);
    mmapi_on("game.new_day", nearby_affection_reset);
    mmapi_on("save.game_loaded", nearby_affection_reset);
    mmapi_on("game.title_entered", nearby_affection_reset);
}

mmapi_mod_declare("nearby_affection", NEARBY_AFFECTION_VERSION);
nearby_affection_register();
