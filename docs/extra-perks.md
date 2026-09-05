# Extra Perks

Three new skill perks, chosen to fill gaps the game's own 169 perks leave open.

| Perk | Skill | Effect |
| --- | --- | --- |
| **Pathfinder** | Combat, tier 5 (200 essence) | Monsters count **double** toward revealing the ladder down |
| **Curator's Eye** | Archaeology, tier 5 (200 essence) | Museum donations grant **50% more Renown** |
| **Well Spring** | Farming, tier 5 (205 essence) | Water Sprite Statues reach **one tile further** in every direction |

## Why these three

Across all 169 shipped perks, not one mentions the museum, donations, renown,
quests, festivals, letters, spells, sleep, sprinklers or the mine ladder. These
take three of those gaps.

They also aim at real friction:

- **Pathfinder** — the ladder only appears once you've cleared a random 25–75%
  of the floor, and monsters are worth the same as a rock while costing **no
  stamina at all**. This makes fighting the actual descent strategy rather than
  a sideline.
- **Curator's Eye** — Renown is what raises your maximum stamina (+20 per rank),
  and donating is otherwise a slow trickle toward it.
- **Well Spring** — Water Sprite Statues are the only watering automation in the
  game, and nothing improves them.

## How it works

`Perk` is generated from `perks.toml`, so declaring a perk there creates the
`Perk.X` constant on its own. The skill-menu TOML puts it in a tree, and a few
lines of GML give it an effect:

| File | Hook |
| --- | --- |
| `DungeonRunner.gml` | `on_monster_destroy` — adds the extra ladder points |
| `RenownUtils.gml` | `renown_entry_value`, the single place every renown source is valued |
| `EndDay.gml` | the sprinkler's `range`, in grid cells |

Tier 5 had room in all three trees (combat had 3 of 4 filled, archaeology and
farming only 1), and mining already renders a full row of 4, so the layout is
proven.

Icons are **reused** from existing perks — the texture atlases are prebuilt, so
no new sprite can be added. Curator's Eye borrows the museum-quality icon and
Well Spring the well-watered one, both thematically close.

## Notes

- Perks are bought with essence in the skills menu like any other.
- Removing this mod removes the perks. If you had already bought one, the game
  no longer knows that perk exists — buy back into something else.
- Everything else about this mod is data; only the three effect hooks are code.
