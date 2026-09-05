#!/usr/bin/env python3
"""Mistria Mods - the graphical installer.

Put it in your Fields of Mistria folder next to FieldsOfMistria.exe (the same
place MOMI lives), tick the mods you want, press Apply. Everything install.py
does, with a checklist and a log. Built into a single MistriaMods.exe with
PyInstaller; runs from source too.
"""

import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
import traceback
import urllib.request
import webbrowser

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from mistriamods import VERSION, patcher, registry, verifier  # noqa: E402
from mistriamods.registry import MODS  # noqa: E402

APP = "Mistria Mods"
HOMEPAGE = "https://github.com/RogerRoger29/mistria-mods"
RELEASES_API = "https://api.github.com/repos/RogerRoger29/mistria-mods/releases/latest"
EXE_ASSET = "MistriaMods.exe"
FROZEN = bool(getattr(sys, "frozen", False))


# --- updates ---------------------------------------------------------------
#
# Every new mod ships as a GitHub release, so "update the app" and "get the
# new mods" are the same action. The check is one unauthenticated call to the
# releases API; the update downloads the release's exe beside this one and
# swaps them - a running exe cannot be overwritten on Windows, but it can be
# renamed, so the old one becomes MistriaMods.exe.old and is cleaned up on the
# next start. From source there is nothing to swap, so the release page opens.

def version_tuple(text):
    parts = []
    for piece in text.strip().lstrip("vV").split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _request(url):
    return urllib.request.Request(url, headers={
        "User-Agent": "MistriaMods/" + VERSION,
        "Accept": "application/vnd.github+json",
    })


def latest_release(timeout=8):
    """The newest release: tag, notes, page, and the exe asset's url and size."""
    with urllib.request.urlopen(_request(RELEASES_API), timeout=timeout) as r:
        data = json.load(r)
    asset = next((a for a in data.get("assets", []) if a.get("name") == EXE_ASSET), None)
    return {
        "tag": data.get("tag_name", ""),
        "notes": data.get("body") or "",
        "page": data.get("html_url") or HOMEPAGE + "/releases/latest",
        "url": asset["browser_download_url"] if asset else None,
        "size": asset["size"] if asset else 0,
        # GitHub publishes "sha256:<hex>" for every asset; the swap below
        # refuses anything that does not match it.
        "digest": (asset.get("digest") or "") if asset else "",
    }


def check_download(path, info):
    """The downloaded file's size and, when GitHub published one, its
    SHA-256 must match the release - or the file is removed and this raises."""
    got = os.path.getsize(path)
    if info["size"] and got != info["size"]:
        os.remove(path)
        raise SystemExit("download was incomplete (%d of %d bytes) - try again"
                         % (got, info["size"]))
    if info["digest"].startswith("sha256:"):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != info["digest"][len("sha256:"):]:
            os.remove(path)
            raise SystemExit("download did not match the release's SHA-256 - not installed")


def download(url, dest, progress=None, timeout=30):
    """Stream `url` to `dest`, reporting (done, total) bytes along the way."""
    with urllib.request.urlopen(_request(url), timeout=timeout) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    return dest


def swap_executable(new_path, exe_path):
    """Put `new_path` where `exe_path` is, keeping the old one as .old."""
    old = exe_path + ".old"
    if os.path.exists(old):
        os.remove(old)
    os.rename(exe_path, old)
    try:
        os.replace(new_path, exe_path)
    except Exception:
        os.rename(old, exe_path)
        raise
    return exe_path


def cleanup_old_executable():
    """Remove the previous version left behind by a swap, if any."""
    if not FROZEN:
        return
    old = os.path.abspath(sys.executable) + ".old"
    try:
        if os.path.exists(old):
            os.remove(old)
    except OSError:
        pass  # the old process may still be shutting down; next start gets it

ACCENT = "#6d4fc2"
ACCENT_DARK = "#4a3391"
BG = "#f6f2fb"
CARD = "#ffffff"
INK = "#2a2340"
MUTED = "#7b7391"
GOOD = "#2f9e5c"
BAD = "#c0392b"
LINE = "#e5dff1"


def resource(rel):
    """A bundled file: beside the script from source, inside the exe when frozen."""
    return os.path.join(getattr(sys, "_MEIPASS", HERE), rel)


def summary(mod):
    """The mod's one-line description: its SUMMARY, else its docstring's opening."""
    explicit = getattr(mod, "SUMMARY", None)
    if explicit:
        return explicit
    doc = (mod.__doc__ or "").strip()
    first = " ".join(doc.split("\n\n")[0].split())
    return first if len(first) <= 120 else first[:117].rstrip() + "..."


def details(mod):
    """The longer, player-facing write-up: DETAILS, else the docstring."""
    text = getattr(mod, "DETAILS", None) or (mod.__doc__ or "")
    return " ".join(text.split())


def options_line(mod):
    """'--radius 64 (tiles the effect reaches) ...' for the command line, or ''."""
    if not mod.OPTIONS:
        return ""
    parts = ["--%s %s (%s)" % (k, v[1], v[2]) for k, v in mod.OPTIONS.items()]
    return "Command-line options: " + "; ".join(parts)


def doc_url(mod):
    name = getattr(mod, "DOC", mod.SLUG.replace("_", "-") + ".md")
    return HOMEPAGE + "/blob/main/docs/" + name


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("%s v%s" % (APP, VERSION))
        self.configure(bg=BG)
        self.minsize(760, 680)
        cleanup_old_executable()
        try:
            self.iconbitmap(resource(os.path.join("assets", "mistria_mods.ico")))
        except Exception:
            pass

        self.events = queue.Queue()
        self.busy = False
        self.checks = {}
        self.state_labels = {}
        self.buttons = []
        self.detail_panels = {}   # slug -> (toggle label, panel frame)

        self.update_info = None

        self._style()
        self._build()
        self.after(100, self._poll)

        if registry.looks_like_game(registry.GAME_DIR):
            self.refresh()
        else:
            self.after(250, self.choose_folder)

        # A quiet check on startup; a failed or offline check says nothing.
        self.after(1500, lambda: self.check_updates(quiet=True))

    # --- look --------------------------------------------------------------

    def _style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", background=BG, foreground=INK, font=("Segoe UI", 10))
        st.configure("Card.TFrame", background=CARD)
        st.configure("Card.TLabel", background=CARD)
        st.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground=ACCENT_DARK)
        st.configure("Sub.TLabel", foreground=MUTED)
        st.configure("Muted.TLabel", foreground=MUTED, background=CARD, font=("Segoe UI", 9))
        st.configure("Name.TLabel", font=("Segoe UI", 10, "bold"), background=CARD)
        st.configure("Good.TLabel", foreground=GOOD, background=CARD, font=("Segoe UI", 9, "bold"))
        st.configure("Off.TLabel", foreground=MUTED, background=CARD, font=("Segoe UI", 9))
        st.configure("Link.TLabel", foreground=ACCENT, background=CARD, font=("Segoe UI", 9, "underline"))
        st.configure("Details.TLabel", foreground=INK, background="#faf8fd", font=("Segoe UI", 9),
                     padding=(10, 8))
        st.configure("Options.TLabel", foreground=MUTED, background="#faf8fd", font=("Segoe UI", 8),
                     padding=(10, 0, 10, 8))
        st.configure("TCheckbutton", background=CARD)
        st.configure("TButton", padding=(12, 6))
        st.configure("Accent.TButton", padding=(14, 7), foreground="white",
                     background=ACCENT, font=("Segoe UI", 10, "bold"))
        st.map("Accent.TButton", background=[("active", ACCENT_DARK), ("disabled", "#b9aee0")])
        st.configure("Status.TLabel", foreground=MUTED, font=("Segoe UI", 9))
        st.configure("Version.TLabel", foreground=MUTED, font=("Segoe UI", 11))
        st.configure("Banner.TFrame", background="#efe8ff")
        st.configure("Banner.TLabel", background="#efe8ff", foreground=ACCENT_DARK,
                     font=("Segoe UI", 10, "bold"))
        st.configure("BannerText.TLabel", background="#efe8ff", foreground=INK, font=("Segoe UI", 9))

    # --- layout ------------------------------------------------------------

    def _build(self):
        head = ttk.Frame(self)
        head.pack(fill="x", padx=20, pady=(18, 8))
        title_row = ttk.Frame(head)
        title_row.pack(fill="x")
        ttk.Label(title_row, text=APP, style="Title.TLabel").pack(side="left")
        ttk.Label(title_row, text="v" + VERSION, style="Version.TLabel").pack(side="left", padx=(10, 0), pady=(10, 0))
        ttk.Label(head, text="%d quality-of-life mods for Fields of Mistria, applied straight into assets.zip. "
                             "Tick what you want, press Apply." % len(MODS),
                  style="Sub.TLabel").pack(anchor="w")

        # Update banner: hidden until a newer release is found.
        self.banner = ttk.Frame(self, style="Banner.TFrame", padding=(14, 10))
        self.banner_title = ttk.Label(self.banner, text="", style="Banner.TLabel")
        self.banner_title.pack(anchor="w")
        self.banner_text = ttk.Label(self.banner, text="", style="BannerText.TLabel", wraplength=640, justify="left")
        self.banner_text.pack(anchor="w", pady=(2, 8))
        banner_btns = ttk.Frame(self.banner, style="Banner.TFrame")
        banner_btns.pack(anchor="w")
        self.update_btn = ttk.Button(banner_btns, text="Download & install", style="Accent.TButton",
                                     command=self.do_update)
        self.update_btn.pack(side="left")
        ttk.Button(banner_btns, text="Release notes", command=lambda: webbrowser.open(
            (self.update_info or {}).get("page", HOMEPAGE))).pack(side="left", padx=(6, 0))
        ttk.Button(banner_btns, text="Later", command=self.banner.pack_forget).pack(side="left", padx=(6, 0))

        folder = ttk.Frame(self)
        folder.pack(fill="x", padx=20, pady=(0, 10))
        self.folder_frame = folder
        ttk.Label(folder, text="Game folder:").pack(side="left")
        self.folder_var = tk.StringVar(value=registry.GAME_DIR)
        ttk.Label(folder, textvariable=self.folder_var, style="Sub.TLabel").pack(side="left", padx=(6, 10))
        ttk.Button(folder, text="Browse...", command=self.choose_folder).pack(side="left")
        # Lives up here, not in the action bar, which is exactly full already.
        self.expand_all_btn = ttk.Button(folder, text="Show all details", command=self._toggle_all_details)
        self.expand_all_btn.pack(side="right")

        # Scrollable card list.
        outer = ttk.Frame(self, style="Card.TFrame")
        outer.pack(fill="both", expand=True, padx=20)
        self.canvas = tk.Canvas(outer, bg=CARD, highlightthickness=0, height=300)
        bar = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.rows = ttk.Frame(self.canvas, style="Card.TFrame")
        self.rows_id = self.canvas.create_window((0, 0), window=self.rows, anchor="nw")
        self.rows.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.rows_id, width=e.width))
        # Wheel scrolling only while the pointer is over the list, so the log
        # box below keeps its own scrolling.
        wheel = lambda e: self.canvas.yview_scroll(-int(e.delta / 120), "units")  # noqa: E731
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        for i, mod in enumerate(MODS):
            self._row(mod, i)

        # Actions.
        acts = ttk.Frame(self)
        acts.pack(fill="x", padx=20, pady=10)
        for text, cmd, style in (
            ("Select all", lambda: self._select(True), "TButton"),
            ("Select none", lambda: self._select(False), "TButton"),
        ):
            b = ttk.Button(acts, text=text, command=cmd, style=style)
            b.pack(side="left", padx=(0, 6))
            self.buttons.append(b)
        for text, cmd, style in (
            ("Apply selected", self.do_apply, "Accent.TButton"),
            ("Remove selected", self.do_remove, "TButton"),
            ("Check", self.do_check, "TButton"),
            ("Verify", self.do_verify, "TButton"),
        ):
            b = ttk.Button(acts, text=text, command=cmd, style=style)
            b.pack(side="right", padx=(6, 0))
            self.buttons.append(b)

        # Log.
        self.log_box = scrolledtext.ScrolledText(self, height=9, font=("Consolas", 9),
                                                 bg="#fbf9fe", fg=INK, relief="flat",
                                                 highlightthickness=1, highlightbackground=LINE)
        self.log_box.pack(fill="both", padx=20, pady=(0, 6))
        self.log_box.configure(state="disabled")

        foot = ttk.Frame(self)
        foot.pack(fill="x", padx=20, pady=(0, 12))
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(foot, textvariable=self.status, style="Status.TLabel").pack(side="left")
        link = ttk.Label(foot, text="Docs & source", style="Status.TLabel", cursor="hand2")
        link.pack(side="right")
        link.bind("<Button-1>", lambda e: webbrowser.open(HOMEPAGE))
        ttk.Label(foot, text="  ·  ", style="Status.TLabel").pack(side="right")
        upd = ttk.Label(foot, text="Check for updates", style="Status.TLabel", cursor="hand2")
        upd.pack(side="right")
        upd.bind("<Button-1>", lambda e: self.check_updates(quiet=False))

    def _row(self, mod, index):
        row = ttk.Frame(self.rows, style="Card.TFrame", padding=(12, 8))
        row.grid(row=index, column=0, sticky="ew")
        self.rows.columnconfigure(0, weight=1)
        var = tk.BooleanVar(value=True)
        self.checks[mod.SLUG] = var
        ttk.Checkbutton(row, variable=var).grid(row=0, column=0, rowspan=3, padx=(0, 8), sticky="n")
        ttk.Label(row, text=mod.NAME, style="Name.TLabel").grid(row=0, column=1, sticky="w")
        state = ttk.Label(row, text="", style="Off.TLabel")
        state.grid(row=0, column=2, sticky="e", padx=(12, 0))
        self.state_labels[mod.SLUG] = state
        ttk.Label(row, text=summary(mod), style="Muted.TLabel", wraplength=560,
                  justify="left").grid(row=1, column=1, columnspan=2, sticky="w")

        # The expandable write-up: a link that reveals a panel with the full
        # player-facing description, the command-line options, and the doc.
        toggle = ttk.Label(row, text="More details ▾", style="Link.TLabel", cursor="hand2")
        toggle.grid(row=2, column=1, sticky="w", pady=(3, 0))
        panel = ttk.Frame(row, style="Card.TFrame")
        panel.grid(row=3, column=1, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Label(panel, text=details(mod), style="Details.TLabel", wraplength=570,
                  justify="left").pack(fill="x")
        opts = options_line(mod)
        if opts:
            ttk.Label(panel, text=opts, style="Options.TLabel", wraplength=570,
                      justify="left").pack(fill="x")
        link = ttk.Label(panel, text="Read the full write-up ↗", style="Link.TLabel", cursor="hand2")
        link.pack(anchor="w", padx=10, pady=(0, 8))
        link.bind("<Button-1>", lambda e, m=mod: webbrowser.open(doc_url(m)))
        panel.grid_remove()
        self.detail_panels[mod.SLUG] = (toggle, panel)
        toggle.bind("<Button-1>", lambda e, s=mod.SLUG: self._toggle_details(s))

        row.columnconfigure(1, weight=1)
        ttk.Separator(self.rows, orient="horizontal").grid(row=index, column=0, sticky="sew")

    def _toggle_details(self, slug, show=None):
        toggle, panel = self.detail_panels[slug]
        visible = panel.winfo_manager() != ""
        show = (not visible) if show is None else show
        if show:
            panel.grid()
            toggle.configure(text="Hide details ▴")
        else:
            panel.grid_remove()
            toggle.configure(text="More details ▾")

    def _toggle_all_details(self):
        any_open = any(p.winfo_manager() != "" for _, p in self.detail_panels.values())
        for slug in self.detail_panels:
            self._toggle_details(slug, show=not any_open)
        self.expand_all_btn.configure(text="Hide all details" if not any_open else "Show all details")

    # --- helpers -----------------------------------------------------------

    def _select(self, on):
        for var in self.checks.values():
            var.set(on)

    def selected(self):
        return [mod for mod in MODS if self.checks[mod.SLUG].get()]

    def log(self, line):
        self.events.put(("log", line))

    def _poll(self):
        # Whatever one event does, the pump must keep running: a handler
        # that raised would otherwise leave the buttons disabled for good.
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self.log_box.configure(state="normal")
                    self.log_box.insert("end", payload + "\n")
                    self.log_box.see("end")
                    self.log_box.configure(state="disabled")
                elif kind == "done":
                    self.busy = False
                    for b in self.buttons:
                        b.configure(state="normal")
                    self.status.set(payload)
                    self.refresh()
                elif kind == "update":
                    self._show_update(payload)
                elif kind == "relaunch":
                    if messagebox.askyesno(APP, "Updated to %s. Relaunch now?" % payload["tag"]):
                        subprocess.Popen([payload["exe"]], cwd=os.path.dirname(payload["exe"]))
                        self.destroy()
                        return
        except queue.Empty:
            pass
        except Exception:
            self.log(traceback.format_exc())
            self.busy = False
            for b in self.buttons:
                b.configure(state="normal")
        finally:
            self.after(100, self._poll)

    # --- updates -----------------------------------------------------------

    def check_updates(self, quiet):
        def work():
            try:
                info = latest_release()
            except Exception as e:
                if not quiet:
                    self.log("Could not reach GitHub to check for updates (%s)." % e)
                return
            if version_tuple(info["tag"]) > version_tuple(VERSION):
                self.events.put(("update", info))
            elif not quiet:
                self.log("You have the latest version (v%s)." % VERSION)
        threading.Thread(target=work, daemon=True).start()

    def _show_update(self, info):
        self.update_info = info
        first = " ".join(info["notes"].strip().split("\n")[0].split()) if info["notes"] else ""
        self.banner_title.configure(text="Update available: %s (you have v%s)" % (info["tag"], VERSION))
        self.banner_text.configure(text=first[:220] if first else "A newer release is on GitHub.")
        if FROZEN and info["url"]:
            self.update_btn.configure(text="Download & install (%.1f MB)" % (info["size"] / 1e6))
        else:
            self.update_btn.configure(text="Open release page")
        self.banner.pack(fill="x", padx=20, pady=(0, 10), before=self.folder_frame)

    def do_update(self):
        info = self.update_info
        if not info:
            return
        if not (FROZEN and info["url"]):
            webbrowser.open(info["page"])
            return

        def fn():
            exe = os.path.abspath(sys.executable)
            new_path = os.path.join(os.path.dirname(exe), EXE_ASSET + ".new")
            self.log("Downloading %s %s ..." % (EXE_ASSET, info["tag"]))
            marks = set()

            def progress(done, total):
                pct = int(100 * done / total) if total else 0
                if pct // 20 not in marks and total:
                    marks.add(pct // 20)
                    self.log("  %d%%" % pct)
            download(info["url"], new_path, progress)
            check_download(new_path, info)
            swap_executable(new_path, exe)
            self.log("Installed %s. The previous version is kept as %s.old until next launch."
                     % (info["tag"], EXE_ASSET))
            self.events.put(("relaunch", {"tag": info["tag"], "exe": exe}))

        self.run("Updating to " + info["tag"], fn)

    def run(self, label, fn):
        if self.busy:
            return
        self.busy = True
        for b in self.buttons:
            b.configure(state="disabled")
        self.status.set(label + " ...")

        def work():
            outcome = label + " finished."
            try:
                fn()
            except SystemExit as e:
                self.log("ERROR: %s" % e)
                outcome = label + " failed - see the log."
            except Exception:
                self.log(traceback.format_exc())
                outcome = label + " failed - see the log."
            self.events.put(("done", outcome))

        threading.Thread(target=work, daemon=True).start()

    def refresh(self):
        try:
            states = verifier.installed_states(registry.ASSETS, MODS)
        except Exception as e:
            self.status.set("Could not read assets.zip: %s" % e)
            return
        for mod in MODS:
            on = states.get(mod.SLUG)
            self.state_labels[mod.SLUG].configure(
                text="Installed" if on else "Not installed",
                style="Good.TLabel" if on else "Off.TLabel")
        n = sum(1 for v in states.values() if v)
        self.folder_var.set(registry.GAME_DIR)
        if not self.busy:
            self.status.set("%d of %d mods installed." % (n, len(MODS)))

    def choose_folder(self):
        path = filedialog.askdirectory(title="Where is Fields of Mistria installed?",
                                       initialdir=registry.GAME_DIR)
        if not path:
            return
        if not registry.looks_like_game(path):
            messagebox.showerror(APP, "That folder has no assets.zip beside Maybe.toml - "
                                      "it does not look like the game folder.")
            return
        registry.set_game_dir(path)
        self.refresh()

    # --- actions -----------------------------------------------------------

    def do_apply(self):
        mods = self.selected()
        if not mods:
            messagebox.showinfo(APP, "Tick at least one mod first.")
            return

        def fn():
            self.log("Loading %s ..." % registry.ASSETS)
            archive = patcher.Archive(registry.ASSETS)
            if not os.path.exists(registry.BACKUP):
                self.log("Saving a clean backup -> assets.vanilla.zip (once)")
            patcher.ensure_backup(archive, registry.BACKUP, MODS)
            bad = 0
            for mod in mods:
                patcher.strip_mod(archive, mod)
                for name, ok, detail in patcher.check_mod(archive, mod):
                    if not ok:
                        self.log("  ! %s - %s: %s" % (mod.NAME, os.path.basename(name), detail))
                        bad += 1
            if bad:
                self.log("Nothing was changed: %d anchor problem(s). Is the game a version "
                         "this release supports?" % bad)
                raise SystemExit("anchors did not match")
            for mod in mods:
                patcher.apply_mod(archive, mod, mod.defaults())
                self.log("  + " + mod.NAME)
            self.log("Rebuilding assets.zip - this takes a moment ...")
            archive.save()
            self.log("Done: %d mod(s) applied. Launch the game." % len(mods))

        self.run("Applying %d mod(s)" % len(mods), fn)

    def do_remove(self):
        mods = self.selected()
        if not mods:
            messagebox.showinfo(APP, "Tick the mods to remove first.")
            return

        def fn():
            self.log("Loading %s ..." % registry.ASSETS)
            archive = patcher.Archive(registry.ASSETS)
            touched = 0
            for mod in mods:
                if patcher.strip_mod(archive, mod):
                    touched += 1
                    self.log("  - " + mod.NAME)
            if not touched:
                self.log("None of those were installed - nothing to do.")
                return
            self.log("Rebuilding assets.zip ...")
            archive.save()
            self.log("Done: %d mod(s) removed." % touched)

        self.run("Removing", fn)

    def do_check(self):
        mods = self.selected() or list(MODS)

        def fn():
            bad = 0
            with verifier.ZipView(registry.ASSETS) as archive:
                for mod in mods:
                    report = patcher.check_mod(archive, mod)
                    ok = all(good for _, good, _ in report)
                    self.log("  [%s] %s" % ("ok" if ok else "!!", mod.NAME))
                    for name, good, detail in report:
                        if not good:
                            self.log("        %s: %s" % (verifier.short(name), detail))
                            bad += 1
            self.log("Check complete: %s." % ("every anchor matches" if not bad
                                              else "%d problem(s), see above" % bad))

        self.run("Checking anchors", fn)

    def do_verify(self):
        def fn():
            problems = 0
            for mod, ok, details in verifier.verify_all(registry.ASSETS, MODS):
                self.log("  [%s] %s %s" % ("ok" if ok else "!!", mod.NAME, "  ".join(details)))
                problems += 0 if ok else 1
            momi = verifier.momi_manifest()
            if momi:
                self.log("MOMI reports %d mod(s) applied: %s" % (len(momi), ", ".join(momi)))
            self.log("Verify complete: %s." % ("all good" if not problems
                                               else "%d mod(s) with problems" % problems))

        self.run("Verifying", fn)


def headless_update():
    """`MistriaMods.exe --update`: check, download, swap - no window.

    Logs to MistriaMods-update.log beside the exe, since a windowed build
    has no console. Exit code 0 on success or when already current, 1 on
    an error, 2 on an incomplete download.
    """
    exe = os.path.abspath(sys.executable if FROZEN else __file__)
    log_path = os.path.join(os.path.dirname(exe), "MistriaMods-update.log")

    def log(msg):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    try:
        log("Mistria Mods v%s: checking %s" % (VERSION, RELEASES_API))
        info = latest_release()
        if version_tuple(info["tag"]) <= version_tuple(VERSION):
            log("Up to date (latest is %s)." % info["tag"])
            return 0
        if not (FROZEN and info["url"]):
            log("Newer release %s at %s - not a frozen build, nothing to swap."
                % (info["tag"], info["page"]))
            return 0
        new_path = os.path.join(os.path.dirname(exe), EXE_ASSET + ".new")
        log("Downloading %s (%d bytes)" % (info["url"], info["size"]))
        download(info["url"], new_path)
        try:
            check_download(new_path, info)
        except SystemExit as e:
            log("Rejected: %s" % e)
            return 2
        swap_executable(new_path, exe)
        log("Installed %s over %s; the previous version is kept as .old."
            % (info["tag"], os.path.basename(exe)))
        return 0
    except Exception as e:
        log("ERROR: %r" % (e,))
        return 1


def main():
    if "--version" in sys.argv:
        print("Mistria Mods v" + VERSION)
        return
    if "--update" in sys.argv:
        sys.exit(headless_update())
    App().mainloop()


if __name__ == "__main__":
    main()
