"""The two finished perks the game never puts in a skill tree.

perks.toml defines 169 perks; the ten skill trees between them list 167. The two
left over are not stubs - both have a working implementation in the shipped GML,
and both already have artwork drawn for them. They are simply unreachable.

    gemini_season        Stable.gml                animals can bear twins
    ancient_inspiration  Ari.gml, CraftingMenu.gml weekly recipe inspiration

This mod only adds tree entries - no new code, and no new perk definitions.

Note on the count. An earlier version of this mod claimed five orphans and also
placed horsepower, harvest_horse and nice_ride. That was wrong: all three live in
`ui/skill_menu/mount.toml`, the "Mistmare" tree, which is reachable in game at
the horse statue in the Narrows once `repaired_horse_statue` is unlocked. It is
easy to miss because mount is not a Skill - `load_dragon_shrine_data()` calls
`try_string_to_skill("mount")`, gets undefined, and the shrine's Horse variant
returns level 1 instead of a skill level - so any tree list derived from the
Skill enum silently drops exactly that one. Deriving the list from the trees
themselves is the check that holds.
"""

from ..patcher import Markers

SLUG = "unreleased_perks"
NAME = "Unreleased Perks"
SUMMARY = "Two finished perks the game never put in a tree: Gemini Season and Ancient Inspiration."
LEGACY = []
markers = Markers(SLUG, legacy=LEGACY)
block = markers.block
APPEND = Markers.APPEND

OPTIONS = {}


def defaults():
    return {}


TREE_RANCH = "assets/fiddle/ui/skill_menu/ranching.toml"
TREE_SMITH = "assets/fiddle/ui/skill_menu/blacksmithing.toml"

# Each perk keeps the icon that was drawn for it, and lands in the tree its own
# artwork names. Essence costs match the 200-210 band the rest of tier 5 uses.
#
# FOUR PER TIER IS THE LIMIT - a row is centred across the whole backplate and
# the "Tier N" label sits at its left end, so a fifth icon slides under the
# label. Both of these tiers stay well inside that.

RANCH_ENTRIES = '''[[tier_5]]
	perk = "gemini_season"
	essence = 200
	icon = "spr_ui_skills_ranching_icon_gemini_season"
'''

SMITH_ENTRIES = '''[[tier_5]]
	perk = "ancient_inspiration"
	essence = 205
	icon = "spr_ui_skills_crafting_icon_ancient_inspiration"
'''


def patches(mk, opt):
    return {
        TREE_RANCH: [(mk.APPEND, mk.block(RANCH_ENTRIES, toml=True))],
        TREE_SMITH: [(mk.APPEND, mk.block(SMITH_ENTRIES, toml=True))],
    }
