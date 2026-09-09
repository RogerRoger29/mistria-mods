#!/usr/bin/env python3
"""Mistria Mods - the graphical installer.

Put it in your Fields of Mistria folder next to FieldsOfMistria.exe (the same
place MOMI lives), tick the mods you want, press Apply. Everything install.py
does, with a checklist and a log. Built into a single MistriaMods.exe with
PyInstaller; runs from source too.
"""

import os
import queue
import sys
import threading
import traceback
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
RELEASES = HOMEPAGE + "/releases/latest"


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

        self._style()
        self._build()
        self.after(100, self._poll)

        if registry.looks_like_game(registry.GAME_DIR):
            self.refresh()
        else:
            self.after(250, self.choose_folder)

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
        # No update check: the app never touches the network. New versions are
        # a download from the releases page, swapped in by hand.
        rel = ttk.Label(foot, text="New versions", style="Status.TLabel", cursor="hand2")
        rel.pack(side="right")
        rel.bind("<Button-1>", lambda e: webbrowser.open(RELEASES))

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
        except queue.Empty:
            pass
        except Exception:
            self.log(traceback.format_exc())
            self.busy = False
            for b in self.buttons:
                b.configure(state="normal")
        finally:
            self.after(100, self._poll)

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
            momi = verifier.momi_states(registry.ASSETS, MODS)
        except Exception as e:
            self.status.set("Could not read assets.zip: %s" % e)
            return
        for mod in MODS:
            on = states.get(mod.SLUG)
            packaged = momi.get(mod.SLUG)
            self.state_labels[mod.SLUG].configure(
                text="Installed" if on else ("MOMI package" if packaged else "Not installed"),
                style="Good.TLabel" if (on or packaged) else "Off.TLabel")
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
            kept = []
            for mod in mods:
                patcher.strip_mod(archive, mod)
                # Its MOMI package is already in the archive: the two editions
                # cannot coexist, so this copy stays out.
                if patcher.momi_installed(archive, mod):
                    self.log("  - %s: its MOMI package is installed; leaving it to MOMI" % mod.NAME)
                    continue
                kept.append(mod)
                for name, ok, detail in patcher.check_mod(archive, mod):
                    if not ok:
                        self.log("  ! %s - %s: %s" % (mod.NAME, os.path.basename(name), detail))
                        bad += 1
            if bad:
                self.log("Nothing was changed: %d anchor problem(s). Is the game a version "
                         "this release supports?" % bad)
                raise SystemExit("anchors did not match")
            for mod in kept:
                patcher.apply_mod(archive, mod, mod.defaults())
                self.log("  + " + mod.NAME)
            self.log("Rebuilding assets.zip - this takes a moment ...")
            archive.save()
            self.log("Done: %d mod(s) applied. Launch the game." % len(kept))

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


def main():
    if "--version" in sys.argv:
        print("Mistria Mods v" + VERSION)
        return
    App().mainloop()


if __name__ == "__main__":
    main()
