# Vein Tools

**Watering:** water one plant and every connected plant of the same type gets
watered. **Mining:** hit one rock and your swing lands on every connected rock of
the same kind.

Four toggles in **Settings → Accessibility**, so nothing here needs re-patching
to change:

| Toggle | Default | What it does |
| --- | --- | --- |
| Vein Watering | on | water spreads across the patch |
| Vein Watering: Any Crop | off | drop the same-crop requirement |
| Vein Mining | on | a swing spreads across the vein |
| Vein Mining: Any Rock | off | drop the same-rock requirement |

Each tile costs its own stamina and rolls its own perks, so **Refreshing still
refunds energy** and **Bountiful still drops free seeds**, exactly as if you'd
done them one at a time.

## Install / uninstall

```bash
python mistria-mods/install.py status
```

```bash
python mistria-mods/install.py apply vein-tools
```

```bash
python mistria-mods/install.py remove vein-tools
```

`--remove` restores the original code byte-for-byte. `--max` caps tiles per swing
(default 200) as a runaway guard.

## Rules it follows

- **Same object only** — unless you turn that off. By default cabbage never
  spreads into the turnips and copper ore never spreads into stone. The two
  "Any" toggles replace that test with a category test, so a vein runs through
  everything connected: a mixed bed waters in one go, and a cave wall mines
  through stone, ore, seams and boulders alike. See below.
- **Connected only**, from the tile you actually hit. Watering spreads in the
  four cardinal directions; **mining also spreads diagonally**, because ore
  runs corner-to-corner through a cave as often as it runs edge-to-edge, and
  a cardinal-only fill kept stopping halfway along a seam.
- **Already-watered plants still conduct.** A wet plant mid-row doesn't sever the
  patch — it's skipped, not treated as a wall.
- **The pickaxe quality gate is preserved.** A weak pick still bounces off the
  rocks it always bounced off, and those rocks aren't collected.
- **It stops when you can't pay.** Neither tool will faint you.
- Watering only spreads when the tile you aimed at was waterable; mining only
  spreads on a rock (not dig sites or furniture).
- **Uncharged swings only.** See below.

## Tool tier is the upgrade path

| Tool tier | Vein reach |
| --- | --- |
| Worn (tier 1) | 8 tiles |
| Copper | 16 |
| Iron | 32 |
| Silver | 64 |
| Gold | 128 |
| Mistril | 200 (`--max`) |

This matters because of a quirk in the game: hoes and watering cans have **no
damage stat**, so upgrading them never made a swing cheaper. All a higher tier
bought was a wider *charged* swing area (tier 1 = 1 tile, tier 2 = 1x3, up to
tier 6 = 6x9) — and since stamina is charged per tile, the same plot cost the
same energy either way.

With vein watering that upgrade would have been worth nothing at all, since the
vein already covered the patch. Tying reach to tier gives farm tools a real
upgrade path again, and it stacks on the pickaxe's existing damage gain rather
than replacing it.

### Why uncharged swings only

A charged swing applies to its N targets in sequence, but watering resolves
inside an animation chain, so targets 2..N still look unwatered when the loop
reaches them. Each would kick off another full patch spread. No double stamina
charge — already-watered tiles no-op — but a 6x9 can over a large patch would
queue thousands of redundant animation effects.

So each mechanism owns its case: an **uncharged** swing veins across the patch
(as far as your tier allows), a **charged** swing uses the tool's own area
pattern, which is still the better tool on mixed plots where a vein won't cross
between different crops. The same guard is on mining, for the same reason.

### One caveat on mining

Vein mining applies **one swing** to every rock in the vein. With **Instant
Tools** installed that's a clean break for each. Without it, they all take a
swing's worth of damage together and big rocks need several passes.

## How it works

It never reimplements watering or mining. `watering_can()` and `pick_axe()` in
`AriFsm.gml` are both self-contained and take a target position, so the mod
flood-fills to find the vein and then calls that same function once per tile.
Stamina, XP, essence, perks, animation and sound all follow naturally, with no
second copy of the rules to drift out of sync.

Details that needed care:

- **Recursion.** Each spawned call would try to spread again, so a global
  `VEIN_ACTIVE` guard means only the outermost call expands.
- **Mining destroys its target before we look at it.** `pick_node()` removes the
  rock synchronously, so by the time the spread code runs the cell you aimed at
  is already empty and a flood fill seeded from it finds nothing. The rock's
  identity is therefore captured *before* the call and passed into the fill.
  (Watering has no such problem — it defers into an animation chain and never
  removes the crop object.) With Instant Tools on, every rock dies on the first
  swing, so this bug hid the feature completely rather than partially.
- **Two different stamina timings.** Watering resolves inside an animation chain,
  so `ARI.get_stamina()` does *not* fall as the loop runs — the affordable count
  has to be computed up front. Mining charges synchronously, so there the balance
  can simply be checked before each rock. Getting this backwards would either
  over-commit or stop short.
- **Mixed object sizes.** Crops are 2×2; rocks are 2×2, 4×4 or 6×6. All are
  even-aligned, so the fill steps by 2 and dedupes on each object's parent cell —
  otherwise a 4×4 rock would be collected four times over.

## Adding the settings

A toggle needs three coordinated pieces:

| File | Change |
| --- | --- |
| `Settings.gml` | `vein_watering` / `vein_mining` defaults |
| `SettingsMenu.gml` | Two `self.checkbox(...)` rows in the accessibility category |
| `misc_local.toml` | The labels the menu displays |

New settings don't need a migration — a key absent from your `settings.json`
falls back to the default here.

## Notes

- **Saves are untouched.**
- Composes with the other mods; it shares `AriFsm.gml` with Instant Tools without
  overlapping.
- MOMI may wipe this if it rebuilds `assets.zip`. Re-run `--apply` afterwards.

## Ignoring type

The two "Any" toggles change **what conducts**, and nothing else.

Normally the object id has to match all the way along the vein. With the toggle
on, it is the *category* that has to match. Category is still the boundary, so a
crop vein can never wander into rock and a rock vein never into crops — it is
the distinction between cabbage and turnip, or between stone and mistril, that
stops mattering.

Everything else still applies per tile:

- **The pickaxe quality gate survives.** Connectivity and worth-acting-on are
  separate tests, so an "any rock" vein spreading past a mistril node still
  won't collect it with a copper pick — it is skipped, exactly as it would be if
  you swung at it directly.
- **Stamina is still per tile**, and both halves still stop when you can't pay.
- **Perks still roll per tile.** Refreshing and Bountiful don't care how the
  vein was chosen.

Both default to **off**, because they widen behaviour that already works, and a
mixed bed suddenly costing four times the stamina is a surprise you should opt
into rather than discover.

The **tier cap matters much more with these on**. A mine floor is close to one
connected mass of rock once type stops separating it, so "any rock" is the case
the 8/16/32/64/128 reach limit was really there for — a worn pickaxe clears a
corner, a mistril one clears the room.

Watering stays orthogonal even here, so an "any crop" vein still won't jump
between rows that only touch at a corner. Mining stays diagonal.
