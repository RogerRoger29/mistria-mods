//
// Mistria Notices You - nine letters that arrive as your play crosses
// milestones. The letters themselves are data (fiddle/letters.toml, merged
// into the game's own letter table by MOMI); this file only keeps them
// readable in every language.
//
// letters.toml is registered for localization by the game, so the English
// text resolves natively. A language table has no entry for a letter that
// did not exist when it was translated, and the engine renders MISSING for
// that. This answers local.missing with the English source instead.
//
#macro MISTRIA_NOTICES_VERSION "1.0.0"

function __mistria_notices_runtime() {
    if (global[$ "__mistria_notices"] == undefined) {
        global.__mistria_notices = { registered: false };
    }
    return global.__mistria_notices;
}

function mistria_notices_local_missing(_value, _ctx) {
    if (_value != undefined || !is_struct(_ctx)) { return undefined; }
    var _key = _ctx[$ "key"];
    if (!is_string(_key) || string_copy(_key, 1, 16) != "letters/notices_") { return undefined; }
    var _parts = string_split(_key, "/");
    if (array_length(_parts) != 3) { return undefined; }
    var _text = undefined;
    try {
        var _letter = fiddle_get("letters/" + _parts[1]);
        if (is_struct(_letter)) { _text = _letter[$ _parts[2]]; }
    } catch (_e) {}
    return is_string(_text) ? _text : undefined;
}

function mistria_notices_register() {
    var _rt = __mistria_notices_runtime();
    if (_rt.registered) { return; }
    _rt.registered = true;
    mmapi_filter("local.missing", mistria_notices_local_missing);
}

mmapi_mod_declare("mistria_notices", MISTRIA_NOTICES_VERSION);
mistria_notices_register();
