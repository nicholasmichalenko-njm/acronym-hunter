"""Keywords in Qt (2.66.0): the effort's keywords (category, status Proposed, Keep or Reject, source, why, who, when),
suggestions from the customer documents and our volumes with their reasons and sample sentences (rules and counts, No
AI), and the export laid out for the SharePoint columns. Kept in the effort list workbook (Keywords sheet), the same as
the classic window. Nothing leaves the PC."""
import os
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
                               QLineEdit, QPlainTextEdit, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import effortfolders as EF
import effort as E
from . import design as D

COLS = ["Keyword", "Category", "Status", "Source", "Why", "Added by", "Date"]
TONE = {"Keep": "ok", "Proposed": "accent", "Reject": "faint"}


class SuggestWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(object)

    def __init__(self, session, sources):
        super().__init__()
        self.session, self.sources = session, sources

    def run(self):
        try:
            items = self.session.kw_compute(self.sources, progress=lambda m: self.progress.emit(str(m)))
        except Exception:
            diag.swallowed()
            items = []
        self.finished_ok.emit(items)


class KeywordsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.words, self.sugg, self.sugg_all = [], [], []
        self.worker = None
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.f_status = QComboBox(); self.f_status.addItems(["All keywords", "Keep", "Proposed", "Reject"])
        self.f_status.currentIndexChanged.connect(lambda _i: self.fill())
        top.addWidget(self.f_status)
        for text, kind, fn in (("+ Keyword...", "primary", lambda: self.add_dialog()), ("Keep", None, lambda: self.set_status("Keep")),
                               ("Proposed", None, lambda: self.set_status("Proposed")), ("Reject", "danger", lambda: self.set_status("Reject")),
                               ("Remove", "ghost", lambda: self.remove())):
            top.addWidget(D.button(text, kind, fn))
        top.addStretch(1)
        self.b_suggest = D.button("Suggest keywords", None, lambda: self.suggest(), "From the customer documents and our volumes")
        top.addWidget(self.b_suggest)
        top.addWidget(D.button("Export for SharePoint...", None, lambda: self.export(), "Keywords marked Keep (Excel or CSV)"))
        split = QSplitter(Qt.Vertical)
        self.table = self._make(COLS)
        split.addWidget(self.table)
        sug = QWidget(); sv = QVBoxLayout(sug); sv.setContentsMargins(0, 0, 0, 0)
        sh = QHBoxLayout(); sv.addLayout(sh)
        self.s_head = D.label("Suggest keywords reads the customer documents and our volumes (typed text only).", "muted")
        sh.addWidget(self.s_head, 1)
        self.s_side = QComboBox(); self.s_side.addItems(["All", "From the customer", "In both", "From our volumes"])
        self.s_side.currentIndexChanged.connect(lambda _i: self.fill_suggestions())
        sh.addWidget(self.s_side)
        sh.addWidget(D.button("Add selected", "primary", lambda: self.add_suggested()))
        sh.addWidget(D.button("Not a keyword", "danger", lambda: self.reject_suggested()))
        inner = QSplitter(Qt.Horizontal)
        self.s_table = self._make(["Phrase", "Kind", "Answers", "Score", "Why"])
        self.s_table.itemSelectionChanged.connect(self.show_sample)
        inner.addWidget(self.s_table)
        self.s_side_text = QPlainTextEdit(); self.s_side_text.setReadOnly(True); inner.addWidget(self.s_side_text)
        inner.setSizes([900, 360])
        sv.addWidget(inner, 1)
        split.addWidget(sug); split.setSizes([420, 380])
        v.addWidget(split, 1)

    @staticmethod
    def _make(cols):
        t = QTableWidget(0, len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.verticalHeader().setVisible(False); t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectRows); t.setAlternatingRowColors(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive); t.horizontalHeader().setStretchLastSection(True)
        t.setColumnWidth(0, 240)
        return t

    @property
    def session(self):
        return self.host.acronym_page.session

    def refresh(self):
        h = self.host
        if h.ws is not None and self.session is None:
            h.acronym_page.load()
        self.setEnabled(h.ws is not None)
        self.fill()

    def fill(self):
        s = self.session
        L = s.effort if s is not None else None
        st = self.f_status.currentText()
        kws = [k for k in (L.keywords if L is not None else []) if st == "All keywords" or k["Status"] == st]
        self.words = [k["Keyword"] for k in kws]
        self.table.setRowCount(len(kws))
        for i, k in enumerate(kws):
            for c, col in enumerate(COLS):
                it = QTableWidgetItem(str(k.get(col, "") or ""))
                if col == "Status":
                    it.setForeground(D.color(TONE.get(k["Status"], "accent")))
                self.table.setItem(i, c, it)

    def selected(self, table=None):
        t = table or self.table
        rows = sorted({ix.row() for ix in t.selectedIndexes()})
        return rows if table is not None else [self.words[r] for r in rows if r < len(self.words)]

    def select(self, words):
        self.table.clearSelection()
        for w in words:
            if w in self.words:
                self.table.selectRow(self.words.index(w))

    # ------------------------------------------------------------ the list
    def add(self, text, category="Other", why=""):
        s = self.session
        if s is None or s.effort is None:
            return "no effort"
        r = s.kw_add(text, category, "Typed in", why)
        self.fill()
        return r

    def add_dialog(self):
        dlg = QDialog(self); dlg.setWindowTitle("Add a keyword")
        f = QFormLayout(dlg)
        t = QLineEdit(); cat = QComboBox(); cat.addItems(E.KW_CATEGORIES); cat.setCurrentText("Other"); why = QLineEdit()
        f.addRow("Keyword", t); f.addRow("Category", cat); f.addRow("Why", why)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        f.addRow(bb)
        if dlg.exec() == QDialog.Accepted and t.text().strip():
            return self.add(t.text().strip(), cat.currentText(), why.text().strip())
        return None

    def set_status(self, status, words=None):
        words = words or self.selected()
        if not words:
            return 0
        n = self.session.kw_set_status(status, words)
        self.fill(); self.select(words)
        return n

    def remove(self, words=None):
        words = words or self.selected()
        if not words:
            return 0
        self.session.kw_remove(words)
        self.fill()
        return len(words)

    def export(self, path=None, keep_only=True):
        s = self.session
        if s is None or s.effort is None:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export keywords for SharePoint", EF.out(self.host.effort_path,
                                                  f"{self.host.effort_name}_Keywords.xlsx".replace(" ", "_")), "Excel (*.xlsx);;CSV (*.csv)")
            if not path:
                return None
        try:
            n = s.kw_export(path, keep_only=keep_only)
        except PermissionError:
            self.host.status("That file is open in Excel. Close it, then export again.")
            return None
        self.host.toast(f"{n} keyword(s) exported")
        return path

    # ------------------------------------------------------------ suggestions
    def suggest(self, wait=False):
        s = self.session
        if s is None or self.worker is not None:
            return None
        s.matrix = self.host.review.M if self.host.review is not None else None
        srcs = s.kw_sources()
        if not srcs:
            self.s_head.setText("No documents yet: add customer documents to the effort or scan our volumes first.")
            return []
        diag.activity("keywords_suggest", files=len(srcs))
        if wait:                                       # tests
            self.suggested(s.kw_compute(srcs))
            return self.sugg_all
        self.worker = SuggestWorker(s, srcs)
        self.worker.progress.connect(self.s_head.setText)
        self.worker.finished_ok.connect(self.suggested)
        self.b_suggest.setEnabled(False)
        self.worker.start()
        return self.worker

    def suggested(self, items):
        if self.worker is not None:
            self.worker.wait(2000)
            self.worker = None
        self.b_suggest.setEnabled(True)
        self.sugg_all = list(items or [])
        import keywords as KW
        n = {k: sum(1 for x in self.sugg_all if x.get("side") == k) for k in KW.SIDES}
        self.s_head.setText(f"{len(self.sugg_all)} suggestions: customer {n['customer']}, both {n['both']}, ours {n['ours']}. "
                            "Select and add; Not a keyword keeps one from coming back. Rules and counts only (No AI).")
        self.fill_suggestions()

    def fill_suggestions(self):
        import keywords as KW
        want = {v: k for k, v in KW.SIDES.items()}.get(self.s_side.currentText())
        self.sugg = [x for x in self.sugg_all if want is None or x.get("side") == want]
        self.s_table.setRowCount(len(self.sugg))
        for i, it in enumerate(self.sugg):
            for c, val in enumerate((it["phrase"], it["bucket"], ", ".join(it.get("answers") or []), it["score"], "; ".join(it["why"]))):
                self.s_table.setItem(i, c, QTableWidgetItem(str(val)))

    def show_sample(self):
        rows = self.selected(self.s_table)
        if len(rows) != 1:
            self.s_side_text.setPlainText("")
            return
        it = self.sugg[rows[0]]
        import keywords as KW
        where = KW.SIDES.get(it.get("side"), "")
        self.s_side_text.setPlainText(it["phrase"] + "\n" + (where + "\n" if where else "")
                                      + (("Answers: " + ", ".join(it["answers"]) + "\n") if it.get("answers") else "") + "\n"
                                      + "\n".join("- " + w for w in it["why"]) + "\n\n"
                                      + "\n\n".join(f"{lbl}:\n{s}" for lbl, s in it["samples"]))

    def add_suggested(self, rows=None):
        s = self.session
        rows = rows if rows is not None else self.selected(self.s_table)
        picked = [self.sugg[r] for r in rows if r < len(self.sugg)]
        got = 0
        for it in picked:
            cat = it["bucket"] if it["bucket"] in E.KW_CATEGORIES else "Other"
            got += s.effort.add_keyword(it["phrase"], cat, "Suggested", "; ".join(it["why"])) == "added"
        if got:
            diag.activity("keywords_suggested_added", n=got)
            s._save_effort_list()
        self.sugg_all = [x for x in self.sugg_all if x not in picked]
        self.fill_suggestions(); self.fill()
        return got

    def reject_suggested(self, rows=None):
        import keywords
        s = self.session
        rows = rows if rows is not None else self.selected(self.s_table)
        picked = [self.sugg[r] for r in rows if r < len(self.sugg)]
        got = 0
        for it in picked:
            if s.effort.add_keyword(it["phrase"], "Other", "Suggested", "Not a keyword", status="Reject") == "added":
                got += 1
                keywords.learn(it["phrase"], "Reject")
        if got:
            s._save_effort_list()
        self.sugg_all = [x for x in self.sugg_all if x not in picked]
        self.fill_suggestions(); self.fill()
        return got
