"""Which mods exist, and where the game is.

Apply order does not matter - the mods use distinct markers and their anchors
survive each other - but the list is kept in a readable order for `list` and
`status` output.
"""

import os
import sys

from .mods import (
    nearby_affection,
    curious_neighbours,
    map_name_labels,
    instant_tools,
    vein_tools,
    crop_labels,
    ladder_progress,
    mistria_notices,
    extra_perks,
    unreleased_perks,
    daily_checklist,
    big_rock_credit,
    storage_anywhere,
    magic_skill,
    uncaught_sparkles,
    uncaught_flora,
    shovel_sense,
)

MODS = [
    nearby_affection,
    curious_neighbours,
    map_name_labels,
    instant_tools,
    vein_tools,
    crop_labels,
    ladder_progress,
    mistria_notices,
    extra_perks,
    unreleased_perks,
    daily_checklist,
    big_rock_credit,
    storage_anywhere,
    magic_skill,
    uncaught_sparkles,
    uncaught_flora,
    shovel_sense,
]

def looks_like_game(path):
    """The game folder: assets.zip beside the engine's own Maybe.toml."""
    return (os.path.isfile(os.path.join(path, "assets.zip"))
            and os.path.isfile(os.path.join(path, "Maybe.toml")))


def find_game_dir():
    """Where the game is, or None.

    From source, install.py lives in <game>/mistria-mods/, so the game folder
    is the package's grandparent. The standalone exe is meant to sit in the
    game folder itself, like MOMI, so the executable's folder is tried first
    when frozen. The working directory is the last resort.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.dirname(os.path.abspath(sys.executable)))
    candidates += [
        os.path.dirname(os.path.dirname(here)),
        os.path.dirname(here),
        os.getcwd(),
    ]
    for path in candidates:
        if looks_like_game(path):
            return path
    return None


GAME_DIR = find_game_dir() or os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(GAME_DIR, "assets.zip")
BACKUP = os.path.join(GAME_DIR, "assets.vanilla.zip")


def set_game_dir(path):
    """Point the registry at a game folder chosen at runtime (the GUI)."""
    global GAME_DIR, ASSETS, BACKUP
    GAME_DIR = path
    ASSETS = os.path.join(path, "assets.zip")
    BACKUP = os.path.join(path, "assets.vanilla.zip")


def by_slug(name):
    want = name.replace("-", "_").lower()
    for mod in MODS:
        if mod.SLUG == want:
            return mod
    sys.exit(
        "unknown mod %r. Known: %s"
        % (name, ", ".join(m.SLUG.replace("_", "-") for m in MODS))
    )
