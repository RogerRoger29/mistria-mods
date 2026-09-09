# Moving mods to MOMI: what fits and what doesn't

**Status, 2026-09-09.** The twelve in the first two groups below are built,
under [`momi/`](../momi/): every package passes MOMI's strict lints and its
bundled GML compile checker, installs through MOMI's own command-line build
alongside the thirteen third-party mods already on this machine, and was
confirmed in play the same day: the game boots, the mail still reads after
MOMI's rewrite of `letters.toml`, and every package behaves as its framework
edition does. The framework refuses to apply a mod whose package is present. Nothing in the
other three groups has been started.

Written 2026-09-09 against MOMI 0.15.10 (its source at `Garethp/Mods-of-Mistria-Installer`),
the MMAPI hook catalog MOMI installed into this archive for game 1.0.4, and the twenty
mods as of 1.3.0 plus Barn Labels. Every claim below was checked in one of those three
places; where something could only be settled by running the game, it says so.

## What a MOMI mod can and cannot do

- **Code.** A mod's `gml/` files land under `assets/gml/scripts/<author_mod>/` and register
  handlers on the hook catalog. That is all. `GmlLayer.cs` stages MOMI's own seams against
  the pristine game and only ever *adds* a mod's files; there is no installer for raw
  script files, so a mod cannot patch or replace a vanilla `.gml`. The manifest's
  `requires_hooks` lists the hooks a mod needs, and a mod whose hooks are missing on a
  given game build is excluded cleanly rather than half-installed.
- **Hooks.** This build's catalog (`mmapi_hook_catalog.gml`, generated, do-not-edit)
  declares 113 hooks of four kinds: `filter` (transform a value), `event` (observe),
  `guard` (veto), `override` (replace, first non-undefined wins; `spells.cast`,
  `spells.can_cast` and `object.interact` are claim-scoped so several mods can coexist).
- **Per-frame work.** `game.clock_tick` is emitted from the Game object's `step_begin`
  every frame before any pause logic, `mmapi_register(fn)` queues a function that runs
  every frame from the same place, and `ui.toolbar_tick` fires while the HUD is live.
  Any of these replaces the `obj_ari.step_end` anchor five of our mods hang off.
- **Data.** Every `*.toml` in the mod folder lands at `assets/<same relative path>`
  (`Installer.DestinationPath`). If the file exists MOMI merges: tables merge
  recursively and new keys are added; `[[table array]]` entries are appended unless
  they carry `MOMIidentify`; plain arrays are replaced unless the enclosing table-array
  entry says `MOMIaction = "merge"`. If the file does not exist it is written new
  (`TOMLInstaller.MergeOrWriteToml`). So a mod can add `[homeward]` to `spells.toml`,
  append `[[tier_5]]` to a skill tree, and ship a brand-new `ui/skill_menu/magic.toml`
  that the shrine's `fiddle_get_directory` will pick up by itself.
- **Text.** Strings live in `fiddle/mods/<mod>/<file>.toml`, registered through a
  `localization/l10n.meta.toml` with one `fiddle_renames` line per file, and are used as
  keys `mods/<mod>/<file>/<key>`. Other languages: the same path rule lets a mod overlay
  `localization/translations/<lang>.meta.toml` and `source_caches/`, which is exactly the
  fourteen-table mirroring the framework does. Not yet verified in play.
- **Settings.** `mmapi_config_*` reads and writes JSON under
  `%LOCALAPPDATA%/FieldsOfMistria/mod_data/<mod>/`. The third-party **MMAPI Mod Configs**
  mod (Nexus 779, 8,400 unique downloads) shows those files under Settings as a "Mod
  Configs" tab; changes need a restart, and its page says it was built for MOMI 0.14.0,
  so compatibility with 0.15.10 is unverified. Nothing can be added to Accessibility or
  Controls: `SettingsMenu.gml`, `Settings.gml` and the `InputId` enum have no seams.
- **Keys.** `mmapi_hotkey_register` fires on a press edge and `mmapi_hotkey_binding_held`
  answers whether a binding is down, for keyboard letters, digits, F-keys, named specials,
  gamepad buttons and chords. Bindings come from the mod's config. They never appear in
  Settings > Controls and cannot be rebound without a restart.
- **Menus.** `ui.menu_opened` delivers `{menu, kind}` after a menu is fully built.
  `Anchor.spawn_menu` is a closed switch that ends in `impossible()`, but its body is
  three lines (stats bump, construct, push onto `ANCHOR.open_menus`, emit), so a mod can
  build its own menu class and open it the same way without the switch.
- **Files.** MOMI adds sprites, meta files and new fiddle files, which the framework
  cannot do at all.

## The verdict

| Group | Mods | Confidence |
| --- | --- | --- |
| Pure data, no code at all | Mistria Notices, Unreleased Perks | High |
| Clean port on hooks | Homeward, Ladder Progress, Shovel Sense, Barn Labels, Crop Labels, Daily Checklist, Curious Neighbours, Nearby Affection, Big Rock Credit, Storage Anywhere | High for the first six, medium for the rest |
| Port with a changed mechanism | Instant Tools, Uncaught Sparkles, Uncaught Flora, Extra Perks (two of three perks), Vein Tools (mining only) | Medium |
| Only by patching a live menu after it opens | Field Notes, Map Name Labels | Low; untested idea |
| Reduced version only | Magic Skill | Medium that it works, high that it is worse |

Every ported mod loses its Accessibility checkbox or Controls entry; the toggle or key
moves to the config file, or to the Mod Configs tab with a restart.

## Mod by mod

**Mistria Notices.** `letters.toml` gains new tables, which is the merge's happy path.
Translations go in as overlays of the language tables. No code.

**Unreleased Perks.** Two `[[tier_5]]` appends, which MOMI's table-array merge does
verbatim. No code.

**Homeward.** `[homeward]` in `spells.toml` mints `Spell.Homeward` exactly as now. The
cast is a `spells.cast` override that returns handled for Homeward and undefined for
everything else; the gate is a `spells.can_cast` override the same way; both are
claim-scoped. Learning: `game.new_day` fires after the mana tick, and `save.game_loaded`
fires *before* the save is read, so the load-time check runs on the first frame after
load instead. Learning together with the very first spell has no hook, so that case
arrives a day late.

**Ladder Progress, Shovel Sense, Barn Labels.** Each is a per-frame update building
Anchor nodes on the Vitals canvas; `game.clock_tick` replaces the `step_end` anchor and
the engine calls they make are all public. The Accessibility toggle becomes a config
flag.

**Crop Labels, Daily Checklist.** Same as above plus a held key:
`mmapi_hotkey_binding_held` on a binding read from config. The "real, rebindable
control" in Settings > Controls is gone; a gamepad button can be configured but not
rebound in game.

**Curious Neighbours.** The per-villager check in `par_NPC`'s step becomes one tick over
all `par_NPC` instances. Nothing else changes.

**Nearby Affection.** The trigger moves from the talk and gift sites to the
`npc.heart_points` filter, which fires inside `add_heart_points` for the daily greeting
and for gifts. The handler must guard against its own bystander awards re-entering the
filter; the daily reset moves to `game.new_day`. Cutscene heart gains would also trigger
it, which the current mod ignores.

**Big Rock Credit.** `resource.node_picked` carries `grid, x, y, item, node, destroyed`,
enough to add the footprint-weighted score to `DUNGEON_RUNNER.ladder_score` when a large
rock or boulder dies. Vanilla scores those at zero, so nothing double-counts.

**Storage Anywhere.** `[chest_picker]` in `standard_menus.toml` mints `Menu.ChestPicker`
as now; the menu class ships as mod GML; the B key becomes a hotkey whose callback checks
`game_paused()`, seeds the stats entry, constructs the menu and pushes it onto
`ANCHOR.open_menus`. Inside the menu the two `InputId` reads and the binding hint become
config reads. Pins persist through `mmapi_config` instead of settings.json. Biggest
rewrite of the clean group, but nothing in it needs a seam.

**Instant Tools.** `resource.node_modifier` runs at the top of `chop_node` and
`pick_node` with the tool and the cell, so the handler can look up the node's hit points
and return a modifier that fells it in one hit, and charge the extra swings' stamina
itself through `ARI.modify_stamina`, refusing when it cannot afford them. Tarballs and
cutscenes are excluded by checking the item is Ari's held tool. Different code, same
behaviour.

**Uncaught Sparkles.** `obj_bug` has no seams. A tick that scans `obj_bug` instances,
attaches a twinkle to new ones, mirrors height and alpha, and destroys twinkles whose bug
is gone does the same job for a handful of instances per map.

**Uncaught Flora.** `object.node_sprite` fires inside every renderer's `set_sprite`
with the renderer as context, so the twinkle attaches there once per renderer. The
`orphan_dies` flag we added to `obj_animation_effect` is not available, so the same tick
cleans up twinkles whose renderer is gone.

**Extra Perks.** The three perks and their tree slots are data. Pathfinder hooks
`monster.death`; Curator's Eye hooks `museum.donate_item` and awards its bonus directly
through `modify_renown`, so it stops appearing as part of the ledger line. Well Spring
patches the sprinkler pass in `EndDay.gml`, which has no seam and runs before
`game.new_day`, so it cannot be reproduced. A MOMI version has two perks.

**Vein Tools.** Mining chains through `resource.node_picked`, calling the game's own
`pick_axe()` per connected rock behind a re-entrancy guard. Watering has nothing:
`Water.gml` has no seam and the watering swing is inside `AriFsm`. A MOMI version is
mining only.

**Field Notes.** The four Almanac categories can be added as data (the `categories`
array is replaced whole, so the overlay carries the vanilla entries too). The page
itself is built by our branch in `create_category`, which runs in the constructor. The
only route is `ui.menu_opened` for the Almanac: find the four category rows in
`category_scroller` (they are labelled `scroller_element_N` in creation order) and swap
their tap callbacks for our page builder bound to the menu. Whether a node's tap callback
can be replaced after the fact and whether children are enumerable has not been checked.

**Map Name Labels.** The head icons are children of `hub.node` for each hub in the global
`MAP_HUBS`, so a post-open pass can reach them, but the resident behind each icon is not
stored; it would have to be recovered by matching the sprite back to the villager whose
small icon it is. Possible, fragile, and not worth it for a tooltip.

**Magic Skill.** The mechanics port better than expected: `[magic]` in `skills.toml`,
the perks in `perks.toml`, and the tree as a real `ui/skill_menu/magic.toml` that the
shrine loads by itself; cost perks become one `spells.cost` filter, which is cleaner than
the bracketed deduction we patch in now; XP, Breath, Rain, Sacred Light, Second Wind,
Guardian Flame, Arcane Economy and Mistria's Bounty run from `spells.cast_done`; the
mana perks from `player.acquire_perk`; Dreamer's Well from `game.new_day`; Alchemist's
Draught from `items.use_guard` plus the `player.mana_delta` filter. What cannot be done:
the journal. `PlayerMenu.gml` hardcodes the skill list for the levels popup and ends its
colour switch in `impossible()`, so Magic can have no journal tile and no popup row, and
must not be added to the journal order or the journal crashes. The bespoke XP curve in
`Xp.gml` is lost to the vanilla default curve, and the shrine tile shows the borrowed
crafting icon uncovered. It would work, and it would be a lesser mod.

## Order of work, if the port happens

1. Homeward, Shovel Sense, Mistria Notices, Unreleased Perks, Ladder Progress, Barn
   Labels: small, clean, and the first three are what people asked for.
2. Crop Labels, Daily Checklist, Big Rock Credit, Curious Neighbours, Nearby Affection,
   Storage Anywhere.
3. Instant Tools, both Uncaught mods, Extra Perks without Well Spring, Vein Tools mining.
4. Leave on the framework: Field Notes, Map Name Labels, Magic Skill, Vein Tools
   watering, Well Spring.

Things to settle with a running game before the first upload: that MMAPI Mod Configs
works on MOMI 0.15.10, that a language-table overlay renders in a non-English game, and
how `mmapi_hotkey_binding_held` behaves while a menu is open.
