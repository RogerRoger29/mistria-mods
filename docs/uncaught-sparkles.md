# Uncaught Sparkles

Every insect whose species is not yet on display in the museum's Insect wing
carries a looping white twinkle. An accessibility mod: the cue is luminance
and motion, so it reads without any colour vision at all.

Toggle: Settings → Accessibility → "Uncaught Insect Sparkles" (on by default).
The setting is read when an insect spawns, so a change applies to the insects
that appear after it.

## Install / uninstall

```bash
python mistria-mods/install.py apply uncaught-sparkles
```

```bash
python mistria-mods/install.py apply uncaught-sparkles --lift 6
```

```bash
python mistria-mods/install.py remove uncaught-sparkles
```

`--lift` raises the twinkle that many pixels above the insect's drawn
position, if it sits too low on some species.

## What counts as "uncaught"

**Donation state, not catch state.** The check is
`MUSEUM_DATA.is_museum_item(item) && MUSEUM_PROGRESS[item] != true` —
`MUSEUM_PROGRESS` is a bool array by item id and is exactly the flag the
museum's own set-progress code reads. So a species you have caught but not
yet handed in keeps sparkling until it is on display, which is the moment it
stops mattering for completion. Catching one does not silence the others of
its kind; donating does.

If "never caught" is the preferred meaning (the journal's discovered state),
it is a one-line change to the condition in `uncaught_sparkles.py`.

## The art: dormant assets

`spr_fx_twinkle_1`, `_2` and `_3` ship in the atlas but are referenced by
**no GML at all** — the game has bug-sized (18×18) pure-white four-point-star
twinkle animations it never wired up. In greyscale they are the strongest
signal in the entire fx set. The other dormant candidates,
`spr_fx_bug_pheromone_common/uncommon/rare/legendary` — evidently a cut
bug-attractant item — are faint drifting specks whose only differences are
hue, i.e. exactly the information that must not carry the meaning here. The
choice was made by compositing the strips upscaled in greyscale and looking,
not by name.

Each bug picks one of the three at random and starts on a random frame, so a
crowd of uncaught insects never twinkles in lockstep.

## How it rides the bug

The twinkle is an `obj_animation_effect` created with
`create_animation_effect_on_object(bug, sprite, -1, z)` — the same follower
Guardian's Shield uses on Ari. Three properties of that object shaped the
patch:

- **It dies after one animation cycle unless `live_on_anim_end` is set.** Set
  it, and the animation loops forever.
- **When its target is destroyed it merely stops following; it never dies.**
  So `obj_bug`'s own `destroy` handler puts the effect down — which covers
  being caught, the flee fade-out and despawn alike, since all three go
  through `instance_destroy()`.
- **It only knows the bug's `y`, but bugs draw at `y + z`** — fliers hover at
  `z = -13`, jumpers arc to −15, canopy spawns drop in from −32. The bug's
  `step` mirrors `z` into the follower's `y_offset` every frame, and mirrors
  `image_alpha` in the same breath, which makes the flee fade and the
  cutscene hide (`image_alpha = 0`) fall out for free.

The creation sits at the end of `setup()`: past the terrain check that can
destroy a freshly spawned bug, past the idle/canopy state choice. The field
is initialised in `create` — before `setup()` can run — because that early
destroy fires the destroy handler, which reads it.

## Files touched

| File | Change |
| --- | --- |
| `obj_bug.gml` | field init in `create`; creation at the end of `setup()`; z/alpha mirror in `step`; teardown in `destroy` |
| `Settings.gml` | `uncaught_sparkles: true` default |
| `SettingsMenu.gml` | the Accessibility checkbox |
| `misc_local.toml` | the label |

`Settings.gml`, `SettingsMenu.gml` and `misc_local.toml` are shared with the
other toggle-bearing mods; the same single-line anchors, inserted beside, so
application order does not matter.

## Notes

- Fish are never visible in the world (shadows only), so there is nothing to
  mark; artifacts come from dig spots. The natural follow-up is the **Flora
  wing** — forageables and flowers are world objects too, but they are grid
  nodes with renderers rather than instances, a different hook.
- Roughly 4–10 bugs per map (doubled by the MOMI spawn mod), one follower
  each, one assignment per step: no measurable cost.
