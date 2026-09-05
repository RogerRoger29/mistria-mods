# Big Rock Credit

Large rocks and boulders in the Mines count toward revealing the floor's ladder,
and count by their **size** rather than as a single object.

Toggleable in **Settings → Accessibility** — "Big Rock Credit".

## Install / uninstall

```bash
python mistria-mods/install.py status
```

```bash
python mistria-mods/install.py apply big-rock-credit
```

```bash
python mistria-mods/install.py remove big-rock-credit
```

## The problem

A mine floor hides its ladder until you have destroyed enough of the floor.
Every destructible thing carries a `ladder_candidate` flag, and only flagged
objects score.

Small rocks are flagged. Ore nodes and seams are flagged. Barrels, crates and
monsters are flagged. Every large rock in the game is **not**:

| Object | Footprint | Counts in vanilla |
| --- | --- | --- |
| `rock_stone_*` (small) | 2×2 | yes |
| `large_rock_stone_one` … `five`, `_upper` | 4×4 | **no** |
| `boulder_rock_stone` | 6×6 | **no** |

So the most expensive objects on the floor — the ones that eat the most swings
and the most stamina — move the ladder not one point. Clearing a big rock
actively costs you progress, because the stamina it takes is stamina you can no
longer spend on the small rocks that do count.

## What this changes

**Every rock counts.** Rocks are opted into `ladder_candidate` regardless of
size.

**Big rocks count for what they occupy.** A large rock covers the ground of four
small ones, so it is worth four; a boulder covers nine, so it is worth nine. The
base award happens as it does for any object, and this adds the difference:

```
extra = (size.x div 2) * (size.y div 2) - 1
```

The 8px grid puts every rock on an even-aligned footprint, so that division is
exact — 4×4 → 4 cells, 6×6 → 9 cells.

## Why size-weighted rather than one point each

The floor's threshold is a fraction of the number of candidate objects on it,
and each object is counted once when that total is computed. A boulder therefore
adds **1** to the requirement while paying out **9**. That asymmetry is the
point: a floor dense with big rocks becomes faster to clear rather than slower,
which is the opposite of vanilla and the reason for the mod.

If you would rather big rocks simply counted once each, like everything else,
delete the `AWARD_EFFECT` block from `mods/big_rock_credit.py` and re-apply —
the opt-in half stands on its own.

## Interaction with the other mods

**Instant Tools** pairs with this directly. One swing takes the boulder down,
charging the full stamina it would have cost, and the whole nine points land at
once.

**Vein Tools** spreads a pickaxe swing across connected same-type rock, and
since large rocks are all distinct object types a vein won't wander from small
stone into a boulder. They don't interfere.

**Ladder Progress** is the readout that makes this visible — the score jumps by
nine instead of nothing.

## Files touched

| File | Change |
| --- | --- |
| `Rocks.gml` | opt rocks into `ladder_candidate` |
| `GridUtils.gml` | award the extra points at the destroy site |
| `Settings.gml` | `big_rock_credit` default |
| `SettingsMenu.gml` | the Accessibility checkbox |
| `misc_local.toml` | its label |

The award hook reads `node.prototype.size` at the destroy site. `pick_node()`
clears the node out of the grid **synchronously**, but the local `node` variable
is still in scope there — the game's own next statement uses it — so the
prototype is still readable.
