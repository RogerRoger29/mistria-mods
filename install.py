#!/usr/bin/env python3
"""Mistria Mods - installer.

Fields of Mistria compiles the GML shipped inside assets.zip at startup, so
these mods work by editing that source in place. Every insertion is wrapped in
marker comments, which makes each patch idempotent, removable byte-for-byte,
and safe to combine with the others.

    python install.py list
    python install.py status
    python install.py apply crop-labels vein-tools
    python install.py apply --all
    python install.py remove crop-labels
    python install.py remove --all
    python install.py apply vein-tools --max 400

Requires only the Python standard library. Run it from anywhere; it finds the
game folder as its own parent directory.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mistriamods import patcher, verifier
from mistriamods.registry import MODS, by_slug, GAME_DIR, ASSETS, BACKUP


def cmd_list(args):
    print("Mods available (%d):\n" % len(MODS))
    for mod in MODS:
        print("  %-20s %s" % (mod.SLUG.replace("_", "-"), mod.NAME))
        if mod.OPTIONS:
            for k, (ty, dv, help_) in mod.OPTIONS.items():
                print("  %-20s   --%s (default %s) %s" % ("", k, dv, help_))
    print("\nInstall with:  python install.py apply --all")


def cmd_status(args):
    archive = patcher.Archive(ASSETS)
    print("game folder : %s" % GAME_DIR)
    print("backup      : %s\n" % (os.path.basename(BACKUP)
                                  if os.path.exists(BACKUP) else "none yet"))
    for mod in MODS:
        on = patcher.is_installed(archive, mod)
        momi = patcher.momi_installed(archive, mod)
        print("  [%s] %-20s %s%s" % ("x" if on else ("M" if momi else " "),
                                     mod.SLUG.replace("_", "-"), mod.NAME,
                                     "  (MOMI package)" if momi else ""))


def _selected(args):
    if args.all:
        return list(MODS)
    if not args.mods:
        sys.exit("name at least one mod, or pass --all. See: python install.py list")
    return [by_slug(m) for m in args.mods]


def _options_for(mod, args):
    """The mod's options: its namespaced flag wins, then the bare flag."""
    opt = mod.defaults()
    for k in opt:
        v = getattr(args, mod.SLUG + "__" + k, None)
        if v is None:
            v = getattr(args, k, None)
        if v is not None:
            opt[k] = v
    return opt


def _report_check(mod, report):
    ok = all(good for _, good, _ in report)
    print("  [%s] %s" % ("x" if ok else "!", mod.SLUG.replace("_", "-")))
    for name, good, detail in report:
        if not good:
            print("        %s: %s" % (verifier.short(name), detail))
    return ok


def cmd_check(args):
    """Dry run: does every anchor of every selected mod match this archive?"""
    mods = list(MODS) if (args.all or not args.mods) else [by_slug(m) for m in args.mods]
    archive = patcher.Archive(ASSETS)
    print("archive : %s\n" % ASSETS)
    bad = 0
    for mod in mods:
        if not _report_check(mod, patcher.check_mod(archive, mod, _options_for(mod, args))):
            bad += 1
    print()
    if bad:
        sys.exit("%d mod(s) would not apply cleanly. Nothing was changed." % bad)
    print("all %d mod(s) would apply cleanly." % len(mods))


def cmd_apply(args):
    mods = _selected(args)
    archive = patcher.Archive(ASSETS)

    # Before anything is written: capture a copy with every known mod stripped
    # out, so the backup is genuinely clean even if mods are already installed.
    patcher.ensure_backup(archive, BACKUP, MODS)

    # Always re-apply from clean, so changing an option just works - and check
    # every anchor of every selected mod BEFORE writing anything, so a game
    # update reports the whole list of misses instead of aborting on the first.
    options = {mod.SLUG: _options_for(mod, args) for mod in mods}
    bad = 0
    kept = []
    for mod in mods:
        patcher.strip_mod(archive, mod)
        # A MOMI package of the same mod is already in the archive: the two
        # editions cannot coexist, so the framework's copy stays out (any
        # stale block of it was just stripped).
        if patcher.momi_installed(archive, mod):
            print("  - %-20s its MOMI package is installed; leaving it to MOMI"
                  % mod.SLUG.replace("_", "-"))
            continue
        kept.append(mod)
        report = patcher.check_mod(archive, mod, options[mod.SLUG])
        if not all(good for _, good, _ in report):
            _report_check(mod, report)
            bad += 1
    if bad:
        sys.exit("\n%d mod(s) would not apply cleanly - assets.zip was not changed." % bad)
    mods = kept

    for mod in mods:
        opt = options[mod.SLUG]
        patcher.apply_mod(archive, mod, opt)
        extra = " ".join("%s=%s" % (k, opt[k]) for k in sorted(opt))
        print("  + %-20s %s" % (mod.SLUG.replace("_", "-"), extra))

    print("rebuilding assets.zip ...")
    archive.save()
    print("done - %d mod(s) installed." % len(mods))


def cmd_remove(args):
    mods = _selected(args)
    archive = patcher.Archive(ASSETS)

    any_touched = False
    for mod in mods:
        touched = patcher.strip_mod(archive, mod)
        if touched:
            any_touched = True
            print("  - %s" % mod.SLUG.replace("_", "-"))

    if not any_touched:
        print("nothing to remove - none of those are installed.")
        return

    print("rebuilding assets.zip ...")
    archive.save()
    print("done.")


def main():
    p = argparse.ArgumentParser(
        description="Install Fields of Mistria mods.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Close the game before applying or removing.",
    )
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("list", help="show every mod and its options")
    sub.add_parser("status", help="show what is currently installed")

    for name, fn, help_ in (("apply", cmd_apply, "apply mods"),
                            ("remove", cmd_remove, "remove mods"),
                            ("check", cmd_check,
                             "dry run: report whether every anchor matches, change nothing")):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("mods", nargs="*", help="mod names, e.g. crop-labels")
        sp.add_argument("--all", action="store_true", help="every mod")
        sp.set_defaults(func=fn)

    # Per-mod options, hung off `apply` and `check`. Every option has a
    # namespaced flag (--nearby-affection-radius) that reaches one mod; the
    # bare flag (--radius) is registered once and reaches every mod that
    # declares that name, which matters with --all.
    declared = {}
    for mod in MODS:
        for k in mod.OPTIONS:
            declared.setdefault(k, []).append(mod.SLUG.replace("_", "-"))
    for ap in (sub.choices["apply"], sub.choices["check"]):
        seen = set()
        for mod in MODS:
            slug = mod.SLUG.replace("_", "-")
            for k, (ty, dv, help_) in mod.OPTIONS.items():
                flag = k.replace("_", "-")
                dest = mod.SLUG + "__" + k
                if ty is bool:
                    ap.add_argument("--no-%s-%s" % (slug, flag), dest=dest,
                                    action="store_false", default=None,
                                    help="disable, for %s only: %s" % (slug, help_))
                else:
                    ap.add_argument("--%s-%s" % (slug, flag), dest=dest, type=ty,
                                    default=None,
                                    help="for %s only: %s (default %s)" % (slug, help_, dv))
                if k in seen:
                    continue
                seen.add(k)
                note = ""
                if len(declared[k]) > 1:
                    note = " [shared by %s]" % ", ".join(declared[k])
                if ty is bool:
                    ap.add_argument("--no-" + k, dest=k, action="store_false",
                                    default=None, help="disable: " + help_ + note)
                else:
                    # Accept both --chest_key and --chest-key spellings.
                    names = ["--" + k]
                    if "_" in k:
                        names.append("--" + flag)
                    ap.add_argument(*names, type=ty, default=None,
                                    help="%s (default %s)%s" % (help_, dv, note))

    args = p.parse_args()
    if args.cmd == "list":
        return cmd_list(args)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd in ("apply", "remove", "check"):
        return args.func(args)
    p.print_help()


if __name__ == "__main__":
    main()
