"""The Qt edition's main window (2.59.0): the effort (picked from the efforts on this PC, held with the same lock as
the tkinter edition), the steps of Compliance that are in Qt so far (Read RFP, Review), the status line, and autosave
of the compliance matrix two seconds after each change."""
import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut
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
from .builder import BuilderPage          # 3.30.0: the Structure Builder (with the structure text inside)
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


RAIL = [("Home", [("efforts", "All Efforts"), ("mywork", "My Work")]),                                       # 3.13.0: grouped by job
        ("Effort", [("home", "Effort Dashboard"), ("deliverables", "Deliverables"), ("effortfmt", "Effort Formatting"),   # 3.36.0
                    ("record", "Effort Record"),
                    ("reviews", "Color Reviews")]),
        ("Solicitation", [("library", "Library"), ("compare", "Compare"), ("custqa", "Customer Q&A")]),
        ("Compliance", [("assign", "Review"), ("structure", "Structure Builder"), ("matrix", "Matrix")]),   # 3.30.0
        ("Writing", [("storyboards", "Storyboards"), ("truth", "Wall of Truth"), ("acronyms", "Acronyms")]),
        ("Quality", [("qa", "Submission Check"), ("checks", "Final Checks")]),
        ("Production", [("prodstd", "Production Standards"), ("audit", "Audit"), ("fixcopy", "Fix a Copy")]),
        ("Post-Submission", [("postsub", "Checklist"), ("keywords", "Keywords")]),
        ("Effort files", [("exportall", "Export All"), ("settings", "Settings")])]
# 3.16.0: one place per job. Pages that belong to a menu item are tabs under its title, never menu items of their own.
TABS = {"home": [("home", "Dashboard"), ("requirements", "Submission Rules")],
        "record": [("record", "Effort Record"), ("meetings", "Meetings")],                 # 3.20.0
        "library": [("library", "Documents"), ("read", "Read into Review")],
        "assign": [("assign", "Review"), ("prove", "Coverage")],
        "matrix": [("matrix", "Matrix"), ("crosswalk", "L/M Crosswalk")],
        "acronyms": [("acronyms", "Scan"), ("acrlist", "Acronym List")]}      # 3.37.0: Lists to Submit is in the Acronym List
HEAD_OF = {k: h for h, tabs in TABS.items() for k, _t in tabs}
HEAD_OF.update({"docs": "library", "impact": "compare", "dashboard": "home"})   # pages opened from inside another
MATRIX_UNDO = {"home", "reviews", "docs", "compare", "impact", "structure", "prove", "crosswalk", "matrix", "setup"}   # 3.18.2:
# pages that change the matrix (decisions, the structure, placements, setup) share its Undo steps; Review has its own
BETA = {"fixcopy"}                                  # 3.16.0: tools still being proven, marked Beta in the menu and on the page
GROUP_OF = {k: g for g, items in RAIL for k, _t in items}     # 3.15.0: the page's menu group, shown above its title
GROUP_OF.update({k: GROUP_OF[h] for k, h in HEAD_OF.items() if h in GROUP_OF})


def members(key):
    """The page keys a menu item holds: itself, or its tabs."""
    return [k for k, _t in TABS.get(key, [(key, "")])]


TITLES = {"efforts": ("All Efforts", "Every effort in progress, a new one, and work not filed yet"),
          "fixcopy": ("Fix a Copy", "Beta: check drafts against their profile; fixes go into a dated copy, never the original"),
          "audit": ("Audit", "Check files against every standard that applies to them: read only, nothing changed"),
          "prodstd": ("Production Standards", "The global formatting standards for every effort: the global standard, volume profiles, effort types and the template library"),
          "effortfmt": ("Effort Formatting", "This effort's formatting on top of the global standards: its own fonts, sizes, margins and parts, and the RFP's rules"),
          "checks": ("Final Checks", "The PDF package, cross-references and numbering, and what changed between two drafts"),
          "truth": ("Wall of Truth", "The one approved way to state every fact and number, and the drafts checked against it"),
          "storyboards": ("Storyboards", "One sheet per section before the first draft: message, themes, approach, features and proof"),
          "mywork": ("My Work", "One person's work in every effort, soonest first"),
          "home": ("Effort Dashboard", "Where the effort stands: the numbers, the stage and its gate, requirements, tasks and the calendar"),
          "dashboard": ("Effort Dashboard", "Where the effort stands: the numbers, the stage and its gate, requirements, tasks and the calendar"),
          "record": ("Effort Record", "Details, team, stages and gates, status, package and backup"),
          "meetings": ("Meetings", "Who met, what was said, and the topics to follow up until each is considered"),
          "reviews": ("Color Reviews", "Color team review packets, read back onto each requirement"),
          "library": ("Library", "Every document of the effort: categories, folders, tags, roles and search"),
          "docs": ("Customer Versions", "The customer's documents and every version of them"),
          "requirements": ("Submission Rules", "Every rule the customer's documents set, which version changed it, and what you confirmed"),
          "custqa": ("Customer Q&A", "The questions we submit to the customer: their exact wording, our question, status and the answer"),
          "compare": ("Compare", "Compare two versions: what changed, what it touches, and a decision on every change"),
          "impact": ("Impact Review", "What one new version touched across the effort"),
          "deliverables": ("Deliverables", "Every deliverable at a glance: where each stands and what is missing"),
          "acronyms": ("Acronyms", "Scan the customer's documents or your own drafts for acronyms, abbreviations, units and symbols"),
          "acrlist": ("Acronym List", "The effort's acronym list: every term with its approved definition"),
          "qa": ("Submission Check", "End: the volumes you will submit, against the effort list, banned words and page limits"),
          "lists": ("Lists to Submit", "The acronym lists for your volumes, built from what each one uses"),
          "keywords": ("Keywords", "After submission: the effort's keywords, suggestions with reasons, and the SharePoint export"),
          "exportall": ("Export All", "Every feature's outputs in one dated folder"),
          "settings": ("Settings", "New effort, the effort's folders, the master database, backups"),
          "read": ("Read into Review", "Read several customer documents into the compliance matrix at once"),
          "structure": ("Structure Builder", "Build the response: sections and headings, elements, library items, and "
                        "everything placed in each section; Make templates from it"),
          "assign": ("Review", "Read every sentence on the page: decide it and capture what it holds"),
          "prove": ("Coverage", "Every sentence of every file read and decided, and the word-for-word text check"),
          "crosswalk": ("L/M Crosswalk", "Each instruction, the factor that scores it, and the work it describes"),
          "matrix": ("Matrix", "The compliance matrix as the customer will see it"),
          "setup": ("Response Setup", "The Word documents your writers start from"),
          "postsub": ("Post-Submission Checklist", "What the team does after the proposal goes in: owners, due dates, done")}



def _relabel_record(root, mapping):
    """3.29.1: the effort record's captures and topics follow a section renamed, renumbered, moved or taken out."""
    import effortrec as RR
    import excerpts as EX
    return EX.relabel(RR.Record(root), mapping)

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
        # 3.15.0: the open effort and its stage at the top; then the groups by job, each tool in one place only, the
        # stage's tools marked with a dot in the stage's color (no separate stage group); a group folds away
        from .brandview import RailEffort
        self.rail_effort = RailEffort(self); rv.addWidget(self.rail_effort)
        self.stage_tools_now = []
        self.group_heads, self.group_items, self.group_counts = {}, {}, {}
        for gi, (head, items) in enumerate(RAIL):
            h = QPushButton(head); h.setObjectName("railgroup"); h.clicked.connect(lambda _=False, g=head: self.toggle_group(g))
            h.setProperty("first", gi == 0)
            hf = h.font(); hf.setCapitalization(QFont.AllUppercase); hf.setLetterSpacing(QFont.AbsoluteSpacing, 1.0); h.setFont(hf)
            hl = QHBoxLayout(h); hl.setContentsMargins(0, 0, D.SPACE["m"], 5); hl.addStretch(1)
            cnt = QLabel(""); cnt.setObjectName("railcount"); cnt.setVisible(False)
            hl.addWidget(cnt, 0, Qt.AlignBottom | Qt.AlignRight)
            self.group_counts[head] = cnt
            rv.addWidget(h); self.group_heads[head] = h; self.group_items[head] = []
            for key, text in items:
                b = QPushButton(text.replace("&", "&&")); b.setObjectName("rail"); b.setCheckable(bool(key))
                bl = QHBoxLayout(b); bl.setContentsMargins(0, 0, D.SPACE["m"], 0); bl.addStretch(1)
                if key in BETA:                                         # 3.16.0: a tool still being proven
                    bt = QLabel("BETA"); bt.setObjectName("railbeta"); bt.setToolTip("Beta: still being proven on real documents")
                    bl.addWidget(bt, 0, Qt.AlignVCenter)
                b.stage_dot = QLabel(); b.stage_dot.setFixedSize(8, 8); b.stage_dot.setVisible(False)
                bl.addWidget(b.stage_dot, 0, Qt.AlignVCenter)
                if key:
                    b.clicked.connect(lambda _=False, k=key: self.go(k))
                    self.steps.addButton(b); self.step_btns[key] = b
                else:
                    b.setEnabled(False)
                    b.setToolTip("Still in Stationkeeper (classic): it moves to Qt in a coming release.")
                rv.addWidget(b); self.group_items[head].append(b)
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
        self.page_crumb = D.label("", "crumb", wrap=False)              # 3.15.0: the menu group the page is in
        cf = self.page_crumb.font(); cf.setCapitalization(QFont.AllUppercase); self.page_crumb.setFont(cf)
        self.page_crumb.setMinimumWidth(1)                              # it never widens the window
        from PySide6.QtWidgets import QSizePolicy
        self.page_crumb.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        tcol.addWidget(self.page_crumb)
        trow = QHBoxLayout(); trow.setSpacing(D.SPACE["s"]); tcol.addLayout(trow)
        self.page_title = D.label("", "display", wrap=False); trow.addWidget(self.page_title)
        self.beta_pill = D.Pill("Beta", "warn"); self.beta_pill.setVisible(False)          # 3.16.0
        self.beta_pill.setToolTip("Still being proven on real documents: check what it makes before you rely on it")
        trow.addWidget(self.beta_pill, 0, Qt.AlignVCenter); trow.addStretch(1)
        self.page_sub = D.label("", "muted"); self.page_sub.setMinimumWidth(120); tcol.addWidget(self.page_sub)   # 3.0.4: wraps; 3.9.0: 120 so the bar fits 1280 with Issue or idea
        bh.addLayout(tcol, 1)
        self.undo_btn = D.button("Undo", "ghost", lambda: self.undo_here(), "Undo the last change on this page (Ctrl+Z)")   # 3.18.2
        self.undo_btn.setEnabled(False)
        bh.addWidget(self.undo_btn)
        self.issue_btn = D.button("Issue or idea", "ghost", lambda: self.open_issues(),
                                  "Write down a bug, an improvement or an idea about this page (Ctrl+Shift+I). It stays on this PC.")
        bh.addWidget(self.issue_btn)                 # 3.9.0
        try:
            import secure as _sec
            self.issue_btn.setVisible(not _sec.ACTIVE)   # SCIF-ready keeps no reports
        except Exception:
            diag.swallowed()
        self.search = QLineEdit(); self.search.setPlaceholderText("Find a sentence (words or ID)...")
        self.search.setMinimumWidth(170); self.search.setClearButtonEnabled(True)   # 3.12.0: room for "Effort Dashboard" at 1280; 3.18.2: and Undo
        self.search.returnPressed.connect(self.find_go)
        bh.addWidget(self.search)
        self.effort_box = QComboBox(); self.effort_box.setMinimumWidth(156)   # 3.15.0: the menu names the open effort; 3.18.2: 156 for Undo
        self.effort_box.setToolTip("The open effort: pick another to switch")
        self.effort_box.activated.connect(lambda i: self.open_effort(self.effort_box.itemText(i)))
        bh.addWidget(self.effort_box)
        self.saved = D.Pill("Saved", "ok", dot=True); bh.addWidget(self.saved, 0, Qt.AlignVCenter)
        self.mode_chip = D.Pill("", "ok", dot=True); bh.addWidget(self.mode_chip, 0, Qt.AlignVCenter)   # 2.97.0: Offline, Connected or SCIF-ready
        self.mode_chip.mousePressEvent = lambda _e: self.go_mode()
        self.marking = MarkingStrip(); cv.addWidget(self.marking)            # 2.88.0: CUI or proprietary, on every page
        from .unfiledview import UnfiledStrip
        self.unfiled_strip = UnfiledStrip(self); cv.addWidget(self.unfiled_strip)   # 2.91.0: work not filed yet
        from .watchview import WatchStrip
        self.watch_strip = WatchStrip(self); cv.addWidget(self.watch_strip)         # 2.94.0: new, changed, missing files
        self.watch_found, self._wa_thread, self._wa_result, self._wa_last = None, None, None, 0.0
        cv.addWidget(bar)
        from PySide6.QtWidgets import QTabBar
        self.page_tabs = QTabBar(); self.page_tabs.setObjectName("pagetabs")        # 3.16.0: a menu item's own pages
        self.page_tabs.setDocumentMode(True); self.page_tabs.setExpanding(False); self.page_tabs.setDrawBase(False)
        self.page_tabs.currentChanged.connect(self._tab_picked)
        self._tab_keys, self._tab_sync = [], False
        tw = QFrame(); tw.setObjectName("pagetabsbox"); tl = QHBoxLayout(tw)
        tl.setContentsMargins(D.SPACE["xl"], 0, D.SPACE["xl"], 0); tl.addWidget(self.page_tabs); tl.addStretch(1)
        self.page_tabs_box = tw; tw.setVisible(False)
        cv.addWidget(tw)
        from .adaptive import PageStack
        self.stack = PageStack()                   # 2.86.0: a page scrolls only when the window is smaller than it needs
        from .effortshome import EffortsHome
        self.efforts_page = EffortsHome(self)        # 2.91.0: Home: every effort, + Add an Effort, Unfiled work
        self.dash_page = DashPage(self)              # 3.12.0: its numbers and cards show on the Effort Dashboard
        self.home_page = HomePage(self)
        self.record_page = RecordPage(self)
        from .meetingspage import MeetingsPage
        self.meetings_page = MeetingsPage(self)                 # 3.20.0
        self.review_page = ReviewPage(self)
        self.acronym_page = AcronymPage(self)
        self.acrlist_page = EffortListPage(self)
        self.docs_page = DocsPage(self)
        from .librarypage import LibraryPage
        self.library_page = LibraryPage(self)        # 2.83.0
        self.lists_page = self.acrlist_page.submit    # 2.86.0; 3.37.0: shown in the Acronym List (Show > Lists to submit)
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
        self.structure_page = BuilderPage(self)
        self.assign_page = AssignPage(self)
        self.prove_page = ProvePage(self)
        self.crosswalk_page = CrosswalkPage(self)
        self.matrix_page = MatrixPage(self)
        self.setup_page = SetupPage(self)
        from .postsubpage import PostSubPage
        self.postsub_page = PostSubPage(self)          # 2.91.0
        from .myworkpage import MyWorkPage
        self.mywork_page = MyWorkPage(self)            # 3.1.0
        from .storyboardpage import StoryboardPage
        self.storyboards_page = StoryboardPage(self)   # 3.2.0
        from .wallpage import WallPage
        self.truth_page = WallPage(self)               # 3.3.0
        from .checkspage import ChecksPage
        self.checks_page = ChecksPage(self)            # 3.4.0
        from .prodstdpage import StandardsPage
        from .prodfixpage import FixPage
        self.fixcopy_page = FixPage(self)              # 3.6.0
        from .auditpage import AuditPage
        self.audit_page = AuditPage(self)              # 3.17.0
        self.prodstd_page = StandardsPage(self)        # 3.6.0: every rule, three layers
        from .effortformatpage import EffortFormatPage
        self.effortfmt_page = EffortFormatPage(self)   # 3.36.0: one effort's formatting, apart from the team's
        self.pages = {"efforts": self.efforts_page, "mywork": self.mywork_page, "home": self.home_page, "dashboard": self.dash_page, "record": self.record_page, "meetings": self.meetings_page, "reviews": self.review_page, "library": self.library_page, "docs": self.docs_page, "requirements": self.requirements_page, "compare": self.compare_page, "custqa": self.custqa_page,
                      "impact": self.impact_page, "deliverables": self.deliverables_page, "qa": self.qa_page, "keywords": self.keywords_page, "exportall": self.exportall_page,
                      "settings": self.settings_page, "acronyms": self.acronym_page, "acrlist": self.acrlist_page, "read": self.read_page, "structure": self.structure_page, "assign": self.assign_page, "prove": self.prove_page,
                      "crosswalk": self.crosswalk_page, "matrix": self.matrix_page, "setup": self.setup_page, "storyboards": self.storyboards_page, "truth": self.truth_page, "checks": self.checks_page, "postsub": self.postsub_page,
                      "fixcopy": self.fixcopy_page, "prodstd": self.prodstd_page, "audit": self.audit_page,
                      "effortfmt": self.effortfmt_page}
        for pg in self.pages.values():
            self.stack.addWidget(pg)
        from .roleview import NoticePage                 # 3.13.0: a tool for another role, or a Preview tool not turned on
        self.notice_page = NoticePage(self); self.stack.addWidget(self.notice_page)
        cv.addWidget(self.stack, 1)
        rh.addWidget(col, 1)
        self.setCentralWidget(root)
        self.toaster = D.Toast(self)
        from .progress import StatusTask
        self.task = StatusTask(self)                # 2.82.0: a running job's bar in the status bar, on every page
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: (self.search.setFocus(), self.search.selectAll()))
        from . import helpcenter as HC               # 2.81.0: find anything, and the shortcuts
        QShortcut(QKeySequence("Ctrl+K"), self, activated=lambda: HC.open_finder(self))
        from . import guide as GD                    # 3.0.2: F1 opens the Guide at the page you are on
        QShortcut(QKeySequence("F1"), self, activated=lambda: GD.open_guide(self))
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=lambda: self.undo_here())    # 3.18.2: one Undo for the window
        QShortcut(QKeySequence("Ctrl+Shift+I"), self, activated=lambda: self.open_issues())   # 3.9.0: issues and ideas
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
        self.refresh_access()                      # 3.13.0
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
        if getattr(self, "efforts_page", None) is not None and self.stack.currentWidget() is self.efforts_page:
            self.efforts_page.refresh()            # 3.34.1: a new effort shows in the list at once

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
        import outline_ops as _O                   # 3.29.1: captures and topics follow their sections
        _O.HOOKS[:] = [lambda m, root=ws.root: _relabel_record(root, m)]
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
        self.since = None                          # 3.1.0: what the others did since this person last opened it
        try:
            import effortrec as _R, sincelast as SL
            self.since = SL.on_open(ws.root, _R.Record(ws.root), self.review.M if self.review is not None else None)
        except Exception:
            diag.swallowed()
        say(0.7, f"{name}: setting up the pages")
        self.read_page.refresh()
        self.go("assign" if self.review is not None and self.review.M.items else "read")
        self.safety.opened()
        self.warm_up()                             # 2.82.0: pages that read every document are ready before you open them
        say(0.9, f"{name}: back where you were")
        self.safety.restore_view()                 # 2.78.0: back where you were in this effort
        if recovered:
            self.toast(self.safety.recovered_text)
        elif self.since and self.since["count"]:
            import sincelast as SL
            self.toast(SL.summary(self.since) + "; Effort Home lists them")
            diag.activity("since_last_shown", n=self.since["count"])
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
        self.refresh_access()                      # 3.13.0: the role in this effort, and this stage's tools
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
        try:                                        # 3.16.0: the Library shows the new files too, with Add and Ignore
            self.library_page.show_new(found)
        except Exception:
            diag.swallowed()
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
        """Review (3.12.0; was Add them...): the new and changed files go to the Library's reading table (a changed file comes up as a new
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
                        "Review again for the rest.")
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

    def export_full_effort(self, folder=None, open_it=True):
        """3.12.0: a full copy of the effort and everything in it, as plain files, in a dated folder named for the effort
        and the stage it was exported from (in the effort's Exports folder unless a folder is given)."""
        import datetime as _dt
        import shutil
        import effortfolders as EF
        import readable as RD
        if self.ws is None:
            self.status("Open an effort first.")
            return ""
        src = self.readable_now(overview=True)
        if not src or not os.path.isdir(src):
            self.status("The effort could not be written out just now. Try again after the next save.")
            return ""
        try:
            import effortrec as _R
            stage = (_R.Record(self.ws.root).stage() or {}).get("name", "")
        except Exception:
            stage = ""
        base = folder or EF.folder(self.effort_path, "exports") or os.path.dirname(src)
        name = RD._safe(" - ".join(x for x in (self.effort_name, stage, "full export " + _dt.datetime.now().strftime("%Y-%m-%d %H%M")) if x))
        dest = os.path.join(base, name)
        n = 2
        while os.path.exists(dest):
            dest = os.path.join(base, f"{name} ({n})"); n += 1
        try:
            os.makedirs(base, exist_ok=True)
            shutil.copytree(src, dest)
        except OSError:
            diag.swallowed()
            self.status("The full export could not be written there. Pick another folder.")
            return ""
        diag.activity("qt_full_effort_exported")
        self.toast("Full effort exported: " + os.path.basename(dest))
        if open_it and not os.environ.get("AH_TEST"):
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(dest))
        return dest

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
        import outline_ops as _O
        _O.HOOKS[:] = []
        import secure
        secure.EFFORT_LEVEL = -1                     # 2.97.0
        if hasattr(self, "marking"):
            self.marking.show_marking("")
        if hasattr(self, "unfiled_strip"):
            self.unfiled_strip.setVisible(False)
        if hasattr(self, "group_items"):
            try:
                self.refresh_access()                # 3.13.0: no effort: the person's own role, no stage tools
            except Exception:
                diag.swallowed()

    def set_matrix(self, M, new=False):
        self.review = AO.Review(M)
        if self.ws is not None:                     # 3.29.1: Undo puts the captures' sections back too
            import effortrec as _RR
            import excerpts as _EX
            root = self.ws.root
            self.review.extra_get = lambda: _EX.sections_state(_RR.Record(root))
            self.review.extra_set = lambda st: _EX.restore_sections(_RR.Record(root), st)
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
    # ------------------------------------------------------------ 3.18.2: undo, on the page you are on
    def undo_text(self):
        """What Undo would put back on the current page ('' for nothing)."""
        pg = self.stack.currentWidget()
        fn = getattr(pg, "undo_text", None)
        if callable(fn):
            try:
                return fn() or ""
            except Exception:
                diag.swallowed()
                return ""
        key = next((k for k, p in self.pages.items() if p is pg), "")
        if key in MATRIX_UNDO and self.review is not None:
            return self.review.undo_label()
        return ""

    def undo_here(self):
        """Ctrl+Z or the top bar's Undo: the last change on the page you are on. Pages that change the matrix share its
        steps (decisions, the structure, placements, setup); a page with its own steps undoes those."""
        pg = self.stack.currentWidget()
        fn = getattr(pg, "undo_here", None)
        if callable(fn):
            got = fn()
        else:
            key = next((k for k, p in self.pages.items() if p is pg), "")
            got = None
            if key in MATRIX_UNDO and self.review is not None:
                got = self.review.undo_label()
                if got and self.review.undo_last():
                    if hasattr(pg, "refresh"):
                        pg.refresh()
                    self.changed()
                    self.status(f"Undone: {got}")
                else:
                    got = None
            if not got:
                self.status("Nothing to undo on this page.")
        if got:
            diag.activity("undo_done")
        self.refresh_undo()
        return got

    def refresh_undo(self):
        t = self.undo_text()
        self.undo_btn.setEnabled(bool(t))
        self.undo_btn.setToolTip(f"Undo: {t} (Ctrl+Z)" if t else "Nothing to undo on this page")
        return t

    def changed(self):
        if self.review is not None:
            self.review.label_last(f"the last change on {self.page_title.text() or 'this page'}")
        if self.review is not None:
            self.review.M.pending = True
            self.save_timer.start()
            self.safety.changed()                  # 2.78.0: the recovery copy, written as you work
        self.title()
        try:
            self.refresh_undo()
        except Exception:
            diag.swallowed()

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
    # ------------------------------------------------------------ 3.13.0 roles, Preview tools, the stage's tools, groups
    def profile(self):
        """(profile, where it came from) for the person at this PC in the open effort."""
        import branding as BR
        import roleaccess as RA
        from .modes import settings
        st = settings() or {}
        rec = None
        if self.ws is not None:
            try:
                import effortrec as _R
                rec = _R.Record(self.ws.root)
            except Exception:
                diag.swallowed()
        return RA.current(rec, st.get("my_name", ""), BR.layout(st).get("role", RA.PM))

    def blocked(self, step):
        """Why a page does not open for this person now: None, or {"kind": "role" | "preview", ...}."""
        import roleaccess as RA
        prof, src = self.profile()
        if not RA.allowed(prof, step):
            return {"kind": "role", "step": step, "profile": prof, "source": src, "roles": RA.roles_for(step)}
        if step in RA.PREVIEW and not RA.preview_on(self.config_dir, step):
            return {"kind": "preview", "step": step, "profile": prof}
        return None

    def refresh_access(self):
        """Grey (or hide, when the person asked) the menu's tools that are not for this person's role."""
        import roleaccess as RA
        from .modes import settings
        prof, _src = self.profile()
        hide = bool((settings() or {}).get("hide_other_roles"))
        collapsed = set((settings() or {}).get("rail_collapsed") or [])
        for head, items in self.group_items.items():
            shown = 0
            for key, b in ((k, self.step_btns.get(k)) for k, _t in dict(RAIL)[head]):
                if b is None:
                    continue
                ok = any(RA.allowed(prof, k) for k in members(key))       # 3.16.0: open when any of its tabs is
                b.setProperty("offrole", not ok)
                b.style().unpolish(b); b.style().polish(b)
                b.setToolTip("" if ok else f"For {', '.join(RA.roles_for(key))}. Your role here: {prof}.")
                vis = (ok or not hide) and head not in collapsed
                b.setVisible(vis); shown += (ok or not hide)
            self.group_heads[head].setVisible(shown > 0)
            self.group_heads[head].setText(head + ("  ▸" if head in collapsed else ""))
        self.refresh_stage_tools(prof, collapsed)
        return prof

    def refresh_stage_tools(self, prof=None, collapsed=None):
        """3.15.0: the tools the effort's stage needs keep their one place in the menu and get a dot in the stage's
        color; each group says how many it holds; the effort and its stage show at the top of the menu."""
        import roleaccess as RA
        import stagecolors as SC
        from .modes import settings
        st = settings() or {}
        tools, color, name = [], "", ""
        if self.ws is not None:
            try:
                import effortrec as _R
                r = _R.Record(self.ws.root)
                cur = r.stages[r.index()]
                color, name = SC.color_of(cur, r.index()), cur["name"]
                if st.get("stage_tools", True):
                    tools = list(dict.fromkeys(HEAD_OF.get(k, k) for k in RA.stage_tools(cur)))   # 3.16.0: a tab marks its item
                    tools = [k for k in tools if k in self.step_btns]
            except Exception:
                diag.swallowed()
        self.rail_effort.set(self.effort_name if self.ws is not None else "", name, color)
        self.stage_tools_now = tools
        for k, b in self.step_btns.items():               # refresh_access set each tooltip just before this
            on = k in tools
            b.stage_dot.setVisible(on)
            b.stage_dot.setStyleSheet(f"background:{color};border-radius:4px;" if on else "")
            if on:
                b.setToolTip(" ".join(x for x in (b.toolTip(), f"A tool for {name}.") if x))
        for head, items in RAIL:                              # a small badge: how many of the group's tools this stage needs
            n = sum(1 for k, _t in items if k in tools)
            c = self.group_counts[head]
            c.setText(str(n) if n else ""); c.setVisible(bool(n))
            c.setToolTip(f"{n} tool{'s' if n != 1 else ''} here for {name}" if n else "")
            c.setStyleSheet(f"QLabel#railcount{{color:#FFFFFF;background:{color};border-radius:7px;padding:0 5px;}}" if n else "")
        return tools

    def toggle_group(self, head):
        from .modes import settings, save
        cur = list((settings() or {}).get("rail_collapsed") or [])
        cur = [x for x in cur if x != head] if head in cur else cur + [head]
        save(rail_collapsed=cur)
        self.refresh_access()
        return head in cur

    def go(self, step):
        if step == "lists":                          # 3.37.0: Lists to Submit lives in the Acronym List
            ok = self.go("acrlist")
            if ok is not False:
                self.acrlist_page.show_view("submit")
            return ok
        step = {"format": "fixcopy", "dashboard": "home", "setup": "structure"}.get(step, step)   # 3.30.0: Response Setup is in the Builder   # 3.9.0: Format Check is in Fix a Copy; 3.12.0: one dashboard
        if step in TABS and self.blocked(step) is not None:     # 3.16.0: a menu item opens on a tab the role has
            step = next((k for k in members(step)[1:] if self.blocked(k) is None), step)
        why = self.blocked(step)                     # 3.13.0: another role's tool, or a Preview tool not turned on
        if why is not None:
            self.notice_page.show_for(why)
            self.stack.setCurrentWidget(self.notice_page)
            b0 = self.step_btns.get(step) or self.step_btns.get(HEAD_OF.get(step, step))
            if b0 is not None:
                b0.setChecked(True)
            self.show_tabs(step)
            self.beta_pill.setVisible(False)
            t, _sub = TITLES[step]
            self.page_crumb.setText(GROUP_OF.get(step, ""))
            self.page_title.setText(t)
            self.page_sub.setText(("In Preview: not turned on for this team" if why["kind"] == "preview" else
                                   f"For {', '.join(why['roles'])}") + (f"  ·  {self.effort_name}" if self.effort_name else ""))
            diag.activity("qt_page_blocked")
            return False
        pg = self.pages[step]
        if hasattr(pg, "refresh"):
            pg.refresh()
        self.stack.setCurrentWidget(pg)
        head = HEAD_OF.get(step, step)               # 3.16.0: a tab's page marks its menu item
        btn = self.step_btns.get(step) or self.step_btns.get(head)
        if btn is not None:                          # 2.85.0: Customer versions and Impact review live inside other pages
            btn.setChecked(True)
        else:
            for b in self.step_btns.values():
                b.setChecked(False)
        _t, sub = TITLES[step]
        t = TITLES[head][0] if step in HEAD_OF and head in TITLES and step in dict(TABS.get(head, [])) else TITLES[step][0]
        self.page_crumb.setText(GROUP_OF.get(step, ""))
        self.page_title.setText(t)
        self.beta_pill.setVisible(step in BETA)
        self.page_sub.setText(sub + (f"  \u00b7  {self.effort_name}" if self.effort_name else ""))
        self.show_tabs(step)
        try:
            self.refresh_undo()                    # 3.18.2: Undo says what it would put back on this page
        except Exception:
            diag.swallowed()
        try:
            self.refresh_access()                  # 3.13.0: a stage moved or a role changed shows in the menu
        except Exception:
            diag.swallowed()
        return True

    def show_tabs(self, step):
        """3.16.0: the tabs of the menu item the page belongs to (none for a page that is its own item)."""
        head = HEAD_OF.get(step, step)
        tabs = TABS.get(head) if step in dict(TABS.get(head, [])) else None
        self._tab_sync = True
        try:
            while self.page_tabs.count():
                self.page_tabs.removeTab(0)
            self._tab_keys = []
            for k, label in tabs or []:
                self.page_tabs.addTab(label); self._tab_keys.append(k)
            if tabs:
                self.page_tabs.setCurrentIndex(self._tab_keys.index(step))
        finally:
            self._tab_sync = False
        self.page_tabs_box.setVisible(bool(tabs))
        return self._tab_keys

    def _tab_picked(self, i):
        if self._tab_sync or not (0 <= i < len(self._tab_keys)):
            return
        self.go(self._tab_keys[i])

    def open_issues(self, feature=None, run=True):
        """3.9.0: Issues and ideas, opened on the page you are on."""
        from .issueview import open_issues
        diag.activity("issues_opened")
        return open_issues(self, feature, run)

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
        self.finish_background()
        e.accept()

    def finish_background(self, wait_ms=600000):
        """3.14.3: before the window closes, every background job ends: Office PDF copies stop at once (the Office they
        started is ended and no half-made copy is kept); other jobs are asked to stop and waited for, so none is cut off
        mid-file and Stationkeeper never ends with a job still running. Returns how many were running."""
        import gc
        from PySide6.QtCore import QThread
        running = []
        for o in gc.get_objects():
            try:
                if isinstance(o, QThread) and o.isRunning():
                    running.append(o)
            except Exception:
                pass
        if not running:
            return 0
        self.hide()
        for t in running:
            if hasattr(t, "stop_asked"):
                t.stop_asked = True
            t.requestInterruption()
        for t in running:
            t.wait(wait_ms)
        diag.activity("background_jobs_finished_at_close", n=len(running))
        return len(running)
