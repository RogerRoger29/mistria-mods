"""Curious Neighbours - a small Fields of Mistria mod."""

from ..patcher import Markers

SLUG = "curious_neighbours"
NAME = "Curious Neighbours"
SUMMARY = "Villagers you walk past react to the item you are carrying with their true gift opinion."
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {
    "radius": (int, 40, 'how close you must walk, in pixels'),
}

def defaults():
    return {k: v[1] for k, v in OPTIONS.items()}

#!/usr/bin/env python3
"""
Curious Neighbours - a small Fields of Mistria mod.

Walk near a villager while carrying something and they react to what you are
holding, with a thought bubble over their head:

    heart       they would love it as a gift
    cute face   they would like it
    ellipses    they would rather you didn't
    sweat drop  they would hate it
    (nothing)   they don't care either way

It turns gift discovery into something you notice in passing instead of
something you look up. Only villagers you have actually met will react.

Like the Nearby Affection mod, this edits the GML that the game compiles out of
assets.zip at startup. Insertions are wrapped in CURIOUS_NEIGHBOURS markers, so
the patch is idempotent, removable, and composes with other marker-based mods.

Usage:
    python curious_neighbours.py --apply
    python curious_neighbours.py --apply --radius 32
    python curious_neighbours.py --remove
    python curious_neighbours.py --status
"""



NPC = "assets/gml/scripts/GameplaySystems/NPCs/Npc.gml"
PARNPC = "assets/gml/objects/system/parents/par_NPC.gml"



# Desire -> bubble. Neutral deliberately shows nothing, so the bubbles stay
# meaningful instead of firing at every villager for every item.
DESIRE_BARKS = [
    ("Loved", "Heart"),
    ("Liked", "CuteFace"),
    ("Disliked", "Ellipses"),
    ("Hated", "SweatDrop"),
]




# ---------------------------------------------------------------- the patches

def helpers_gml():
    cases = "\n".join(
        "        case Desire.%s: return BarkId.%s;" % (d, b) for d, b in DESIRE_BARKS
    )
    return block("""
//
// Curious Neighbours: would `npc` want `item` as a gift? This mirrors the
// desire calculation inside Npc.give_gift(), including the two hand-written
// special cases, but without any of its side effects.
//
function curious_desire_for(npc, item) {
    if item.item_id == ItemId.VoidNewt {
        return npc.id == NpcId.Juniper ? Desire.Loved : Desire.Disliked;
    }

    if item.item_id == ItemId.VoidCake {
        return npc.id == NpcId.Eiland ? Desire.Loved : Desire.Disliked;
    }

    if item.infusion == Infusion.Loveable || npc.prototype.loved_gifts.contains(item.item_id) {
        return Desire.Loved;
    }

    if item.infusion == Infusion.Likeable || npc.prototype.liked_gifts.contains(item.item_id) {
        return Desire.Liked;
    }

    if item.item_id == npc.prototype.hated_gift {
        return Desire.Hated;
    }

    if item.prototype.tags.contains_any_value_from(npc.prototype.disliked_gift_tags) {
        return Desire.Disliked;
    }

    return Desire.Neutral;
}

//
// Which bubble to show for that opinion, or undefined to stay quiet.
//
function curious_bark_for(npc, item) {
    switch curious_desire_for(npc, item) {
__CASES__
        default: return undefined;
    }
}
""".replace("__CASES__", cases))


def curiosity_handler(radius):
    return block("""
self.curious_last_item = undefined;

//
// Curious Neighbours: react to whatever the player is carrying past us. We
// only fire when the held item changes, so standing around does not spam
// bubbles, and we never speak over an existing bark, a chat, or a cutscene.
//
function handle_curiosity() {
    static RADIUS = __RADIUS__;

    if self.bark_emitter.is_barking() || self.chat_partner != undefined || MIST.running {
        return;
    }

    if !instance_exists(obj_ari) {
        return;
    }

    var item = ARI.held_item();
    if item == undefined || point_distance(self.x, self.y, obj_ari.x, obj_ari.y) > RADIUS {
        //
        self.curious_last_item = undefined;
        return;
    }

    if self.curious_last_item == item.item_id {
        return;
    }
    self.curious_last_item = item.item_id;

    var npc = NPCS[gm_obj_id_to_npc_id(object_index)];
    if !npc.has_met() {
        return;
    }

    var bark = curious_bark_for(npc, item);
    if bark != undefined {
        self.bark_emitter.emit(bark, BarkType.Thought);
    }
}
""".replace("__RADIUS__", str(radius)), "            ")


def _patches(radius):
    return {
        NPC: [
            (APPEND, helpers_gml()),
        ],
        PARNPC: [
            # Defined alongside the game's own handle_chatting/handle_thinking,
            # inside the Create event, so it shares their scope.
            (
                "            function handle_chatting() {\n",
                curiosity_handler(radius) + "            function handle_chatting() {\n",
            ),
            # ... and driven from the same place they are.
            (
                "            self.handle_chatting();\n"
                "            self.handle_thinking();\n",
                "            self.handle_chatting();\n"
                "            self.handle_thinking();\n"
                + block("self.handle_curiosity();", "            "),
            ),
        ],
    }




def patches(mk, opt):
    return _patches(opt["radius"])
