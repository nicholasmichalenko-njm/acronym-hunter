"""The Qt edition's main window (2.59.0): the effort (picked from the efforts on this PC, held with the same lock as
the tkinter edition), the steps of Compliance that are in Qt so far (Read RFP, Review), the status line, and autosave
of the compliance matrix two seconds after each change."""
import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QCompleter, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                               QMessageBox, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget)
import diag
import compliance as C
import effort as E
import setupdoc as SD
import workspace as W
import assign_ops as AO
from . import design as D
from .readpage import ReadPage
from .assign import AssignPage
from .structure import StructurePage
from .prove import ProvePage
from .crosswalkpage import CrosswalkPage
from .matrixpage import MatrixPage
from .setuppage import SetupPage
from .homepage import HomePage
from .dashpage import DashPage
from .recordpage import RecordPage
from .reviewpage import ReviewPage
from .acronympage import AcronymPage
from .effortlistpage import EffortListPage
from .custdocs import ComparePage, DeliverablesPage, DocsPage, ImpactPage, RequirementsPage
from .qapage import QAPage
from .keywordspage import KeywordsPage
from .exportallpage import ExportAllPage
from .settingspage import SettingsPage


RAIL = [("Home", [("efforts", "All Efforts")]),
        ("Effort", [("home", "Effort Home"), ("deliverables", "Deliverables"), ("dashboard", "Dashboard"), ("record", "Effort Record"),
                    ("reviews", "Color Reviews")]),
        ("Compliance", [("read", "Read RFP"), ("structure", "Structure"), ("assign", "Review"), ("prove", "Prove"),     # 2.99.0: near the
                        ("crosswalk", "L/M Crosswalk")]),                                                              # top: the review starts here
        ("Documents", [("library", "Library"), ("compare", "Changes"), ("requirements", "Submission Rules"),
                       ("custqa", "Customer Q&A")]),
        ("Deliver", [("matrix", "Matrix"), ("setup", "Response Setup"), ("postsub", "Post-Submission")]),
        ("Response Quality", [("acronyms", "Customer Terms"), ("acrlist", "Effort List"), ("qa", "Submission Check"),
                              ("lists", "Lists to Submit"), ("keywords", "Keywords")]),
        ("Effort Files", [("exportall", "Export All"), ("settings", "Settings")])]
TITLES = {"efforts": ("All Efforts", "Every effort in progress, a new one, and work not filed yet"),
          "home": ("Effort Home", "Stage, gate goals, tasks, questions and the calendar"),
          "dashboard": ("Dashboard", "The effort on one screen"),
          "record": ("Effort Record", "Details, team, stages and gates, status, package and backup"),
          "reviews": ("Color Reviews", "Color team review packets, read back onto each requirement"),
          "library": ("Library", "Every document of the effort: categories, folders, tags, roles and search"),
          "docs": ("Customer Versions", "The customer's documents and every version of them"),
          "requirements": ("Submission Rules", "What the customer requires of the submission now, and what changed it"),
          "custqa": ("Customer Q&A", "The questions we submit to the customer: their exact wording, our question, status and the answer"),
          "compare": ("Changes", "What a new version changed, what it touches, and a decision on every change"),
          "impact": ("Impact Review", "What one new version touched across the effort"),
          "deliverables": ("Deliverables", "Every deliverable at a glance: where each stands and what is missing"),
          "acronyms": ("Customer Terms", "Start: the acronyms the customer's documents use, offered to the effort list"),
          "acrlist": ("Effort List", "Throughout: the effort's glossary, with approved definitions"),
          "qa": ("Submission Check", "End: the volumes you will submit, against the effort list, banned words and page limits"),
          "lists": ("Lists to Submit", "End: the acronym lists for your volumes, built from what each one uses"),
          "keywords": ("Keywords", "The effort's keywords, suggestions with reasons, and the SharePoint export"),
          "exportall": ("Export All", "Every feature's outputs in one dated folder"),
          "settings": ("Settings", "New effort, the effort's folders, the master database, backups"),
          "read": ("Read RFP", "Bring the customer's documents into the review"),
          "structure": ("Structure", "The sections of your response"),
          "assign": ("Review", "Read every sentence on the page: decide it and capture what it holds"),
          "prove": ("Prove", "Every line read and decided"),
          "crosswalk": ("L/M Crosswalk", "Each instruction, the factor that scores it, and the work it describes"),
          "matrix": ("Matrix", "The compliance matrix as the customer will see it"),
          "setup": ("Response Setup", "The Word documents your writers start from"),
          "postsub": ("Post-Submission", "What the team does after the proposal goes in: owners, due dates, done")}


class MainWindow(QMainWindow):
    def __init__(self, app, config_dir, version=""):
        super().__init__()
        self.app = app
        self.config_dir = config_dir
        self.version = version
        self.efforts = E.Registry(os.path.join(config_dir, "efforts.json"))
        try:                                       # 2.86.0: default gate goals saved on this PC
            import effortrec as _ER
            _ER.load_default_goals(config_dir)
            import process as _PR                  # 2.93.0: the team's stages, gates and roles
            _PR.apply(config_dir)
            import doctypes as _DT                 # 2.94.0: the team's document types and initials
            _DT.apply(config_dir)
            import folderplan as _FP               # 2.95.0: the team's folders and file names
            _FP.apply(config_dir)
        except Exception:
            diag.swallowed()
        self.authors = self._load_authors(config_dir)          # 2.77.0: the one place names come from
        self.ws = None
        self.effort_name = ""
        self.effort_path = ""
        self.review = None
        self.presence_answer = None                # tests: "open" or "cancel"
        self.resize(1600, 1000)
        root = QWidget(); rh = QHBoxLayout(root); rh.setContentsMargins(0, 0, 0, 0); rh.setSpacing(0)
        # the navigation rail: areas of the app, the ones still in the classic window shown but not clickable
        rail = QWidget(); rail.setObjectName("railbox"); rail.setFixedWidth(232)
        rv = QVBoxLayout(rail); rv.setContentsMargins(D.SPACE["s"], 0, D.SPACE["s"], D.SPACE["m"]); rv.setSpacing(2)
        from .brandview import MarkingStrip, RailBrand, RailFooter
        self.rail_brand = RailBrand(self)                                   # 2.88.0: the company logos, always in view
        self.steps = QButtonGroup(self)
        self.step_btns = {}
        for head, items in RAIL:
            h = QLabel(head); h.setObjectName("railhead"); h.setWordWrap(True); rv.addWidget(h)
            for key, text in items:
                b = QPushButton(text.replace("&", "&&")); b.setObjectName("rail"); b.setCheckable(bool(key))
                if key:
                    b.clicked.connect(lambda _=False, k=key: self.go(k))
                    self.steps.addButton(b); self.step_btns[key] = b
                else:
                    b.setEnabled(False)
                    b.setToolTip("Still in Stationkeeper (classic): it moves to Qt in a coming release.")
                rv.addWidget(b)
        rv.addStretch(1)
        self.rail_footer = RailFooter(version)                              # 2.88.0: the Stationkeeper mark, always in view
        rail_scroll = QScrollArea(); rail_scroll.setObjectName("railbox"); rail_scroll.setWidgetResizable(True)    # 2.65.0: a long rail scrolls
        rail_scroll.setFrameShape(QFrame.NoFrame); rail_scroll.setFixedWidth(232); rail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rail.setFixedWidth(232 - 2); rail_scroll.setWidget(rail)
        rail_col = QWidget(); rail_col.setObjectName("railbox"); rail_col.setFixedWidth(232)
        rcv = QVBoxLayout(rail_col); rcv.setContentsMargins(0, 0, 0, D.SPACE["m"]); rcv.setSpacing(0)
        rcv.addWidget(self.rail_brand); rcv.addWidget(rail_scroll, 1); rcv.addWidget(self.rail_footer)
        rh.addWidget(rail_col)
        col = QWidget(); cv = QVBoxLayout(col); cv.setContentsMargins(0, 0, 0, 0); cv.setSpacing(0)
        # the top bar: where you are, the effort, search, and whether everything is saved
        bar = QFrame(); bar.setProperty("bar", True)
        bh = QHBoxLayout(bar); bh.setContentsMargins(D.SPACE["xl"], D.SPACE["m"], D.SPACE["xl"], D.SPACE["m"]); bh.setSpacing(D.SPACE["m"])
        tcol = QVBoxLayout(); tcol.setSpacing(0)
        self.page_title = D.label("", "display", wrap=False); tcol.addWidget(self.page_title)
        self.page_sub = D.label("", "muted", wrap=False); tcol.addWidget(self.page_sub)
        bh.addLayout(tcol, 1)
        self.search = QLineEdit(); self.search.setPlaceholderText("Find a sentence (words or ID)...")
        self.search.setMinimumWidth(320); self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self.find_go)
        bh.addWidget(self.search)
        bh.addWidget(D.label("Effort", "label", wrap=False))
        self.effort_box = QComboBox(); self.effort_box.setMinimumWidth(220)
        self.effort_box.activated.connect(lambda i: self.open_effort(self.effort_box.itemText(i)))
        bh.addWidget(self.effort_box)
        self.saved = D.Pill("Saved", "ok"); bh.addWidget(self.saved)
        self.mode_chip = D.Pill("", "ok"); bh.addWidget(self.mode_chip)   # 2.97.0: Offline, Connected or SCIF-ready
        self.mode_chip.mousePressEvent = lambda _e: self.go_mode()
        self.marking = MarkingStrip(); cv.addWidget(self.marking)            # 2.88.0: CUI or proprietary, on every page
        from .unfiledview import UnfiledStrip
        self.unfiled_strip = UnfiledStrip(self); cv.addWidget(self.unfiled_strip)   # 2.91.0: work not filed yet
        from .watchview import WatchStrip
        self.watch_strip = WatchStrip(self); cv.addWidget(self.watch_strip)         # 2.94.0: new, changed, missing files
        self.watch_found, self._wa_thread, self._wa_result, self._wa_last = None, None, None, 0.0
        cv.addWidget(bar)
        from .adaptive import PageStack
        self.stack = PageStack()                   # 2.86.0: a page scrolls only when the window is smaller than it needs
        from .effortshome import EffortsHome
        self.efforts_page = EffortsHome(self)        # 2.91.0: Home: every effort, + Add an Effort, Unfiled work
        self.home_page = HomePage(self)
        self.dash_page = DashPage(self)
        self.record_page = RecordPage(self)
        self.review_page = ReviewPage(self)
        self.acronym_page = AcronymPage(self)
        self.acrlist_page = EffortListPage(self)
        self.docs_page = DocsPage(self)
        from .librarypage import LibraryPage
        self.library_page = LibraryPage(self)        # 2.83.0
        from .listspage import ListsPage
        self.lists_page = ListsPage(self)            # 2.86.0
        self.requirements_page = RequirementsPage(self)
        self.compare_page = ComparePage(self)
        from .custqapage import CustQAPage
        self.custqa_page = CustQAPage(self)           # 2.98.0
        self.impact_page = ImpactPage(self)
        self.deliverables_page = DeliverablesPage(self)
        self.qa_page = QAPage(self)
        self.keywords_page = KeywordsPage(self)
        self.exportall_page = ExportAllPage(self)
        self.settings_page = SettingsPage(self)
        self.read_page = ReadPage(self)
        self.structure_page = StructurePage(self)
        self.assign_page = AssignPage(self)
        self.prove_page = ProvePage(self)
        self.crosswalk_page = CrosswalkPage(self)
        self.matrix_page = MatrixPage(self)
        self.setup_page = SetupPage(self)
        from .postsubpage import PostSubPage
        self.postsub_page = PostSubPage(self)          # 2.91.0
        self.pages = {"efforts": self.efforts_page, "home": self.home_page, "dashboard": self.dash_page, "record": self.record_page, "reviews": self.review_page, "library": self.library_page, "docs": self.docs_page, "requirements": self.requirements_page, "compare": self.compare_page, "custqa": self.custqa_page,
                      "impact": self.impact_page, "deliverables": self.deliverables_page, "qa": self.qa_page, "lists": self.lists_page, "keywords": self.keywords_page, "exportall": self.exportall_page,
                      "settings": self.settings_page, "acronyms": self.acronym_page, "acrlist": self.acrlist_page, "read": self.read_page, "structure": self.structure_page, "assign": self.assign_page, "prove": self.prove_page,
                      "crosswalk": self.crosswalk_page, "matrix": self.matrix_page, "setup": self.setup_page, "postsub": self.postsub_page}
        for pg in self.pages.values():
            self.stack.addWidget(pg)
        cv.addWidget(self.stack, 1)
        rh.addWidget(col, 1)
        self.setCentralWidget(root)
        self.toaster = D.Toast(self)
        from .progress import StatusTask
        self.task = StatusTask(self)                # 2.82.0: a running job's bar in the status bar, on every page
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: (self.search.setFocus(), self.search.selectAll()))
        from . import helpcenter as HC               # 2.81.0: find anything, and the shortcuts
        QShortcut(QKeySequence("Ctrl+K"), self, activated=lambda: HC.open_finder(self))
        QShortcut(QKeySequence("F1"), self, activated=lambda: HC.show_shortcuts(self))
        self.save_timer = QTimer(self, singleShot=True, interval=2000, timeout=self.save_now)
        self.lock_timer = QTimer(self, interval=60000, timeout=lambda: self.ws.refresh_lock() if self.ws else None)
        self.lock_timer.start()
        self._rd_seen = self._rd_done = None                   # 2.92.0: the readable copy, kept current
        self._rd_thread = None
        self.rd_written = ""
        self.rd_timer = QTimer(self, interval=3000, timeout=lambda: (self.readable_tick(), self.watch_tick()))
        self.rd_timer.start()
        from .safety import Safety                 # 2.78.0: backups, recovery, where you were, the crash screen
        self.safety = Safety(self)
        self.fill_efforts()
        self.go("read")
        self.title()

    # ------------------------------------------------------------ finding a sentence
    def fill_search(self):
        R = self.review
        items = [f"{it['id']}   {it['text'][:110]}" for it in R.M.items] if R else []
        comp = QCompleter(items, self)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        comp.setMaxVisibleItems(14)
        comp.activated.connect(lambda text: self.find_go(text))
        self.search.setCompleter(comp)

    def find_go(self, text=None):
        """Go to the sentence picked (or the first one whose ID or words match) in Review."""
        R = self.review
        q = (text if isinstance(text, str) and text else self.search.text()).strip()
        if R is None or not q:
            return None
        iid = q.split("   ", 1)[0]
        it = R.item(iid)
        if it is None:
            ql = q.casefold()
            it = next((x for x in R.M.items if ql == x["id"].casefold()), None) or \
                next((x for x in R.M.items if ql in x["text"].casefold()), None)
        if it is None:
            self.status(f"No sentence has \"{q}\".")
            return None
        self.go("assign")
        self.assign_page.select(it["id"])
        diag.activity("qt_find_sentence")
        return it["id"]

    # ------------------------------------------------------------ efforts
    def fill_efforts(self):
        names = [n for n in self.efforts.names() if not (self.efforts.get(n) or {}).get("archived")]
        self.effort_box.clear()
        self.effort_box.addItems(names)
        cur = self.efforts.current
        if cur in names:
            self.effort_box.setCurrentText(cur)

    def open_with_progress(self, name, title=""):
        """2.82.0: open an effort under a cover that says what is happening (after an update, at start), so the pause
        while the matrix loads never looks like lost work."""
        from .progress import Overlay
        if getattr(self, "overlay", None) is None:
            self.overlay = Overlay(self)
        self.overlay.begin(title or f"Opening {name}", "Getting ready")
        try:
            ok = self.open_effort(name, progress=self.overlay.step)
        finally:
            self.overlay.finish()
        if ok:
            self.toast(f"{name} is open, as you left it.")
        return ok

    def open_effort(self, name, force=False, progress=None):
        """Hold the effort (the same lock as the tkinter edition) and open its compliance matrix. Returns True.
        progress(fraction, text): 2.82.0, each step as it opens (open_with_progress)."""
        say = progress or (lambda _f, _t: None)
        info = self.efforts.get(name) or {}
        if not info.get("path"):
            return False
        if hasattr(self, "read_page") and not self.read_page.confirm_stop():   # 2.82.0: a read is running
            self.fill_efforts()
            return False
        from .modes import warn_open                # 2.79.0 Connected mode: someone else has it open
        if not warn_open(self, name, self.presence_answer):
            return False
        self.close_effort()
        ws = W.Workspace(W.data_dir_for(info["path"]), name)
        if not ws.acquire_lock(force=force):
            who = ws.locked_by or {}
            QMessageBox.information(self, "Effort open elsewhere", f"{name} is open in another window"
                                    + (f" ({who.get('user', '')} on {who.get('computer', '')})" if who else "")
                                    + ". Close it there first: both editions work on the same files.")
            self.fill_efforts()
            return False
        self.ws, self.effort_name, self.effort_path = ws, name, info["path"]
        try:                                       # 2.90.0: a note in the effort's app data folder: the app's files
            import effortfolders as EF
            EF.note_app_data(ws.root)
        except Exception:
            diag.swallowed()
        if self.efforts.current != name:          # 2.84.0: the next start (after an update too) reopens this effort
            try:
                self.efforts.current = name
            except OSError:
                diag.swallowed()
        diag.activity("qt_effort_opened")
        say(0.1, f"{name}: checking the effort's files")
        _issues, repaired = self.safety.health()   # 2.80.0: check the effort; put back a damaged list or matrix
        p = ws.get("compliance_path") or ""
        recovered = False
        if p and os.path.isfile(p):
            say(0.3, f"{name}: loading the compliance matrix")
            try:
                M = C.Matrix(p).load()
                recovered = self.safety.offer_recovery(M)
                self.set_matrix(M)
                if recovered:
                    self.save_now()
            except Exception:
                diag.swallowed()
                self.status("The compliance matrix could not be opened.")
        else:
            self.review = None
            self.assign_page.load()
        say(0.7, f"{name}: setting up the pages")
        self.read_page.refresh()
        self.go("assign" if self.review is not None and self.review.M.items else "read")
        self.safety.opened()
        self.warm_up()                             # 2.82.0: pages that read every document are ready before you open them
        say(0.9, f"{name}: back where you were")
        self.safety.restore_view()                 # 2.78.0: back where you were in this effort
        if recovered:
            self.toast(self.safety.recovered_text)
        if repaired:
            self.toast(repaired[0])
        elif any(i["severity"] == "error" for i in _issues):
            self.status("Effort health: a problem needs you. See Effort record > Effort health.")
        self.apply_marking()
        self.unfiled_strip.refresh()
        self.remember_fields()                     # 2.95.0: folder and file names use the effort's fields
        self.watch_found = None; self.watch_strip.setVisible(False)
        self.watch_start()                         # 2.94.0: what changed in the watched folders since last time
        self.title()
        return True

    def make_unfiled_effort(self, name=None):
        """2.91.0: Unfiled work becomes a named effort (see unfiledview)."""
        from .unfiledview import make_effort
        return make_effort(self, name)

    def open_effort_folder(self, kind=None, open_it=True):
        """2.90.0: the effort's folder (or one of its folders) in File Explorer. Returns the folder."""
        import effortfolders as EF
        if self.ws is None:
            self.status("Open an effort first.")
            return ""
        d = EF.folder(self.effort_path, kind) if kind else EF.root(self.effort_path)
        if open_it and not os.environ.get("AH_TEST"):
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        diag.activity("qt_effort_folder_opened")
        return d

    def apply_marking(self):
        """2.88.0: the strip across every page for an effort marked CUI, Proprietary or the team's own marking."""
        sens = ""
        if self.ws is not None:
            try:
                import branding as BR
                import effortrec as _R
                sens = BR.identity(_R.Record(self.ws.root))["sensitivity"]
            except Exception:
                diag.swallowed()
        self.marking.show_marking(sens)
        self.refresh_level()
        return sens

    def refresh_level(self):
        """2.97.0: the open effort's sensitivity (declared, and its documents' markings), which decides whether
        training data and bug reports may be kept. -1 when nothing is known or no effort is open."""
        import secure
        import sensitivity as S
        try:
            secure.EFFORT_LEVEL = S.effort_level(self.effort_path) if self.ws is not None else -1
        except Exception:
            diag.swallowed()
            secure.EFFORT_LEVEL = -1
        if hasattr(self, "mode_chip"):
            self.show_mode_chip()
        return secure.EFFORT_LEVEL

    def go_branding(self):
        """2.88.0: Settings, at the Branding card."""
        self.go("settings")
        try:
            self.settings_page.scroll.ensureWidgetVisible(self.settings_page.branding_card, 0, 0)
        except Exception:
            diag.swallowed()
        return True

    # ------------------------------------------------------------ 2.92.0 the readable copy
    def _readable_on(self):
        return not os.environ.get("AH_TEST") or bool(os.environ.get("SK_READABLE_TEST"))

    # ------------------------------------------------------------ 2.95.0 folders and file names
    def effort_fields(self):
        info = self.efforts.get(self.effort_name) or {}
        return {"Effort": self.effort_name, "Client": info.get("client", ""), "Solicitation": info.get("solicitation", ""),
                "Internal": info.get("internal_no", "")}

    def remember_fields(self):
        import effortfolders as EF
        if self.effort_path:
            EF.remember(self.effort_path, self.effort_fields())

    def out_path(self, key, ext=None, **fields):
        """Where a save dialog starts for an output: its folder and name by Settings > Folders and file names."""
        import effortfolders as EF
        self.remember_fields()
        return EF.place(self.effort_path, key, fields, ext)

    # ------------------------------------------------------------ 2.94.0 watched folders
    WATCH_EVERY_S = 180

    def _watch_on(self):
        return not os.environ.get("AH_TEST") or bool(os.environ.get("SK_WATCH_TEST"))

    def watch_customer_dir(self):
        import effortfolders as EF
        info = self.efforts.get(self.effort_name) or {}
        return info.get("customer_dir") or (EF.folder(self.effort_path, "customer", make=False) if self.effort_path else "")

    def watch_lib_rec(self):
        import docversions as DV
        import effortrec as RR
        return DV.Library(self.ws.p("documents")).load(), RR.Record(self.ws.root)

    def watch_now(self):
        """Check the watched folders now (in this thread) and show what was found. Returns it."""
        import watch as WA
        if self.ws is None:
            return None
        lib, _rec = self.watch_lib_rec()
        found = WA.check(lib, self.ws.root, self.watch_customer_dir())
        return self.watch_show(found)

    def watch_show(self, found):
        self.watch_found = found
        self.watch_strip.show_found(found)
        if found and found.get("missing"):
            diag.activity("qt_watch_missing", n=len(found["missing"]))
        return found

    def watch_start(self, force=False):
        """Check the watched folders in the background (shown when it finishes)."""
        import bgwork
        import time
        import watch as WA
        if self.ws is None or (not force and not self._watch_on()) or (self._wa_thread is not None and self._wa_thread.is_alive()):
            return None
        root, cust, docs, name = self.ws.root, self.watch_customer_dir(), self.ws.p("documents"), self.effort_name
        self._wa_last = time.monotonic()

        def run():
            import docversions as DV
            try:
                self._wa_result = (name, WA.check(DV.Library(docs).load(), root, cust))
            except Exception:
                diag.swallowed()
        self._wa_thread = bgwork.start(run, "stationkeeper-watch")
        return self._wa_thread

    def watch_tick(self):
        import time
        if self._wa_result is not None and (self._wa_thread is None or not self._wa_thread.is_alive()):
            name, found = self._wa_result
            self._wa_result = None
            if self.ws is not None and name == self.effort_name:
                self.watch_show(found)
            return True
        if self.ws is not None and self._watch_on() and time.monotonic() - self._wa_last > self.WATCH_EVERY_S:
            self.watch_start()
        return False

    def watch_add(self, choices=None):
        """Add them...: the new and changed files go to the Library's reading table (a changed file comes up as a new
        version of its document), one category at a time."""
        import watch as WA
        f = self.watch_found or {}
        items = list(f.get("new", [])) + [(p, d.get("category", "customer")) for p, d, _v in f.get("changed", [])]
        if not items or self.ws is None:
            return None
        cats = {}
        for p, c in items:
            cats.setdefault(c, []).append(p)
        cat, paths = next(iter(cats.items()))
        rel = WA.relative_folders(paths, self.ws.root, self.watch_customer_dir())
        self.go("library")
        if len(cats) > 1:
            self.status(f"Adding the {self.library_page.lib.category_name(cat) if self.library_page.lib else cat} files first; "
                        "Add them... again for the rest.")
        diag.activity("qt_watch_add", n=len(paths))
        return self.library_page.add(paths, folders=rel, category=cat, choices=choices)

    def watch_set_aside(self):
        import watch as WA
        f = self.watch_found or {}
        paths = [p for p, _c in f.get("new", [])] + [p for p, _d, _v in f.get("changed", [])]
        if self.ws is None or not paths:
            return 0
        n = WA.set_aside(self.ws.root, paths)
        diag.activity("qt_watch_set_aside", n=n)
        self.toast(f"{n} file(s) set aside: they come back only if they change")
        self.watch_show(dict(f, new=[], changed=[]))
        return n

    def watch_missing(self, run=True):
        from .watchview import MissingDialog
        if not (self.watch_found or {}).get("missing"):
            return None
        d = MissingDialog(self, self.watch_found)
        if not run:
            return d
        d.exec()
        self.watch_now()
        self.library_page.refresh() if hasattr(self, "library_page") else None
        return d

    def watch_folders(self, run=True):
        from .watchview import FoldersDialog
        if self.ws is None:
            return None
        d = FoldersDialog(self)
        if not run:
            return d
        d.exec()
        return d

    def readable_job(self, overview=False):
        import readablejob as RJ
        import tzones as TZ
        from .modes import settings
        if self.ws is None:
            return None
        info = dict(self.efforts.get(self.effort_name) or {})
        mp = self.ws.get("compliance_path", "") or ""
        return RJ.job(self.effort_name, self.effort_path, self.ws.root, mp, info, self.version, overview, TZ.my_zone(settings()))

    def readable_tick(self):
        """Every few seconds: when the effort's saved files changed and have been quiet since the last look, rewrite the
        readable copy in the background."""
        import readablejob as RJ
        if self.ws is None or not self._readable_on() or (self._rd_thread is not None and self._rd_thread.is_alive()):
            return False
        sig = RJ.signature(self.effort_path, self.ws.root, self.ws.get("compliance_path", "") or "")
        quiet = sig == self._rd_seen
        self._rd_seen = sig
        if not quiet or sig == self._rd_done:
            return False
        self._rd_done = sig
        self.readable_start(self.readable_job())
        return True

    def readable_start(self, job):
        import bgwork
        import readablejob as RJ
        if job is None:
            return None

        def run():
            try:
                RJ.write(job)
                import datetime as _dt
                self.rd_written = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
            except Exception:
                diag.swallowed()
        self._rd_thread = bgwork.start(run, "stationkeeper-readable")
        diag.activity("qt_readable_written")
        return self._rd_thread

    def readable_now(self, overview=True, wait=True):
        """Write the readable copy now (with the Effort overview). Returns its folder, or ''."""
        import readablejob as RJ
        job = self.readable_job(overview)
        if job is None:
            return ""
        if self._rd_thread is not None and self._rd_thread.is_alive():
            self._rd_thread.join(timeout=120)
        if wait:
            try:
                RJ.write(job)
                import datetime as _dt
                self.rd_written = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
            except Exception:
                diag.swallowed()
                self.status("The readable copy could not be written just now; it is written again after the next change.")
                return ""
        else:
            self.readable_start(job)
        return job["folder"]

    def open_readable(self, open_it=True):
        """The readable copy's folder in File Explorer (written first)."""
        if self.ws is None:
            self.status("Open an effort first.")
            return ""
        d = self.readable_now(overview=True)
        if d and open_it and not os.environ.get("AH_TEST"):
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        diag.activity("qt_readable_opened")
        return d

    def close_effort(self):
        self._warm_stop = True
        if self.ws is not None and self._readable_on():         # 2.92.0: the readable copy, with the overview, as it closes
            try:
                self.save_now()
                self.readable_now(overview=True, wait=False)
            except Exception:
                diag.swallowed()
        if hasattr(self, "read_page"):
            self.read_page.abandon()                 # 2.82.0: a read of this effort ends with it, writing nothing
        self.save_now()
        if self.ws is not None and hasattr(self, "safety"):
            self.safety.closing()
        if self.ws is not None:
            try:
                self.ws.release_lock()
            except Exception:
                diag.swallowed()
        self.ws, self.review = None, None
        import secure
        secure.EFFORT_LEVEL = -1                     # 2.97.0
        if hasattr(self, "marking"):
            self.marking.show_marking("")
        if hasattr(self, "unfiled_strip"):
            self.unfiled_strip.setVisible(False)

    def set_matrix(self, M, new=False):
        self.review = AO.Review(M)
        self.safety.loaded(M.path)                 # 2.80.0: what is on disk now, to notice another copy's save
        SD.setup_of(M)
        if self.ws is not None:                     # 2.68.0: each file's document initial and type
            try:
                import docversions as DV
                SD.sync_docs(M, DV.Library(self.ws.p("documents")).load())
            except Exception:
                diag.swallowed()
        try:                                        # 2.70.0: list lead-ins an older read kept inside their items
            import capture as CAP
            got = CAP.add_lead_ins(M)
            if got:
                diag.activity("compliance_lead_ins_added", n=len(got))
                self.status(f"{len(got)} list lead-in(s) are now sentences of their own, ready to assign.")
        except Exception:
            diag.swallowed()
        if self.ws is not None:
            self.ws.set("compliance_path", M.path)
        if new:
            self.save_now()
        self.assign_page.load()
        self.fill_search()
        self.title()

    def people(self):
        """2.77.0: the names on the author list that show in the open effort (the only names pickers offer)."""
        return self.authors.for_effort(self.effort_name) if self.ws is not None else []

    def _load_authors(self, config_dir):
        import authorlist as AL
        lst = AL.load(config_dir)
        if not lst.exists:                       # first start of 2.77.0: start from each effort's team; nothing disappears
            teams = []
            for n in self.efforts.names():
                path = (self.efforts.get(n) or {}).get("path")
                if path:
                    try:
                        rec = W.read_json(os.path.join(W.data_dir_for(path), "record.json"), None) or {}
                        teams.append((n, [m.get("name", "") for m in rec.get("team", []) if isinstance(m, dict)]))
                    except Exception:
                        diag.swallowed()
            try:
                AL.seed(lst, teams)
            except OSError:
                diag.swallowed()
        return lst

    def authors_changed(self):
        """The author list changed: pages that show names refresh."""
        try:
            if self.ws is not None:
                self.record_page.refresh()
        except Exception:
            diag.swallowed()

    # ------------------------------------------------------------ saving
    def changed(self):
        if self.review is not None:
            self.review.M.pending = True
            self.save_timer.start()
            self.safety.changed()                  # 2.78.0: the recovery copy, written as you work
        self.title()

    def save_now(self):
        self.save_timer.stop()
        if self.review is not None and self.review.M.pending:
            if not self.safety.before_save(self.review.M):
                self.title()
                return
            try:
                self.review.M.save()
                self.review.M.pending = False
                self.safety.saved(self.review.M.path)      # 2.78.0: clear the recovery copy; a dated copy now and then
                self.fill_search()
            except PermissionError:
                self.status("The matrix is open in Excel: close it there, and it is saved again in two seconds.")
                self.save_timer.start()
            except Exception:
                diag.swallowed()
                self.status("The matrix could not be saved.")
        self.title()

    # ------------------------------------------------------------ the rest
    def go(self, step):
        pg = self.pages[step]
        if hasattr(pg, "refresh"):
            pg.refresh()
        self.stack.setCurrentWidget(pg)
        if step in self.step_btns:                  # 2.85.0: Customer versions and Impact review live inside other pages
            self.step_btns[step].setChecked(True)
        else:
            for b in self.step_btns.values():
                b.setChecked(False)
        t, sub = TITLES[step]
        self.page_title.setText(t)
        self.page_sub.setText(sub + (f"  \u00b7  {self.effort_name}" if self.effort_name else ""))

    def import_package(self, path=None, dest=None, mode=None):
        """2.74.0: an effort package (.skpkg) someone handed over."""
        from .pkgimport import import_package
        return import_package(self, path, dest, mode)

    def status(self, text):
        self.statusBar().showMessage(text, 9000)

    # 2.82.0: the running job in the status bar (TaskPanel calls these)
    def task_start(self, title):
        self.task.start(title)

    def task_step(self, frac, detail=""):
        self.task.step(frac, detail)

    def task_end(self):
        self.task.end()

    def toast(self, text):
        self.toaster.show_text(text)
        self.status(text)

    def title(self):
        dirty = self.review is not None and self.review.M.pending
        self.setWindowTitle(("* " if dirty else "") + (f"{self.effort_name}: " if self.effort_name else "")
                            + f"Stationkeeper {self.version}".strip() + self._mode_badge())
        if hasattr(self, "mode_chip"):
            try:
                self.show_mode_chip()
            except Exception:
                diag.swallowed()
        if hasattr(self, "saved"):
            self.saved.setText("Saving..." if dirty else ("Saved" if self.review is not None else "No matrix"))
            self.saved.set_tone("warn" if dirty else ("ok" if self.review is not None else "head"))

    def warm_up(self, wait=False):
        """Work out version changes and submission requirements in the background, so Documents, Requirements, Effort
        home and the dashboard open at once. Returns the thread."""
        import threading
        import docversions as DV
        if self.ws is None:
            return None
        folder, root = self.ws.p("documents"), self.ws.root
        cd = (self.efforts.get(self.effort_name) or {}).get("customer_dir", "") or ""
        self._warm_stop = False
        stop = lambda: self._warm_stop or self.ws is None or self.ws.root != root

        def run():
            try:
                DV.Library(folder).load().warm(stop=stop)
                if cd and os.path.isdir(cd):                 # fingerprints of the customer folder's files, for Documents
                    for f in sorted(os.listdir(cd)):
                        if stop():
                            break
                        p = os.path.join(cd, f)
                        if os.path.isfile(p) and f.lower().endswith((".docx", ".pdf", ".pptx", ".xlsx", ".txt")):
                            DV.sha256_cached(p)
            except Exception:
                diag.swallowed()
        t = threading.Thread(target=run, name="stationkeeper-warm-up", daemon=True)
        t.start()
        if wait:
            t.join()
        self._warm_thread = t
        return t

    def show_mode_chip(self):
        """2.97.0: the mode in the top bar, with what the app keeps in it (the tooltip); click: Settings, at the mode."""
        import secure
        import sensitivity as S
        import workmode as WM
        from .modes import mode
        m = mode()
        tone = {WM.SECURED: "crit", WM.CONNECTED: "accent", WM.OFFLINE: "ok"}.get(m, "warn")
        self.mode_chip.setText(WM.NAMES.get(m, "Mode not set"))
        self.mode_chip.set_tone(tone)
        if secure.ACTIVE:
            tip = "SCIF-ready (locked): no logs, no training data, no bug reports or support files."
        else:
            lv = secure.EFFORT_LEVEL
            if self.ws is None:
                train = "Open an effort to see whether its training data may be kept."
            elif secure.training_ok():
                train = f"Training data may be kept for this effort ({S.name(lv)})."
            elif lv < 0:
                train = "No training data for this effort: its sensitivity is not set (Effort Home > Edit details)."
            else:
                train = f"No training data for this effort: it is {S.name(lv)}."
            tip = (WM.LONG.get(m, "Choose where Stationkeeper is used in Settings.") + "\nContent-free logs are kept on this PC. "
                   + train + "\nDocuments marked above CUI are refused.")
        self.mode_chip.setToolTip(tip + "\nClick to change it in Settings.")
        return m

    def go_mode(self):
        self.go("settings")
        try:
            self.settings_page.scroll.ensureWidgetVisible(self.settings_page.mode, 0, 0)
        except Exception:
            diag.swallowed()
        return True

    def _mode_badge(self):
        try:
            from .modes import badge
            b = badge()
            return f"  \u00b7  {b}" if b else ""
        except Exception:
            diag.swallowed()
            return ""

    def closeEvent(self, e):
        if not self.read_page.confirm_stop():         # 2.82.0: a read is running
            e.ignore()
            return
        self.assign_page.save_notes()
        self.close_effort()
        from .readpage import _ORPHANS
        if _ORPHANS:                                  # stopped reads end after their current file; wait so none is cut off
            self.hide()
            for wk in list(_ORPHANS):
                wk.wait(600000)
        e.accept()
