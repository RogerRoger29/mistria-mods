# Map Name Labels

Hover a head on the map screen and their **name appears above it**.

The map groups everyone at a location into one cluster of 11x11 head icons, which
is exactly why they're hard to read — several tiny faces packed into a grid at a
single point. Hovering disambiguates a stack that squinting can't.

The name sits on a small tooltip card, drawn with the game's own
`spr_ui_tooltip_box` nine-slice so it matches the rest of the UI. Pass `--no-card`
for the bare name with no backing.

Villagers you haven't met read `???`, matching how the relationships menu already
treats them, so nothing is revealed that you haven't earned. Your farmer, your pet,
and your children get their real names.

Toggle it any time in **Settings → Accessibility** ("Map Name Labels").

## Install / uninstall

```bash
python mistria-mods/install.py status
```

```bash
python mistria-mods/install.py apply map-name-labels
```

```bash
python mistria-mods/install.py remove map-name-labels
```

`--remove` restores the original code byte-for-byte. On first `--apply` the script
saves a copy of your archive as `assets.pre-map-name-labels.zip`.

## How it works

Only **one file** is patched — `scripts/UI/Anchor/Menus/MapMenu.gml`. The shared UI
framework is left completely untouched, which is the part worth explaining.

The map icons are ordinary sprite nodes that simply never opt into hovering. Two
existing framework features do all the work:

- `listen_for_hovers()` makes a node hover-aware, and sets its `run_logic` flag.
- `add_text_label()` parents a text node to it — and that label is precisely what
  Anchor calls `update()` on every frame for sprite nodes, *while `run_logic` is
  set*.

So a single pair of calls buys both the hover detection and a per-frame hook. The
label's `update` is then overridden with a one-liner: be visible while the parent
icon is hovered, invisible otherwise. No polling loop, no new menu, no changes to
`Anchor.gml`.

Text colour comes from a LUT index into `spr_ui_generic_font_lut` (21 columns, one
per `CommonLutIndex`). `add_text_label()` leaves it on `Source` — raw white glyphs
with a dark outline, meant for drawing over the world, and unreadable on a pale
card. With the card on, the label uses `Standard`, which is what the game's own
tooltips use for body text on this very sprite; with `--no-card` it stays on
`Source`, which is the right choice over the map itself.

The card is a `nine_slice` node sized from the label's measured width, sitting one
z-step behind the text. Both are pinned to the icon's top edge, so the label is
raised by half the height difference to centre it inside the card. Its 8x8 frames
need roughly 16px of height before the corners render cleanly, hence the floor on
the card height.

Two further details that fell out of the research:

- Names are localization keys, not raw strings, so villager names go through
  `set_key(prototype.name)` and stay translated. Raw names (your farmer, pet,
  children) are passed through `wrap_for_local()`, the same idiom the game uses for
  its own `???`.
- `prevent_spillover` only *logs* oversized text to a QA list; it doesn't clip. The
  label switches it off so long names render fully and the developers' spillover log
  stays clean.

Because the label is a child of the icon, it's freed automatically when the map
rebuilds on a tab switch — no lifetime management needed.

## Notes

- Works with the mouse. It would also work with keyboard/controller navigation for
  free — `hover_node()` is what pilot selection calls too — but the map's head icons
  aren't part of a navigation pilot, so today only the tabs are keyboard-navigable.
  Adding them to one would change how the map's arrow keys behave, so it's left
  alone.
- **Saves are untouched.** This mod only reads state and draws.
- Composes with **Nearby Affection** and **Curious Neighbours**; all three use
  distinct markers and this one is the only mod touching `MapMenu.gml`.
- As with any `assets.zip` patch, MOMI may wipe this if it rebuilds the archive.
  Re-run `--apply` afterwards.
