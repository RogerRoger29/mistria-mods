#!/usr/bin/env python3
"""Mistria Mods - verifier.

Checks the live assets.zip against every registered mod: each patched file
carries exactly as many marker blocks as the mod declares for it, every block
is balanced on braces and parentheses, and (for information) which mods
MOMI's last run reports as applied.

    python verify.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mistriamods import verifier
from mistriamods.registry import MODS, ASSETS


def main():
    print("archive : %s\n" % ASSETS)
    problems = 0
    for mod, ok, details in verifier.verify_all(ASSETS, MODS):
        print("  [%s] %-20s %s" % ("x" if ok else "!",
                                   mod.SLUG.replace("_", "-"),
                                   "  ".join(details)))
        problems += 0 if ok else 1

    momi = verifier.momi_manifest()
    print()
    if momi is None:
        print("no MOMI manifest found (MOMI has not run on this machine)")
    else:
        print("MOMI reports %d mod(s) applied:" % len(momi))
        for m in momi:
            print("  - " + m)

    print()
    if problems:
        sys.exit("%d mod(s) have problems - see above." % problems)
    print("all %d mods verified." % len(MODS))


if __name__ == "__main__":
    main()
