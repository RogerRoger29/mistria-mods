# Curious Neighbours

Walk past a villager while carrying something and they'll react to **what you're
holding**, with a thought bubble over their head:

| Bubble | Meaning |
| --- | --- |
| heart | they'd love it as a gift |
| cute face | they'd like it |
| ellipses | they'd rather you didn't |
| sweat drop | they'd hate it |
| *nothing* | they don't care either way |

The point is to turn gift discovery into something you notice in passing, rather
than something you look up. Carry a suspicious mushroom through the plaza and watch
who lights up and who recoils.

## Install / uninstall

```bash
python mistria-mods/install.py status
```

```bash
python mistria-mods/install.py apply curious-neighbours
```

```bash
python mistria-mods/install.py remove curious-neighbours
```

`--remove` restores the original code byte-for-byte. On first `--apply` the script
saves a copy of your archive as `assets.pre-curious-neighbours.zip`.

## Tuning

| Option | Default | Meaning |
| --- | --- | --- |
| `--radius` | `40` | How close you must walk, in pixels. One tile is 8px, so 40 is 5 tiles — close enough that you're plausibly showing it to them. |

```bash
python mistria-mods/install.py apply curious-neighbours --radius 32
```

Nearby Affection has a `--radius` of its own, so with `--all` the bare flag
reaches both; `--curious-neighbours-radius` sets this one alone.

## Rules it follows

- **Only villagers you've met react.** A stranger has no opinion about your turnips.
- It fires only when the **held item changes**, so standing in a crowd doesn't spam
  bubbles. Walking out of range and back re-arms it.
- It never speaks over an existing bubble, an NPC-to-NPC chat, or a cutscene.
- Neutral items show nothing, which keeps a bubble meaningful when you do see one.
- Thought bubbles are silent outside cutscenes — that's the game's own rule, so
  this adds no new noise.
- Both hand-written special cases are honoured: Juniper and a Void Newt, Eiland and
  a Void Cake.

## How it works

The desire calculation is a faithful mirror of the one inside `Npc.give_gift()` —
loved/liked lists, infusions, the hated gift, and disliked tag matching — but with
none of its side effects, so nothing is consumed, recorded, or gifted. Note that it
reads the villager's *true* preference, not the ones you've discovered; that's the
whole point, but it does mean the bubbles know things your gift log doesn't.

Two files are patched, with every insertion wrapped in
`// >>> CURIOUS_NEIGHBOURS_BEGIN` markers:

| File | Change |
| --- | --- |
| `objects/system/parents/par_NPC.gml` | Adds `handle_curiosity()` next to the game's own `handle_chatting()` / `handle_thinking()`, and calls it from the same step event. |
| `scripts/GameplaySystems/NPCs/Npc.gml` | Adds `curious_desire_for()` and `curious_bark_for()` at file scope. |

**Saves are untouched** — this mod only reads state, and stores one transient
instance variable that never reaches disk.

## Interaction with other mods

Composes cleanly with **Nearby Affection**: both use distinct markers, both touch
`Npc.gml`, and applying or removing either leaves the other intact.

As with any `assets.zip` patch, MOMI may wipe this if it rebuilds the archive.
Re-run `--apply` after changing your mod list there.
