"""First Use Check (3.50.0): check a document's acronyms on their own, in their own window, with no effort open.

Add one or more Word files (in the order they are read). For every acronym the check reports where it is first used
in running text and whether it is defined there ("Spelled Out Words (ACR)"), and every problem:
  used before it is defined           (not defined at first use; spelled out later, and where)
  never defined                       (used, never spelled out in the text)
  defined more than once              (spelled out again later, and where)
  defined but never used again        (spell it out and leave out the (ACR))
  written as (ACR) without its words  (the spelled-out words are not right before it)
First use restarts in each file, in each section of each file, or runs across all the files. Select a row to see the
place: the passage with the acronym highlighted, or the picture with it boxed (foundview). Export the report to Excel.

The same rules as Submission Check (volcheck), which checks an effort's volumes against the effort's acronym list;
here the document stands alone, so nothing is compared with a list. Files are only read. Rules only (No AI)."""
import os

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QListWidget, QMainWindow,
                               QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import diag
from . import design as D

FOLDER = "firstuse_tool"
RULES = (("volume", "Restarts in each file"), ("section", "Restarts in each section of each file"), ("submission", "Runs across all the files"))
SHOW = (("problems", "Problems (fix and check)"), ("all", "Every acronym"))
COLS = (("check", "Check"), ("volume", "File"), ("section", "Section"), ("term", "Acronym"), ("state", "Result"),
        ("loc", "First use in text"), ("written", "Written as"), ("also_defined", "Also spelled out at"), ("in_figures", "In figures or tables"))
_OPEN = []


class CheckWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, session, paths):
        super().__init__()
        self.session, self.paths = session, paths

    def run(self):
        import app_gui as A
        try:
            self.finished_ok.emit(self.session.qa_check(self.paths, lambda m: (A.check_cancel(), self.progress.emit(str(m)))))
        except A.ScanCancelled:
            self.failed.emit("cancelled")
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.failed.emit(type(e).__name__)


def new_session(config_dir, rule):
    """A session of its own, apart from every effort, with an empty list (the document stands alone)."""
    import acrsession as S
    import effort as E
    import workspace as W
    root = os.path.join(config_dir, FOLDER)
    ws = W.Workspace(root, "First Use Check")
    path = os.path.join(root, "First_Use_Check_List.xlsx")
    try:
        os.remove(path)                                     # nothing to compare with: each check starts from an empty list
    except OSError:
        pass
    L = E.EffortList(path, "First Use Check", first_use=rule)
    L.save()
    import app_gui as A
    s = S.AcronymSession(ws, path, {}, A.load_settings())
    s.effort.first_use = rule
    s.first_use_set = dict((ws.load_session() or {}).get("first_use_set") or {})     # 3.51.0: the places chosen before
    return s


def problems(report):
    import volcheck as V
    return [r for r in report.get("first_use", []) if r.get("level") in (V.BAD, V.WARN)]


class FirstUseWindow(QMainWindow):
    def __init__(self, config_dir):
        super().__init__()
        self.config_dir = config_dir
        self.setWindowTitle("First Use Check - Stationkeeper")
        self.resize(1440, 880)
        self.paths, self.report, self.session, self.worker, self.shown = [], None, None, None, []
        root = QWidget(); v = QVBoxLayout(root); v.setContentsMargins(D.SPACE["m"], D.SPACE["m"], D.SPACE["m"], D.SPACE["m"])
        head = QHBoxLayout(); v.addLayout(head)
        head.addWidget(D.label("First Use Check", "title"))
        head.addWidget(D.label("Add Word files: where each acronym is first used, and every acronym used before it is defined, never "
                               "defined, or spelled out more than once.", "muted"), 1)
        top = QHBoxLayout(); v.addLayout(top)
        self.files = QListWidget(); self.files.setMaximumHeight(90); self.files.setAcceptDrops(True)
        self.files.setToolTip("The files, in the order they are read")
        top.addWidget(self.files, 1)
        col = QVBoxLayout(); top.addLayout(col)
        col.addWidget(D.button("Add Word files...", None, lambda: self.add_files()))
        col.addWidget(D.button("Clear", "ghost", lambda: self.set_files([])))
        col2 = QVBoxLayout(); top.addLayout(col2)
        self.rule = QComboBox()
        for k, t in RULES:
            self.rule.addItem(t, k)
        col2.addWidget(D.label("First use", "label")); col2.addWidget(self.rule)
        self.b_check = D.button("Check", "primary", lambda: self.check()); col2.addWidget(self.b_check)
        self.summary = D.label("", "muted"); v.addWidget(self.summary)
        fr = QHBoxLayout(); v.addLayout(fr)
        fr.addWidget(D.label("Show", "label", wrap=False))
        self.show_box = QComboBox()
        for k, t in SHOW:
            self.show_box.addItem(t, k)
        self.show_box.currentIndexChanged.connect(lambda _i: self.fill())
        fr.addWidget(self.show_box); fr.addStretch(1)
        self.b_export = D.button("Export the report...", None, lambda: self.export()); self.b_export.setEnabled(False)
        fr.addWidget(self.b_export)
        sp = QSplitter(Qt.Horizontal); v.addWidget(sp, 1)
        self.t = QTableWidget(0, len(COLS)); self.t.setHorizontalHeaderLabels([h for _k, h in COLS])
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QTableWidget.NoEditTriggers)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows); self.t.setSelectionMode(QAbstractItemView.SingleSelection)
        self.t.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        for c, wdt in enumerate((70, 150, 110, 80, 0, 170, 160, 160, 120)):
            if c != 4:
                self.t.setColumnWidth(c, wdt)
        self.t.currentCellChanged.connect(lambda *_a: self.show_place())
        sp.addWidget(self.t)
        self.right = QWidget(); self.rv = QVBoxLayout(self.right); self.rv.setContentsMargins(0, 0, 0, 0)
        self.place_head = D.label("Select a row to see the place.", "muted"); self.rv.addWidget(self.place_head)
        pr = QHBoxLayout(); self.rv.addLayout(pr)                                   # 3.51.0: the person decides
        self.b_set = D.button("This place is the first use", None, lambda: self.set_here(), "Count the place shown as the "
                              "acronym's first use in this file (a title or a list you would not define it in comes before it)")
        self.b_unset = D.button("Back to the first place it appears", "ghost", lambda: self.unset())
        pr.addWidget(self.b_set); pr.addWidget(self.b_unset); pr.addStretch(1)
        self.b_set.setEnabled(False); self.b_unset.setEnabled(False)
        self.fv = None
        sp.addWidget(self.right)
        sp.setSizes([900, 520])
        self.setCentralWidget(root)
        self.setAcceptDrops(True)
        diag.activity("firstuse_tool_opened")

    # ---- files
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        got = [u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile().lower().endswith(".docx")]
        self.set_files(self.paths + [p for p in got if p not in self.paths])

    def add_files(self):
        got, _ = QFileDialog.getOpenFileNames(self, "Word files to check (in the order they are read)", "", "Word (*.docx)")
        if got:
            self.set_files(self.paths + [p for p in got if p not in self.paths])

    def set_files(self, paths):
        self.paths = [p for p in paths if p.lower().endswith(".docx") and os.path.isfile(p)]
        self.files.clear(); self.files.addItems([os.path.basename(p) for p in self.paths])
        self.b_check.setEnabled(bool(self.paths))
        return self.paths

    # ---- the check
    def check(self, wait=False):
        if not self.paths or self.worker is not None:
            return None
        names = [os.path.basename(p) for p in self.paths]
        if len(set(names)) != len(names):
            self.statusBar().showMessage("Two files have the same name; rename one, then check again.", 12000)
            return None
        self.session = new_session(self.config_dir, self.rule.currentData())
        self.worker = CheckWorker(self.session, list(self.paths))
        self.worker.progress.connect(lambda m: self.statusBar().showMessage(m))
        self.worker.finished_ok.connect(self.done)
        self.worker.failed.connect(self.failed)
        self.b_check.setEnabled(False)
        self.summary.setText("Reading the files...")
        self.worker.start()
        if wait:                                             # tests
            import time
            from PySide6.QtWidgets import QApplication
            t0 = time.time()
            while self.worker is not None and time.time() - t0 < 300:
                QApplication.processEvents(); time.sleep(0.05)
        return self.report

    def done(self, report):
        self.worker = None
        self.b_check.setEnabled(True)
        self.report = report
        if report is None:
            self.summary.setText("Nothing to check: add Word files with different names.")
            return
        import volcheck as V
        rows = report.get("first_use", [])
        c = {k: sum(1 for r in rows if r.get("level") == k) for k in (V.BAD, V.WARN, V.OK, V.INFO)}
        self.summary.setText(f"{c[V.BAD]} to fix, {c[V.WARN]} to check, {c[V.OK] + c[V.INFO]} fine, across {len(report.get('volumes', []))} "
                             f"file(s). First use {V.RULE_SHORT.get(report['summary'].get('rule'), '')}.")
        self.b_export.setEnabled(True)
        self.statusBar().showMessage("Checked.", 6000)
        diag.activity("firstuse_tool_checked", rows=len(rows))
        self.fill()

    def failed(self, why):
        self.worker = None
        self.b_check.setEnabled(True)
        self.summary.setText("Stopped." if why == "cancelled" else f"The files could not be checked ({why}).")

    def fill(self):
        import volcheck as V
        rows = (self.report or {}).get("first_use", [])
        self.shown = problems(self.report) if self.report and self.show_box.currentData() == "problems" else list(rows)
        order = {V.BAD: 0, V.WARN: 1, V.INFO: 2, V.OK: 3}
        self.shown.sort(key=lambda r: (order.get(r.get("level"), 4), (self.report or {}).get("volumes", []).index(r["volume"])
                                       if r.get("volume") in (self.report or {}).get("volumes", []) else 0, r.get("term", "").casefold()))
        self.t.setRowCount(0)
        for r in self.shown:
            i = self.t.rowCount(); self.t.insertRow(i)
            for c, (k, _h) in enumerate(COLS):
                val = V.CHECK_MARKS.get(r.get("level"), "") if k == "check" else str(r.get(k) or "")
                it = QTableWidgetItem(val); it.setToolTip(val)
                if k == "check":
                    it.setForeground(D.color({V.BAD: "crit", V.WARN: "warn", V.OK: "ok"}.get(r.get("level"), "muted")))
                self.t.setItem(i, c, it)
        if self.shown:
            self.t.setCurrentCell(0, 0)

    def show_place(self):
        """The selected acronym's places in its file, its first use first."""
        r = self.t.currentRow()
        if not (0 <= r < len(self.shown)) or self.session is None:
            return None
        row = self.shown[r]
        d = self.session.results.get(row["term"]) or {}
        locs = [x for x in d.get("locations", []) if x.startswith(row["volume"])]
        if row.get("loc") in locs:
            locs.remove(row["loc"]); locs.insert(0, row["loc"])
        elif row.get("loc"):
            locs.insert(0, row["loc"])
        from .foundview import FoundView
        if self.fv is not None:
            self.fv.setParent(None); self.fv.deleteLater()
        paths = {os.path.basename(p): p for p in self.paths}
        self.fv = FoundView(row["term"], locs, lambda n: paths.get(n) or paths.get(n.split(" (")[0]))
        self.rv.addWidget(self.fv, 1)
        self.place_head.setText(f"{row['term']}: {row.get('state') or ''}" + ("  (first use chosen by you)" if self.chosen(row) else ""))
        self.b_set.setEnabled(bool(locs)); self.b_unset.setEnabled(self.chosen(row))
        return self.fv

    def chosen(self, row):
        return bool(self.session and (self.session.first_use_set.get(row["term"]) or {}).get(row["volume"]))

    def set_here(self, loc=None):
        """The place shown (or loc) counts as the selected acronym's first use in its file; the report is rebuilt."""
        r = self.t.currentRow()
        if not (0 <= r < len(self.shown)) or self.fv is None:
            return None
        row = self.shown[r]
        loc = loc or (self.fv.locs[self.fv.k] if self.fv.locs else None)
        if not loc:
            return None
        self.session.set_first_use(row["term"], loc)
        return self._rebuilt(row["term"])

    def unset(self):
        r = self.t.currentRow()
        if not (0 <= r < len(self.shown)):
            return None
        row = self.shown[r]
        self.session.clear_first_use(row["term"], row["volume"])
        return self.check()                                 # read again: the scan's own first use comes back

    def _rebuilt(self, term):
        rep = self.session.qa_rebuild()
        if rep is not None:
            self.report = rep
            self.fill()
            keys = [x["term"] for x in self.shown]
            if term in keys:
                self.t.setCurrentCell(keys.index(term), 0)
        return rep

    def export(self, path=None):
        import volcheck as V
        if not self.report:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "First use report", os.path.join(os.path.expanduser("~"), "First_Use_Check.xlsx"),
                                                  "Excel (*.xlsx)")
            if not path:
                return None
        try:
            V.write_excel(self.report, path, "First Use Check")
        except PermissionError:
            self.statusBar().showMessage("That file is open. Close it, then export again.", 12000)
            return None
        return path

    def closeEvent(self, e):
        if self in _OPEN:
            _OPEN.remove(self)
        super().closeEvent(e)


def open_tool(config_dir, paths=None):
    for w in _OPEN:
        w.show(); w.raise_(); w.activateWindow()
        if paths:
            w.set_files(w.paths + [p for p in paths if p not in w.paths])
        return w
    w = FirstUseWindow(config_dir)
    _OPEN.append(w)
    if paths:
        w.set_files(paths)
    w.show()
    return w


class PlaceDialog:
    """3.51.0 Submission Check: a row's exact place in its volume (the passage highlighted or the picture boxed), with
    This place is the first use and Open the term in Acronyms. Built as a QDialog on demand."""
    def __init__(self, parent, session, row, paths, on_set=None, on_open=None):
        from PySide6.QtWidgets import QDialog
        from .foundview import FoundView
        self.session, self.row, self.on_set = session, row, on_set
        d = (session.results.get(row.get("term")) or {}) if session else {}
        vol = row.get("volume") or ""
        locs = [x for x in d.get("locations", []) if not vol or x.startswith(vol)]
        loc = row.get("loc")
        if loc:
            locs = [loc] + [x for x in locs if x != loc]
        self.dlg = QDialog(parent); self.dlg.setWindowTitle(f"{row.get('term')}: {row.get('state') or 'where it is'}"); self.dlg.resize(980, 760)
        v = QVBoxLayout(self.dlg)
        v.addWidget(D.label(f"{row.get('term')} in {vol or 'the volumes'}. {row.get('state') or ''}", "muted"))
        self.fv = FoundView(row.get("term", ""), locs, lambda n: paths.get(n) or paths.get(n.split(' (')[0]))
        v.addWidget(self.fv, 1)
        br = QHBoxLayout(); v.addLayout(br)
        if "state" in row and vol:
            br.addWidget(D.button("This place is the first use", "primary", lambda: self.set_here(),
                                  "Count the place shown as the first use in this volume"))
        if on_open:
            br.addWidget(D.button("Open the term in Acronyms", None, lambda: (self.dlg.accept(), on_open(row.get("term")))))
        br.addStretch(1)
        br.addWidget(D.button("Close", "ghost", self.dlg.accept))

    def set_here(self, loc=None):
        loc = loc or (self.fv.locs[self.fv.k] if self.fv.locs else None)
        if not loc or self.session is None:
            return None
        self.session.set_first_use(self.row["term"], loc)
        rep = self.session.qa_rebuild()
        if self.on_set:
            self.on_set(rep)
        self.dlg.accept()
        return rep

    def exec(self):
        return self.dlg.exec()
