"""Home > Your Tools (3.53.0, the first screen): drop any file (or choose files, or paste a picture) and pick what to do with
it from the tools that take that kind of file (plan decision 3: ask which tool); your pinned tools, one click each
(decision 4: a starting set by role, changed freely); the files you last opened from here; your efforts and Unfiled.
Any tool works on loose files in Unfiled or on the effort you are working on (the Working on box, top right).
Rules only; nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QScrollArea, QVBoxLayout, QWidget)

import diag
import recentfiles as RF
from . import design as D
from .adaptive import FlowLayout

OFFICE = (".docx", ".xlsx", ".pptx")
# what a dropped file can be used for: key -> (what it says, the extensions it takes, None for any the reader takes)
USES = (("acrfinder", "Find acronyms (Acronym Finder, its own window)", None),
        ("acronyms", "Find acronyms in what I am working on", None),
        ("firstuse", "Check first use (First Use Check)", (".docx",)),
        ("copyreview", "Copy review (Technical Edit) of what I am working on", (".docx",)),
        ("fulltext", "Pull out all the text (Full Text)", None),
        ("shred", "Find the requirements (Shred)", (".pdf", ".docx", ".pptx", ".xlsx")),
        ("library", "Add to the Library of what I am working on", None),
        ("audit", "Audit against the standards (changes nothing)", OFFICE),
        ("leftovers", "Check for leftovers before it goes out (Final Checks)", (".docx",)),     # 3.57.0
        ("strip", "Strip the setup out (a clean copy)", (".docx",)))                             # 3.60.0
# the tools Home can pin: key -> (title, what, kind) ; kind "window" opens its own window, "page" goes to the page
TOOLS = {"acrfinder": ("Acronym Finder", "Scan any files for acronyms, apart from any effort", "window"),
         "firstuse": ("First Use Check", "Your Word files' first uses", "window"),
         "fulltext": ("Full Text", "Every word in the files, as text", "window"),
         "acronyms": ("Acronyms", "Scan and the acronym list", "page"), "acrlist": ("Acronym List", "The effort's list", "page"),
         "assign": ("Review", "Requirements from the customer's documents", "page"), "matrix": ("Matrix", "The compliance matrix", "page"),
         "library": ("Library", "The customer's documents", "page"), "compare": ("Compare", "Two versions, what changed", "page"),
         "structure": ("Structure Builder", "The response structure", "page"), "storyboards": ("Storyboards", "One sheet per section", "page"),
         "drafts": ("Draft Status", "A draft read back", "page"), "truth": ("Wall of Truth", "One approved way to state each fact", "page"),
         "reviews": ("Color Reviews", "Review packets and comments", "page"), "qa": ("Submission Check", "The volumes you will submit", "page"),
         "checks": ("Final Checks", "The PDF package, cross-references", "page"), "templates": ("Templates", "Every template the profiles make", "page"),
         "profiles": ("Effort Profiles", "Profiles built by picking", "page"), "fixcopy": ("Fix a Copy", "Fixes into a dated copy", "page"),
         "audit": ("Audit", "Files against every standard", "page"), "home": ("Effort Dashboard", "Where the effort stands", "page"),
         "mywork": ("My Work", "Your work in every effort", "page"), "refs": ("Team References", "The lists the team keeps", "page"),
         "custqa": ("Customer Q&A", "Questions to the customer", "page"),
         "techedit": ("Technical Edit", "Copy review of a draft", "page"),
         "shredreq": ("Requirements", "Every requirement in one file", "page")}
ROLE_PINS = {"Production": ["acrfinder", "firstuse", "techedit", "templates", "checks", "fixcopy", "refs"],
             "Proposal Manager": ["home", "shredreq", "assign", "reviews", "mywork", "acrfinder", "qa"],
             "Author": ["mywork", "drafts", "techedit", "acrfinder", "firstuse", "truth", "storyboards"],
             "Reviewer": ["reviews", "assign", "checks", "acrfinder"],
             "Capture": ["shredreq", "library", "assign", "structure", "custqa"]}
PINS_FILE = "home_pins.json"


def uses_for(paths):
    """The uses that take every one of the files."""
    import app_gui as A
    exts = {os.path.splitext(p)[1].lower() for p in paths}
    if not exts or not exts <= set(A.SUPPORTED_EXTS):
        return []
    out = [(k, t) for k, t, ok in USES if (ok is None or exts <= set(ok)) and not (k == "shred" and len(paths) != 1)]
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
            got = [k for k in (json.load(f) or {}).get("pins", []) if k in TOOLS and k not in aside]
        return got
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
    def __init__(self, on_files):
        super().__init__()
        self.on_files = on_files
        self.setAcceptDrops(True); self.setObjectName("dropzone")
        self.setStyleSheet("QFrame#dropzone { border: 2px dashed palette(mid); border-radius: 8px; }")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["l"], D.SPACE["l"], D.SPACE["l"], D.SPACE["l"])
        t = QLabel("Drop a file here: Word, PDF, PowerPoint, Excel or a picture. Then pick what to do with it.")
        t.setAlignment(Qt.AlignCenter); t.setWordWrap(True); v.addWidget(t)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        files = [os.path.normpath(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile() and os.path.isfile(u.toLocalFile())]
        if files:
            self.on_files(files)


class UseDialog(QDialog):
    """Ask which tool (decision 3): the uses that take these files."""

    def __init__(self, parent, paths, working_on):
        super().__init__(parent)
        self.setWindowTitle("What do you want to do?"); self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        names = ", ".join(os.path.basename(p) for p in paths[:3]) + (f" and {len(paths) - 3} more" if len(paths) > 3 else "")
        v.addWidget(D.label(names, "label"))
        self.list = QListWidget(); v.addWidget(self.list)
        for k, t in uses_for(paths):
            it = QListWidgetItem(t.replace("what I am working on", working_on)); it.setData(Qt.UserRole, k)
            self.list.addItem(it)
        if self.list.count():
            self.list.setCurrentRow(0)
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def picked(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it is not None else None


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
        ef = D.Card("Your efforts", "Double-click to work on one. Unfiled holds work not filed yet."); g.addWidget(ef, 0, 1)
        self.eff = QListWidget(); self.eff.setMinimumHeight(170); ef.add(self.eff)
        self.eff.itemDoubleClicked.connect(lambda it: self.work_on(it.data(Qt.UserRole)))
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
            b = D.button(t, None, lambda _=False, k_=k: self.open(k_), what)
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
        names = [n for n in h.efforts.names() if not (h.efforts.get(n) or {}).get("archived")]
        cur = h.effort_name
        for n in sorted(names, key=lambda x: (x != cur, x == UF.NAME, x.casefold())):
            label = n + ("   (working on)" if n == cur else "")
            if n == UF.NAME:
                try:
                    label += "   " + (UF.summary_text(UF.counts(h.efforts)) or "empty")
                except Exception:  # noqa: BLE001
                    diag.swallowed()
            it = QListWidgetItem(label); it.setData(Qt.UserRole, n); self.eff.addItem(it)
        if UF.NAME not in names:
            it = QListWidgetItem("Unfiled   (start here with no effort)"); it.setData(Qt.UserRole, UF.NAME); self.eff.addItem(it)

    def working_on(self):
        return self.host.effort_name or "Unfiled"

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

    def files_in(self, paths, use=None):
        """Ask which tool, then hand the files to it. Returns the use chosen (or None)."""
        if not paths:
            return None
        if not uses_for(paths):
            self.host.status("Stationkeeper does not read that kind of file.")
            return None
        if use is None:
            d = UseDialog(self, paths, self.working_on())
            if d.exec() != QDialog.Accepted:
                return None
            use = d.picked()
        if not use:
            return None
        self.run(use, paths)
        RF.add(self.host.config_dir, paths, dict((k, t.split(" (")[0]) for k, t, _ in USES).get(use, use))
        self.refresh()
        diag.activity("home_files_used", n=len(paths))
        return use

    def run(self, use, paths):
        h = self.host
        if use == "acrfinder":
            w = h.open_tool("acronyms")
            import acrlists as AL
            s = w.page.session
            last = ((s.last_scan or {}).get("paths") if s is not None else None) or []
            return w.page.scan(AL.add_files(last, paths))
        if use == "shred":
            h.go("shredreq")
            return h.shred_page.open(paths[0])
        if use == "compare":
            h.go("compare")
            return h.compare_space.show_files(paths[0], paths[1])
        if use == "firstuse":
            from .firstusetool import open_tool
            return open_tool(h.config_dir, paths)
        if use == "fulltext":
            from .fulltexttool import open_tool
            return open_tool(h.config_dir, paths)
        self.ensure_working_on()
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
        return None

    def ensure_working_on(self):
        """A use for 'what I am working on' with nothing open opens Unfiled (decision: loose work kept in Unfiled)."""
        if self.host.ws is None:
            self.host.efforts_page.open_unfiled(go=False)

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
