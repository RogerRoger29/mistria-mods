"""Three new skill perks, filling gaps nothing else covers.

Nothing among the game's 169 perks touches the museum, renown, sprinklers or
the mine ladder. These three do, each slotting into a tier 5 that has room and
each hooking a single line of the game's own code.

  Pathfinder     (Combat)       monsters count double toward the ladder
  Curator's Eye  (Archaeology)  museum donations grant more renown
  Well Spring    (Farming)      Water Sprite Statues reach further

`Perk` is generated from perks.toml, so declaring a perk there creates the
Perk.X constant; the skill-menu TOML places it in the tree; the GML gives it an
effect. Icons are reused from existing perks - new sprites cannot be added
because the texture atlases are prebuilt.
"""

from ..patcher import Markers

SLUG = "extra_perks"
NAME = "Extra Perks"
SUMMARY = "Three new skill perks: Pathfinder, Curator's Eye and Well Spring."
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {}


def defaults():
    return {}


PERKS = "assets/fiddle/perks.toml"
TREE_COMBAT = "assets/fiddle/ui/skill_menu/combat.toml"
TREE_ARCH = "assets/fiddle/ui/skill_menu/archaeology.toml"
TREE_FARM = "assets/fiddle/ui/skill_menu/farming.toml"

DUNGEON = "assets/gml/scripts/GameplaySystems/Dungeon/DungeonRunner.gml"
RENOWN = "assets/gml/scripts/GameplaySystems/Player/RenownUtils.gml"
ENDDAY = "assets/gml/scripts/GameplaySystems/Cycle/EndDay.gml"

# --- perk definitions --------------------------------------------------------

PERK_DEFS = '''[pathfinder]
	name = "Pathfinder"
	description = "Monsters defeated in the Mines count double toward revealing the ladder down."
	value = 2

[curators_eye]
	name = "Curator's Eye"
	description = "Donations to the Museum grant 50% more Renown."
	value = 1.5

[well_spring]
	name = "Well Spring"
	description = "Water Sprite Statues reach one tile further in every direction."
	value = 1
'''

# Tier 5 sits at 200-210 essence in every tree, so these match their neighbours.
TREE_COMBAT_ENTRY = '''[[tier_5]]
	perk = "pathfinder"
	essence = 200
	icon = "spr_ui_skills_combat_icon_sonic_boom"
'''

TREE_ARCH_ENTRY = '''[[tier_5]]
	perk = "curators_eye"
	essence = 200
	icon = "spr_ui_skills_archaeology_icon_museum_quality_iii"
'''

TREE_FARM_ENTRY = '''[[tier_5]]
	perk = "well_spring"
	essence = 205
	icon = "spr_ui_skills_farming_icon_well_watered"
'''

# --- anchors and effects -----------------------------------------------------

LADDER_ANCHOR = """    function on_monster_destroy(xx, yy) {
        self.ladder_score += DUNGEON.biomes[DUNGEON_BIOME].monster_element_points;
"""

LADDER_EFFECT = """
//
// Pathfinder. The base points were already added just above, so only the
// difference goes on here - value 2 means one extra helping, i.e. double.
//
if ARI.perk_active(Perk.Pathfinder) {
    self.ladder_score += DUNGEON.biomes[DUNGEON_BIOME].monster_element_points
        * (ARI.perk_value(Perk.Pathfinder) - 1);
}
"""

RENOWN_ANCHOR = """        case RenownEntryType.MuseumDonation:
            //
            return ITEM_PROTOTYPES[entry.item_id].value.renown ?? 5;
"""

RENOWN_EFFECT = """
//
// Curator's Eye. renown_entry_value() is the single place every renown source
// is valued, so boosting the donation case here covers every route a donation
// can take to the ledger.
//
if ARI.perk_active(Perk.CuratorsEye) {
    return round((ITEM_PROTOTYPES[entry.item_id].value.renown ?? 5)
        * ARI.perk_value(Perk.CuratorsEye));
}
"""

SPRINKLER_ANCHOR = "                    var range = sprinkler.prototype.sprinkler * 2;\n"

SPRINKLER_EFFECT = """
//
// Well Spring. `range` counts grid cells and a crop occupies two of them, so a
// perk value of 1 tile is worth 2 cells in each direction.
//
if ARI.perk_active(Perk.WellSpring) {
    range += ARI.perk_value(Perk.WellSpring) * 2;
}
"""


def patches(mk, opt):
    return {
        # Declaring the perk is what creates the Perk.X constant.
        PERKS: [(mk.APPEND, mk.block(PERK_DEFS, toml=True))],

        # Placing it in a tier is what makes it buyable.
        TREE_COMBAT: [(mk.APPEND, mk.block(TREE_COMBAT_ENTRY, toml=True))],
        TREE_ARCH: [(mk.APPEND, mk.block(TREE_ARCH_ENTRY, toml=True))],
        TREE_FARM: [(mk.APPEND, mk.block(TREE_FARM_ENTRY, toml=True))],

        # And these give them effects.
        DUNGEON: [(LADDER_ANCHOR,
                   LADDER_ANCHOR + mk.block(LADDER_EFFECT, " " * 8))],
        RENOWN: [(RENOWN_ANCHOR,
                  "        case RenownEntryType.MuseumDonation:\n"
                  "            //\n"
                  + mk.block(RENOWN_EFFECT, " " * 12)
                  + "            return ITEM_PROTOTYPES[entry.item_id].value.renown ?? 5;\n")],
        ENDDAY: [(SPRINKLER_ANCHOR,
                  SPRINKLER_ANCHOR + mk.block(SPRINKLER_EFFECT, " " * 20))],
    }
