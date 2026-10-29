"""The Qt edition's main window (2.59.0): the effort (picked from the efforts on this PC, held with the same lock as
the tkinter edition), the steps of Compliance that are in Qt so far (Read RFP, Assign), the status line, and autosave
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


RAIL = [("EFFORT", [("home", "Effort home"), ("dashboard", "Dashboard"), ("record", "Effort record"), ("reviews", "Reviews")]),
        ("CUSTOMER DOCUMENTS", [("docs", "Documents"), ("requirements", "Requirements"), ("compare", "Compare"),
                                ("impact", "Impact review"), ("deliverables", "Deliverables")]),
        ("ACRONYMS", [("acronyms", "Scan and review"), ("acrlist", "Effort list")]),
        ("COMPLIANCE", [("read", "Read RFP"), ("structure", "Structure"), ("assign", "Assign"), ("prove", "Prove"),
                        ("crosswalk", "L/M crosswalk")]),
        ("DELIVER", [("matrix", "Matrix"), ("setup", "Response Setup")]),
        ("QUALITY", [("qa", "QA/QC"), ("keywords", "Keywords")]),
        ("EFFORT FILES", [("exportall", "Export all"), ("settings", "Settings")])]
TITLES = {"home": ("Effort home", "Stage, gate goals, tasks, questions and the calendar"),
          "dashboard": ("Dashboard", "The effort on one screen"),
          "record": ("Effort record", "Details, team, stages and gates, status, package and backup"),
          "reviews": ("Reviews", "Color team review packets, read back onto each requirement"),
          "docs": ("Documents", "The customer's documents and every version of them"),
          "requirements": ("Requirements", "What the customer documents require of the submission"),
          "compare": ("Compare", "Two versions side by side, each change beside the matrix requirement it touches"),
          "impact": ("Impact review", "What one new version touched across the effort"),
          "deliverables": ("Deliverables", "What the effort owes the customer, and where each stands"),
          "acronyms": ("Scan and review", "Every acronym, abbreviation, unit and symbol, and the effort list"),
          "acrlist": ("Effort list", "The effort's acronyms: definitions, status, approvers, and the lists to deliver"),
          "qa": ("QA/QC", "Our Word volumes against the effort list, banned words and page limits"),
          "keywords": ("Keywords", "The effort's keywords, suggestions with reasons, and the SharePoint export"),
          "exportall": ("Export all", "Every feature's outputs in one dated folder"),
          "settings": ("Settings", "New effort, the effort's folders, the master database, backups"),
          "read": ("Read RFP", "Bring the customer's documents into the review"),
          "structure": ("Structure", "The sections of your response"),
          "assign": ("Assign", "Decide every sentence on the page"),
          "prove": ("Prove", "Every line read and decided"),
          "crosswalk": ("L/M crosswalk", "Each instruction, the factor that scores it, and the work it describes"),
          "matrix": ("Matrix", "The compliance matrix as the customer will see it"),
          "setup": ("Response Setup", "The Word documents your writers start from")}


class MainWindow(QMainWindow):
    def __init__(self, app, config_dir, version=""):
        super().__init__()
        self.app = app
        self.config_dir = config_dir
        self.version = version
        self.efforts = E.Registry(os.path.join(config_dir, "efforts.json"))
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
        brand = QLabel("Stationkeeper"); brand.setObjectName("brand"); rv.addWidget(brand)
        self.steps = QButtonGroup(self)
        self.step_btns = {}
        for head, items in RAIL:
            h = QLabel(head); h.setObjectName("railhead"); h.setWordWrap(True); rv.addWidget(h)
            for key, text in items:
                b = QPushButton(text); b.setObjectName("rail"); b.setCheckable(bool(key))
                if key:
                    b.clicked.connect(lambda _=False, k=key: self.go(k))
                    self.steps.addButton(b); self.step_btns[key] = b
                else:
                    b.setEnabled(False)
                    b.setToolTip("Still in Stationkeeper (classic): it moves to Qt in a coming release.")
                rv.addWidget(b)
        rv.addStretch(1)
        ver = QLabel(f"Offline. No AI. {version}"); ver.setObjectName("railhead"); rv.addWidget(ver)
        rail_scroll = QScrollArea(); rail_scroll.setObjectName("railbox"); rail_scroll.setWidgetResizable(True)    # 2.65.0: a long rail scrolls
        rail_scroll.setFrameShape(QFrame.NoFrame); rail_scroll.setFixedWidth(232); rail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rail.setFixedWidth(232 - 2); rail_scroll.setWidget(rail)
        rh.addWidget(rail_scroll)
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
        cv.addWidget(bar)
        self.stack = QStackedWidget()
        self.home_page = HomePage(self)
        self.dash_page = DashPage(self)
        self.record_page = RecordPage(self)
        self.review_page = ReviewPage(self)
        self.acronym_page = AcronymPage(self)
        self.acrlist_page = EffortListPage(self)
        self.docs_page = DocsPage(self)
        self.requirements_page = RequirementsPage(self)
        self.compare_page = ComparePage(self)
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
        self.pages = {"home": self.home_page, "dashboard": self.dash_page, "record": self.record_page, "reviews": self.review_page, "docs": self.docs_page, "requirements": self.requirements_page, "compare": self.compare_page,
                      "impact": self.impact_page, "deliverables": self.deliverables_page, "qa": self.qa_page, "keywords": self.keywords_page, "exportall": self.exportall_page,
                      "settings": self.settings_page, "acronyms": self.acronym_page, "acrlist": self.acrlist_page, "read": self.read_page, "structure": self.structure_page, "assign": self.assign_page, "prove": self.prove_page,
                      "crosswalk": self.crosswalk_page, "matrix": self.matrix_page, "setup": self.setup_page}
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
        """Go to the sentence picked (or the first one whose ID or words match) in Assign."""
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

    def open_effort(self, name, force=False):
        """Hold the effort (the same lock as the tkinter edition) and open its compliance matrix. Returns True."""
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
        diag.activity("qt_effort_opened")
        _issues, repaired = self.safety.health()   # 2.80.0: check the effort; put back a damaged list or matrix
        p = ws.get("compliance_path") or ""
        recovered = False
        if p and os.path.isfile(p):
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
        self.read_page.refresh()
        self.go("assign" if self.review is not None and self.review.M.items else "read")
        self.safety.opened()
        self.warm_up()                             # 2.82.0: pages that read every document are ready before you open them
        self.safety.restore_view()                 # 2.78.0: back where you were in this effort
        if recovered:
            self.toast(self.safety.recovered_text)
        if repaired:
            self.toast(repaired[0])
        elif any(i["severity"] == "error" for i in _issues):
            self.status("Effort health: a problem needs you. See Effort record > Effort health.")
        self.title()
        return True

    def close_effort(self):
        self._warm_stop = True
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
        self.step_btns[step].setChecked(True)
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
