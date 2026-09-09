# MOMI editions

Twelve of the mods, packaged for the Mods of Mistria Installer (MOMI) so they
install the way every other Fields of Mistria mod does: drop the folder or zip
into `mods/`, run MOMI, press Install. No second installer, no exe.

| Package | What it is | Needs |
| --- | --- | --- |
| `homeward` | The Homeward spell | MOMI 0.15.10 |
| `shovel_sense` | Dig sites give themselves away | MOMI 0.15.10 |
| `mistria_notices` | Nine milestone letters | MOMI 0.15.10 |
| `unreleased_perks` | Gemini Season and Ancient Inspiration in their trees | MOMI 0.15.10 |
| `ladder_progress` | The mine ladder readout | MOMI 0.15.10 |
| `barn_labels` | The animal card | MOMI 0.15.10 |
| `crop_labels` | Hold a key for a crop's name and days to harvest | MOMI 0.15.10 |
| `daily_checklist` | Hold a key for today's checklist | MOMI 0.15.10 |
| `curious_neighbours` | Villagers react to what you carry | MOMI 0.15.10 |
| `nearby_affection` | Bystanders share in a chat or gift | MOMI 0.15.10 |
| `big_rock_credit` | Big rocks count toward the ladder | MOMI 0.15.10 |
| `storage_anywhere` | Every chest in the world, from anywhere | MOMI 0.15.10 |

Each folder here is a complete MOMI mod: a `manifest.json`, its GML under
`gml/`, and any data it merges under `fiddle/` and `localization/`. The zips
on the Nexus page and the GitHub release are these folders, built by
`build_packages.py`.

## How they differ from the framework editions

The behaviour is the same. What changes is where the switches live.

- **Options and keys** are in a small JSON file MOMI's runtime keeps at
  `%LOCALAPPDATA%\FieldsOfMistria\mod_data\<mod>\<mod>.json`, created with
  defaults the first time the game runs. The keys are named after what they do
  (`enabled`, `key`, `radius_px`, ...) and the file also carries readable names
  for each, which the [MMAPI Mod Configs](https://www.nexusmods.com/fieldsofmistria/mods/779)
  mod shows under Settings as a "Mod Configs" tab. Changes take effect on the
  next launch. The framework editions put the same switches under Settings >
  Accessibility and Settings > Controls, which MOMI mods cannot reach.
- **Keys** use MMAPI's hotkey names: single letters and digits, `F1` to `F12`,
  `HOME`, `INSERT` and friends, and gamepad buttons such as
  `GAMEPAD_LEFT_TRIGGER`. Crop Labels, Daily Checklist and Storage Anywhere each
  accept a keyboard key and an optional gamepad button.
- **Other languages** get the English text where a language table has no entry,
  exactly as the framework editions do.
- **Storage Anywhere's pins** are kept in its config file rather than the
  game's settings file. Still never in the save.

## Do not install both editions of one mod

A MOMI package and the framework edition of the same mod define the same
functions and the same data, and the game will not boot with both. The
framework refuses to apply a mod whose MOMI package is already in the archive,
and tells you so. Going the other way, remove the framework edition first (or
let MOMI rebuild the archive, which removes every framework mod), then install
the package.

Run MOMI first, then the framework for anything not packaged here. MOMI
rebuilds `assets.zip` from its own backup every time it installs, which removes
every framework mod; apply them again afterwards.

## Building the zips

```bash
python momi/build_packages.py
```

Writes `nexus/momi/<Name>-<version>.zip` for every package, each with the
folder as its top level and a short README inside, which is the layout MOMI
expects (`mods/<folder>/manifest.json`).

## Checking a package before shipping

MOMI's own command-line build can lint a package against the game's pristine
archive without writing anything:

```bash
ModsOfMistriaInstaller-cli.exe --lint momi/homeward assets.bak.zip --strict-lints --compile-check on
```

Every package here passes with `--strict-lints` and with the compile gate on.
The gate needs MOMI's bundled `momi-gml-check.exe`, which a source build lacks;
the installed MOMI unpacks its copy under `%TEMP%\.net\ModsOfMistriaInstaller\`,
and `MOMI_GML_CHECKER` pointed at it makes `--compile-check require` work.
