"""Data calls in Qt (3.39.0): a tab beside Customer Q&A for what the team needs from its own experts. Each call says
what is needed, which section or requirement it serves, how much, an example of a good answer, the owner and the due
date. Send Word files... writes one file per person with their open calls; Read answers... puts each returned answer
on its call; Place in the section puts an answer into the response structure as context for the section's author.
Rules only (No AI); nothing leaves the PC."""
import datetime, os
from PySide6.QtCore import QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QLineEdit, QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import datacalls as DC
from . import design as D

COLS = ("Call", "Status", "What we need", "For", "Owner", "Due", "Answer")
TONE = {"Draft": "head", "Sent": "warn", "Answered": "accent", "Placed": "ok"}


class CallDialog(QDialog):
    """Every field of one call."""

    def __init__(self, parent, c, people=(), sections=()):
        super().__init__(parent)
        self.setWindowTitle(f"Data call {DC.code_of(c)}" if c.get("id") else "New data call")
        self.setMinimumWidth(720)
        v = QVBoxLayout(self)
        f = QFormLayout(); v.addLayout(f)
        self.question = QPlainTextEdit(c.get("question", "")); self.question.setMaximumHeight(90)
        self.question.setPlaceholderText("What we need, in one or two sentences: the facts, numbers or story")
        f.addRow("What we need", self.question)
        self.section = QComboBox(); self.section.setEditable(True); self.section.addItem(""); self.section.addItems(list(sections))
        self.section.setCurrentText(c.get("section", "")); f.addRow("For the section", self.section)
        self.req = QLineEdit(c.get("req", "")); self.req.setPlaceholderText("The requirement or evaluation factor it answers (L.4.2, M.3...)")
        f.addRow("And the requirement", self.req)
        self.words = QLineEdit(c.get("words", "")); self.words.setPlaceholderText("150 to 250 words, a table of 5 rows...")
        f.addRow("How much", self.words)
        self.example = QPlainTextEdit(c.get("example", "")); self.example.setMaximumHeight(80)
        self.example.setPlaceholderText("A short example of a good answer: answers come back closer to what you need")
        f.addRow("An example", self.example)
        self.owner = QComboBox(); self.owner.setEditable(True); self.owner.addItem(""); self.owner.addItems(list(people))
        self.owner.setCurrentText(c.get("owner", "")); f.addRow("Owner", self.owner)
        self.due = QDateEdit(); self.due.setCalendarPopup(True); self.due.setDisplayFormat("yyyy-MM-dd")
        d = QDate.fromString((c.get("due") or "")[:10], "yyyy-MM-dd")
        self.due.setDate(d if d.isValid() else QDate.currentDate().addDays(3)); f.addRow("Due", self.due)
        self.status = QComboBox(); self.status.addItems(DC.STATUSES); self.status.setCurrentText(c.get("status", "Draft"))
        f.addRow("Status", self.status)
        self.answer = QPlainTextEdit(c.get("answer", "")); self.answer.setMaximumHeight(110)
        self.answer.setPlaceholderText("The answer, typed here or read from the returned file"); f.addRow("Answer", self.answer)
        self.note = QLineEdit(c.get("note", "")); self.note.setPlaceholderText("For the team (never sent)"); f.addRow("Team note", self.note)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        return {"question": self.question.toPlainText().strip(), "section": self.section.currentText().strip(), "req": self.req.text().strip(),
                "words": self.words.text().strip(), "example": self.example.toPlainText().strip(), "owner": self.owner.currentText().strip(),
                "due": self.due.date().toString("yyyy-MM-dd"), "status": self.status.currentText(),
                "answer": self.answer.toPlainText().strip(), "note": self.note.text().strip()}


class DataCallsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.rows = []
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["s"])
        top = QHBoxLayout(); v.addLayout(top)
        self.summary = D.label("", "title", wrap=False); top.addWidget(self.summary); top.addStretch(1)
        top.addWidget(D.label("Show", "label", wrap=False))
        self.filter = QComboBox(); self.filter.addItems(("All",) + DC.STATUSES + ("Overdue",))
        self.filter.currentIndexChanged.connect(lambda _i: self.fill()); top.addWidget(self.filter)
        bar = QHBoxLayout(); v.addLayout(bar)
        for text, kind, fn, tip in (("+ Data call", "primary", lambda: self.add(), "Ask an expert for what a section needs"),
                                    ("Edit", None, lambda: self.edit(), "Every field, the answer included"),
                                    ("Place in the section", None, lambda: self.place(),
                                     "Put the answer into the response structure as context for the section's author"),
                                    ("Remove", "danger", lambda: self.remove(), "Take it out of the list")):
            bar.addWidget(D.button(text, kind, fn, tip))
        bar.addStretch(1)
        bar.addWidget(D.button("Send Word files...", None, lambda: self.send(), "One Word file per person with their open calls; they become Sent"))
        bar.addWidget(D.button("Read answers...", None, lambda: self.read(), "Returned files: each answer goes back on its call"))
        self.table = QTableWidget(0, len(COLS)); self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False); self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.setWordWrap(True)
        for k, w in enumerate((60, 90, 360, 200, 130, 90, 320)):
            self.table.setColumnWidth(k, w)
        self.table.itemDoubleClicked.connect(lambda _i: self.edit())
        v.addWidget(self.table, 1)
        self.empty = D.label("No data calls yet. Press + Data call to ask an expert for what a section needs: say how much, give an "
                             "example, set an owner and a due date, then Send Word files...", "muted")
        v.addWidget(self.empty)

    # ------------------------------------------------------------ data
    def rec(self):
        import effortrec as R
        return R.Record(self.host.ws.root) if self.host.ws is not None else None

    def M(self):
        return getattr(self.host.review, "M", None) if getattr(self.host, "review", None) is not None else None

    def sections(self):
        M = self.M()
        if M is None:
            return []
        import compliance as C
        return [C.outline_label(o) for o in M.outline]

    def refresh(self):
        self.fill()

    def fill(self):
        rec = self.rec()
        self.table.setRowCount(0)
        self.rows = []
        if rec is None:
            self.summary.setText("Open an effort"); self.empty.setVisible(False)
            return
        self.summary.setText(DC.summary(rec))
        f = self.filter.currentText()
        late = {c["id"] for c in DC.overdue(rec)}
        for c in DC.items(rec):
            if f in DC.STATUSES and c.get("status") != f:
                continue
            if f == "Overdue" and c["id"] not in late:
                continue
            self.rows.append(c)
        self.table.setRowCount(len(self.rows))
        t = D.tokens()
        for r, c in enumerate(self.rows):
            vals = [DC.code_of(c), c.get("status", ""), c.get("question", ""), " / ".join(x for x in (c.get("section", ""), c.get("req", "")) if x),
                    c.get("owner", ""), (c.get("due", "") + ("  late" if c["id"] in late else "")), c.get("answer", "")]
            for k, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if k == 1:
                    tone = TONE.get(val, "head")
                    it.setBackground(QColor(t.get(tone + "_soft", t["accent_soft"]))); it.setForeground(QColor(t.get(tone, t["accent"])))
                if k == 5 and c["id"] in late:
                    it.setForeground(QColor(t.get("crit", "#B91C1C")))
                self.table.setItem(r, k, it)
        self.table.resizeRowsToContents()
        self.empty.setVisible(not DC.items(rec))

    def selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.rows[r] for r in rows if r < len(self.rows)]

    def select_id(self, cid):
        for r, c in enumerate(self.rows):
            if c["id"] == cid:
                self.table.selectRow(r)
                return True
        return False

    # ------------------------------------------------------------ actions
    def add(self, values=None):
        rec = self.rec()
        if rec is None:
            return None
        if values is None:
            d = CallDialog(self, {}, self.host.people(), self.sections())
            if d.exec() != QDialog.Accepted:
                return None
            values = d.values()
        cid = DC.add(rec, values.get("question", ""), section=values.get("section", ""), req=values.get("req", ""),
                     words=values.get("words", ""), example=values.get("example", ""), owner=values.get("owner", ""),
                     due=values.get("due", ""))
        if not cid:
            self.host.status("Say what you need first.")
            return None
        rest = {k: v for k, v in values.items() if k in ("status", "answer", "note") and v}
        if rest:
            DC.update(rec, cid, **rest)
        diag.activity("data_call_added")
        self.fill(); self.select_id(cid)
        return cid

    def edit(self, values=None):
        rec = self.rec()
        sel = self.selected()
        if rec is None or not sel:
            return False
        c = sel[0]
        if values is None:
            d = CallDialog(self, c, self.host.people(), self.sections())
            if d.exec() != QDialog.Accepted:
                return False
            values = d.values()
        DC.update(rec, c["id"], **values)
        self.fill(); self.select_id(c["id"])
        return True

    def remove(self):
        rec = self.rec()
        sel = self.selected()
        if rec is None or not sel:
            return 0
        for c in sel:
            DC.remove(rec, c["id"])
        self.fill()
        return len(sel)

    def place(self):
        rec, M = self.rec(), self.M()
        sel = self.selected()
        if rec is None or not sel:
            return ""
        if M is None:
            self.host.status("Open the effort's response structure first (Review or Setup).")
            return ""
        c = sel[0]
        if not c.get("answer"):
            self.host.status(f"{DC.code_of(c)} has no answer yet.")
            return ""
        xid = DC.place(rec, M, c["id"])
        if not xid:
            self.host.status(f"Choose a section of the response structure for {DC.code_of(c)} first (Edit > For the section).")
            return ""
        try:
            self.host.review.save()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        diag.activity("data_call_placed")
        self.host.status(f"{DC.code_of(c)}'s answer is in {c.get('section', '')} as context for its author.")
        self.fill(); self.select_id(c["id"])
        return xid

    def send(self, folder=None):
        rec = self.rec()
        if rec is None:
            return []
        if not DC.owners(rec):
            self.host.status("No open data call has an owner yet.")
            return []
        if folder is None:
            start = self.host.out_path("data_calls") if self.host.effort_path else os.path.expanduser("~")
            folder = QFileDialog.getExistingDirectory(self, "Folder for the data call files", start)
            if not folder:
                return []
            folder = os.path.join(folder, f"Data calls {datetime.datetime.now():%Y-%m-%d %H%M}")
        from .custqapage import export_info
        info = export_info(self.host, rec)
        out = DC.export_all(folder, rec, effort=self.host.effort_name or "", marking=info.get("marking", ""))
        diag.activity("data_calls_sent", n=len(out))
        self.host.status(f"{len(out)} Word file(s), one per person, in {folder}.")
        self.fill()
        return out

    def read(self, paths=None):
        rec = self.rec()
        if rec is None:
            return None
        if paths is None:
            paths, _ = QFileDialog.getOpenFileNames(self, "Returned data call files", os.path.expanduser("~"), "Word (*.docx)")
            if not paths:
                return None
        total, unknown = 0, []
        for p in paths:
            try:
                got = DC.apply_answers(rec, DC.read_back(p))
            except Exception:  # noqa: BLE001
                diag.swallowed()
                continue
            total += got["answered"]; unknown += got["unknown"]
        diag.activity("data_call_answers_read", n=total)
        self.host.status(f"{total} answer(s) read back" + (f"; not in this effort: {', '.join(unknown)}" if unknown else "") + ".")
        self.fill()
        return {"answered": total, "unknown": unknown}
