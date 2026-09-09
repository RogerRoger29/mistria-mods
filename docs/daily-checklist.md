# Daily Checklist

**Hold `V`** for a panel gathering what's left to do today, and what's coming up
this season.

```
Day  10 / 28

TODAY
12 crops need water
6 villagers not greeted
8 gifts still available

COMING UP
Birthday: Juniper, 14
Festival: Flower Festival, 21
```

The key is a **real, rebindable control** — it appears in Settings → Controls
next to everything else, so `V` is only the starting point. On a controller it
has no default button, because the vanilla layout leaves none free; bind one
there.

| Option | Default | Meaning |
| --- | --- | --- |
| `--checklist-key` | `V` | The **default** binding only. Rebind in game afterwards. |

```bash
python mistria-mods/install.py apply daily-checklist --checklist-key H
```

## Why it's worth having

The game tracks every one of these and never puts them in one place. Working out
whether you've greeted everyone means walking the whole town; working out which
crops are dry means walking your whole farm.

## What it reads

| Line | Source |
| --- | --- |
| Crops needing water | The farm grid, counting planted cells that aren't watered |
| Villagers not greeted | `times_spoken_today == 0`, for villagers you've met |
| Gifts still available | `gift_flag`, for villagers you've met |
| Animals not fed / not petted | `has_eaten` and `has_been_pat` on each of your animals, the flags the nightly check in `Stable.gml` judges them on; the lines appear once you own any animal |
| Animals still outside | `is_home()` per animal, shown from five o'clock, since being out overnight is what costs hearts |
| Next birthday | Each villager's `prototype.birthday`, this season only |
| Next festival | `FESTIVALS`, skipping any not marked `implemented` |

Only villagers you've **met and unlocked** are counted, so it never hints at
someone you haven't been introduced to.

## How it works

Anchor nodes on the Vitals canvas — the same construction as the crop label
card, for the same reason: raw drawing inherits whatever shader LUT was last
bound and comes out mistinted.

The whole list is **one text node with newlines** rather than a node per line,
which keeps it simple and lets `measure()` size the card to fit.

The farm sweep is the expensive part, so the panel is **built once when the key
goes down** and cached until you release it, rather than recomputed every frame.

Note the off-by-one the game itself uses: `birthday.day` and festival dates are
1-based while `CALENDAR.day()` is 0-based, which is why the game's own calendar
compares against `date.day - 1`. This follows that.

## Notes

- **Saves are untouched.** It only reads and draws.
- Shares `obj_ari`'s `step_end` with Crop Labels and Ladder Progress, and
  registers a control alongside Crop Labels — the anchors are chosen so both
  survive whichever order they're applied in.
