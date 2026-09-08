# Homeward

A sixth spell. Cast it anywhere, the mines included, and Ari is carried to
her own doorstep the way walking through the front door would take her. The
day goes on: nothing is saved, the clock keeps running, animals and crops are
untouched. It only saves the walk.

It is learned, not given. With Magic Skill installed it arrives when Magic
reaches level 20; without Magic Skill it comes along with the first spell the
Mist teaches. A toast says so when it happens.

## Options

| Option | Default | Meaning |
| --- | --- | --- |
| `--cost` | `8` | Mana cost. The spell card shows cost in whole orbs (cost ÷ 4), so multiples of 4 read cleanly. |
| `--level` | `20` | The Magic level that teaches it, when Magic Skill is installed. |

```bash
python mistria-mods/install.py apply homeward --cost 12 --level 30
```

## How it works

- **The spell is data.** Spells are minted from `spells.toml` the way perks
  and skills are: appending `[homeward]` creates `Spell.Homeward`, the spell
  menu lists learned spells dynamically, and the learned-spell list in saves
  is keyed by name, so the entry sits at the end and existing indices hold.
- **The cast is a door.** Every door in the game moves Ari through the taxi
  system with an itinerary; Homeward builds the same itinerary the farm door
  into the house builds, destination tag included, so she arrives on her own
  doormat. Leaving the mines this way runs the dungeon's own exit hook,
  because that hook fires on any change of room, not on the elevator.
- **The gate.** Refused while a transition is already running, during a
  cutscene, while the day is ending, and when Ari is already home; the
  vanilla gate above it already refuses casting while mounted or holding an
  animal, and while mana is short.
- **Learning.** The check runs after any spell is learned, each morning, and
  once when a save loads (quietly there, since the toast menu does not exist
  yet), so a save that already qualifies has the spell the moment it opens.
  It looks the Magic skill up *by name* at run time, so the code never names
  `Skill.Magic` and is safe whether or not Magic Skill is installed: found,
  it compares `skill_xp_to_level` against the level option; not found, it
  waits for the first spell.
- **Art.** The list icon is the HUD's map glyph, which the button-sprite
  loader accepts as a plain sprite (it falls back to the bare name when a
  family has no `_main` variant); the card icon is the basic doormat; the
  ribbon is Full Restore's.

## Playing with the other mods

- With Magic Skill, every cast earns 8 Magic XP like any spell without its
  own entry, cost perks apply, and Arcane Economy can refund it.
- MOMI's spell-cost data mods change vanilla spells only; Homeward's cost is
  its own option.

## Caveats

1. **A save that has learned it keeps a `homeward` entry** in its spell
   list. The loader's converter skips unknown names in release builds as far
   as the code shows, the same unverified situation as Magic Skill's XP entry:
   test on a throwaway save before removing the mod from a playthrough that
   learned it.
2. Casting from inside a shop or another building works like walking out of
   it; nothing you were doing there is finished for you.

## Files touched

| File | Change |
| --- | --- |
| `spells.toml` | the `[homeward]` entry, appended |
| `Spells.gml` | a case in `can_cast_spell`, a case in `cast_spell`, the helpers appended |
| `Ari.gml` | one call after any spell is learned |
| `NewDay.gml` | one call each morning |
| `misc_local.toml` | the toast text, mirrored into every language table |
