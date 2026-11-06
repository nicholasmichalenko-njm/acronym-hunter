"""Production > Apply in Word (3.67.0): the team's banned phrases put into a draft as tracked changes the author accepts or
rejects. Read a draft (or, once allowed for this session, the document open in Word); review each change (tick, edit the
words); then make a dated copy with the changes tracked, or put them live into Word's open window. A fixed copy from Fix
a Copy compares with its draft in Word, so the formatting fixes reach the author as tracked changes too. Every live
change is logged. wordlab holds the rules."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)
import diag
import effortrec as R
import wordlab as WL
from . import design as D


class ApplyWordPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.changes, self.source, self.live_doc, self.live_text = [], "", "", ""
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        v.addWidget(D.label("Put the team's banned phrases into a draft as tracked changes, each with a comment naming the "
                            "rule, so the author accepts or rejects them in Word. Review every change first. By default "
                            "the changes go into a dated copy beside the draft; the draft itself is only read.", "muted"))
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        top.addWidget(D.button("Read a draft...", "primary", lambda: self.read_draft(), "A Word file: the changes go into a copy"))
        self.b_live_read = D.button("Read the document open in Word...", None, lambda: self.read_live(),
                                    "The changes go into Word's open window as tracked changes; you save in Word")
        top.addWidget(self.b_live_read)
        top.addStretch(1)
        top.addWidget(D.button("A fixed copy as tracked changes...", "ghost", lambda: self.fixed_as_tracked(),
                               "Word compares a draft with its fixed copy from Fix a Copy: the fixes become tracked changes"))
        self.allow = QCheckBox("Allow changes in a document open in Word for this session (banned phrases only, always as "
                               "tracked changes, every change logged; Stationkeeper never saves or closes it)")
        self.allow.toggled.connect(lambda _on: self._buttons())
        v.addWidget(self.allow)
        self.what = D.label("Nothing read yet.", None); v.addWidget(self.what)
        self.table = QTableWidget(0, 5); self.table.setHorizontalHeaderLabels(["Change", "Found", "Replace with", "Rule", "Sentence"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.itemChanged.connect(self._edited)
        v.addWidget(self.table, 2)
        act = QHBoxLayout(); v.addLayout(act)
        self.b_copy = D.button("Make the copy with tracked changes", "primary", lambda: self.make_copy())
        self.b_live = D.button("Put the ticked changes into Word", None, lambda: self.apply_live())
        act.addWidget(self.b_copy); act.addWidget(self.b_live); act.addStretch(1)
        act.addWidget(D.button("Tick all with replacement words", "ghost", lambda: self.tick_all(True)))
        act.addWidget(D.button("Untick all", "ghost", lambda: self.tick_all(False)))
        v.addWidget(D.SectionTitle("Changes made live in Word (this effort)"))
        self.log = QTableWidget(0, 6); self.log.setHorizontalHeaderLabels(["When", "File", "Found", "Now", "Rule", "Done"])
        self.log.verticalHeader().setVisible(False); self.log.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        v.addWidget(self.log, 1)
        self._buttons()

    def rec(self):
        return R.Record(self.host.ws.root) if self.host.ws is not None else None

    def refresh(self):
        self.fill_log()
        self._buttons()

    def _buttons(self):
        ticked = any(c.get("on") and c.get("fix") for c in self.changes)
        self.b_live_read.setEnabled(self.allow.isChecked())
        self.b_copy.setEnabled(bool(self.source) and bool(self.changes))
        self.b_live.setEnabled(self.allow.isChecked() and bool(self.live_doc) and ticked)

    # ------------------------------------------------------------ the changes
    def show_changes(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.changes))
        for i, c in enumerate(self.changes):
            tick = QTableWidgetItem("Change" if c.get("fix") else "Comment")
            tick.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            tick.setCheckState(Qt.Checked if c.get("on") else Qt.Unchecked)
            self.table.setItem(i, 0, tick)
            for j, val in ((1, c["hit"]), (2, c.get("fix") or ""), (3, f"{c['rule']} ({c['level']})"),
                           (4, c["sentence"] + (f"  Advice: {c['advice']}" if c.get("advice") else ""))):
                it = QTableWidgetItem(val)
                if j != 2:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, it)
        self.table.blockSignals(False)
        n = sum(1 for c in self.changes if c.get("on") and c.get("fix"))
        where = os.path.basename(self.live_doc or self.source)
        self.what.setText(f"{where}: {len(self.changes)} phrase(s) found, {n} ticked to change. Untick any you keep; "
                          "edit Replace with to change the words. Unticked phrases with advice become comments in the copy.")
        self._buttons()

    def _edited(self, item):
        i = item.row()
        if not (0 <= i < len(self.changes)):
            return
        if item.column() == 0:
            self.changes[i]["on"] = item.checkState() == Qt.Checked and bool(self.changes[i].get("fix"))
        elif item.column() == 2:
            self.changes[i]["fix"] = " ".join(item.text().split())
            self.changes[i]["on"] = bool(self.changes[i]["fix"]) and self.table.item(i, 0).checkState() == Qt.Checked
        self._buttons()

    def tick_all(self, on):
        for c in self.changes:
            c["on"] = bool(on and c.get("fix"))
        self.show_changes()

    # ------------------------------------------------------------ on a copy
    def read_draft(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "A draft", "", "Word (*.docx)")
            if not path:
                return None
        try:
            self.changes = WL.find(WL.docx_paragraphs(path))
        except Exception:  # noqa: BLE001  not a Word file
            diag.swallowed()
            self.host.status("That file does not read as a Word file.")
            return None
        self.source, self.live_doc, self.live_text = path, "", ""
        diag.activity("applyword_read", n=len(self.changes))
        self.show_changes()
        return self.changes

    def make_copy(self, out_path=None):
        if not (self.source and self.changes):
            return None
        res = WL.to_copy(self.source, self.changes, out_path)
        diag.activity("applyword_copy", n=res["changes"])
        self.host.toast(f"Copy made: {res['changes']} tracked change(s), {res['comments']} comment(s)")
        self.what.setText(f"Made {os.path.basename(res['path'])} beside the draft: {res['changes']} tracked change(s), "
                          f"{res['comments']} comment(s)" + (f", {res['skipped']} skipped (the words moved)" if res["skipped"] else "")
                          + ". Send it to the author to accept or reject in Word.")
        return res

    def fixed_as_tracked(self, draft=None, fixed=None, out_path=None, runner=None):
        import wordcompare as WC
        if draft is None:
            draft, _ = QFileDialog.getOpenFileName(self, "The draft", "", "Word (*.docx)")
            if not draft:
                return None
        if fixed is None:
            fixed, _ = QFileDialog.getOpenFileName(self, "Its fixed copy from Fix a Copy", os.path.dirname(draft), "Word (*.docx)")
            if not fixed:
                return None
        stem = os.path.splitext(os.path.basename(draft))[0]
        out_path = out_path or os.path.join(os.path.dirname(fixed), f"{stem} - fixes as tracked changes.docx")
        res = WC.compare(draft, fixed, out_path, author="Fix a Copy", runner=runner)
        if not res.get("ok"):
            self.host.status(res.get("why", "Word could not compare them."))
            return res
        self.host.toast(f"{res.get('revisions', 0)} fix(es) as tracked changes: {os.path.basename(out_path)}")
        return res

    # ------------------------------------------------------------ live in Word
    def read_live(self, full=None, runner=None):
        if not self.allow.isChecked():
            return None
        if full is None:
            res = WL.open_documents(runner=runner)
            if not res.get("ok"):
                self.host.status(res.get("why", "Word did not answer."))
                return None
            docs = [d for d in res["docs"] if not d.get("ro")]
            if not docs:
                self.host.status("No document open in Word for editing.")
                return None
            names = [d["full"] for d in docs]
            full, ok = QInputDialog.getItem(self, "Which document", "The document open in Word:", names, 0, False)
            if not ok:
                return None
        got = WL.read_open(full, runner=runner)
        if not got.get("ok"):
            self.host.status(got.get("why", "Word did not answer."))
            return None
        self.live_doc, self.live_text, self.source = full, got["text"], ""
        self.changes = WL.find(got["paragraphs"])
        self.show_changes()
        return self.changes

    def apply_live(self, runner=None):
        if not (self.allow.isChecked() and self.live_doc):
            return None
        res = WL.apply_open(self.live_doc, self.live_text, self.changes, runner=runner)
        if not res.get("ok"):
            self.host.status(res.get("why", "Word could not make the changes."))
            return res
        r = self.rec()
        if r is not None:
            WL.log(r, self.live_doc, self.changes, res, who=getattr(self.host, "my_name", None))
        diag.activity("applyword_live", n=res["applied"])
        self.host.toast(f"{res['applied']} tracked change(s) in Word" + (f", {res['skipped']} skipped" if res["skipped"] else "")
                        + ". Save in Word when the author is ready.")
        self.live_text = ""
        self.changes = []
        self.show_changes()
        self.what.setText(f"{res['applied']} tracked change(s) put into {os.path.basename(self.live_doc)}"
                          + (f"; {res['skipped']} skipped (the words had changed)" if res["skipped"] else "")
                          + ". Read it again before more changes.")
        self.live_doc = ""
        self.fill_log()
        self._buttons()
        return res

    def fill_log(self):
        r = self.rec()
        book = list(reversed((r.data.get("word_live") or []) if r is not None else []))[:500]
        self.log.setRowCount(len(book))
        for i, e in enumerate(book):
            for j, val in enumerate((e["when"], e["file"], e["old"], e["new"], e["rule"], "Yes" if e["done"] else f"No: {e.get('why', '')}")):
                self.log.setItem(i, j, QTableWidgetItem(str(val)))
