"""Home > Quick tools (3.53.0, the first screen until 4.52.0 opened on the Overview's doors): drop any file (or choose files, or paste a picture) and pick what to do with
it from the tools that take that kind of file (plan decision 3: ask which tool); your pinned tools, one click each
(decision 4: a starting set by role, changed freely); the files you last opened from here; your efforts and programs.
4.51.0: a use that works in a home asks where the file goes in the same step (skqt/homeask: the open effort or program
first, another one, a new effort or a new program); a tool beside any home asks nothing more. Unfiled takes no new work:
what it holds from before shows here, as Unfiled, from before, only while it holds anything. Rules only; nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QScrollArea, QVBoxLayout, QWidget)

import diag
import doors as DR
import recentfiles as RF
from . import design as D
from .adaptive import FlowLayout

OFFICE = (".docx", ".xlsx", ".pptx")
# what a dropped file can be used for: key -> (what it says, the extensions it takes, None for any the reader takes)
USES = (("acrfinder", "Find acronyms (Acronym Finder, its own window)", None),
        ("acronyms", "Find acronyms in an effort or a program", None),
        ("firstuse", "Check first use (First Use Check)", (".docx",)),
        ("copyreview", "Copy review (Technical Edit), in an effort", (".docx",)),
        ("fulltext", "Pull out all the text (Full Text)", None),
        ("shred", f"{DR.NAMES['shred']}: {DR.WHAT['shred']}", (".pdf", ".docx", ".pptx", ".xlsx")),   # 4.54.0: the door's own route
        ("library", "Add to Documents, in an effort or a program", None),
        ("audit", "Audit against the standards (changes nothing)", OFFICE),
        ("leftovers", "Check for leftovers before it goes out (Final Checks)", (".docx",)),     # 3.57.0
        ("strip", "Strip the setup out (a clean copy)", (".docx",)),                             # 3.60.0
        ("redline", "Prepare it for redline (a Word file beside it)",                           # 4.22.0: a file outside any effort
         (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp")))
# 4.51.0: the uses that work in a home (asked where in the same step), and those of them only an effort has: Technical Edit
# is Drafts', Strip is Setup's and Final Checks is Submit's (programs.OUT); Audit reads the effort's volume standards
NEEDS_HOME = ("acronyms", "copyreview", "library", "audit", "strip", "leftovers", "shred")
EFFORT_ONLY = ("copyreview", "strip", "leftovers", "shred")     # 4.52.0: Audit works in a program too; 4.54.0: Shred to setup
NO_HOME = object()
# the tools Home can pin: key -> (title, what, kind) ; kind "window" opens its own window, "page" goes to the page
TOOLS = {"acrfinder": ("Acronym Finder", "Scan any files for acronyms, apart from any effort", "window"),
         "firstuse": ("First Use Check", "Your Word files' first uses", "window"),
         "fulltext": ("Full Text", "Every word in the files, as text", "window"),
         "acronyms": ("Acronyms", "Scan and the acronym list", "page"), "acrlist": ("Acronym List", "The effort's list", "page"),
         "assign": ("Shred", "Every piece of the customer's documents, on the page", "page"), "matrix": ("Matrix", "The compliance matrix", "page"),
         "library": ("Documents", "The customer's documents", "page"), "compare": ("What changed", "Two versions of a document", "page"),
         "structure": ("Setup", "The sections and each author's starting draft", "page"), "storyboards": ("Storyboards", "One sheet per section", "page"),
         "drafts": ("Draft Status", "A draft read back", "page"), "truth": ("Wall of Truth", "One approved way to state each fact", "page"),
         "reviews": ("Color Reviews", "Review packets and comments", "page"), "qa": ("Submission Check", "The volumes you will submit", "page"),
         "checks": ("Final Checks", "The PDF package, cross-references", "page"), "templates": ("Templates", "Every template the profiles make", "page"),
         "profiles": ("Effort Profiles", "Profiles built by picking", "page"), "fixcopy": ("Fix a Copy", "Fixes into a dated copy", "page"),
         "audit": ("Audit", "Files against every standard", "page"), "home": ("Overview", "Where the effort stands", "page"),
         "mywork": ("My Work", "Your work in every effort", "page"), "refs": ("Team References", "The lists the team keeps", "page"),
         "custqa": ("Customer Q&A", "Questions to the customer", "page"),
         "techedit": ("Technical Edit", "Copy review of a draft", "page"),
         "shredacc": ("Shred accuracy", "How well the reader finds requirements, on answer keys", "page"),     # 4.19.0: off Shred
         "sort": ("Themes", "Cross-cutting themes on requirements, for filtering and assignments", "page"),
         "redline": ("Redlining", "The effort's documents marked Redlined Deliverable, prepared and checked", "page")}   # 4.59.2
ROLE_PINS = {"Production": ["acrfinder", "firstuse", "techedit", "templates", "checks", "fixcopy", "refs"],
             "Proposal Manager": ["home", "assign", "reviews", "mywork", "acrfinder", "qa"],
             "Author": ["mywork", "drafts", "techedit", "acrfinder", "firstuse", "truth", "storyboards"],
             "Reviewer": ["reviews", "assign", "checks", "acrfinder"],
             "Capture": ["library", "assign", "structure", "custqa"]}
PINS_FILE = "home_pins.json"
OLD = {"shredreq": "assign"}                 # 4.54.0: a pin saved before Quick shred became Shred's table


def uses_for(paths):
    """The uses that take every one of the files."""
    import app_gui as A
    exts = {os.path.splitext(p)[1].lower() for p in paths}
    if not exts or not exts <= set(A.SUPPORTED_EXTS):
        return []
    out = [(k, t) for k, t, ok in USES if ok is None or exts <= set(ok)]
    if len(paths) == 2:                                            # 3.55.0: two files dropped together
        out.insert(0, ("compare", "Compare the two files (earlier first)"))
    return out


def load_pins(config_dir, role=""):
    import json
    import menufocus as MF
    from .modes import settings
    aside = MF.hidden(settings())                   # 3.57.0: a set-aside page is not pinned
    try:
        with open(os.path.join(config_dir, PINS_FILE), encoding="utf-8") as f:
            got = [OLD.get(k, k) for k in (json.load(f) or {}).get("pins", [])]       # 4.54.0: Quick shred's pin is Shred
        return [k for n, k in enumerate(got) if k in TOOLS and k not in aside and k not in got[:n]]
    except (OSError, ValueError, AttributeError):
        return [k for k in (ROLE_PINS.get(role) or ROLE_PINS["Production"]) if k not in aside]


def save_pins(config_dir, pins):
    import json
    os.makedirs(config_dir, exist_ok=True)
    p = os.path.join(config_dir, PINS_FILE)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"pins": [k for k in pins if k in TOOLS]}, f, indent=1)
    os.replace(p + ".tmp", p)


class DropZone(QFrame):
    def __init__(self, on_files, text=None):
        super().__init__()
        self.on_files = on_files
        self.setAcceptDrops(True); self.setObjectName("dropzone")
        self.setStyleSheet("QFrame#dropzone { border: 2px dashed palette(mid); border-radius: 8px; }")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["l"], D.SPACE["l"], D.SPACE["l"], D.SPACE["l"])
        t = QLabel(text or "Drop a file here: Word, PDF, PowerPoint, Excel or a picture. Then pick what to do with it.")
        t.setAlignment(Qt.AlignCenter); t.setWordWrap(True); v.addWidget(t)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        files = [os.path.normpath(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile() and os.path.isfile(u.toLocalFile())]
        if files:
            self.on_files(files)


class UseDialog(QDialog):
    """Ask which tool (decision 3) and, for a use that works in a home, where the file goes, in one step (4.51.0)."""

    def __init__(self, parent, paths, host):
        super().__init__(parent)
        from .homeask import WhereBox
        self.setWindowTitle("What do you want to do?"); self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        names = ", ".join(os.path.basename(p) for p in paths[:3]) + (f" and {len(paths) - 3} more" if len(paths) > 3 else "")
        v.addWidget(D.label(names, "label"))
        self.list = QListWidget(); v.addWidget(self.list)
        for k, t in uses_for(paths):
            it = QListWidgetItem(t); it.setData(Qt.UserRole, k)
            self.list.addItem(it)
        self.where = WhereBox(host.efforts, host.effort_name if host.ws is not None else "", paths)
        v.addWidget(self.where)
        self.list.itemDoubleClicked.connect(lambda _i: self.accept() if self.ok_btn.isEnabled() else None)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        self.ok_btn = bb.button(QDialogButtonBox.Ok)
        v.addWidget(bb)
        self.where.on_change = self.settle_ok
        self.list.currentItemChanged.connect(lambda *_a: self.use_changed())
        if self.list.count():
            self.list.setCurrentRow(0)
        self.use_changed()

    def use_changed(self):
        use = self.picked()
        self.where.setVisible(use in NEEDS_HOME)
        if use in NEEDS_HOME:
            self.where.fill(programs=use not in EFFORT_ONLY)
        return self.settle_ok()

    def settle_ok(self):
        use = self.picked()
        ok = use is not None and (use not in NEEDS_HOME or self.where.ok())
        self.ok_btn.setEnabled(ok)
        return ok

    def picked(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it is not None else None

    def home(self):
        """The home picked, as WhereBox.picked() gives it; None for a use beside any home."""
        return self.where.picked() if self.picked() in NEEDS_HOME else None


def hand(h, use, paths, choices=None):
    """What a use that works in a home does once the home is open (Quick tools and the Overview's doors share it, 4.52.0).
    choices (tests): Documents' table answers for Shred to setup."""
    if use == "acronyms":
        import acrlists as AL
        h.go("acronyms")
        s = h.acronym_page.session
        last = ((s.last_scan or {}).get("paths") if s is not None else None) or []
        return h.acronym_page.scan(AL.add_files(last, paths))
    if use == "copyreview":
        h.go("techedit")
        return h.techedit_page.add_files(paths, run=True)
    if use == "library":
        h.go("library")
        return h.library_page.add(paths)
    if use == "audit":
        h.go("audit")
        return h.audit_page.add_files(paths)
    if use == "strip":                                  # 3.60.0
        return h.setups_page.strip_files(paths)
    if use == "leftovers":                              # 3.57.0
        h.go("checks")
        return h.checks_page.check_leftovers(paths)
    if use == "shred":                                  # 4.54.0: Shred to setup, the door's own route
        from . import doorsview as DVW
        import programs as PG
        if PG.is_program(h.efforts, h.effort_name):
            h.status(DVW.REFUSE_SHRED)
            return None
        return DVW.shred(h, h.effort_name, paths, choices)
    return None


class ToolsHome(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QScrollArea.NoFrame); outer.addWidget(sc)
        body = QWidget(); sc.setWidget(body)
        v = QVBoxLayout(body); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.drop = DropZone(self.files_in); v.addWidget(self.drop)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Choose files...", "primary", lambda: self.choose()))
        row.addWidget(D.button("Paste a picture", None, lambda: self.paste(), "A screenshot or a copied figure, read in Acronym Finder"))
        row.addStretch(1)
        pins = D.Card("Pinned tools", "One click each. Edit pins... to change them.",
                      actions=(D.button("Edit pins...", "ghost", lambda: self.edit_pins()),))
        v.addWidget(pins)
        self.tiles = QWidget(); self.tl = FlowLayout(self.tiles); self.tl.setSpacing(D.SPACE["s"]); pins.add(self.tiles)
        g = QGridLayout(); g.setSpacing(D.SPACE["m"]); v.addLayout(g)
        rf = D.Card("Recent files", "Open one again with any tool."); g.addWidget(rf, 0, 0)
        self.recent = QListWidget(); self.recent.setMinimumHeight(170); rf.add(self.recent)
        self.recent.itemDoubleClicked.connect(lambda it: self.files_in([it.data(Qt.UserRole)]))
        ef = D.Card("Your efforts", "Double-click to work on one."); g.addWidget(ef, 0, 1)
        self.eff = QListWidget(); self.eff.setMinimumHeight(170); ef.add(self.eff)
        self.eff.itemDoubleClicked.connect(lambda it: self.work_on(it.data(Qt.UserRole)))
        # 4.27.2 (Nicholas 2026-11-12 21:25, answer 4): Unfiled is a list here, not an effort; 4.51.0: only while it holds work
        import homes as HM
        self.uf_card = D.Card(HM.SHOWN, "What was made with a tool before every document had a named home.")
        self.uf_list = QListWidget(); self.uf_list.setMinimumHeight(110); self.uf_list.setMaximumHeight(200); self.uf_card.add(self.uf_list)
        self.uf_list.itemDoubleClicked.connect(lambda _it: self.open_unfiled())
        ur = FlowLayout(None, D.SPACE["s"]); self.uf_card.body.addLayout(ur)
        from PySide6.QtWidgets import QMenu      # 4.27.2: one button; the list's row opens on a double-click
        self.uf_file = D.button("File it", None, None, "Name it as an effort or a program, open it, add it to an effort, or clear it")
        m = QMenu(self.uf_file); self.uf_file.setMenu(m)
        self.uf_make = m.addAction("Name it...", lambda: self.host.make_unfiled_effort())       # 4.51.0: one way to name it
        self.uf_open = m.addAction("Open", lambda: self.open_unfiled())
        self.uf_add = m.addAction("Add to an effort...", lambda: self.host.efforts_page.add_unfiled_to())
        self.uf_clear = m.addAction("Clear...", lambda: (self.host.efforts_page.clear_unfiled(), self.refresh()))
        ur.addWidget(self.uf_file)
        v.addWidget(self.uf_card)
        v.addStretch(1)
        self.pins = []

    # ---- what shows
    def role(self):
        try:
            return self.host.profile()[0]
        except Exception:  # noqa: BLE001
            return ""

    def refresh(self):
        cfg = self.host.config_dir
        self.pins = load_pins(cfg, self.role())
        while self.tl.count():
            it = self.tl.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for k in self.pins:
            t, what, _kind = TOOLS[k]
            b = D.button(t.replace("&", "&&"), None, lambda _=False, k_=k: self.open(k_), what)   # 4.20.0: Acros & Abs, not a shortcut mark
            b.setMinimumWidth(150)
            self.tl.addWidget(b)
        self.recent.clear()
        for r in RF.shown(cfg):
            it = QListWidgetItem(f"{os.path.basename(r['path'])}    ({r.get('tool', '')}, {str(r.get('at', ''))[:10]})")
            it.setData(Qt.UserRole, r["path"]); it.setToolTip(r["path"])
            self.recent.addItem(it)
        if not self.recent.count():
            self.recent.addItem(QListWidgetItem("Files you open from here show here."))
        self.eff.clear()
        h = self.host
        import unfiled as UF
        names = [n for n in h.efforts.names() if not (h.efforts.get(n) or {}).get("archived") and n != UF.NAME]
        cur = h.effort_name
        for n in sorted(names, key=lambda x: (x != cur, x.casefold())):
            it = QListWidgetItem(n + ("   (program)" if (h.efforts.get(n) or {}).get("program") else "") + ("   (working on)" if n == cur else ""))   # 4.50.0
            it.setData(Qt.UserRole, n); self.eff.addItem(it)
        if not names:
            self.eff.addItem(QListWidgetItem("No efforts yet. All Efforts starts one."))
        self.fill_unfiled()

    def unfiled_rows(self):
        """What Unfiled holds, one line each: its documents by name, then its terms, its matrix and its notes as counts."""
        import unfiled as UF
        h = self.host
        out = []
        try:
            c = UF.counts(h.efforts)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            c = {}
        info = h.efforts.get(UF.NAME) or {}
        path = info.get("path", "")
        if info.get("unfiled") and path and os.path.isfile(path):
            try:
                import docversions as DV
                import workspace as W
                for d in DV.Library(os.path.join(W.data_dir_for(path), "documents")).load().all:
                    out.append("Document:   " + (d.get("name") or ""))
            except Exception:  # noqa: BLE001
                diag.swallowed()
        for key, one, many in (("terms", "acro or abb", "acronyms"), ("matrix", "compliance matrix", "compliance matrices"),
                               ("context", "piece of context", "pieces of context"), ("notes", "note", "notes")):
            n = int(c.get(key) or 0)
            if n:
                out.append(f"{n} {one if n == 1 else many}")
        return out

    def fill_unfiled(self):
        rows = self.unfiled_rows()
        self.uf_list.clear()
        for r in rows:
            self.uf_list.addItem(QListWidgetItem(r))
        if not rows:
            self.uf_list.addItem(QListWidgetItem("Nothing in it."))
        for b in (self.uf_make, self.uf_add, self.uf_clear):
            b.setEnabled(bool(rows))
        import homes as HM
        import programs as PG
        self.uf_add.setEnabled(bool(rows) and bool(PG.effort_names(self.host.efforts)))
        self.uf_card.setVisible(HM.holds_work(self.host.efforts))      # 4.51.0: hidden while Unfiled holds nothing
        return rows

    def open_unfiled(self):
        return self.host.efforts_page.open_unfiled()

    def working_on(self):
        """The home open now ('' when none is open; never Unfiled's name for nothing open)."""
        return self.host.effort_name if self.host.ws is not None else ""

    # ---- actions
    def open(self, key):
        t, _what, kind = TOOLS[key]
        diag.activity("home_tool_opened")
        if kind == "window":
            return self.host.open_tool({"acrfinder": "acronyms"}.get(key, key))
        return self.host.go(key)

    def choose(self):
        import app_gui as A
        exts = " ".join("*" + e for e in sorted(A.SUPPORTED_EXTS))
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose files", "", f"Documents and pictures ({exts})")
        return self.files_in(paths) if paths else None

    def paste(self):
        w = self.host.open_tool("acronyms")
        from . import acrextras as AX
        return AX.paste_picture(w.page) if w is not None else None

    def files_in(self, paths, use=None, home=None, choices=None):
        """Ask which tool and, for a use that works in a home, where the file goes (one step), then hand the files to it.
        use, home, choices (tests): the answers, home as homeask.WhereBox.picked() gives it. Returns the use chosen (or None)."""
        if not paths:
            return None
        if not uses_for(paths):
            self.host.status("Stationkeeper does not read that kind of file.")
            return None
        if use is None:
            d = UseDialog(self, paths, self.host)
            if d.exec() != QDialog.Accepted:
                return None
            use, home = d.picked(), d.home()
        if not use:
            return None
        if self.run(use, paths, home, choices) is NO_HOME:
            return None
        RF.add(self.host.config_dir, paths, dict((k, t.split(" (")[0].split(": ")[0]) for k, t, _ in USES).get(use, use))
        self.refresh()
        diag.activity("home_files_used", n=len(paths))
        return use

    def run(self, use, paths, home=None, choices=None):
        """Hand the files to the use. NO_HOME when a use that works in a home has none (the status line says why)."""
        h = self.host
        if use == "acrfinder":
            w = h.open_tool("acronyms")
            import acrlists as AL
            s = w.page.session
            last = ((s.last_scan or {}).get("paths") if s is not None else None) or []
            return w.page.scan(AL.add_files(last, paths))
        if use == "compare":
            h.go("compare")
            return h.compare_space.show_files(paths[0], paths[1])
        if use == "firstuse":
            from .firstusetool import open_tool
            return open_tool(h.config_dir, paths)
        if use == "fulltext":
            from .fulltexttool import open_tool
            return open_tool(h.config_dir, paths)
        if use == "redline":                                # 4.22.0: beside the file; no effort needed
            return [h.redline_page.prepare(path=p) for p in paths]
        if use in NEEDS_HOME and (home is not None or h.ws is None):   # 4.51.0: the home picked in the same step (the
            from .homeask import settle                   # dialog always gives one, never Unfiled); a call from code with
            import programs as PG                         # none works on the home open now, as before
            if use in EFFORT_ONLY and home and (home[0] == "new_program" or (home[0] == "home" and PG.is_program(h.efforts, home[1]))):
                h.status("That works in an effort. Pick an effort, or a new one.")
                return NO_HOME
            if not settle(h, home):
                return NO_HOME
        return hand(h, use, paths, choices)

    def work_on(self, name):
        import unfiled as UF
        if name == UF.NAME:
            self.host.efforts_page.open_unfiled()
        elif name:
            self.host.open_with_progress(name)
        return name

    def edit_pins(self, chosen=None):
        if chosen is None:
            d = QDialog(self); d.setWindowTitle("Pinned tools"); d.resize(420, 560)
            v = QVBoxLayout(d)
            v.addWidget(D.label("Tick the tools Home shows. Your role's starting set is a starting point only.", "muted"))
            boxes = {}
            import menufocus as MF
            from .modes import settings
            aside = MF.hidden(settings())
            for k, (t, what, _kind) in TOOLS.items():
                if k in aside:
                    continue
                cb = QCheckBox(f"{t}: {what}"); cb.setChecked(k in self.pins); v.addWidget(cb); boxes[k] = cb
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            v.addWidget(bb)
            if d.exec() != QDialog.Accepted:
                return self.pins
            chosen = [k for k in self.pins if k in boxes and boxes[k].isChecked()] + [k for k in boxes if boxes[k].isChecked() and k not in self.pins]
        save_pins(self.host.config_dir, chosen)
        self.refresh()
        return self.pins
