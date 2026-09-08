"""Shared plumbing for the Mistria mods.

Every mod is a set of exact-text insertions into the GML and TOML that ship
inside assets.zip. This module owns everything the mods have in common: marker
blocks, applying and removing them, the backup, and rewriting the archive
safely. Mods themselves only declare their anchors and their injected code.

Fields of Mistria compiles the GML in assets.zip at startup with an embedded VM
called `fabricator`, which is why editing that source works at all.
"""

import os
import re
import sys
import tomllib
import zipfile


class Markers(object):
    """Builds and finds one mod's marker blocks.

    Insertions are wrapped in BEGIN/END comments so a patch can be removed
    byte-exactly and re-applied from clean. GML takes `//`, TOML takes `#`.
    """

    APPEND = "\x00APPEND\x00"

    def __init__(self, slug, legacy=None):
        tag = slug.upper()
        self.begin = "// >>> %s_BEGIN" % tag
        self.end = "// <<< %s_END" % tag
        self.tbegin = "# >>> %s_BEGIN" % tag
        self.tend = "# <<< %s_END" % tag

        # GML and TOML need DIFFERENT conventions, and conflating them corrupts
        # files. GML blocks are mostly inserted *between two lines of code*, and
        # each block already carries its own trailing newline - so the pattern
        # must NOT consume a leading newline, or removal glues the line above to
        # the line below. TOML blocks are only ever appended, to a file with no
        # trailing newline of its own, so there the append supplies a newline
        # and removal has to reclaim exactly that one.
        self.gml_re = re.compile(
            r"[ \t]*" + re.escape(self.begin) + r".*?"
            + re.escape(self.end) + r"[ \t]*\n?",
            re.DOTALL,
        )
        self.toml_re = re.compile(
            r"\n?[ \t]*" + re.escape(self.tbegin) + r".*?"
            + re.escape(self.tend) + r"[ \t]*\n?",
            re.DOTALL,
        )
        # A TOML block inserted after an anchor line (inside an array, say)
        # sits on lines of its own, exactly like a GML block: it must not
        # reclaim the newline that ends the line above it.
        self.toml_inline_re = re.compile(
            r"[ \t]*" + re.escape(self.tbegin) + r".*?"
            + re.escape(self.tend) + r"[ \t]*\n?",
            re.DOTALL,
        )
        # The appended block, when a file also carries inline ones: it is the
        # last thing in the file.
        self.toml_tail_re = re.compile(
            r"\n?[ \t]*" + re.escape(self.tbegin) + r".*?"
            + re.escape(self.tend) + r"[ \t]*\n?\Z",
            re.DOTALL,
        )

        # Blocks shipped under an older marker name, so upgrades strip cleanly.
        self.legacy_res = []
        for old in (legacy or []):
            # GML convention, same as gml_re: no leading \n?.
            self.legacy_res.append(re.compile(
                r"[ \t]*" + re.escape("// >>> %s_BEGIN" % old) + r".*?"
                + re.escape("// <<< %s_END" % old) + r"[ \t]*\n?",
                re.DOTALL,
            ))

    def block(self, body, indent="", toml=False):
        b, e = (self.tbegin, self.tend) if toml else (self.begin, self.end)
        lines = [indent + b]
        lines += [(indent + l).rstrip() for l in body.strip("\n").split("\n")]
        lines.append(indent + e)
        return "\n".join(lines) + "\n"

    def strip(self, text, toml=False, mode="append"):
        """Remove this mod's blocks.

        For TOML the caller says how the blocks got there - strip_file()
        works it out from the mod's edits: "append" (every block was appended,
        each owning the newline before it), "inline" (every block was
        inserted after an anchor line), or "mixed".
        """
        if not toml:
            out = self.gml_re.sub("", text)
            for r in self.legacy_res:
                out = r.sub("", out)
            return out
        if mode == "append":
            return self.toml_re.sub("", text)
        if mode == "mixed":
            text = self.toml_tail_re.sub("", text)
        return self.toml_inline_re.sub("", text)

    def present_in(self, text, toml=False):
        return (self.tbegin if toml else self.begin) in text

    def block_in(self, text, toml=False):
        """The mod's own block, for status checks that must not scan the file."""
        m = (self.toml_re if toml else self.gml_re).search(text)
        return m.group(0) if m else ""


ANY_MARKER_RE = re.compile(r"(?://|#) >>> [A-Z_]+_BEGIN")


class Alternatives(object):
    """One edit with several candidate anchors, tried in order.

    The same game line can exist in more than one form - vanilla, or as
    rewritten by MOMI's MMAPI layer - and a mod that must work on both gives
    each form its own (anchor, replacement[, expected]) candidate. The first
    candidate whose anchor matches its expected count is the one applied.
    """

    def __init__(self, *candidates):
        self.candidates = [
            (c[0], c[1], c[2] if len(c) > 2 else 1) for c in candidates
        ]


def edit_candidates(edit):
    """Every (anchor, replacement, expected) an edit could apply as."""
    if isinstance(edit, Alternatives):
        return edit.candidates
    return [(edit[0], edit[1], edit[2] if len(edit) > 2 else 1)]


def resolve_edit(text, edit):
    """The candidate that fits `text`, or None when none does."""
    for anchor, replacement, expected in edit_candidates(edit):
        if anchor == Markers.APPEND or text.count(anchor) == expected:
            return anchor, replacement, expected
    return None


def describe_miss(text, edit):
    """Why no candidate fit: each anchor's first line and its count."""
    parts = []
    for anchor, _, expected in edit_candidates(edit):
        head = anchor.strip().split("\n")[0][:70]
        parts.append("%r matched %d, expected %d" % (head, text.count(anchor), expected))
    return "; ".join(parts)


def check_mod(archive, mod, opt=None):
    """Dry-run one mod against the archive: [(file, ok, detail), ...].

    Judged on the text with the mod's own blocks stripped, so an installed
    mod checks the same as an uninstalled one.
    """
    opt = mod.defaults() if opt is None else opt
    report = []
    for name, edits in mod_edits(mod, opt).items():
        if name not in archive.files:
            report.append((name, False, "not in assets.zip"))
            continue
        text = strip_file(mod, name, archive.read(name), edits)
        problems = []
        for edit in edits:
            if resolve_edit(text, edit) is None:
                problems.append(describe_miss(text, edit))
        report.append((name, not problems, "; ".join(problems)))
    return report


class Archive(object):
    """assets.zip, loaded into memory and rewritten atomically."""

    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            sys.exit("could not find " + path)
        with zipfile.ZipFile(path) as z:
            self.infolist = list(z.infolist())
            self.files = {i.filename: z.read(i.filename) for i in self.infolist}

    def read(self, name):
        if name not in self.files:
            sys.exit(
                "%s is not in assets.zip - the game was probably updated, and "
                "this mod needs its anchors rechecked." % name
            )
        return self.files[name].decode("utf-8")

    def write(self, name, text):
        self.files[name] = text.encode("utf-8")

    def has_any_mod(self):
        """True if any marker-based mod is currently installed."""
        for name, data in self.files.items():
            if name.endswith((".gml", ".toml")):
                if ANY_MARKER_RE.search(data.decode("utf-8", "replace")):
                    return True
        return False

    def save(self):
        tmp = self.path + ".tmp"
        try:
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED,
                                 allowZip64=True) as out:
                for info in self.infolist:
                    ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                    ni.compress_type = info.compress_type
                    ni.external_attr = info.external_attr
                    ni.internal_attr = info.internal_attr
                    ni.create_system = info.create_system
                    out.writestr(ni, self.files[info.filename])
                # Land the bytes on disk before the rename, so a power cut can
                # not leave a present-but-truncated assets.zip.
                out.fp.flush()
                os.fsync(out.fp.fileno())
            os.replace(tmp, self.path)
        except PermissionError:
            _unlink(tmp)
            sys.exit(NOT_WRITABLE % "assets.zip")
        except BaseException:
            # Never leave a ~600 MB orphan behind on disk-full, Ctrl-C, etc.
            _unlink(tmp)
            raise


# Windows reports both "the game has it open" and "you may not write here"
# as PermissionError, so the message covers both.
NOT_WRITABLE = (
    "could not write %s.\n"
    "Either the game is running - close Fields of Mistria and try again - or "
    "this folder is not writable: run the installer as administrator, or move "
    "the game out of Program Files."
)


def _unlink(path):
    try:
        if os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass


def ensure_backup(archive, backup_path, mods):
    """Save a pristine copy of assets.zip, once.

    The subtlety: by the time a second mod is installed the archive is no
    longer vanilla, so copying it verbatim would enshrine a modded archive as
    the "original". Instead every known mod is stripped from a copy first -
    removal is byte-exact, so the result is genuinely clean.
    """
    if os.path.exists(backup_path):
        return

    clean = dict(archive.files)
    for mod in mods:
        for name in mod_files(mod):
            if name not in clean:
                continue
            text = clean[name].decode("utf-8")
            edits = mod_edits(mod, mod.defaults())[name]
            clean[name] = strip_file(mod, name, text, edits).encode("utf-8")

    tmp = backup_path + ".tmp"
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED, allowZip64=True) as out:
            for info in archive.infolist:
                ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                ni.compress_type = info.compress_type
                ni.external_attr = info.external_attr
                ni.internal_attr = info.internal_attr
                ni.create_system = info.create_system
                out.writestr(ni, clean[info.filename])
            out.fp.flush()
            os.fsync(out.fp.fileno())
        os.replace(tmp, backup_path)
    except PermissionError:
        _unlink(tmp)
        sys.exit(NOT_WRITABLE % os.path.basename(backup_path))
    except BaseException:
        _unlink(tmp)
        raise

    print("saved a clean backup -> " + os.path.basename(backup_path))


# --- localization fallbacks --------------------------------------------------
#
# The game's translations are keyed by path ("misc_local/skills",
# "perks/pathfinder/name", "letters/<id>/local") in one table per language,
# with a matching source cache holding the English each translation was made
# from. A key with no entry in the active language's table renders as the
# literal word "MISSING" - so every label, perk and letter a mod adds must
# also be appended, in English, to all seven non-English tables. A mod
# declares what it added with
#
#     TRANSLATE = {"misc_local": LABELS, "perks": PERK_DEFS, "letters": ...}
#
# mapping a key prefix to the very TOML text the mod appends, and the entries
# are derived from that text, so they can never drift from it.

LANGUAGES = ("fra", "jpn", "kor", "rus", "spa", "zh-Hans", "zh-Hant")

TRANSLATION_FILES = (
    ["assets/localization/translations/%s.meta.toml" % l for l in LANGUAGES]
    + ["assets/localization/source_caches/%s.meta.toml" % l for l in LANGUAGES]
)

# The fields of a table (a perk, a letter, a spell) that carry player-visible
# text. A spell's `type` is a localized label too ("Farming", "Utility").
LOCALIZED_FIELDS = ("name", "description", "subject_line", "local", "type")


def toml_string(value):
    """A TOML string spelled exactly as the game's own tables spell it.

    The engine's parser is only ever exercised by what ships: basic strings
    with no escape sequences, literal strings when the text holds a double
    quote, and triple-quoted strings (opening delimiter on its own line) when
    it spans lines. So this writes those three forms and nothing else, and
    refuses text that would need an escape rather than guess at support.
    """
    if "\\" in value or '"""' in value:
        raise ValueError("cannot spell %r without a TOML escape" % value)
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError("control character in %r" % value)
    if "\n" not in value:
        if '"' not in value:
            return '"' + value + '"'
        if "'" not in value:
            return "'" + value + "'"
    if value.endswith('"'):
        raise ValueError("cannot spell %r without a TOML escape" % value)
    if "\n" in value:
        return '"""\n' + value + '"""'
    return '"""' + value + '"""'


def translation_entries(sections):
    """'"prefix/key" = "English"' lines for every string in the sections."""
    lines = []
    for prefix, toml_text in sections.items():
        for key, value in tomllib.loads(toml_text).items():
            if isinstance(value, str):
                lines.append('"%s/%s" = %s' % (prefix, key, toml_string(value)))
            elif isinstance(value, dict):
                for field in LOCALIZED_FIELDS:
                    if isinstance(value.get(field), str):
                        lines.append('"%s/%s/%s" = %s'
                                     % (prefix, key, field, toml_string(value[field])))
    return "\n".join(lines)


def mod_edits(mod, opt):
    """A mod's patches plus the localization fallbacks its TRANSLATE implies."""
    edits = dict(mod.patches(mod.markers, opt))
    sections = getattr(mod, "TRANSLATE", None)
    if sections:
        text = translation_entries(sections)
        if text:
            for path in TRANSLATION_FILES:
                edits[path] = [(Markers.APPEND, mod.markers.block(text, toml=True))]
    return edits


def mod_files(mod):
    """Every archive path a mod touches."""
    return list(mod_edits(mod, mod.defaults()).keys())


def strip_mode(edits):
    """How a file's TOML blocks were placed: "append", "inline" or "mixed"."""
    appended = set()
    for edit in edits:
        for anchor, _, _ in edit_candidates(edit):
            appended.add(anchor == Markers.APPEND)
    if appended == {True} or not appended:
        return "append"
    if appended == {False}:
        return "inline"
    return "mixed"


def strip_file(mod, name, text, edits):
    """The file's text with this mod's blocks removed, byte-exactly."""
    toml = name.endswith(".toml")
    return mod.markers.strip(text, toml=toml, mode=strip_mode(edits) if toml else "append")


def strip_mod(archive, mod):
    """Remove a mod's blocks. Returns the paths that actually changed."""
    touched = []
    for name, edits in mod_edits(mod, mod.defaults()).items():
        text = archive.read(name)
        cleaned = strip_file(mod, name, text, edits)
        if cleaned != text:
            touched.append(name)
        archive.write(name, cleaned)
    return touched


def apply_mod(archive, mod, opt):
    """Insert a mod's blocks. Assumes strip_mod ran first."""
    for name, edits in mod_edits(mod, opt).items():
        toml = name.endswith(".toml")
        text = archive.read(name)

        for edit in edits:
            chosen = resolve_edit(text, edit)
            if chosen is None:
                sys.exit(
                    "%s: no anchor matched.\n"
                    "Either the game was updated, or a stale block is present "
                    "- try --remove first.\n%s"
                    % (name, describe_miss(text, edit))
                )
            anchor, replacement, expected = chosen

            if anchor == Markers.APPEND:
                if toml:
                    # letters.toml / misc_local.toml have no trailing newline of
                    # their own, so the newline lives OUTSIDE the block and
                    # toml_re reclaims exactly it. Round-trip stays exact.
                    text = text + "\n" + replacement
                else:
                    # GML: the block carries its own trailing newline, and
                    # gml_re must not eat a leading one, so just ensure the file
                    # ends with a newline before appending.
                    if not text.endswith("\n"):
                        text += "\n"
                    text = text + replacement
                continue

            found = text.count(anchor)
            if found != expected:
                sys.exit(
                    "%s: anchor matched %d times, expected %d.\n"
                    "Either the game was updated, or a stale block is present "
                    "- try --remove first.\nanchor:\n%s"
                    % (name, found, expected, anchor)
                )
            text = text.replace(anchor, replacement)

        archive.write(name, text)


def is_installed(archive, mod):
    # The mod's own files only: the fourteen localization tables are 5 MB
    # each and only ever carry a block when the mod's own files do.
    for name in mod.patches(mod.markers, mod.defaults()):
        if name not in archive.files:
            continue
        toml = name.endswith(".toml")
        if mod.markers.present_in(archive.read(name), toml=toml):
            return True
    return False
