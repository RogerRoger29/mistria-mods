# Instant Tools

Axe fells a tree in one swing. Pickaxe breaks a rock in one swing. **You still pay
the stamina it would have cost to do it the long way.** The grind goes, the cost
stays.

Toggle it any time in **Settings → Accessibility** ("Instant Tools").

## Install / uninstall

```bash
python mistria-mods/install.py status
```

```bash
python mistria-mods/install.py apply instant-tools
```

```bash
python mistria-mods/install.py remove instant-tools
```

`--remove` restores the original code byte-for-byte. On first `--apply` the script
saves a copy of your archive as `assets.pre-instant-tools.zip`.

## Rules it follows

- Stamina is exact: `ceil(hitpoints / damage)` swings, charged at your tool's normal
  per-swing cost, including your stamina-cost modifier.
- **If you can't afford the whole break, you get a normal single hit instead.** No
  surprise faints. Chip away and come back to it.
- **Tool quality gating is untouched.** A starter axe still can't fell a hardwood
  tree — that check is separate from hitpoints, so upgrades still matter.
- Only *your* swings are affected. See below.

## How it works

Trees and rocks are hitpoints; tools have damage. Both `Chop.gml` and `Pick.gml`
reduce to the same line:

```
node.hitpoints -= min(damage, node.hitpoints);
```

The mod inserts a call just above it that returns boosted damage — enough to finish
the node — after billing the stamina for the swings you skipped. The caller charges
one swing itself immediately afterwards, so the helper only bills the *others*.

### The part that needed care

`chop_node()` and `pick_node()` aren't only called by you. Tarball explosions,
monsters, and cutscene scripts call them too. Patching those functions
unconditionally would have billed **your** stamina when a monster smashed a rock.

So the player's two call sites in `AriFsm.gml` — and only those — raise a global
flag around their call:

```
INSTANT_TOOLS_ACTIVE = true;
var success = chop_node(...);
INSTANT_TOOLS_ACTIVE = false;
```

The helper does nothing unless that flag is up. The flag is declared at file scope
following the game's own `MAP_HUBS` idiom.

## Known side effect

Essence is granted **per swing** (`ARI.gain_essence` sits next to the stamina
charge). Fewer swings therefore means less essence from felling the same tree. The
stamina economy is preserved exactly as asked; the essence economy is not. Say the
word if you'd like the skipped swings' essence granted too.

## Notes

- **Saves are untouched.** This mod changes only in-the-moment behaviour.
- Composes with the other mods here — distinct markers, and it's the only one
  touching `Chop.gml`, `Pick.gml`, and `AriFsm.gml`.
- As with any `assets.zip` patch, MOMI may wipe this if it rebuilds the archive.
  Re-run `--apply` afterwards.
