//
// Curious Neighbours - walk near a villager you have met while carrying
// something and they react to it with a thought bubble: a heart for loved, a
// cute face for liked, ellipses for disliked, a sweat drop for hated, nothing
// for neutral. It fires when the item in your hand changes, so a crowd never
// spams you, and it never talks over an existing bubble, a chat between
// villagers, or a cutscene. It reveals their true preferences.
//
// MOMI edition of the Mistria Mods framework mod of the same name. One tick a
// frame walks every villager instead of a patch in each villager's step.
// Options live in mod_data/curious_neighbours/curious_neighbours.json. Do not
// install both editions at once.
//
#macro CURIOUS_NEIGHBOURS_VERSION "1.0.0"
#macro CURIOUS_NEIGHBOURS_CONFIG_VERSION 1

function __curious_neighbours_runtime() {
    if (global[$ "__curious_neighbours"] == undefined) {
        global.__curious_neighbours = { registered: false, cfg: undefined, last: {} };
    }
    return global.__curious_neighbours;
}

function curious_neighbours_config() {
    var _rt = __curious_neighbours_runtime();
    if (_rt.cfg != undefined) { return _rt.cfg; }
    var _src = mmapi_config_read_valid("curious_neighbours", CURIOUS_NEIGHBOURS_CONFIG_VERSION);
    var _cfg = {
        enabled: mmapi_config_bool(_src, "enabled", true),
        radius_px: mmapi_config_number(_src, "radius_px", 40, 8, 200)
    };
    _cfg[$ "__friendly_names"] = {
        enabled: "Enabled",
        radius_px: "Reaction distance (pixels, 8 per tile)"
    };
    mmapi_config_write("curious_neighbours", CURIOUS_NEIGHBOURS_CONFIG_VERSION, _cfg);
    _rt.cfg = _cfg;
    return _cfg;
}

//
// Would this villager want this item as a gift? Mirrors the desire
// calculation inside Npc.give_gift(), including its two hand-written special
// cases, without any of its side effects.
//
function curious_neighbours_desire_for(_npc, _item) {
    if (_item.item_id == ItemId.VoidNewt) {
        return _npc.id == NpcId.Juniper ? Desire.Loved : Desire.Disliked;
    }
    if (_item.item_id == ItemId.VoidCake) {
        return _npc.id == NpcId.Eiland ? Desire.Loved : Desire.Disliked;
    }
    if (_item.infusion == Infusion.Loveable || _npc.prototype.loved_gifts.contains(_item.item_id)) {
        return Desire.Loved;
    }
    if (_item.infusion == Infusion.Likeable || _npc.prototype.liked_gifts.contains(_item.item_id)) {
        return Desire.Liked;
    }
    if (_item.item_id == _npc.prototype.hated_gift) {
        return Desire.Hated;
    }
    if (_item.prototype.tags.contains_any_value_from(_npc.prototype.disliked_gift_tags)) {
        return Desire.Disliked;
    }
    return Desire.Neutral;
}

// Which bubble to show for that opinion, or undefined to stay quiet.
function curious_neighbours_bark_for(_npc, _item) {
    switch (curious_neighbours_desire_for(_npc, _item)) {
        case Desire.Loved: return BarkId.Heart;
        case Desire.Liked: return BarkId.CuteFace;
        case Desire.Disliked: return BarkId.Ellipses;
        case Desire.Hated: return BarkId.SweatDrop;
        default: return undefined;
    }
}

//
// One villager instance. Each villager is its own object type with one
// instance, so the "last item shown" memory is keyed by object index.
//
function curious_neighbours_check(_inst, _cfg) {
    var _rt = __curious_neighbours_runtime();
    if (_inst.bark_emitter.is_barking() || _inst.chat_partner != undefined) { return; }

    var _key = string(_inst.object_index);
    var _item = ARI.held_item();
    if (_item == undefined || point_distance(_inst.x, _inst.y, obj_ari.x, obj_ari.y) > _cfg.radius_px) {
        _rt.last[$ _key] = undefined;
        return;
    }

    if (_rt.last[$ _key] == _item.item_id) { return; }
    _rt.last[$ _key] = _item.item_id;

    var _npc = NPCS[gm_obj_id_to_npc_id(_inst.object_index)];
    if (!_npc.has_met()) { return; }

    var _bark = curious_neighbours_bark_for(_npc, _item);
    if (_bark != undefined) {
        _inst.bark_emitter.emit(_bark, BarkType.Thought);
    }
}

function curious_neighbours_tick() {
    var _cfg = curious_neighbours_config();
    if (!_cfg.enabled || !instance_exists(obj_ari) || MIST.running || non_cutscene_pause()) { return; }
    with (par_NPC) {
        curious_neighbours_check(id, _cfg);
    }
}

function curious_neighbours_register() {
    var _rt = __curious_neighbours_runtime();
    if (_rt.registered) { return; }
    _rt.registered = true;
    mmapi_register(curious_neighbours_tick);
}

mmapi_mod_declare("curious_neighbours", CURIOUS_NEIGHBOURS_VERSION);
curious_neighbours_register();
