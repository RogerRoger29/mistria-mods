//
// Homeward - a sixth spell that carries Ari home. The day goes on.
//
// Cast it anywhere, the mines included, and Ari is delivered to her own
// doorstep by the same taxi system every door in the game uses. It does not
// end the day, touch the clock, or save; it only moves her. It is learned,
// not given: with the Magic Skill mod present it arrives at a Magic level
// (20 by default); without it, alongside the first spell the Mist teaches.
//
// MOMI edition of the Mistria Mods framework mod of the same name. The spell
// itself is data (fiddle/spells.toml, merged by MOMI, which mints
// Spell.Homeward); the cast and its gate are spells.cast and spells.can_cast
// overrides that answer only for Homeward. Options live in
// mod_data/homeward/homeward.json. Do not install both editions at once.
//
#macro HOMEWARD_VERSION "1.0.0"
#macro HOMEWARD_CONFIG_VERSION 1
#macro HOMEWARD_TEXT "mods/homeward/labels/"

function __homeward_runtime() {
    if (global[$ "__homeward"] == undefined) {
        global.__homeward = { registered: false, cfg: undefined, tick: 0, after_load: false };
    }
    return global.__homeward;
}

function homeward_config() {
    var _rt = __homeward_runtime();
    if (_rt.cfg != undefined) { return _rt.cfg; }
    var _src = mmapi_config_read_valid("homeward", HOMEWARD_CONFIG_VERSION);
    var _cfg = {
        learn_level: mmapi_config_number(_src, "learn_level", 20, 1, 99)
    };
    _cfg[$ "__friendly_names"] = {
        learn_level: "Magic level that teaches it (with Magic Skill installed)"
    };
    mmapi_config_write("homeward", HOMEWARD_CONFIG_VERSION, _cfg);
    _rt.cfg = _cfg;
    return _cfg;
}

function homeward_can_cast() {
    return !TAXI.is_traveling()
        && !MIST.is_running()
        && ARI.end_of_day_status == undefined
        && CURRENT_LOCATION_ID != LocationId.PlayerHome;
}

//
// The taxi itinerary a door into the house would make, so Ari arrives on her
// own doormat. Leaving the mines this way runs the dungeon's own exit hook,
// since that fires on every change of room.
//
function homeward_cast() {
    TANGO.play("SoundEffects/Ari/MagicGeneric", obj_ari.x, obj_ari.y);
    goto_location_id(LocationId.PlayerHome)
        .set_specific_location_tag(DECOR.player_home_room_transition());
}

//
// Learned, not given. The Magic skill is looked up by name at run time, so
// this never names Skill.Magic and is safe with or without that mod.
//
function homeward_try_learn(_quiet) {
    if (ARI == undefined || ARI[$ "spells_learned"] == undefined) { return; }
    if (ARI.spells_learned[Spell.Homeward]) { return; }

    var _magic = try_string_to_skill("magic");
    var _ready = false;
    if (_magic != undefined) {
        _ready = skill_xp_to_level(_magic, ARI.skill_xp[_magic] ?? 0) >= homeward_config().learn_level;
    } else {
        _ready = array_contains(ARI.spells_learned, true);
    }

    if (_ready) {
        ARI.learn_spell(Spell.Homeward);
        if (!_quiet) {
            create_notification(HOMEWARD_TEXT + "homeward_learned");
        }
    }
}

// spells.can_cast: claim Homeward, defer everything else to the game.
function homeward_can_cast_override(_spell) {
    if (_spell != Spell.Homeward) { return undefined; }
    return homeward_can_cast();
}

// spells.cast: the same claim; a non-undefined result marks the cast handled.
function homeward_cast_override(_spell) {
    if (_spell != Spell.Homeward) { return undefined; }
    homeward_cast();
    return true;
}

function homeward_on_new_day(_ctx) {
    homeward_try_learn(false);
}

// The save is read after this fires, so the check waits for the next frame.
function homeward_on_game_loaded(_ctx) {
    __homeward_runtime().after_load = true;
}

function homeward_on_title(_ctx) {
    __homeward_runtime().after_load = false;
}

//
// Once a second: a save that has just qualified (a spell learned, a Magic
// level gained) gets the spell within the second, quietly right after a load
// and with a toast in play.
//
function homeward_tick() {
    var _rt = __homeward_runtime();
    if (_rt.after_load) {
        _rt.after_load = false;
        homeward_try_learn(true);
        return;
    }
    _rt.tick += 1;
    if (_rt.tick % 60 != 0) { return; }
    if (!instance_exists(obj_ari) || MIST.is_running() || non_cutscene_pause()) { return; }
    homeward_try_learn(false);
}

//
// The spell's name, description and type come from spells.toml and the toast
// from this mod's own label file; both resolve natively in English. A language
// whose table has no entry gets the English source instead of MISSING.
//
function homeward_local_missing(_value, _ctx) {
    if (_value != undefined || !is_struct(_ctx)) { return undefined; }
    var _key = _ctx[$ "key"];
    if (!is_string(_key)) { return undefined; }
    var _text = undefined;
    try {
        var _n = string_length(HOMEWARD_TEXT);
        if (string_copy(_key, 1, _n) == HOMEWARD_TEXT) {
            var _table = fiddle_get("mods/homeward/labels");
            _text = _table[$ string_delete(_key, 1, _n)];
        } else if (string_copy(_key, 1, 16) == "spells/homeward/") {
            var _spell = fiddle_get("spells/homeward");
            if (is_struct(_spell)) { _text = _spell[$ string_delete(_key, 1, 16)]; }
        }
    } catch (_e) {}
    return is_string(_text) ? _text : undefined;
}

function homeward_register() {
    var _rt = __homeward_runtime();
    if (_rt.registered) { return; }
    _rt.registered = true;
    mmapi_override("spells.can_cast", homeward_can_cast_override);
    mmapi_override("spells.cast", homeward_cast_override);
    mmapi_on("game.new_day", homeward_on_new_day);
    mmapi_on("save.game_loaded", homeward_on_game_loaded);
    mmapi_on("game.title_entered", homeward_on_title);
    mmapi_filter("local.missing", homeward_local_missing);
    mmapi_register(homeward_tick);
}

mmapi_mod_declare("homeward", HOMEWARD_VERSION);
homeward_register();
