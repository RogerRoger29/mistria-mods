# Shovel Sense

Hold the shovel and the ground gives itself away. Every undug dig site within
reach lets out an occasional puff of settling earth, and the first one to come
within a few tiles makes Ari notice it: a thought bubble with the archaeology
icon, a soft chime, and a nudge of rumble on a controller. Put the shovel away
and everything goes quiet again.

Toggle: Settings → Accessibility → "Shovel Sense" (on by default).

## Why it's built this way

Dig sites are 16-pixel mounds drawn in the same palette as the ground around
them, and the mines only offer a few per floor. A map marker or a HUD arrow
would find them, but it would also turn archaeology into waypoint-following.
This keeps the finding in the world: the earth moves, Ari reacts, and the cue
is tied to the tool you would use anyway. Both tells are motion and sound, so
they read with no colour vision at all.

The archaeology thought bubble, the dirt puffs (`spr_fx_poof1_dirt_once` and
`_2_`), the chime (`SoundEffects/NPCs/DialogSparkle`) and the rumble
(`RumbleKind.ItemCollect`) are all the game's own assets; nothing new is
drawn.

## Options

| Option | Default | Meaning |
| --- | --- | --- |
| `--radius` | `5` | Tiles within which Ari notices a dig site. |
| `--reach` | `12` | Tiles within which dig sites puff earth — roughly the screen. |
| `--no-shovel-only` | off | Sense all the time, whatever is in hand. |
| `--no-sound` | off | Skip the chime; the bubble, puffs and rumble stay. |

```bash
python mistria-mods/install.py apply shovel-sense --radius 8 --no-sound
```

## How it works

Everything runs from `obj_ari`'s `step_end`, on the same four-line anchor
Crop Labels, Daily Checklist and Ladder Progress hang off (each inserts
immediately after it, so they survive each other in any order). Every fifteen
frames, if the mod is on, no cutscene is running and the held item carries the
`shovel` tag — the exact test the fish trap uses for bait — the cells around
Ari are scanned for `ObjectId.DigSite` nodes:

- Dig sites are 2×2 nodes on even coordinates, so the scan steps by two and
  counts each site once, at its top-left. A dug site is `DigSiteDestroyed`
  and never matches.
- A site in reach gets a one-shot dirt puff with probability 1 in 8 per scan,
  so about every two seconds, jittered a few pixels so it never looks looped.
  The puff's depth is `get_instance_depth(bottom of the mound) - 1`, the
  renderer's own formula, so it draws just in front of the mound.
- The first site inside the notice radius that Ari has not noticed yet gets
  the bubble (only if she is not already barking), the chime and the rumble.
  "Noticed" is a runtime set keyed by room, dungeon floor, day and cell —
  nothing is written to the node, so nothing reaches the save, and a fresh
  day's dig site on the same cell counts as new.

At 12 tiles of reach the scan covers a 49×49 cell window four times a second;
on a 52×56-cell farm that is a few thousand array reads a second, well under
what one frame of the game's own grid work costs.

## Traps found building it

- `held_item()` returns `undefined` for an empty slot, so the tag test has to
  be guarded, as the fish trap's is.
- Node structs are serialized wholesale. Marking a node as "noticed" would
  have been the obvious design and would have left a trace in every save.
- `obj_node_renderer` has no step event, so a per-site effect loop would have
  meant adding one to every renderer in the game — thousands of instances for
  a handful of dig sites. Scanning from Ari is one instance's work.

## Files touched

| File | Change |
| --- | --- |
| `Digsite.gml` | the helpers, appended |
| `obj_ari.gml` | one call in `step_end` |
| `Settings.gml` | the `shovel_sense` default |
| `SettingsMenu.gml` | the Accessibility checkbox |
| `misc_local.toml` | the label, mirrored into every language table |
