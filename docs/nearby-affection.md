# Nearby Affection

A small Fields of Mistria mod: **when you talk to or gift an NPC, everyone standing
nearby gains a little affection too.**

Chat with Juniper in the plaza while Ryis and Celine are within a few tiles, and all
three tick up — the bystanders just get a smaller share, once per day each.

## Install / uninstall

```bash
python mistria-mods/install.py status
```

```bash
python mistria-mods/install.py apply nearby-affection
```

```bash
python mistria-mods/install.py remove nearby-affection
```

`--remove` restores the original code byte-for-byte. On first `--apply` the script
also saves a copy of your current archive as `assets.pre-nearby-affection.zip`.

## Tuning

| Option | Default | Meaning |
| --- | --- | --- |
| `--radius` | `64` | How close a bystander must be, in pixels. **One tile is 8px**, so 64 is a radius of 8 tiles / 16 tiles across. The game's own "close enough for two NPCs to strike up a chat" distance is 48 (6 tiles). |
| `--points` | `2` | Heart points each bystander gains. For scale: a normal daily conversation is 7 in vanilla, and heart level 1 is 80 points. |
| `--no-popup` | off | Suppress the heart thought-bubble over bystanders. |

### What 64px looks like on screen

The game renders at 426x240 world pixels, so a 64px radius is a circle **128px
across — about 30% of the screen's width, or half its height**. In practice: anyone
sharing the same stretch of street or the same room-ish area with you, not merely the
person you're standing on top of. Comfortably generous without reaching across town.

Some reference distances, all in the same units:

| Distance | What it is |
| --- | --- |
| 8 | one tile |
| 48 | two NPCs decide they're close enough to chat to each other |
| 64 | this mod's default |
| 128 | roughly one screen-height |

Re-run `--apply` with new numbers any time; it re-patches from clean each run.

```bash
python mistria-mods/install.py apply nearby-affection --radius 96 --points 4
```

Curious Neighbours has a `--radius` of its own, so with `--all` the bare flag
reaches both; `--nearby-affection-radius` sets this one alone.

## Rules it follows

- Fires on the first conversation of a day with an NPC, and on giving a gift.
- Each **bystander** can collect this at most once per day, so it can't be farmed by
  re-talking to the same person.
- Only NPCs actually loaded in your current location count.
- Caldarus and Seridia are skipped below 6 hearts, matching the game's own rule for
  them in the normal talk bonus.
- Heart-level-up sparkles and the level-up jingle fire normally, since it routes
  through the game's own `add_heart_points`.
- Each bystander shows a heart thought-bubble over their head — the same
  `BarkId.Heart` bubble pets and barn animals show when you pet them. It's skipped
  if that NPC is already showing a bubble, so it never stomps a chat or cutscene
  line, and it expires on the game's own bark timer.

## How it works

The game compiles the GML source shipped inside `assets.zip` at startup using its
embedded `fabricator` VM, so editing that source is enough — no DLL injection.
The script rewrites three files:

| File | Change |
| --- | --- |
| `scripts/GameplaySystems/NPCs/Npc.gml` | Adds the `nearby_affection_on_interact()` helper, the per-day flag, and the gift-giving trigger. |
| `scripts/GameplaySystems/NPCs/NpcDatabase.gml` | Clears the per-day flag in `npcs_on_new_day()`. |
| `scripts/GameplaySystems/T2r.gml` | Triggers on the `SpokeTo` dialogue action. |

Every inserted chunk is wrapped in `// >>> NEARBY_AFFECTION_BEGIN` / `// <<< END`
markers, which is how `--remove` and re-applying work.

**Saves are untouched.** The per-day flag is deliberately not serialized, so a save
made with this mod still loads in an unmodded game. The only side effect is that
reloading mid-day re-arms the bonus for that day.

## Note on MOMI

MOMI installs mods by rewriting `assets.zip` too. If you add, remove, or reorder mods
in MOMI, it may rebuild the archive and wipe this patch. That's harmless — just run
`--apply` again afterwards, and check with `--status` if you're unsure.

This mod stacks fine with your `Quick Relationship Options` mod; that one changes the
`daily_hearts_for_speaking` fiddle value, which this doesn't touch.
