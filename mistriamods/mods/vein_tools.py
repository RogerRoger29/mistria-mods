"""Vein Tools - a small Fields of Mistria mod."""

from ..patcher import Markers

SLUG = "vein_tools"
NAME = "Vein Tools"
SUMMARY = "Water a whole crop patch or mine a whole vein of rock in one swing; reach scales with tool tier."
DETAILS = """Water one plant and the whole connected patch is watered; hit one rock and the swing lands on every connected rock of that kind. Four toggles under Settings > Accessibility: Vein Watering (on), Vein Watering: Any Crop (off), Vein Mining (on), Vein Mining: Any Rock (off). Reach scales with your tool tier, from 8 tiles up to 200, which finally gives hoes and watering cans a reason to upgrade. Under the hood it calls the game's own watering and mining actions once per tile, so stamina, XP, essence, perks and sounds all behave normally. Mining spreads diagonally, watering orthogonally, and only uncharged swings trigger it."""
LEGACY = ['VEIN_WATERING']
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "max": (int, 200, 'tiles a top-tier tool veins; lower tiers scale 8/16/32/64/128'),
}

def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}

#!/usr/bin/env python3
"""
Vein Tools - a small Fields of Mistria mod.

Water one plant and the whole connected patch of that crop gets watered. Hit one
rock and your swing lands on every connected rock of the same type. Minecraft
vein-mining, for the farm and the mines.

Four toggles in Settings > Accessibility, so none of this needs re-patching to
change. "Vein Watering" and "Vein Mining" turn each half on and off. "Vein
Watering: Any Crop" and "Vein Mining: Any Rock" drop the same-type requirement,
so a vein runs through everything connected in that category instead - a mixed
bed waters in one go, a cave wall mines through stone, ore and boulders alike.
Both are off by default, since they widen behaviour that already works.

Each tile costs its own stamina and rolls its own perks - Refreshing still
refunds energy, Bountiful still drops free seeds - because the mod re-invokes
the game's own watering_can() / pick_axe() once per tile rather than
reimplementing either. It stops early when you can't afford the rest.

Note on mining: one swing is applied to every rock in the vein. With Instant
Tools installed each of those is a clean break; without it, they all take a
swing's worth of damage together.

Usage:
    python vein_tools.py --apply
    python vein_tools.py --apply --max 400
    python vein_tools.py --remove
    python vein_tools.py --status
"""



WATER = "assets/gml/scripts/GameplaySystems/Data/Grid/GridActions/Water.gml"
PICK = "assets/gml/scripts/GameplaySystems/Data/Grid/GridActions/Pick.gml"
FSM = "assets/gml/scripts/Player/AriFsm.gml"
SETTINGS = "assets/gml/scripts/Serialization/Settings.gml"
MENU = "assets/gml/scripts/UI/Anchor/Menus/SettingsMenu.gml"
LOCAL = "assets/fiddle/misc_local.toml"

# Leading \n? because misc_local.toml has no trailing newline of its own.
# The first release shipped under a different marker name; strip those too so an
# upgrade from it is clean.


# --- anchors -----------------------------------------------------------------

WATER_ANCHOR = """                    };
                } else {
                    set_rumble(RumbleKind.ToolInvalid);
                }
            }
"""

PICK_CALL = ("                var pick_result = pick_node(GRID, target_pos.x, target_pos.y,"
             " self.live_item.prototype, self.range_pattern == RangePattern.One ? 0 : -1,"
             " undefined, doppel);\n")

CAPTURE = """
//
// pick_node() destroys the rock outright, so remember what we were aiming at
// before it does - the vein fill has nothing to match on afterwards.
//
// Scan the same 2x2 pick_node scans, in the same order: it does not read the
// aimed cell directly, it takes the first of the four with an object on it. If
// we only looked at target_pos we would miss every rock sitting at +1 and the
// vein would silently never fire. try_ rather than the asserting variant, for
// the same reason pick_node uses it - the aimed cell can be out of bounds.
//
var vein_pick_target_id = undefined;
for (var vein_i = 0; vein_i < 4 && vein_pick_target_id == undefined; vein_i++) {
    var vein_ni = GRID.try_node_index_for_cell(
        target_pos.x + (vein_i div 2),
        target_pos.y + (vein_i mod 2)
    );
    if vein_ni != undefined {
        vein_pick_target_id = GRID.node_object_id[vein_ni];
    }
}
"""

PICK_ANCHOR = """                switch pick_result {
                    case PickResult.Rock:
                        //
                        break;
                    case PickResult.DigSite:
                        ARI.gain_xp(Skill.Archaeology, XpValue.break_dig_spot);
                        break;
                    case PickResult.Furniture:
                        //
                        break;
                }
"""

SETTINGS_ANCHOR = "        can_burn_fruit_trees: true,\n"

MENU_ANCHOR = ('        self.checkbox("screenshake");\n'
               '        self.checkbox("screen_flash");\n')

# --- injected GML ------------------------------------------------------------

WATER_HELPER = """
//
// Vein Tools. Global guard, following the MAP_HUBS idiom.
//
#macro VEIN_ACTIVE global.__vein_tools_active
VEIN_ACTIVE = false;

//
// How far one action reaches, by tool tier. This is the upgrade path: a worn
// tool veins a little, a mistril tool veins a whole field. It gives hoes and
// watering cans - which have no damage stat, and so never got cheaper per tile -
// something real to buy, and it stacks on top of the pickaxe's damage gain.
//
function vein_cap_for_quality(quality) {
    static CAPS = [8, 16, 32, 64, 128, __MAX__];

    if quality == undefined {
        return CAPS[0];
    }

    return CAPS[clamp(quality, 0, array_length(CAPS) - 1)];
}

//
// Flood-fill outward from a tile, collecting every connected tile that still
// needs the tool applied. What counts as connected is the `any_type` argument:
// the same object id (default), or anything in the same category.
//
// Crops are 2x2 and rocks are 2x2, 4x4 or 6x6, all aligned to even coordinates,
// so the fill steps by 2 and dedupes on each object's parent cell - otherwise a
// 4x4 rock would be collected four times over.
//
// Whether a tile is worth acting on depends on the tool; connectivity is decided
// only by matching object id, so an already-watered plant in the middle of a row
// still conducts rather than severing the patch.
//
// `target_id` may be supplied by the caller. Mining needs that: pick_node()
// destroys the rock synchronously, so by the time we run, the cell we were
// aimed at is already empty and there is nothing left to match on.
//
function vein_collect(x_pos, y_pos, category, quality, target_id, max_tiles,
                      diagonal, any_type) {
    var start = GRID.try_node_index_for_cell(x_pos, y_pos);
    if start == undefined {
        return [];
    }
    if target_id == undefined {
        target_id = GRID.node_object_id[start];
    }
    if target_id == undefined {
        return [];
    }
    if object_id_to_object_category(target_id) != category {
        return [];
    }

    var out = [];
    var queue = [[x_pos, y_pos]];
    var head = 0;
    var scanned = 0;
    var seen = {};
    var parents = {};
    seen[$ string(x_pos) + "," + string(y_pos)] = true;

    //
    // Only seed the starting object when it is still there - for mining it has
    // already been destroyed, and there is no parent left to read.
    //
    if GRID.node_object_id[start] == target_id {
        parents[$ string(GRID.node_top_left_x[start]) + ","
                 + string(GRID.node_top_left_y[start])] = true;
    }

    //
    // Mining also follows diagonals - ore runs corner to corner as often as it
    // runs in straight lines. Watering stays orthogonal, so a vein does not
    // jump between rows that only touch at a corner.
    //
    var dirs = [[2, 0], [-2, 0], [0, 2], [0, -2]];
    if diagonal {
        dirs = [[2, 0], [-2, 0], [0, 2], [0, -2],
                [2, 2], [2, -2], [-2, 2], [-2, -2]];
    }

    //
    // `out` only grows for tiles the tool can actually act on, so capping on it
    // alone lets the fill walk an entire already-watered field for nothing.
    // Bound the search itself too.
    //
    while head < array_length(queue)
        && array_length(out) < max_tiles
        && scanned < max_tiles * 4
    {
        var cur = queue[head];
        head += 1;
        scanned += 1;

        for (var i = 0; i < array_length(dirs); i++) {
            var nx = cur[0] + dirs[i][0];
            var ny = cur[1] + dirs[i][1];

            if nx < 0 || ny < 0 || nx >= GRID.dims.x || ny >= GRID.dims.y {
                continue;
            }

            var key = string(nx) + "," + string(ny);
            if struct_exists(seen, key) {
                continue;
            }
            seen[$ key] = true;

            var ni = GRID.node_index_for_cell(nx, ny);
            var nid = GRID.node_object_id[ni];
            if nid == undefined {
                continue;
            }

            //
            // What conducts. Normally a vein is one kind of thing and the object
            // id has to match all the way along. With the "any type" setting on
            // it is the CATEGORY that has to match instead, so a mixed bed
            // waters in one go and a cave wall mines through stone, ore and
            // boulders alike.
            //
            // Category stays the boundary either way - a crop vein can never
            // wander into rock - and the tool-specific test below still decides
            // what is worth acting on, so the pickaxe quality gate survives: a
            // weak pick still will not collect mistril.
            //
            if any_type {
                if object_id_to_object_category(nid) != category {
                    continue;
                }
            } else if nid != target_id {
                continue;
            }

            array_push(queue, [nx, ny]);

            //
            var pkey = string(GRID.node_top_left_x[ni]) + ","
                     + string(GRID.node_top_left_y[ni]);
            if struct_exists(parents, pkey) {
                continue;
            }
            parents[$ pkey] = true;

            var worth_it = category == ObjectCategory.Crop
                ? can_water_node(GRID, ni)
                : can_pick_node(GRID, ni, quality);

            if worth_it {
                array_push(out, { x: nx, y: ny });
            }
        }
    }

    return out;
}

function vein_water_collect(x_pos, y_pos, quality) {
    return vein_collect(
        x_pos, y_pos, ObjectCategory.Crop, undefined, undefined,
        vein_cap_for_quality(quality), false,
        SETTINGS.get("vein_water_any_crop")
    );
}
"""

PICK_HELPER = """
//
// Vein Tools: connected rock this pickaxe can actually break - of the same kind,
// or of any kind when "Vein Mining: Any Rock" is on. The quality gate is
// preserved either way, so a weak pick still bounces off the rocks it always
// bounced off rather than collecting them and failing on each.
//
function vein_pick_collect(x_pos, y_pos, item_quality, target_id) {
    return vein_collect(
        x_pos, y_pos, ObjectCategory.Rock, item_quality, target_id,
        vein_cap_for_quality(item_quality), true,
        SETTINGS.get("vein_mine_any_rock")
    );
}
"""

WATER_SPREAD = """
//
// Spread to the rest of the patch. VEIN_ACTIVE keeps the recursive calls from
// each trying to spread again.
//
// Only on an UNCHARGED swing (RangePattern.One). A charged swing from an
// upgraded can already covers an area itself, and because watering resolves in
// an animation chain the later targets in that area still look unwatered - so
// each one would kick off another full spread and queue thousands of redundant
// effects. Uncharged swing: the vein handles it. Charged swing: the tool's own
// pattern handles it.
//
// Budget: watering resolves inside an animation chain, so the tiles we spawn
// have not charged their stamina yet and ARI.get_stamina() will not fall as we
// iterate. Work out up front how many she can pay for.
//
if SETTINGS.get("vein_watering") && !VEIN_ACTIVE
    && self.range_pattern == RangePattern.One
{
    VEIN_ACTIVE = true;

    var vein = vein_water_collect(target_pos.x, target_pos.y, live_item.prototype.quality);
    var cost = abs(live_item.prototype.stamina_cost * ARI.stamina_costs_modifier);
    var budget = cost > 0 ? floor(ARI.get_stamina() / cost) - 1 : array_length(vein);

    for (var vi = 0; vi < array_length(vein) && vi < budget; vi++) {
        watering_can(vein[vi]);
    }

    VEIN_ACTIVE = false;
}
"""

PICK_SPREAD = """
//
// Spread the swing across connected rock of the same kind.
//
// Uncharged swings only, for the same reason as watering: a charged pickaxe
// already sweeps an area of its own.
//
// Unlike watering, pick_axe() charges its stamina synchronously the moment it
// returns, so ARI.get_stamina() is accurate as we go and can simply be checked
// before each rock.
//
if pick_result == PickResult.Rock && SETTINGS.get("vein_mining") && !VEIN_ACTIVE
    && self.range_pattern == RangePattern.One
{
    VEIN_ACTIVE = true;

    var vein = vein_pick_collect(
        target_pos.x,
        target_pos.y,
        self.live_item.prototype.quality,
        vein_pick_target_id
    );
    var step = self.live_item.prototype.stamina_cost * ARI.stamina_costs_modifier;

    for (var vi = 0; vi < array_length(vein); vi++) {
        //
        // A single swing's cost is not the whole bill. With Instant Tools
        // installed each rock also charges for the swings it skipped, so budget
        // for the worst case - ceil(hitpoints / damage) - before committing.
        // Without that mod this merely stops a little early, which is the safe
        // direction to be wrong in.
        //
        var vein_ni = GRID.try_node_index_for_cell(vein[vi].x, vein[vi].y);
        var vein_swings = 1;
        if vein_ni != undefined && GRID.node_parent[vein_ni] != undefined {
            var vein_damage = self.live_item.prototype.damage;
            if vein_damage > 0 {
                vein_swings = ceil(GRID.node_parent[vein_ni].hitpoints / vein_damage);
            }
        }

        if ARI.get_stamina() + (step * vein_swings) < 0 {
            break;
        }

        pick_axe(vein[vi], doppel);
    }

    VEIN_ACTIVE = false;
}
"""




def _patches(max_tiles):
    return {
        WATER: [(APPEND, block(WATER_HELPER.replace("__MAX__", str(max_tiles))))],
        PICK: [(APPEND, block(PICK_HELPER))],
        FSM: [
            (WATER_ANCHOR,
             "                    };\n"
             + block(WATER_SPREAD, " " * 20)
             + "                } else {\n"
               "                    set_rumble(RumbleKind.ToolInvalid);\n"
               "                }\n"
               "            }\n"),
            (PICK_CALL, block(CAPTURE, " " * 16) + PICK_CALL),
            (PICK_ANCHOR, PICK_ANCHOR + block(PICK_SPREAD, " " * 16)),
        ],
        SETTINGS: [
            (SETTINGS_ANCHOR,
             SETTINGS_ANCHOR
             + block("vein_watering: true,\nvein_mining: true,\n"
                     "vein_water_any_crop: false,\nvein_mine_any_rock: false,",
                     " " * 8)),
        ],
        MENU: [
            (MENU_ANCHOR,
             block('self.checkbox("vein_watering");\n'
                   'self.checkbox("vein_water_any_crop");\n'
                   'self.checkbox("vein_mining");\n'
                   'self.checkbox("vein_mine_any_rock");', " " * 8)
             + MENU_ANCHOR),
        ],
        LOCAL: [
            (APPEND, block('vein_watering = "Vein Watering"\n'
                           'vein_water_any_crop = "Vein Watering: Any Crop"\n'
                           'vein_mining = "Vein Mining"\n'
                           'vein_mine_any_rock = "Vein Mining: Any Rock"',
                           toml=True)),
        ],
    }




def patches(mk, opt):
    return _patches(opt["max"])
