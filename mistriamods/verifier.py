"""Checks the live assets.zip against every registered mod.

Shared by verify.py and the GUI. Reads the archive lazily - a verification
touches a few dozen members, not all 122,000 - so it stays fast and light
enough to run on every refresh.
"""

import json
import os
import re
import zipfile

from . import patcher


class ZipView(object):
    """A read-only, lazy stand-in for patcher.Archive.

    Exposes the two things the checks use - `name in archive.files` and
    `archive.read(name)` - without loading 600 MB into memory.
    """

    def __init__(self, path):
        self.path = path
        self._zip = zipfile.ZipFile(path)
        self.files = set(self._zip.namelist())

    def read(self, name):
        return self._zip.read(name).decode("utf-8")

    def close(self):
        self._zip.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def momi_manifest():
    """Mods MOMI's last run reports as applied, or None without a manifest."""
    manifest = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                            "FieldsOfMistria", "mods", "manifest.json")
    if not os.path.exists(manifest):
        return None
    with open(manifest, encoding="utf-8") as f:
        data = json.load(f)
    return ["%s (%s)" % (m.get("name"), m.get("version"))
            for m in data.get("mods", [])]


def short(name):
    """A file name that stays unambiguous: the fourteen localization tables
    share their basenames across translations/ and source_caches/."""
    parts = name.split("/")
    if "localization" in parts:
        return "/".join(parts[-2:])
    return parts[-1]


def verify_mod(archive, mod):
    """(ok, [details]) for one mod: the right number of marker blocks in every
    patched file, every block balanced on braces and parentheses."""
    tag = mod.SLUG.upper()
    details = []
    for name, edits in patcher.mod_edits(mod, mod.defaults()).items():
        if name not in archive.files:
            details.append("%s: missing from archive" % short(name))
            continue
        text = archive.read(name)
        toml = name.endswith(".toml")
        lead = "# " if toml else "// "
        begin = text.count(lead + ">>> %s_BEGIN" % tag)
        end = text.count(lead + "<<< %s_END" % tag)

        # Expected blocks: judged on the stripped text so the right anchor
        # alternative is chosen, then blocks-per-site times sites.
        stripped = patcher.strip_file(mod, name, text, edits)
        want = 0
        for edit in edits:
            chosen = patcher.resolve_edit(stripped, edit)
            if chosen is None:
                details.append("%s: no anchor alternative matches"
                               % short(name))
                continue
            _, replacement, expected = chosen
            want += replacement.count(">>> %s_BEGIN" % tag) * expected
        if not (begin == end == want):
            details.append("%s: blocks %d/%d, expected %d"
                           % (short(name), begin, end, want))
        if not toml:
            pat = re.compile(re.escape(lead + ">>> %s_BEGIN" % tag)
                             + r"(.*?)" + re.escape(lead + "<<< %s_END" % tag),
                             re.S)
            for m in pat.finditer(text):
                blk = m.group(1)
                if blk.count("{") != blk.count("}") or blk.count("(") != blk.count(")"):
                    details.append("%s: unbalanced block" % short(name))
    # Fourteen tables missing the same block is one problem, not fourteen.
    tables = [d for d in details if d.startswith(("translations/", "source_caches/"))]
    if len(tables) > 1:
        rest = [d for d in details if d not in tables]
        problems = sorted({d.split(": ", 1)[1] for d in tables})
        details = rest + ["%d localization tables: %s"
                          % (len(tables), "; ".join(problems))]
    return (not details, details)


def verify_all(archive_path, mods):
    """[(mod, ok, [details]), ...] for every mod, against one archive."""
    with ZipView(archive_path) as archive:
        return [(mod,) + verify_mod(archive, mod) for mod in mods]


def installed_states(archive_path, mods):
    """{slug: bool} - which mods are present in the archive right now."""
    with ZipView(archive_path) as archive:
        return {mod.SLUG: patcher.is_installed(archive, mod) for mod in mods}
