# Magic Skill

A tenth skill: **Magic**. Cast spells to earn XP, level from 1 to 60, and buy
perks from a five-tier Magic tree on Seridia's shrine, gated at levels
1 / 15 / 30 / 45 / 60 like every other skill.

Status: **built and applied** (2026-08-31). The Magic tile appears beside
Mining and Combat on Seridia's shrine and on the journal's skill grid;
existing saves start at level 1 automatically. Three perks changed between
the reviewed design and the build — each because the engine disagreed with
the plan; see the tier tables and Build notes.

## Why this works (verified against the engine)

- `Skill` is minted from `skills.toml` — appending `[magic]` creates
  `Skill.Magic`. Every icon lookup goes through that file's `sprite` field.
- XP, levels, level-up toast and save/load are generic. The XP cost function
  has a safe `default:` curve; we add a `case Skill.Magic:` to tune pacing.
- The shrine's category screen reads rows from `ui/misc.toml`
  `[shrine_categories]`; the journal reads `player_menu_skill_category_order`.
  Both auto-center any count. Magic joins Seridia's row: mining, combat, magic.
- The tree is a prototype in the same shape as the nine `ui/skill_menu/*.toml`
  files, injected into the shrine loader's data right after it reads that
  directory — the archive writer cannot add files, so it is not a tenth file
  (see Build notes). Perks mint from `perks.toml` (extra-perks proved the
  pattern).
- Hand-written code needed: the XP hook in `cast_spell()`, one journal-popup
  ORDER/color patch, and one effect hook per perk below.

## Mana facts that shaped the list

- Mana does **not** refill on sleep — vanilla mornings grant exactly **+1
  mana** (`ARI.modify_mana(1)` in NewDay.gml, Dreamer's Well anchors right
  after it); otherwise only potions, Magical Meals infusions, and Mist
  cutscenes restore it. Base 16 mana (4 orbs of 4).
- Cost is deducted at two `ARI.modify_mana(-SPELLS[self.spell].cost)` sites in
  AriFsm.gml, and checked in `can_cast()` — a `magic_spell_cost(spell)` helper
  patched into all three gives us cost-modifying perks cleanly.
- Dragon's Breath cooldown = `fiddle_get("player").fire_breath_time_cap`, one
  site. Sacred Light is a status effect; `Speedy`/`Restorative` statuses exist
  to borrow. `acquire_perk()` has a precedent for permanent stat bumps on
  purchase (Guardian's Shield does `invulnerable_hits += 1`).

## XP

Per-cast constants (deliberately NOT scaled by mana cost, so the MOMI
2-mana mods don't distort leveling):

| Spell | XP |
| --- | --- |
| Dragon's Breath | 6 |
| Full Restore | 8 |
| Growth | 10 |
| Summon Rain | 12 |
| Sacred Light | 15 |

Curve (`case Skill.Magic` in `skill_level_individual_cost`): levels below 10
cost `(level - 1) * 6`; from 10 up, `54 + 4 * (level - 10)`. Total to 60 is
roughly 8,000 XP ≈ 800 casts — tier 2 in a couple of in-game weeks of casual
casting, max level a long-haul goal like the vanilla skills. Tunable at build;
Xp.gml's own parallel-test idiom verifies the curve.

## The tree — 19 perks (4 / 4 / 4 / 4 / 3, mining-tree density and costs)

### Tier 1 — level 1 (15–25 essence)

| Perk | Cost | Effect | Hook |
| --- | --- | --- | --- |
| **Attunement** | 25 | +4 max mana (a fifth orb) | `acquire_perk` stat-bump idiom |
| **Apprentice's Thrift** | 25 | All spells cost 1 less mana (min 1) | `magic_spell_cost` helper |
| **Deep Roots** | 20 | Growth advances trees 2 stages instead of 1 | extra pass in `magic_growth_extras()` |
| **Kindled Focus** | 20 | Dragon's Breath lasts 50% longer | `fire_breath_time_cap` site — the timer IS the duration; it doubles as the recast lock, so "cooldown" was the wrong frame |

### Tier 2 — level 15 (45–50 essence)

| Perk | Cost | Effect | Hook |
| --- | --- | --- | --- |
| **Second Wind** | 45 | Full Restore also grants Restorative regeneration for 90 in-game minutes | FullRestore case + the same `StatusEffectId.Restorative` regen food applies. (Changed: players never receive Frozen/Venomous — those are monster-only, so there was nothing to cure) |
| **Stormcaller** | 50 | Indoor Summon Rain lasts twice as long | `indoor_duration` read site |
| **Alchemist's Draught** | 45 | Mana restoratives restore double (potions + Magical Meals infusions) | potion-drink `mana_modifier` site |
| **Luminous Stride** | 50 | Sacred Light also grants Speedy while it lasts | SacredLight case + `StatusEffectId.Speedy` |

### Tier 3 — level 30 (75–85 essence)

| Perk | Cost | Effect | Hook |
| --- | --- | --- | --- |
| **Wide Growth** | 85 | Growth covers 5×5 instead of 3×3 | outer-ring pass mirroring the vanilla cell logic |
| **Dreamer's Well** | 80 | Wake every morning with mana fully restored | NewDay.gml, after the vanilla +1 |
| **Sunlit Depths** | 80 | Sacred Light shines twice as long | stretches the registered effect's own `finish`. (Replaced Blazing Trail: vanilla Dragon's Breath already fells trees and breaks rocks — its tarball ships with chop/pick/destroy flags at 999 damage) |
| **Arcane Economy** | 75 | 15% chance a cast refunds its full cost | deduction site + roll |

### Tier 4 — level 45 (150–155 essence)

| Perk | Cost | Effect | Hook |
| --- | --- | --- | --- |
| **Grand Wellspring** | 150 | +4 max mana again (six orbs with Attunement) | stat-bump idiom |
| **Verdant Rain** | 155 | Growth also waters every tile it touches | Growth case + per-tile water action (vein-tools precedent) |
| **Guardian Flame** | 150 | Dragon's Breath kindles a shield charge if none is banked; the first hit after the breath is absorbed | the breath's cap site in `cast_spell`, writing vanilla's own `invulnerable_hits` counter. (Changed in 1.2.0: the original "no damage while the breath burns" did nothing — vanilla already breaks out of its damage loop on `fire_breath_time > 0`) |
| **Ritualist** | 150 | Casting grants double Magic XP | our own XP hook |

### Tier 5 — level 60 (200–210 essence)

| Perk | Cost | Effect | Hook |
| --- | --- | --- | --- |
| **Twinflow** | 210 | All spell costs halved (after Thrift, min 1) | `magic_spell_cost` helper |
| **Eternal Flame** | 205 | Dragon's Breath lasts twice as long again (×3 with Kindled Focus) | same cap site. (Reframed: cooldown and duration are one timer) |
| **Mistria's Bounty** | 200 | Each cast has a 25% chance to conjure +5 essence | `magic_skill_on_cast()` + `ARI.modify_essence` |

Design rules honored: no overlap with the game's own magic-flavored perks
(Magical Meals, Magic Design, Mist Sight — all already placed in vanilla
trees; Alchemist's Draught deliberately *synergizes* with Magical Meals);
every effect anchors to a site verified in the live GML; each spell gets at
least two perks; the two "build-defining" QoL perks (Dreamer's Well, the max
mana orbs) pace the tree.

## Art (reuse only — atlases are prebuilt)

- `skills.toml` sprite: `spr_ui_hud_health_mana_bar_icon`.
- Shrine domain tile: the unused `spr_ui_skills_domain_icon_crafting` with two
  overlays that turn it into a magic tile — the composite is described under
  Build notes.
- Perk entry icons: the `_main` variants of the five
  `spr_ui_journal_magic_*_spell_icon` families, plus the mana-orb, mana-item
  and mana-potion sprites — the exact assignments are the tier entries in
  `magic_skill.py`.

## Build notes

- **The tree ships as a GML-injected prototype, not a new TOML file.** The
  archive writer only rewrites members that already exist, so instead of a
  `ui/skill_menu/magic.toml`, the prototype is `toml_data.set("magic", {...})`
  inserted right after `load_dragon_shrine_data()` reads the directory — it
  then flows through the same defaults, perk resolution and `{value}`
  description interpolation as the nine real files, and the loader's own
  `try_string_to_skill(key)` resolves it to `Skill.Magic`.
- **Every layout join is a guarded, idempotent array push** into cached
  fiddle data (Seridia's shrine row, the journal grid row, the popup's
  static ORDER) — insertions only, nothing edited in place, so removal is
  byte-exact and a game update that rearranges those rows degrades loudly at
  the anchor rather than silently.
- **Cost discounts bracket the vanilla charge.** A pre-block remembers the
  pre-cast mana, the vanilla `modify_mana(-cost)` runs untouched, and a
  post-block sets the exact discounted remainder; a mirror of
  `can_cast_spell`'s gate (active only when a cost perk is owned) answers
  from the discounted price so casts you can now afford aren't refused.
  The first version refunded the discount after the vanilla line instead —
  and `set_mana` clamps at zero, so casting at exactly 1 mana took 1,
  refunded 1, and the pool never emptied (the "stuck at a quarter orb" bug
  found in play). Charging `before - due` is exact at every boundary and
  lands on precisely the vanilla value when no cost perk is owned.
- The mana orbs from Attunement / Grand Wellspring use the Guardian's Shield
  purchase idiom in `acquire_perk()` — `mana_max` is a serialized stat, so
  they persist in the save (and survive uninstall as a harmless leftover).
- The spell journal's cost readout shows the **undiscounted** cost (it reads
  `spell_data.cost` directly); the real charge is the discounted one.
- **`icon_key` strings are not assets** — the first launch crashed at boot on
  `requested asset "spr_ui_journal_magic_growth_spell_icon" does not exist`.
  spells.toml's `icon_key` values are sprite-key *families*: `load_spells()`
  deliberately skips `string_to_asset()` on that one field, and the journal
  resolves it through `set_sprites_from_key()`, which appends a state suffix —
  the real assets are `..._spell_icon_main` / `..._spell_icon_locked`. The
  shrine loader, by contrast, converts every tree entry icon with
  `string_to_asset()` at boot, so a key-family name detonates before the
  title screen. All ten spell-perk icons now use the `_main` variants (same
  artwork, real assets). The mod's verify step now audits every sprite
  string in every block against the archive's `.meta.toml` registry; the
  category tile's `spr_ui_skills_domain_icon_crafting` resolves via its
  `_enabled`/`_hovered` family, the exact structure every vanilla domain
  icon ships with — none has a `_disabled` variant, mount included.
- **The shrine loader's `{field}` description interpolation is dead code** —
  it looks like it substitutes `{value}` from the perk's own fields, zero
  vanilla perks use it, and in practice the pattern comes through literally
  (`All spells cost {value} less mana.`). Numbers are now hardcoded in the
  descriptions, exactly as every vanilla perk does — keep them in sync with
  the `value` fields by hand when tuning.
- **Category names are localization keys, not strings** — the tile's bubble
  and the tree header render via `local_get()`/`set_key()`, which answer
  literal "MISSING" for an unknown key. A raw `"Magic"` is not a fallback the
  way the mount tree's rendering suggested. Fix: `magic_skill_category =
  "Magic"` appended to misc_local.toml (the shared label file crop-labels,
  daily-checklist and storage-anywhere already append to) and the prototype's
  `name` set to `"misc_local/magic_skill_category"`.
- **The same is true in every other language, one level up.** misc_local.toml
  and perks.toml are only the English source; a French or Japanese game
  looks each key up in its own translation table and shows MISSING for the
  category name and all 38 perk strings. The mod declares its text in
  `TRANSLATE` and the framework appends it, in English, to all seven
  translation tables — the general fix every text-adding mod uses.
- **The shrine tile is a three-layer composite**: the unused crafting domain
  tile underneath (keeps the frame, hover-variant swap and pilot wiring), the
  shrine's own blank `spr_ui_skills_skill_slot_white` centered over it to
  blank the baked-in tool glyph, and `spr_ui_journal_magic_header_icon` — the
  game's magic sparkle — stamped on top. Chosen by compositing the candidates
  from the atlas PNGs and looking at them, not by name. Hover feedback stays
  the name bubble (keyed off `tile.is_hovered`, unaffected by the overlays).
- Remaining perk-entry icons were chosen for *fit* — swap any that look wrong
  in game by editing the tier entries in `magic_skill.py` and re-applying.

## Game 1.0.4 and the MMAPI base (2026-09-04)

After the game updated to 1.0.4 and MOMI 0.15.10 installed its MMAPI code
layer (Poly Marriage, The Perfect Gift), four anchors here stopped matching —
not because 1.0.4 changed those lines, but because MMAPI's *seams* rewrote
them and left a `// mmapi_*` comment on each:

| Site | Now anchored on |
| --- | --- |
| both spell-cost deductions | `ARI.modify_mana(-mmapi_apply_filters("spells.cost", …));` — one anchor cut at the semicolon and expected twice, so the two sites' differing trailing comments (`// mmapi_spell_loop_cost`, `// mmapi_spell_default_cost`) don't matter |
| the mana potion | `ARI.modify_mana(self.live_item.prototype.mana_modifier); // mmapi_player_mana_item_delta` (the bonus now uses `modify_mana` too) |
| the damage gate | `if ARI.invulnerable_hits <= 0 {` followed by `var defense = …` (MMAPI moved `took_damage` into its flinch logic) |
| the can-cast mirror | after MMAPI's `spells.can_cast` override return, so a mod's override still wins |

Both forms are carried as `Alternatives`, so the mod applies with or without
MOMI. With MMAPI present, the cost mirror and the deduction hand
`magic_spell_cost()` MMAPI's filtered price — `mmapi_apply_filters("spells.cost", …)`,
exactly what the vanilla gate beside them reads — so a mod that filters spell
costs is honoured; on a bare game they pass the base `SPELLS[spell].cost`.
The helper itself never names an `mmapi_*` function, which only exists with
MOMI's layer present.

## Caveats

1. **Uninstalling after the save has Magic XP**: the save keeps a `magic`
   key in `skill_xp`. On load without the mod it reaches the strict
   `string_to_skill` — but inside `apply_struct_to_array`, whose guard skips
   non-numeric results unless `DEBUG_ASSERTIONS` is on, and the shrine
   loader itself uses the forgiving `try_string_to_skill`. Evidence leans
   "release builds skip it silently," but it is unverified against the
   native converter — **test on a throwaway save before uninstalling a
   leveled playthrough.** Purchased perks are uninstall-safe (`try_string_to_perk`),
   and the mana_max bumps simply persist.
2. Existing saves start Magic at level 1 automatically (name-keyed load).
3. `[magic]` sits at the END of skills.toml so existing enum indices hold.
4. Verify in game, first session: the Magic tile on Seridia's shrine (icon
   is the unused "crafting" domain icon, Mistmare's LUT recolor), the tenth
   journal tile, an XP toast from any cast, and — with five-plus orbs after
   Attunement — that the vitals HUD renders the extra orbs sanely.
5. **The "one tier-5 perk per category" achievement** is computed from the
   shrine data at run time, so a tenth tree would have become a tenth
   requirement — a player midway through it would have seen it un-tick. The
   mod skips the Magic tree in that count (a one-line guard in
   `get_tier_five_perks_by_category()`), so the achievement stays the vanilla
   nine categories. The requirement is derived, not saved, so removing the
   mod restores vanilla either way.
6. **A cutscene's Dragon's Breath** goes through `cast_spell` too; the XP
   hook returns early while the Mist is running, so scripted breaths teach
   nothing and never roll Mistria's Bounty.
