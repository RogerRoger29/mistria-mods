# Ladder Progress

Shows how close the current mine floor is to revealing its ladder down.

## Why this is worth having

The ladder **isn't hidden somewhere waiting to be found**. It does not exist
until you've cleared enough of the floor, and then it spawns wherever you made
the final break. Searching for it is wasted stamina.

The threshold is a fresh random **25–75% of the floor, rerolled every time**, so
without a readout there's no way to tell an unlucky floor from one you've barely
started. This puts the number on screen: `Ladder  7 / 14`.

## What moves the number

**Counts (1 point each):** small rocks, dirt rocks, every ore node and seam,
barrels, crates, boxes — and **monsters**.

**Doesn't count:** large rocks and boulders. The game explicitly excludes them,
so they cost you stamina for no progress at all.

Since killing a monster costs no stamina and is worth the same as a rock, the
readout usually tells you to go fight something.

## Install / uninstall

```bash
python mistria-mods/install.py status
```

```bash
python mistria-mods/install.py apply ladder-progress
```

```bash
python mistria-mods/install.py remove ladder-progress
```

Toggle it in **Settings → Accessibility** ("Ladder Progress"). `--x` / `--y`
move the readout if it collides with your HUD; it defaults to `3, 46`, just
below the vitals bars.

## How it works

The readout reads `DUNGEON_RUNNER.ladder_score` against `ladder_score_needed` —
the values the game already maintains. It shows only on ordinary mine floors,
hides in special rooms, and disappears once the ladder is out.

### Styling

It's built from Anchor nodes on the Vitals canvas (raw drawing inherits whatever
shader LUT was last bound and comes out mistinted; Anchor owns that state).

The visual follows the **HUD** idiom rather than the tooltip one, which matters:
a tooltip box is what this game uses for transient hover popups, and this is a
persistent readout. So it uses `spr_ui_hud_info_backplate_middle` — the same
nine-slice the info HUD stacks for essence and gold — with the mining skill icon
and a bare number. The game's own persistent readouts are all icon + number with
no words, which is why it says `7 / 14` rather than `Ladder 7 / 14`.

Layout is 4px lead-in, the 8px icon, a 3px gap, the text, then a 5px tail. The
backplate's nine-slice corners are 7x7, so the plate is floored at 16px tall for
them to render cleanly.

## Notes

- **Saves are untouched.** It only reads and draws.
- Shares `obj_ari`'s `step_end` hook with Crop Labels — both append their own
  call, so they interleave rather than collide.
- MOMI may wipe this if it rebuilds `assets.zip`. Re-run `--apply` afterwards.
