//
// Big Rock Credit - large rocks and boulders count toward revealing the mine
// ladder, weighted by their size: a 4x4 rock is worth four small ones, a 6x6
// boulder nine. In the unmodded game they ship as non-candidates and are
// worth nothing, so the most expensive objects on the floor moved the ladder
// not at all.
//
// MOMI edition of the Mistria Mods framework mod of the same name. It listens
// on resource.node_picked, which fires with the node and a destroyed flag on
// the hit that kills it. The game itself only scores ladder candidates, so a
// big rock is scored here alone and never twice. Options live in
// mod_data/big_rock_credit/big_rock_credit.json. Do not install both
// editions at once.
//
#macro BIG_ROCK_CREDIT_VERSION "1.0.0"
#macro BIG_ROCK_CREDIT_CONFIG_VERSION 1

function __big_rock_credit_runtime() {
    if (global[$ "__big_rock_credit"] == undefined) {
        global.__big_rock_credit = { registered: false, cfg: undefined };
    }
    return global.__big_rock_credit;
}

function big_rock_credit_config() {
    var _rt = __big_rock_credit_runtime();
    if (_rt.cfg != undefined) { return _rt.cfg; }
    var _src = mmapi_config_read_valid("big_rock_credit", BIG_ROCK_CREDIT_CONFIG_VERSION);
    var _cfg = {
        enabled: mmapi_config_bool(_src, "enabled", true)
    };
    _cfg[$ "__friendly_names"] = { enabled: "Enabled" };
    mmapi_config_write("big_rock_credit", BIG_ROCK_CREDIT_CONFIG_VERSION, _cfg);
    _rt.cfg = _cfg;
    return _cfg;
}

//
// The killing hit on a rock in the Mines. A candidate (every small rock, ore
// node and seam) is the game's own business. A non-candidate with a footprint
// gets the whole footprint: the extra cells here, then the runner's own award
// for the last one, which also runs the ladder check.
//
function big_rock_credit_on_node_picked(_ctx) {
    if (!is_struct(_ctx)) { return; }
    if (_ctx[$ "result"] != "rock" || !_ctx[$ "destroyed"]) { return; }
    if (!big_rock_credit_config().enabled) { return; }

    var _grid = _ctx[$ "grid"];
    if (_grid == undefined || _grid.location_id != LocationId.Dungeon) { return; }
    if (DUNGEON_RUNNER == undefined) { return; }

    var _node = _ctx[$ "node"];
    if (_node == undefined || _node[$ "prototype"] == undefined) { return; }
    if (_node[$ "ladder_candidate"]) { return; }

    var _cells = (_node.prototype.size.x div 2) * (_node.prototype.size.y div 2);
    if (_cells < 1) { return; }

    if (_cells > 1) {
        DUNGEON_RUNNER.ladder_score +=
            DUNGEON.biomes[DUNGEON_BIOME].object_element_points * (_cells - 1);
    }
    DUNGEON_RUNNER.on_object_destroy(_ctx.x, _ctx.y);
}

function big_rock_credit_register() {
    var _rt = __big_rock_credit_runtime();
    if (_rt.registered) { return; }
    _rt.registered = true;
    mmapi_on("resource.node_picked", big_rock_credit_on_node_picked);
}

mmapi_mod_declare("big_rock_credit", BIG_ROCK_CREDIT_VERSION);
big_rock_credit_register();
