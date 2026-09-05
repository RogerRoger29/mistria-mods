# Crop Labels

**Hold `F`** and the crop you're pointing at shows what it is and how many days
until harvest - at any distance, not just what's in reach.

The key is a **real, rebindable control**. It registers a new "Show Crop Labels"
action that appears in *Settings > Controls* with everything else, so you can
change it in game — no re-patching.

The game gives you no way to identify a plant already in the ground — the
grow-time tooltip only appears on seeds you're *holding* — so a row of young
stems stays a mystery until it's grown. This fixes that.

## Install / uninstall

```bash
python mistria-mods/install.py status
```

```bash
python mistria-mods/install.py apply crop-labels
```

```bash
python mistria-mods/install.py remove crop-labels
```

`--remove` restores the original code byte-for-byte. First `--apply` saves a
backup as `assets.pre-crop-labels.zip`.

## Tuning

| Option | Default | Meaning |
| --- | --- | --- |
| `--key` | `F` | The **default** binding only. Rebind in game afterwards. Your bindings leave F H V X Y Z U free. |

```bash
python mistria-mods/install.py apply crop-labels --key V
```

## What it reads

- **Name** comes from the crop's harvest item, so it's the same localized name
  you'd see in your inventory.
- **Days left** counts against the crop's growth table.
- **Regrowing crops are handled properly.** After a crop has fruited once it
  follows a shorter post-harvest schedule; the countdown switches to that table
  rather than reporting the original grow time. A strawberry that's already
  fruited says 3 days, not 5.
- A crop that's ready says `ready`.

The label is drawn on the same tooltip card the map name labels use, with the
same `Standard` text palette.

## How it works

The label is built from **Anchor nodes**, not raw draw calls, and is driven from
`obj_ari`'s `step_end`. It follows `obj_ari.cell_select`, the cell you're
currently aiming at, resolved to the plant's parent cell so pointing anywhere in
a 2×2 crop works. Anchor lays out in GUI space, which is 1:1 with the camera
view, so the world position converts by subtracting the camera origin.

### Two things learned the hard way

**`draw_text()` does not exist in this engine.** It appears in the shipped GML,
but only inside debug objects that never run in a release build. Calling it
crashes. The runner's text API offers `draw_text_with_color(...)` instead — check
`mistria::runner::api::text::*` in the executable, not the source, for what's
real.

**Raw world-space text inherits the last bound LUT.** Even with the correct
function, the label came out red, because Anchor sets a shader LUT for its own
text pass and a raw draw picks up whatever was left. Using Anchor nodes sidesteps
the GPU state entirely and gives the card styling for free.

### Registering a real control

Adding a rebindable action means touching four places, and two of them are
load-bearing:

| File | Change |
| --- | --- |
| `InputUtils.gml` | New `ShowCropLabels` member, added **immediately before `LEN`** so no existing input id shifts |
| `InputUtils.gml` | A case in `input_id_to_input_category()` |
| `Settings.gml` | A case in `default_bindings_for_input_id()` |
| `misc_local.toml` | `input_show_crop_labels` — the label the Controls menu displays |

Both of those switches end in `impossible(...)`, so a new input id that isn't
added to **both** crashes the game the moment it's looked up.

No settings migration is needed: `decode_binding()` falls back to the default
whenever a binding is missing from your saved file, so an existing
`settings.json` picks up `F` on its own.

## Notes

- **Saves are untouched.** This only reads and draws.
- Composes with the other mods here; it's the only one touching `obj_ari.gml`
  and `Crops.gml`.
- MOMI may wipe this if it rebuilds `assets.zip`. Re-run `--apply` afterwards.
