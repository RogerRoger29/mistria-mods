# Unreleased Perks

Two finished perks the game defines but never puts in a skill tree.

| Perk | Tree | Effect | Implemented in |
| --- | --- | --- | --- |
| **Gemini Season** | Ranching | Animals can bear twins | `Stable.gml` |
| **Ancient Inspiration** | Blacksmithing | Weekly chance to be inspired with a new recipe | `Ari.gml`, `CraftingMenu.gml` |

## Install / uninstall

```bash
python mistria-mods/install.py status
```

```bash
python mistria-mods/install.py apply unreleased-perks
```

```bash
python mistria-mods/install.py remove unreleased-perks
```

## What this actually is

`perks.toml` defines **169** perks. The ten skill trees between them list
**167**. The two left over aren't stubs — both have a working implementation in
the shipped GML, and both already have artwork drawn for them, sitting in the
icon atlas next to perks you can buy.

Nothing references them. No tree lists them, so there is no way to acquire
either one in a normal game.

**Enabling this means playing content the developers haven't released yet.** It
may arrive properly in a patch, possibly in a different tree, at a different
cost, or balanced differently. That's the trade.

## Placement

No new code and no new perk definitions — only tree entries.

Each perk goes where its own artwork says it belongs. Gemini Season keeps its
`spr_ui_skills_ranching_` icon and takes ranching's last free tier 5 slot;
Ancient Inspiration keeps its `spr_ui_skills_crafting_` icon and goes to
blacksmithing. Costs are 200 and 205 essence, matching the tier 5 band around
them.

## Correction: it used to claim five

An earlier version of this mod listed five orphans and also placed
`horsepower`, `harvest_horse` and `nice_ride` into farming and blacksmithing.

That was wrong. All three are already in the game, in
`ui/skill_menu/mount.toml` — a full eleventh tree named **Mistmare**, with its
own domain icon and LUT set. You reach it at the **horse statue in the
Narrows**, which `world_mod.toml` gates behind the `repaired_horse_statue`
requirement (the `find_the_weathervane_setup` cutscene). Interacting with it
while mounted spawns `ShrineMenuVariant.Horse`, a third dragon-shrine variant
built specifically for that tree.

The trap: **mount is not a Skill.** `load_dragon_shrine_data()` runs
`try_string_to_skill("mount")`, gets `undefined`, and the Horse variant returns
a flat level 1 rather than a skill level. So any tree list derived from the
`Skill` enum — which is how the original list was built — silently drops exactly
the tree that was designed to sit outside it.

The check that holds is deriving the list from the tree files themselves:

```bash
python -c "import zipfile,re; z=zipfile.ZipFile('assets.vanilla.zip'); t=''.join(z.read(n).decode() for n in z.namelist() if '/skill_menu/' in n); p=set(re.findall(r'^\[([a-z_0-9]+)\]', z.read('assets/fiddle/perks.toml').decode(), re.M))-{'default'}; print(sorted(p-set(re.findall(r'perk = \"([a-z_0-9]+)\"', t))))"
```

Nothing broke while the claim was wrong — `entry_is_acquired()` reads
`ARI.perks[entry.perk]`, indexed globally by perk id, so a perk bought in one
tree already showed as acquired in the other. The duplicate entries were an
alternate purchase route that skipped the statue quest, not a double spend.

## Notes

- Removing this mod removes the perks. If you had bought one, the game no longer
  knows it exists — buy back into something else.
- Independent of **extra-perks**; both can be installed together.
