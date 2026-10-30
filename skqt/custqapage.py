"""Customer Q&A (2.98.0): the formal list of questions we submit to the customer. Each row quotes the customer's exact
wording and where it is, then our question, its category, owner and status (Draft, Approved, Submitted, Answered) and,
when the answer comes back, the answer and the document it came in. Capture > Question in Review adds them from the
page; + Question adds one by hand. Export as a polished Word document, the government Excel layout, or into the
customer's own template; exporting can mark the questions Submitted. Rules only (No AI); nothing leaves the PC."""
import os
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QLineEdit, QPlainTextEdit, QRadioButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)
import diag
import custqa as Q
from . import design as D

FILTERS = ("All",) + Q.STATUSES + ("Not answered",)
COLS = ("No.", "Status", "Category", "Document", "Where", "Their wording", "Our question", "Answer")
TONE = {"Draft": "head", "Approved": "accent", "Submitted": "warn", "Answered": "ok"}


class EditDialog(QDialog):
    """Every field of one question, its answer included."""

    def __init__(self, parent, q, people=()):
        super().__init__(parent)
        self.setWindowTitle(f"Customer question {q.get('n', '')}" if q.get("id") else "New customer question")
        self.setMinimumWidth(720)
        v = QVBoxLayout(self)
        f = QFormLayout(); v.addLayout(f)
        self.quote = QPlainTextEdit(q.get("quote", "")); self.quote.setMaximumHeight(80); f.addRow("Their exact wording", self.quote)
        self.doc = QLineEdit(q.get("doc", "")); f.addRow("Document", self.doc)
        row = QHBoxLayout()
        self.section = QLineEdit(q.get("section", "")); self.page = QLineEdit(q.get("page", "")); self.para = QLineEdit(q.get("para", ""))
        self.page.setMaximumWidth(70); self.para.setMaximumWidth(70)
        for lab, w in (("Section", self.section), ("Page", self.page), ("Paragraph", self.para)):
            row.addWidget(D.label(lab, "label", wrap=False)); row.addWidget(w)
        f.addRow("Where", row)
        self.question = QPlainTextEdit(q.get("question", "")); self.question.setMaximumHeight(100); f.addRow("Our question", self.question)
        self.category = QComboBox(); self.category.addItems(Q.CATEGORIES); self.category.setCurrentText(q.get("category", "Technical"))
        f.addRow("Category", self.category)
        self.owner = QComboBox(); self.owner.setEditable(True); self.owner.addItem(""); self.owner.addItems(list(people))
        self.owner.setCurrentText(q.get("owner", "")); f.addRow("Owner", self.owner)
        self.status = QComboBox(); self.status.addItems(Q.STATUSES); self.status.setCurrentText(q.get("status", "Draft"))
        f.addRow("Status", self.status)
        self.answer = QPlainTextEdit(q.get("answer", "")); self.answer.setMaximumHeight(90)
        self.answer.setPlaceholderText("The customer's answer, when it comes back"); f.addRow("Their answer", self.answer)
        self.answer_doc = QLineEdit(q.get("answer_doc", "")); self.answer_doc.setPlaceholderText("Amendment 2, Q&A Round 1...")
        f.addRow("Answered in", self.answer_doc)
        self.note = QLineEdit(q.get("note", "")); self.note.setPlaceholderText("For the team (never exported)"); f.addRow("Team note", self.note)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        return {"quote": self.quote.toPlainText().strip(), "doc": self.doc.text().strip(), "section": self.section.text().strip(),
                "page": self.page.text().strip(), "para": self.para.text().strip(), "question": self.question.toPlainText().strip(),
                "category": self.category.currentText(), "owner": self.owner.currentText().strip(), "status": self.status.currentText(),
                "answer": self.answer.toPlainText().strip(), "answer_doc": self.answer_doc.text().strip(), "note": self.note.text().strip()}


class ExportDialog(QDialog):
    """Which questions, how they are numbered, and whether exporting marks them Submitted."""

    def __init__(self, parent, rec, kind):
        super().__init__(parent)
        self.setWindowTitle({"docx": "Export to Word", "xlsx": "Export to Excel", "template": "Fill the customer's template"}[kind])
        self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        c = Q.counts(rec)
        v.addWidget(D.label("Which questions", "label"))
        self.boxes = {}
        default = {"Approved"} if c.get("Approved") else {"Draft", "Approved"}
        for s in Q.STATUSES:
            cb = QCheckBox(f"{s} ({c.get(s, 0)})"); cb.setChecked(s in default); self.boxes[s] = cb; v.addWidget(cb)
        v.addWidget(D.label("Numbers", "label"))
        self.keep = QRadioButton("Keep each question's number in the list"); self.new = QRadioButton("Number the exported ones 1, 2, 3")
        self.keep.setChecked(True); v.addWidget(self.keep); v.addWidget(self.new)
        self.mark = QCheckBox("Mark the exported questions Submitted"); v.addWidget(self.mark)
        self.answers = QCheckBox("Include the answers we have (Government Response column)")
        if kind in ("xlsx", "docx"):                 # 3.0.1: Word has the column too
            v.addWidget(self.answers)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        return {"statuses": [s for s, cb in self.boxes.items() if cb.isChecked()], "numbers": "list" if self.keep.isChecked() else "new",
                "mark": self.mark.isChecked(), "answers": self.answers.isChecked()}


class CustQAPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.rows = []
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); v.addLayout(top)
        self.summary = D.label("", "title", wrap=False); top.addWidget(self.summary)
        self.due = D.Pill("", "warn"); top.addWidget(self.due)
        top.addStretch(1)
        top.addWidget(D.label("Show", "label", wrap=False))
        self.filter = QComboBox(); self.filter.addItems(FILTERS); self.filter.currentIndexChanged.connect(lambda _i: self.fill())
        top.addWidget(self.filter)
        self.find = QLineEdit(); self.find.setPlaceholderText("Find words"); self.find.setClearButtonEnabled(True); self.find.setMaximumWidth(220)
        self.find.textChanged.connect(lambda _t: self.fill()); top.addWidget(self.find)
        bar = QHBoxLayout(); v.addLayout(bar)
        for text, kind, fn, tip in (("+ Question", "primary", lambda: self.add(), "A question typed here (Capture > Question in Review quotes the page for you)"),
                                    ("Edit", None, lambda: self.edit(), "Every field, the answer included"),
                                    ("Approve", None, lambda: self.set_status("Approved"), "Ready to send"),
                                    ("Up", "ghost", lambda: self.move(-1), "Earlier in the list (the numbers follow)"),
                                    ("Down", "ghost", lambda: self.move(1), "Later in the list"),
                                    ("Show on the page", "ghost", lambda: self.show_page(), "The sentence in Review"),
                                    ("Remove", "danger", lambda: self.remove(), "Take it out of the list")):
            bar.addWidget(D.button(text, kind, fn, tip))
        bar.addStretch(1)
        for text, fn, tip in (("Export to Word...", lambda: self.export("docx"), "A polished document: cover block, numbered table, the marking"),
                              ("Export to Excel...", lambda: self.export("xlsx"), "The layout most solicitations ask for"),
                              ("Fill the customer's template...", lambda: self.export("template"), "Their Excel or Word form, filled in under its header row")):
            bar.addWidget(D.button(text, None, fn, tip))
        self.table = QTableWidget(0, len(COLS)); self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setWordWrap(True)
        for k, w in enumerate((44, 90, 110, 140, 110, 340, 360, 240)):     # the answer takes what is left (adaptive.tune)
            self.table.setColumnWidth(k, w)
        self.table.itemDoubleClicked.connect(lambda _i: self.edit())
        v.addWidget(self.table, 1)
        self.empty = D.label("No customer questions yet. In Review, select a sentence (or drag across words in it) and press "
                             "Capture > Question; or press + Question here.", "muted")
        v.addWidget(self.empty)

    # ------------------------------------------------------------ data
    def rec(self):
        import effortrec as R
        return R.Record(self.host.ws.root) if self.host.ws is not None else None

    def refresh(self):
        self.fill()

    def fill(self):
        rec = self.rec()
        self.table.setRowCount(0)
        self.rows = []
        if rec is None:
            self.summary.setText("Open an effort"); self.due.setVisible(False); self.empty.setVisible(False)
            return
        self.summary.setText(Q.summary(rec))
        due = questions_due(rec)
        self.due.setVisible(bool(due)); self.due.setText(f"Questions due {due}" if due else "")
        f, words = self.filter.currentText(), self.find.text().strip().casefold()
        for q in Q.items(rec):
            if f in Q.STATUSES and q.get("status") != f:
                continue
            if f == "Not answered" and q.get("status") == "Answered":
                continue
            if words and words not in " ".join(str(q.get(k, "")) for k in ("quote", "question", "answer", "doc", "section")).casefold():
                continue
            self.rows.append(q)
        self.table.setRowCount(len(self.rows))
        t = D.tokens()
        for r, q in enumerate(self.rows):
            vals = [str(q.get("n", "")), q.get("status", ""), q.get("category", ""), q.get("doc", ""), Q.where(q),
                    q.get("quote", ""), q.get("question", ""), q.get("answer", "") + (f"  ({q['answer_doc']})" if q.get("answer_doc") else "")]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c == 1:
                    tone = TONE.get(val, "head")
                    it.setBackground(QColor(t.get(tone + "_soft", t["accent_soft"]))); it.setForeground(QColor(t.get(tone, t["accent"])))
                if c == 5 and val:
                    it.setText(f"“{val}”")
                self.table.setItem(r, c, it)
        self.table.resizeRowsToContents()
        self.empty.setVisible(not Q.items(rec))

    def selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.rows[r] for r in rows if r < len(self.rows)]

    def select_id(self, qid):
        for r, q in enumerate(self.rows):
            if q["id"] == qid:
                self.table.selectRow(r)
                return True
        return False

    # ------------------------------------------------------------ actions
    def add(self, values=None):
        """values (tests): the dialog's values."""
        rec = self.rec()
        if rec is None:
            return None
        if values is None:
            d = EditDialog(self, {}, self.host.people())
            if d.exec() != QDialog.Accepted:
                return None
            values = d.values()
        qid = Q.add(rec, values.get("question", ""), values.get("quote", ""), doc=values.get("doc", ""), section=values.get("section", ""),
                    page=values.get("page", ""), para=values.get("para", ""), category=values.get("category", "Technical"),
                    owner=values.get("owner", ""))
        if not qid:
            self.host.status("Not added: write our question, or the customer's wording.")
            return None
        rest = {k: values[k] for k in ("status", "answer", "answer_doc", "note") if values.get(k) and not (k == "status" and values[k] == "Draft")}
        if rest:
            Q.update(rec, qid, **rest)
        diag.activity("custqa_added")
        self.fill(); self.select_id(qid)
        return qid

    def edit(self, values=None):
        sel = self.selected()
        rec = self.rec()
        if not sel or rec is None:
            return self.host.status("Select a question first.")
        q = sel[0]
        if values is None:
            d = EditDialog(self, q, self.host.people())
            if d.exec() != QDialog.Accepted:
                return None
            values = d.values()
        Q.update(rec, q["id"], **values)
        diag.activity("custqa_edited")
        self.fill(); self.select_id(q["id"])
        return True

    def set_status(self, status):
        rec = self.rec()
        sel = self.selected()
        if not sel or rec is None:
            return self.host.status("Select one or more questions first.")
        for q in sel:
            Q.update(rec, q["id"], status=status)
        diag.activity("custqa_status", n=len(sel))
        self.fill()
        self.host.toast(f"{len(sel)} question(s) {status.lower()}")
        return len(sel)

    def move(self, delta):
        rec = self.rec()
        sel = self.selected()
        if not sel or rec is None:
            return False
        ok = Q.move(rec, sel[0]["id"], delta)
        self.fill(); self.select_id(sel[0]["id"])
        return ok

    def remove(self, confirm=None):
        rec = self.rec()
        sel = self.selected()
        if not sel or rec is None:
            return False
        if confirm is None:
            from PySide6.QtWidgets import QMessageBox
            confirm = QMessageBox.question(self, "Remove", f"Remove {len(sel)} question(s) from the list?") == QMessageBox.Yes
        if not confirm:
            return False
        for q in sel:
            Q.remove(rec, q["id"])
        diag.activity("custqa_removed", n=len(sel))
        self.fill()
        return True

    def show_page(self):
        sel = self.selected()
        if not sel or not sel[0].get("sid") or self.host.review is None:
            return self.host.status("This question was not captured from a sentence of the matrix.")
        self.host.go("assign")
        return self.host.assign_page.select(sel[0]["sid"])

    def export(self, kind, path=None, choice=None, template=None):
        """kind: docx, xlsx or template. path, choice (ExportDialog.values()), template (tests)."""
        rec = self.rec()
        if rec is None:
            return None
        if choice is None:
            d = ExportDialog(self, rec, kind)
            if d.exec() != QDialog.Accepted:
                return None
            choice = d.values()
        rows = Q.chosen(rec, choice.get("statuses") or None)
        if not rows:
            self.host.status("No questions with the statuses chosen.")
            return None
        if kind == "template" and template is None:
            template, _ = QFileDialog.getOpenFileName(self, "The customer's Q&A template", "", "Excel or Word (*.xlsx *.xlsm *.docx)")
            if not template:
                return None
        ext = {"docx": ".docx", "xlsx": ".xlsx"}.get(kind, os.path.splitext(template or "")[1].lower() or ".xlsx")
        if path is None:
            start = self.host.out_path("customer_questions", ext)
            path, _ = QFileDialog.getSaveFileName(self, "Save the customer questions", start, f"*{ext}")
            if not path:
                return None
        info = export_info(self.host, rec)
        try:
            if kind == "docx":
                Q.export_docx(path, rows, numbers=choice.get("numbers", "list"), answers=choice.get("answers", False), **info)
            elif kind == "xlsx":
                info.pop("contact", None)
                Q.export_xlsx(path, rows, numbers=choice.get("numbers", "list"), answers=choice.get("answers", False), **info)
            else:
                n, _fields = Q.fill_template(template, path, rows, numbers=choice.get("numbers", "list"))
        except ValueError as ex:
            self.host.status(f"Not filled: {ex}")
            return None
        except OSError as ex:
            self.host.status(f"Not saved ({type(ex).__name__}): is the file open in Excel or Word?")
            return None
        if choice.get("mark"):
            for q in rows:
                if q.get("status") in ("Draft", "Approved"):
                    Q.update(rec, q["id"], status="Submitted")
        diag.activity("custqa_exported", n=len(rows))
        self.fill()
        self.host.toast(f"{len(rows)} question(s) saved: {os.path.basename(path)}")
        return path


def questions_due(rec):
    """'Nov 20, 2026 2:00 p.m. ET' from the calendar's Questions due entry, or ''."""
    import effortcal as EC
    import effortrec as R
    for e in rec.data.get("events", []):
        if e.get("kind") == "Questions due" and e.get("date"):
            d = R.parse_date(e["date"])
            if d is None:
                continue
            return f"{d.strftime('%b')} {d.day}, {d.year}" + (f" {EC.entry_times(e)}" if e.get("start") else "")
    return ""


def export_info(host, rec):
    """The cover block: solicitation, offeror (the company), point of contact (the proposal manager) and the marking."""
    import branding as BR
    out = {"effort": host.effort_name or "", "solicitation": "", "offeror": "", "contact": "", "marking": ""}
    try:
        fields = host.effort_fields() if hasattr(host, "effort_fields") else {}
        out["solicitation"] = fields.get("Solicitation", "") or rec.data.get("solicitation", "")
        import folderplan as FP
        out["offeror"] = (FP.current() or {}).get("company", "")
        ident = BR.identity(rec)
        out["contact"] = ident.get("pm", "")
        if BR.marking(ident.get("sensitivity", "")):
            out["marking"] = ident["sensitivity"]
    except Exception:
        diag.swallowed()
    return out
