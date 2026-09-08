# Field Notes

The sparkle mods tell you the thing in front of you is still needed. Field
Notes tells you where to go. The journal's Almanac gains four pages — Notes:
Artifacts, Notes: Fish, Notes: Flora, Notes: Insects — and each lists
everything that wing of the museum still lacks, grouped the way the museum
groups it, with a line under every name saying where and when it turns up:

```
Notes: Fish                         Fall Pond Fish Set
  [icon] Bluefish                     Fall - Pond - Rain
  [lock] White Perch                  Fall - Pond
                                    Deep Earth Fish Set
  [lock] Emerald Horned Charger       Mines 41-60
```

Items you have never held show the lock icon, as the Almanac's own pages do;
the name shows regardless, since the point is to go and find it. There is no
toggle; remove the mod to take the pages away.

## Why it lives in the Almanac

The Almanac is the game's own item encyclopedia, with a category list on
the left page and contents on the right, keyboard, mouse and controller
navigation, and a back action — the whole frame a "what do I still need"
page wants. Its category list is data: an array in `ui/menus/sub_menus.toml`
whose entries name a label, an icon and the item tags to collect. Four more
entries go into that array, each carrying a `field_notes` field, and a
six-line branch at the top of the vanilla category builder hands those four
to this mod's builder instead. The vanilla builder never sees them.

## Where the lines come from

Everything is computed when the page opens, from the game's tables, so data
mods and updates are honoured:

| Wing | Source of the line |
| --- | --- |
| Artifacts | the museum set's name (mine biome → floor range; overworld set → `artifacts.toml`'s location map → that location's dig sites; the perk-gated sets → their perk) plus the item's rarity from `artifacts.toml` |
| Fish | the raw `fish.toml` entry: seasons, water type(s), weather (rain only), dive-spot-only, bait-only, legendary, the Deep Woods, or the mine biome from the set's name |
| Insects | the raw `bugs.toml` entry with its `[default]` fallbacks: seasons, where (mine biome, beach, Deep Woods, near water, or just "outdoors"), night or day, rain, on rocks / in trees / in tall grass, pheromones-only, rarity |
| Flora | the set's name: season crops are seeds at the store, forage gets its season and rarity from `forageables.toml` (beach shells from its sand list), the mines and Deep Woods their place, Void its sight |

Every word is a localization key. The seasons and location names are the
game's own; the rest are this mod's labels, mirrored into every language
table by the installer, so a French game shows French seasons and English
hint words rather than MISSING.

## How it works

- `sub_menus.toml`: four entries appended inside the Almanac's `categories`
  array. The engine's TOML reader accepts comments between array elements
  (`misc.toml` ships one), so the marker lines sit there safely.
- `AlmanacMenu.gml`: the branch at the top of `create_category()`, and two
  methods — `create_field_notes_category()` and `open_field_notes()` —
  inserted before the constructor builds its categories, since a function
  declared inside a constructor becomes a method when that statement runs.
  The left-page entry mirrors the vanilla one exactly (label, icon, a
  donated/total count in the small font). The right page reuses the vanilla
  scroller field, so the Almanac's own Back handling closes it.
- `Museum.gml`: the hint functions, appended.
- Set order is the museum's own (`fish_order` and friends in the museum
  menu's data), so the page reads in the same order as the museum's wall.

## Traps found building it

- Anchors inside a constructor: `self.tooltip = undefined;` appears three
  times at different indents, and a shallower indent is a substring of a
  deeper one. The methods anchor on the one-off `self.categories = List();`
  instead.
- Fish seasons, weather and hours are compiled into spawn *conditions* on
  the runtime prototype; the readable fields only exist on the raw table,
  which `fiddle_get("fish")` still serves.
- Bug entries omit whatever matches `[default]`, so a bug with no `hours`
  is a daytime bug, not an any-time one.

## Files touched

| File | Change |
| --- | --- |
| `ui/menus/sub_menus.toml` | four Almanac categories |
| `AlmanacMenu.gml` | the branch and the two methods |
| `Museum.gml` | the hint functions, appended |
| `misc_local.toml` | the labels, mirrored into every language table |
