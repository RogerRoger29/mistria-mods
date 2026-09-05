# Mistria Notices You

The town pays attention to how you actually play, and writes to you about it.

Faint once and Valen sends a dry note about stamina. Land your hundredth fish and
Terithia wants to hear about the one that got away. Bank fifty thousand gold and
Adeline explains, in her way, what that money did for the town.

Letters arrive in your mailbox the morning after you cross the line, like any
other mail.

## The seven letters

| Sender | Arrives when | Why them |
| --- | --- | --- |
| **Valen** | the first time you faint | He's the doctor |
| **Terithia** | 100 fish caught | She runs the fishing shop off the beach |
| **Reina** | 30 dishes cooked | She cooks at the Inn |
| **Hayden** | 100 crops harvested | Your farming neighbour |
| **Juniper** | 50 bugs caught | She wants specimens for potions |
| **March** | 50 monsters defeated | The blacksmith, on the state of your blade |
| **Adeline** | 50,000 gold earned | She keeps the town's ledgers |

## Install / uninstall

```bash
python mistria-mods/install.py status
```

```bash
python mistria-mods/install.py apply mistria-notices-you
```

```bash
python mistria-mods/install.py remove mistria-notices-you
```

`--remove` restores `letters.toml` byte-for-byte. On first `--apply` the script
saves a copy of your archive as `assets.pre-mistria-notices.zip`.

## How it works

**This mod touches no code at all** — the only mod here that doesn't. It appends
seven ordinary letter entries to `assets/fiddle/letters.toml`, gated the ordinary
way.

That works because the game already tracks all of this and never shows you any of
it. The requirements system has `reached_fish_caught`, `reached_bugs_caught`,
`reached_crops_harvested`, `reached_items_cooked`, `reached_enemies_defeated` and
`earned_gold` built in, and `has_ever_fainted` is already a world fact the game
maintains. `letters.toml` was already gating mail on `earned_gold` and
`reached_mines_level` before this mod existed — these letters just use the same
machinery for things nobody happened to write mail about.

## On the writing

Each sender was matched to a stat that fits the role the game gives them, and each
letter was written from that character's **existing letters** rather than from
guesswork — same medium, same register:

- **Valen** opens with a bare `[Ari],`, reasons in measurements, trails off into
  ellipses, and signs "Thanks for your hard work,".
- **Terithia** calls you an angler, says "come on down", and drops her g's.
- **Reina** opens "Hey [Ari]!" and talks in exclamations and food.
- **Hayden** opens "Hey neighbor!" and puts the kettle on.
- **Juniper** is imperious, keeps Dozy, and signs off "Oh ho ho ho!".
- **March** gives compliments that are structurally insults.
- **Adeline** writes like someone whose desk the ledgers cross.

If any of them rings false to you — you're the one reading their dialogue daily —
say which and I'll rewrite it. The letter bodies are plain text near the top of the
script, easy to edit directly.

## Notes

- Each letter arrives **once** (`can_repeat` defaults to false).
- Thresholds are the numbers in the table above; they live in `LETTERS_TOML` in the
  script if you want them sooner or later.
- No items are attached. Letters *can* carry gifts (`items = [...]`) — an easy
  addition if you'd like them to.
- **Uninstall caveat.** Unlike the read-only mods, this one puts data in your save:
  once a letter is delivered, the save references it by key. Removing the mod makes
  the game log a missing-letter error and carry on, rather than crash — but the
  cleanest order is to keep it installed for the life of a playthrough.
- As with any `assets.zip` patch, MOMI may wipe this if it rebuilds the archive.
  Re-run `--apply` afterwards.
