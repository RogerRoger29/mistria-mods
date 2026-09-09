#!/usr/bin/env python3
"""Zip every MOMI package under momi/ into nexus/momi/.

Each zip holds the package folder as its top level, which is the layout MOMI
expects (mods/<folder>/manifest.json), plus a short README.txt built from the
manifest. Run from anywhere:

    python momi/build_packages.py
    python momi/build_packages.py homeward shovel_sense
"""

import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "nexus", "momi")

README = """{name} {version}
{underline}

{description}

A MOMI mod. Put this folder inside your Fields of Mistria "mods" folder, so
the layout is mods/{folder}/manifest.json, then run the Mods of Mistria
Installer and press Install.

Options, when the mod has any, live in
  %LOCALAPPDATA%\\FieldsOfMistria\\mod_data\\{folder}\\{folder}.json
which the game creates with defaults on its first launch after installing.
Edit it with the game closed, or through the "MMAPI Mod Configs" mod
(Settings > Mod Configs); changes take effect on the next launch.

This is the MOMI edition of the mod of the same name from Mistria Mods
(https://github.com/RogerRoger29/mistria-mods). Do not install both editions
at once.
"""


def packages(selected):
    for folder in sorted(os.listdir(HERE)):
        path = os.path.join(HERE, folder)
        if not os.path.isdir(path) or not os.path.exists(os.path.join(path, "manifest.json")):
            continue
        if selected and folder not in selected:
            continue
        yield folder, path


def build(folder, path):
    with open(os.path.join(path, "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    name = manifest["name"]
    version = manifest["version"]
    readme = README.format(
        name=name,
        version=version,
        underline="=" * (len(name) + len(version) + 1),
        description=manifest.get("description", ""),
        folder=folder,
    )
    out = os.path.join(OUT, "%s-%s.zip" % (name.replace(" ", ""), version))
    os.makedirs(OUT, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames.sort()
            for filename in sorted(filenames):
                full = os.path.join(dirpath, filename)
                rel = os.path.relpath(full, HERE).replace(os.sep, "/")
                z.write(full, rel)
        z.writestr("%s/README.txt" % folder, readme)
    return out


def main(argv):
    selected = set(argv)
    built = [build(folder, path) for folder, path in packages(selected)]
    if not built:
        sys.exit("no packages matched")
    for out in built:
        print("  %s (%d bytes)" % (os.path.relpath(out, ROOT), os.path.getsize(out)))


if __name__ == "__main__":
    main(sys.argv[1:])
