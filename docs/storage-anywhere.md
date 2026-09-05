# Storage Anywhere

Press **B** for a list of every chest in the world. Pick one and it opens, from
wherever you're standing.

The key is a real, rebindable control — it appears in Settings → Controls as
"Open Chest Picker". There's an Accessibility toggle, "Storage Anywhere".

Every row carries a **pin icon on its left edge — click it** to pin or unpin
that chest with the mouse alone (faint = unpinned, solid = pinned), or press
**P** (rebindable — "Pin Chest"; X/west on a gamepad) on a highlighted row.
Pinned chests form their own group at the very top of the list, so the main
storage is always one press away no matter where you're standing.

## Install / uninstall

```bash
python mistria-mods/install.py status
```

```bash
python mistria-mods/install.py apply storage-anywhere
```

```bash
python mistria-mods/install.py apply storage-anywhere --chest-key K
```

```bash
python mistria-mods/install.py apply storage-anywhere --pin-key J
```

```bash
python mistria-mods/install.py remove storage-anywhere
```

## What's in the list

Chests are **grouped under a location header**, using the game's own category
strip. Each chest row is two lines so the columns never fight for the same
pixels:

| | |
| --- | --- |
| **Pin** (left edge) | The pin toggle — faint when unpinned, solid when pinned; the whole strip is clickable |
| **Name** (top left) | The furniture item's name — "Basic Wood Chest", "Coral Storage Chest" |
| **Fill** (top right) | Slots used out of slots available, e.g. `12 / 30`, greyed when the chest is empty |
| **Contents** (bottom left) | Icons for the first few things inside |
| **Crafting** (bottom right) | The pull-button icon, if this chest feeds the crafting menu |

**Pinned chests come first**, under their own "Pinned" header, in the order
they were pinned — unpin and re-pin to reshuffle, the group never rearranges
itself. A pinned row keeps its home in its name ("Basic Wood Chest -
Farmhouse"), since the header no longer says it. After that, chests **in the
room you're standing in**, then everything else in the order the game already
holds them, which is grid by grid — each location is one contiguous run, so
exactly one header is emitted per group. Headers are drawn and scrolled past
but never selectable.

Names are clipped to fit with an ellipsis rather than wrapped. That distinction
matters: `set_max_width()` looks like a clip but re-enables line breaking, which
is what once made a label render one character per line. Measuring with
`string_width_font()` is accurate because it defaults to `ANCHOR.get_text_font()`
— the same font the text nodes draw with.

**Location names need `local_get()`.** `LOCATIONS[i].name` is a localization
key, so printing it raw gives you `locations/player_home/name`. It's also absent
on some locations — the farm included, which is why `show_room_title()`
special-cases the farm to `ARI.farm_name` instead of reading the location at
all. The picker follows the same chain, falling back to "Elsewhere".

The chest you opened last is **pre-selected** when you reopen the picker, so
going back to the same chest is B then Confirm. It's remembered as the chest
itself, not a position in the list, so building or breaking chests in between
doesn't send you somewhere else. The picker also **opens scrolled to that
selection**: the engine's scroller only follows the pilot's selection during
directional control, so without an explicit scroll a mouse user would open
onto the top of the list with the selection invisible below the fold. The
constructor mirrors the scroller's own follow arithmetic (including its `-2`
bottom padding) after `try_force_select`.

Everything is included: plain chests, fridges, the stable chest, miners' crates,
the shipping bin and turn-in boxes. There's no range limit — the mines included.

## Pinning

Mouse users click the pin icon strip on the row's left edge. This is **one
tap listener per row, not two**: the icon itself listens for nothing, and the
row's tap callback routes by mouse position — `point_in_node(pin_icon, ...)`
means toggle, anywhere else means open. Two overlapping listeners would rest
on the engine's newest-first hover scan paying the tap to the child, which
reads like it works but has no shipped precedent — the game's own spell list
keeps its in-row checkbox visual-only and puts the toggle on a separate
button, and the scroller hit-tests its range manually under the tappable
button for the same reason. The widened `set_bbox_offset` makes the whole
strip clickable rather than the icon's nine pixels — the same bbox +
`point_in_node` combination the scroller's range clicks use. The routing only
runs in point control: a directional-mode Interact lands wherever the mouse
was last parked, which is nowhere the player is looking.

The pin key toggles the row under the cursor when there is one — in
directional control hover *is* the selection, courtesy of `hover_node` — and
falls back to the pilot's selected row when the mouse is parked elsewhere, so
keyboard, controller and mouse all pin without separate handling. Toggling
rebuilds the picker through the same close-then-spawn path the tap callback
uses, with `CHEST_PICKER_LAST` pointed at the toggled chest, so the row
visibly jumps groups and keeps focus.

**Pins persist in `settings.json`, never in the save** — one string setting,
`chest_picker_pins`, sitting right next to the key bindings. The settings
loader merges the saved file over `get_default_settings()`, so an existing
settings.json needs no migration, and uninstalling the mod leaves behind one
inert unused key rather than a save your game complains about (the
mistria-notices lesson).

A pin's identity is **location + cell**, not a node reference — nodes don't
survive a restart. Static locations key by `LocationId`, so renaming the farm
keeps its pins; building interiors have no id and key by the building's
(user-typed) name, with the `;`/`@` separators laundered out. A chest that
gets moved or broken simply stops matching — the orphaned entry sits
harmlessly in the string until that cell is pinned again.

The footer hint spells the pin control with whatever key it is currently
bound to, read back through `SETTINGS.bindings` (handling both the string and
raw-keycode forms `decode_binding()` accepts), falling back to the shipped
default when the binding is cleared or unprintable. The icon is
`spr_ui_journal_magic_pin_icon` — the game's own pin, borrowed from the
pinned-spell UI, so no new art was needed against the prebuilt atlases.

The panel also grew from 208 to 256 pixels tall (the UI canvas is 360), which
fits roughly seven rows plus the footer instead of five.

## Why this is a small mod

Almost none of this is new machinery. Three things were already true:

**The game already keeps a global chest registry.** `STORAGE_NODES` is a `List`
of every node that has an inventory, pushed in `setup_furniture_node()` and
spliced out in `GridUtils` when a node is destroyed. The crafting menu walks it
to pull ingredients out of chests. This mod adds no registry of its own — it
reads that one.

**Every location is already loaded.** `LoadGame.gml` builds and loads a grid for
every `LocationId` except the Dungeon at startup, so `STORAGE_NODES` spans the
whole map from the moment you load a save. Nothing needed to be kept in sync,
because nothing is ever unloaded.

**The storage screen already takes arbitrary inventories.** The lost-and-found
box, the museum donation basket and the seal tablet all spawn `Menu.Storage`
with inventories that have no world object behind them. Opening a chest that
isn't in the room is not a special case as far as the menu is concerned.

So the mod is a list, a lookup, and one call into the game's own storage screen.

## The one genuinely new thing

The picker is a real menu with its own `Menu.ChestPicker` id.

`Menu` is an engine-generated enum with no GML declaration — but `load_menus()`
reads `fiddle_get_directory("ui/menus")` and calls `string_to_menu(key)` on each
key it finds. Cross-checking confirms the enum is generated from exactly those
keys: 45 keys across the TOML files, 46 `Menu.X` constants used in the GML, and
the only one without a matching key is `LEN`.

So adding a `[chest_picker]` entry to `ui/menus/standard_menus.toml` mints
`Menu.ChestPicker`, the same way adding to `perks.toml` mints a `Perk`. A case
in `Anchor.gml`'s spawn switch points it at the constructor.

The picker itself is built from the engine's `Scroller` + pilot pair — the same
components the settings pages use — so keyboard, controller and mouse navigation
all work without a line of input handling in this mod.

## Two traps in adding a menu

Both of these crashed or broke on the first play test, and neither shows up in
any structural check — the code compiled and patched cleanly.

**A new menu id must be seeded into the game stats.** `spawn_menu()` counts every
open before it builds anything:

```gml
GAME_STATS.menu_opens[$ menu_to_string(menu_id)] += 1;
```

A key that was never created reads as `undefined`, and `+= 1` on undefined is a
hard crash — `bad unary op "inc" undefined` — so the menu dies there, before its
constructor runs. The keys normally come from `patch_game_stats()`, which walks
`Menu.LEN` filling in whatever is missing. But that only runs on a **new game**,
or from `apply_save_patches()` when a save is migrated between versions. An
existing save already at the current version never gets patched, so it never
learns about a menu added after it was created. The mod seeds the key itself,
once, on demand.

**`add_to_pilot(pilot, newline_after)` — the second argument is not "focused".**
It requests a pilot newline after that node. Passing a "is this the selected
row" boolean puts the entire list into a single pilot row, leaving up/down with
nothing to move between. Every row passes `true`; the initial selection is set
afterwards with `pilot.try_force_select(node)`.

## STORAGE_NODES holds chests that no longer exist

Entries are spliced out of `STORAGE_NODES` by `erase_object_node_data()` when an
object is destroyed. But **nine locations are flagged `reset_every_night`** —
town, the eastern road, the deep woods, the Dragonsworn glade, the narrows, the
summit, the western ruins, the beach and Hayden's farm. Rewriting one of those
grids pushes fresh nodes into the list without retiring the old ones, so after a
few in-game days it holds chests that exist nowhere.

The game never notices. The stale copies are empty, so `sell_shipping_bin_items()`
and the crafting pull walk straight past them. A picker that lists the array
notices very much: it showed three "Shipping Bin" rows on a save with exactly
one shipping bin.

The picker therefore checks each node is still real before listing it — a node
is live only if its own grid still points back at it:

```gml
var ni = grid.try_node_index_for_cell(node.top_left_x, node.top_left_y);
return grid.node_parent[ni] == node;
```

A same-cell dedupe backs that up, since two entries describing one physical
chest can only ever be a bookkeeping artefact.

## The expired-instance trap

Opening a remote chest you had visited earlier crashed with `expired instance`.
Leaving a location destroys its renderer instances, but `node.renderer` keeps
the dead reference — and an expired instance is not `undefined`, so every guard
in the chain (this mod's, and the game's own in `StorageMenu.on_close()`)
passed it straight through to a variable access that kills the game.

Vanilla can never hit this: you must stand next to a chest to open it, and
standing next to it means its renderer is alive. Remote opening is what exposes
it. The fix normalizes the reference before opening —

```gml
if node[$ "renderer"] != undefined && !instance_exists(node.renderer) {
    node.renderer = undefined;
}
```

— which heals both this mod's guard and the game's `on_close` guard at once,
since both test `!= undefined`. Re-entering the location reassigns the renderer,
so nulling it costs nothing. `instance_exists()` on a stored reference is the
engine's own idiom for this (`obj_bird` does it for its perch target).

## Notes and caveats

- **Turn-in boxes open exactly as they do in person** - alt-stack behaviour and
  the quest's recipe checklist, no storage banner. The open path mirrors
  Interact.gml's branches verbatim.
- **B is a toggle** - the same key closes the picker. That lives in the menu's
  on_think, because check_for_menu_opens is gated behind game_paused() and this
  menu pauses.
- **No lid animation for a remote chest.** `node.renderer` only exists for the
  location you're actually in, so the open/close animation and sound are skipped
  when the chest is elsewhere - but the open sound plays either way, at Ari's
  position, exactly where the interaction path plays it. Same-room chests behave
  as normal.
- **Factories aren't listed.** `STORAGE_NODES` also holds furnaces, looms and
  the auto-feeder, since they have inventories too. The list filters on
  `interaction_chest`, so only real containers appear.
- **Shipping from anywhere is a balance change.** You asked for it included, and
  it is — but the walk to the bin was part of the day's cost, and this removes
  it.

## Files touched

| File | Change |
| --- | --- |
| `ui/menus/standard_menus.toml` | `[chest_picker]` — mints `Menu.ChestPicker` |
| `Anchor.gml` | spawn case for the new menu |
| `StorageMenu.gml` | the picker menu and its helpers |
| `InputUtils.gml` | `InputId.OpenChestPicker` + `InputId.PinChest` + their categories |
| `Settings.gml` | default bindings (B, P), the toggle default, and `chest_picker_pins` |
| `SettingsMenu.gml` | the Accessibility checkbox |
| `obj_ari.gml` | the keypress, inside `check_for_menu_opens()` |
| `misc_local.toml` | labels |

`InputUtils.gml` and `Settings.gml` are shared with **crop-labels** and
**daily-checklist**, which also register controls. All three use the same
single-line anchors and insert immediately after them, so they survive each
other in any application order. The default keys — B and P here, F and V in
the others — are all unbound in vanilla.
