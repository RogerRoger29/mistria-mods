"""Nearby Affection - a small Fields of Mistria mod."""

from ..patcher import Markers

SLUG = "nearby_affection"
NAME = "Nearby Affection"
SUMMARY = "Bystanders within eight tiles gain a little affection when you talk to or gift someone."
DETAILS = """When you talk to a villager or give them a gift, every villager you have met who is standing nearby (about eight tiles) also gains a little affection, once each per day, with a small heart bubble over their head. It goes through the game's own heart system, so level-ups, sparkles and jingles happen exactly as they normally would. Caldarus and Seridia are skipped below six hearts, matching the game's own rule for them. Nothing is written to your save."""
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "radius": (int, 64, 'how close a bystander must be, in pixels (8px = 1 tile)'),
    "points": (int, 2, 'heart points per bystander per day'),
    "popup": (bool, True, 'heart thought-bubble over bystanders'),
}

def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}

#!/usr/bin/env python3
"""
Nearby Affection - a small Fields of Mistria mod.

When you talk to or give a gift to an NPC, every other NPC standing near you
also gains a little affection (once per bystander per day).

Fields of Mistria runs its GML through the embedded `fabricator` VM, compiling
the .gml source shipped inside assets.zip at startup. So this mod works by
editing that source in place. Every insertion is wrapped in NEARBY_AFFECTION
markers, which makes the patch idempotent and cleanly removable.

Usage:
    python nearby_affection.py --apply
    python nearby_affection.py --apply --radius 80 --points 3
    python nearby_affection.py --remove
    python nearby_affection.py --status
"""



NPC = "assets/gml/scripts/GameplaySystems/NPCs/Npc.gml"
NPCDB = "assets/gml/scripts/GameplaySystems/NPCs/NpcDatabase.gml"
T2R = "assets/gml/scripts/GameplaySystems/T2r.gml"






# ---------------------------------------------------------------- the patches

POPUP_GML = """
        //
        if !obj.bark_emitter.is_barking() {
            obj.bark_emitter.emit(BarkId.Heart, BarkType.Thought);
        }
"""


def helper_function(radius, points, popup):
    body = """
//
// Nearby Affection: award a small amount of affection to every NPC standing
// close to `origin_id` when the player talks to or gifts them. Each bystander
// can pick this up once per day; the flag is reset by npcs_on_new_day().
//
function nearby_affection_on_interact(origin_id) {
    static RADIUS = __RADIUS__;
    static POINTS = __POINTS__;

    var origin_obj = npc_id_to_gm_obj_id(origin_id);
    if !instance_exists(origin_obj) {
        return;
    }

    var origin_x = origin_obj.x;
    var origin_y = origin_obj.y;

    for (var i = 0; i < NpcId.LEN; i++) {
        if i == origin_id {
            continue;
        }

        var bystander = NPCS[i];
        if !bystander.nearby_affection_flag {
            continue;
        }

        //
        // Strangers have no opinion of you. Curious Neighbours gates on this
        // too; without it a villager you have never been introduced to gains
        // hearts and pops a thought bubble.
        //
        if !bystander.has_met() {
            continue;
        }

        //
        if (i == NpcId.Caldarus || i == NpcId.Seridia) && bystander.heart_level() < 6 {
            continue;
        }

        var obj = npc_id_to_gm_obj_id(i);
        if !instance_exists(obj) {
            continue;
        }

        if point_distance(obj.x, obj.y, origin_x, origin_y) > RADIUS {
            continue;
        }

        bystander.nearby_affection_flag = false;
        bystander.add_heart_points(POINTS);
__POPUP__    }
}
"""
    body = body.replace("__RADIUS__", str(radius)).replace("__POINTS__", str(points))
    # The bark bubble is the same one pets/animals show when petted. Skip it if the
    # NPC is already barking, so we never stomp a chat or cutscene bubble.
    body = body.replace("__POPUP__", POPUP_GML.lstrip("\n") if popup else "")
    return block(body)


def _patches(radius, points, popup):
    """Return {zip_path: [(anchor, replacement), ...]}."""
    return {
        NPC: [
            # 1. per-day bystander flag lives on the Npc struct. It is
            #    deliberately not serialized, so saves stay loadable by an
            #    unmodded game.
            (
                "    self.times_spoken_today = 0;\n"
                "    self.talk_flag = true;\n",
                "    self.times_spoken_today = 0;\n"
                + block("self.nearby_affection_flag = true;", "    ")
                + "    self.talk_flag = true;\n",
            ),
            # 2. gifting an NPC also pleases the bystanders.
            (
                "        self.add_heart_points(hearts);\n",
                "        self.add_heart_points(hearts);\n"
                + block("nearby_affection_on_interact(self.id);", "        "),
            ),
            # 3. the helper itself, appended at file scope.
            (APPEND, helper_function(radius, points, popup)),
        ],
        NPCDB: [
            (
                "        npc.times_spoken_today = 0;\n"
                "        npc.gift_flag = true;\n",
                "        npc.times_spoken_today = 0;\n"
                + block("npc.nearby_affection_flag = true;", "        ")
                + "        npc.gift_flag = true;\n",
            ),
        ],
        T2R: [
            (
                "                npc.times_spoken_today += 1;\n",
                "                npc.times_spoken_today += 1;\n"
                + block("nearby_affection_on_interact(npc_id);", "                "),
            ),
        ],
    }




def patches(mk, opt):
    return _patches(opt["radius"], opt["points"], opt["popup"])
