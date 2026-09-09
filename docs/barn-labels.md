# Barn Labels

Point at one of your animals and a card above it shows its name, its hearts
out of ten, and whether it has been fed and petted today:

```
  Clover   Hearts 7/10
    Fed - Not petted
```

On a controller the card follows the nearest animal within a couple of tiles
of Ari. Words rather than coloured ticks, so it reads with no colour vision.

Toggle: Settings → Accessibility → "Barn Labels" (on by default).

## Why

The journal's Animals tab already keeps these three facts, with a fed tick
and a petted tick per animal, and they are the three things the game's
nightly check judges every animal on: unfed, unpetted, or left outside costs
heart points, and a happy day earns them (more with Close Bond). The
information is exactly what you want while standing in the barn, and exactly
when you don't want to open the journal.

## Options

| Option | Default | Meaning |
| --- | --- | --- |
| `--reach` | `32` | On a controller, how far from Ari (in pixels; a tile is 8) the nearest animal is labelled. |

```bash
python mistria-mods/install.py apply barn-labels --reach 48
```

## How it works

- Driven from `obj_ari`'s `step_end`, the same four-line anchor Crop Labels,
  Daily Checklist, Ladder Progress and Shovel Sense hang off; each inserts
  immediately after it, so they survive each other in any order.
- With a mouse the target is `instance_position(mouse_x(), mouse_y(),
  obj_player_animal)`; on a controller, `instance_nearest` from Ari, within
  the reach option.
- The card is the Crop Labels card: a nine-slice tooltip box and a text node
  on the vitals HUD's canvas, sized by `measure()`, placed in GUI space just
  above the animal's `bbox_top`. Raw world-space text would inherit whatever
  LUT the previous shader pass left bound; Anchor owns that state.
- The facts come straight off the animal's data: `name` (a plain string the
  game generated, so `set_text`), `heart_points` through the game's own
  `points_to_animal_heart_level`, `has_eaten` and `has_been_pat`.
- Nothing is written anywhere. Remove the mod and nothing remains.

## Files touched

| File | Change |
| --- | --- |
| `AnimalUtils.gml` | the helpers, appended |
| `obj_ari.gml` | one call in `step_end` |
| `Settings.gml` | the `barn_labels` default |
| `SettingsMenu.gml` | the Accessibility checkbox |
| `misc_local.toml` | the labels, mirrored into every language table |
