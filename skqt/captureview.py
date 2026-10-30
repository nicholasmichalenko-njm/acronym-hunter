"""Capture in Assign (2.96.0): the selected sentence, or the words dragged across inside it, filed where the effort
keeps it, with the document and place it came from:
- Contact: a point of contact (name, title, organization, e-mail, phone, address, and fields of your own), new or
  added to one already filed; it shows in Effort Home's Customer information.
- Submission: a submission instruction (due date and time, delivery, copies, file format, naming); a due date can
  become the effort's due date and submission time zone, after you confirm.
- Formatting: a formatting rule (page limit, font, margins, page size, line spacing...); it shows in Effort Home's
  Formatting requirements.
- Acronym: the abbreviation and its long form, into the effort list.
- Question (2.98.0): a question for the customer, quoting the exact wording and where it is, into the Customer Q&A list.
- Key date (2.98.0): questions due, a site visit, industry day, orals, award..., onto the effort's calendar with its time
  zone; a proposal due date becomes the effort's due date.
Rules only (captures.py) for the suggestions; the person confirms every capture. Nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView, QLineEdit,
                               QPlainTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import captures as CP
import diag
from . import design as D

SUBMIT_SUBJECTS = [("Due", "Proposal"), ("Questions due", "Questions"), ("Delivery", "Delivery"), ("Copies", "Copies"),
                   ("File", "File format"), ("File", "File naming")]
FORMAT_SUBJECTS = [("Page limit", "Proposal"), ("Format", "Font"), ("Format", "Font in tables and figures"), ("Format", "Margins"),
                   ("Format", "Page size"), ("Format", "Line spacing"), ("Format", "Headers and footers"), ("Format", "Page numbering")]


class ContactDialog(QDialog):
    LABELS = (("name", "Name"), ("title", "Title or role"), ("org", "Organization"), ("email", "E-mail"), ("phone", "Phone"),
              ("address", "Address"))

    def __init__(self, parent, text, contacts):
        super().__init__(parent)
        self.setWindowTitle("Capture a point of contact")
        self.setMinimumWidth(620)
        v = QVBoxLayout(self)
        v.addWidget(D.label("From: " + text[:300], "muted"))
        g = CP.contact_guess(text)
        f = QFormLayout(); v.addLayout(f)
        self.to = QComboBox(); self.to.addItem("A new contact", None)
        for c in contacts:
            self.to.addItem("Add to: " + " · ".join(x for x in (c.get("name"), c.get("title"), c.get("email")) if x), c["id"])
        f.addRow("File it as", self.to)
        self.ed = {}
        for k, lab in self.LABELS:
            e = QLineEdit(g.get(k, "")); f.addRow(lab, e); self.ed[k] = e
        v.addWidget(D.label("Fields of your own (a second phone, an office symbol, a mailing address...):", "muted"))
        self.other = QTableWidget(0, 2); self.other.setHorizontalHeaderLabels(["Field", "Value"])
        self.other.verticalHeader().setVisible(False); self.other.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.other.setColumnWidth(0, 180); self.other.setMaximumHeight(130)
        v.addWidget(self.other)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("+ Field", None, lambda: self.add_field()))
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def add_field(self, label="", value=""):
        i = self.other.rowCount(); self.other.insertRow(i)
        self.other.setItem(i, 0, QTableWidgetItem(label)); self.other.setItem(i, 1, QTableWidgetItem(value))
        return i

    def values(self):
        out = {k: e.text().strip() for k, e in self.ed.items()}
        out["other"] = [{"label": self.other.item(i, 0).text() if self.other.item(i, 0) else "",
                         "value": self.other.item(i, 1).text() if self.other.item(i, 1) else ""} for i in range(self.other.rowCount())]
        return out, self.to.currentData()


class RuleDialog(QDialog):
    """Submission instructions or formatting rules: what the sentence sets (ticked), each one's rule and value
    editable; + Rule for one the app did not see."""

    def __init__(self, parent, text, which):
        super().__init__(parent)
        self.which = which
        subjects = SUBMIT_SUBJECTS if which == "submit" else FORMAT_SUBJECTS
        kinds = {k for k, _s in subjects}
        self.setWindowTitle("Capture submission instructions" if which == "submit" else "Capture formatting requirements")
        self.setMinimumWidth(720)
        v = QVBoxLayout(self)
        v.addWidget(D.label("From: " + text[:300], "muted"))
        self.t = QTableWidget(0, 3); self.t.setHorizontalHeaderLabels(["File it", "Rule", "Required"])
        self.t.verticalHeader().setVisible(False); self.t.setColumnWidth(0, 60); self.t.setColumnWidth(1, 220)
        self.t.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.t.verticalHeader().setDefaultSectionSize(32); self.t.setProperty("sk_rows_fixed", True)
        v.addWidget(self.t)
        self.subjects = subjects
        found = [r for r in CP.rule_guess(text) if r[0] in kinds]
        for kind, subj, val in found:
            self.add_rule(kind, subj, val, True)
        if not found:
            self.add_rule(subjects[0][0], subjects[0][1], " ".join(text.split())[:160], True)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("+ Rule", None, lambda: self.add_rule(subjects[0][0], subjects[0][1], "", True)))
        row.addStretch(1)
        self.due = None
        self.set_due = QCheckBox("")
        if which == "submit":
            g = CP.due_guess(text)
            if g and any(k == "Due" for k, _s, _v in found):
                self.due = g
                import effortrec as R
                import tzones as TZ
                self.set_due.setText(f"Make it the effort's due date: {R.when_text(g[0])}" + (f" {TZ.name(g[1])}" if g[1] else ""))
                self.set_due.setChecked(True)
                v.addWidget(self.set_due)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def add_rule(self, kind, subj, val, on=True):
        i = self.t.rowCount(); self.t.insertRow(i)
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setAlignment(Qt.AlignCenter)
        cb = QCheckBox(); cb.setChecked(on); h.addWidget(cb); w.box = cb
        self.t.setCellWidget(i, 0, w)
        rc = QComboBox(); rc.setEditable(True)
        for k, s in self.subjects:
            rc.addItem(s if k not in ("Due", "Questions due") else ("Proposal due" if k == "Due" else "Questions due"), (k, s))
        idx = next((j for j in range(rc.count()) if rc.itemData(j) == (kind, subj)), -1)
        if idx >= 0:
            rc.setCurrentIndex(idx)
        else:
            rc.setEditText(subj)
        self.t.setCellWidget(i, 1, rc)
        self.t.setItem(i, 2, QTableWidgetItem(val))
        return i

    def values(self):
        out = []
        for i in range(self.t.rowCount()):
            if not self.t.cellWidget(i, 0).box.isChecked():
                continue
            rc = self.t.cellWidget(i, 1)
            data = rc.itemData(rc.currentIndex()) if rc.currentText() == rc.itemText(rc.currentIndex()) else None
            kind, subj = data if data else (("Format" if self.which == "format" else "Delivery"), rc.currentText().strip())
            val = self.t.item(i, 2).text().strip() if self.t.item(i, 2) else ""
            if val:
                out.append((kind, subj, val))
        return out, (self.due if self.due and self.set_due.isChecked() else None)


class AcronymDialog(QDialog):
    def __init__(self, parent, text):
        super().__init__(parent)
        self.setWindowTitle("Capture an acronym")
        self.setMinimumWidth(520)
        f = QFormLayout(self)
        f.addRow(D.label("From: " + text[:300], "muted"))
        a, b = CP.acronym_guess(text)
        self.short = QLineEdit(a); self.long = QLineEdit(b)
        f.addRow("Acronym", self.short); f.addRow("What it stands for", self.long)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def values(self):
        return self.short.text().strip(), self.long.text().strip()


class QuestionDialog(QDialog):
    """2.98.0: a question for the customer: their exact wording (quoted, editable to trim it), where it is, our question,
    its category and who owns it."""

    def __init__(self, parent, text, src, people=()):
        super().__init__(parent)
        import custqa as Q
        self.setWindowTitle("Capture a question for the customer")
        self.setMinimumWidth(680)
        v = QVBoxLayout(self)
        f = QFormLayout(); v.addLayout(f)
        self.quote = QPlainTextEdit(" ".join((text or "").split())); self.quote.setMaximumHeight(90)
        f.addRow("Their exact wording", self.quote)
        self.doc = QLineEdit(src.get("doc", "")); f.addRow("Document", self.doc)
        row = QHBoxLayout()
        self.section = QLineEdit(src.get("section", "")); self.section.setPlaceholderText("L.4.2")
        self.page = QLineEdit(str(src.get("page", "") or "")); self.page.setMaximumWidth(70)
        self.para = QLineEdit(str(src.get("para", "") or "")); self.para.setMaximumWidth(70)
        for lab, w in (("Section", self.section), ("Page", self.page), ("Paragraph", self.para)):
            row.addWidget(D.label(lab, "label", wrap=False)); row.addWidget(w)
        f.addRow("Where", row)
        self.question = QPlainTextEdit(); self.question.setPlaceholderText("Our question, as the customer will read it")
        self.question.setMaximumHeight(110)
        f.addRow("Our question", self.question)
        self.category = QComboBox(); self.category.addItems(Q.CATEGORIES); f.addRow("Category", self.category)
        self.owner = QComboBox(); self.owner.setEditable(True); self.owner.addItem("")
        self.owner.addItems(list(people)); f.addRow("Owner", self.owner)
        v.addWidget(D.label("It goes into Customer Q&A as a Draft, numbered after the others.", "muted"))
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def values(self):
        return {"quote": self.quote.toPlainText().strip(), "doc": self.doc.text().strip(), "section": self.section.text().strip(),
                "page": self.page.text().strip(), "para": self.para.text().strip(), "question": self.question.toPlainText().strip(),
                "category": self.category.currentText(), "owner": self.owner.currentText().strip()}


KEY_KINDS = ("Questions due", "Proposal due", "Meeting", "Orals", "Review", "Milestone", "Due", "Other")


class KeyDateDialog(QDialog):
    """2.98.0: a key date: what it is, the date, the time (optional) and its time zone."""

    def __init__(self, parent, text):
        super().__init__(parent)
        import captures as CP2
        import tzones as TZ
        self.setWindowTitle("Capture a key date")
        self.setMinimumWidth(560)
        g = CP2.key_date_guess(text) or {"date": "", "start": "", "zone": "", "kind": "Milestone", "title": ""}
        f = QFormLayout(self)
        f.addRow(D.label("From: " + (text or "")[:300], "muted"))
        self.kind = QComboBox(); self.kind.addItems(KEY_KINDS)
        self.kind.setCurrentText(g["kind"] if g["kind"] in KEY_KINDS else "Other")
        f.addRow("Kind", self.kind)
        self.title = QLineEdit(g["title"]); f.addRow("What", self.title)
        self.date = QLineEdit(g["date"]); self.date.setPlaceholderText("YYYY-MM-DD"); f.addRow("Date", self.date)
        self.start = QLineEdit(g["start"]); self.start.setPlaceholderText("HH:MM (24-hour), or leave empty"); f.addRow("Time", self.start)
        self.zone = QComboBox(); self.zone.addItem("(not stated)", "")
        for k, n in TZ.choices():
            self.zone.addItem(n, k)
        i = self.zone.findData(g["zone"])
        self.zone.setCurrentIndex(max(0, i))
        f.addRow("Time zone", self.zone)
        f.addRow(D.label("Proposal due becomes the effort's due date and submission time zone. Every other kind goes on "
                         "the effort's calendar.", "muted"))
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def values(self):
        return {"kind": self.kind.currentText(), "title": self.title.text().strip(), "date": self.date.text().strip(),
                "start": self.start.text().strip(), "zone": self.zone.currentData() or ""}


# ------------------------------------------------------------------ filing (used by Assign; tests call these with answers)
def file_contact(host, values, cid, source):
    import effortrec as R
    rec = R.Record(host.ws.root)
    got = rec.save_contact(values, cid=cid, source=source)
    if got:
        diag.activity("capture_contact")
        host.toast("Contact filed in Customer information")
    return got


def file_rules(host, rules, due, source):
    import docversions as DV
    import subreq as SR
    reg = SR.Register(DV.Library(host.ws.p("documents")).load())
    keys = [reg.add(kind, subj, val, source=source) for kind, subj, val in rules]
    if due:
        import effortrec as R
        rec = R.Record(host.ws.root)
        rec.set_due(due[0], due[1], zone_key=due[1] or None)
        rec.log("effort", f"Due date captured from {source.get('doc', 'the documents')}", save=True)
    if keys:
        diag.activity("capture_rules", n=len(keys))
        host.toast(f"{len(keys)} rule(s) filed" + (" and the due date set" if due else ""))
    return keys


def file_acronym(host, short, long_, source):
    import effort as E
    short = " ".join(short.split())
    if not short:
        return False
    L = E.EffortList(host.effort_path, host.effort_name).load()
    row = {"Definition": long_} if long_ else {}
    row["Customer document"] = source.get("doc", "")
    row["Customer wording"] = (source.get("text") or "")[:300]
    L.add_or_update(short, change_note=f"captured from {source.get('doc', 'a customer document')}", **row)
    L.pending = True
    L.save()
    diag.activity("capture_acronym")
    host.toast(f"{short} is in the effort list")
    return True


def file_question(host, values, source):
    """2.98.0: into Customer Q&A as a Draft. Returns its id ('' when nothing was written)."""
    import custqa as Q
    import effortrec as R
    rec = R.Record(host.ws.root)
    qid = Q.add(rec, values.get("question", ""), values.get("quote", ""), doc=values.get("doc", ""), section=values.get("section", ""),
                page=values.get("page", ""), para=values.get("para", ""), category=values.get("category", "Technical"),
                owner=values.get("owner", ""), sid=source.get("sid", ""))
    if qid:
        diag.activity("capture_question")
        host.toast(f"Question {Q.get(rec, qid)['n']} drafted in Customer Q&A")
    return qid


def file_key_date(host, values, source):
    """2.98.0: a key date onto the calendar; Proposal due becomes the effort's due date. Returns the entry id, 'due', or
    '' when the date could not be read."""
    import effortcal as EC
    import effortrec as R
    rec = R.Record(host.ws.root)
    d = R.parse_date(values.get("date", ""))
    start = values.get("start", "")
    if start:
        hm = R.parse_time(start)
        start = f"{hm[0]:02d}:{hm[1]:02d}" if hm else ""
        if not start:
            d = None
    if d is None:
        host.status("Not filed: give the date as YYYY-MM-DD and the time as HH:MM.")
        return ""
    zone = values.get("zone", "")
    where = " ".join(x for x in (source.get("doc", ""), source.get("loc", "")) if x)
    if values.get("kind") == "Proposal due":
        rec.set_due(f"{d.isoformat()}T{start or '17:00'}", zone, zone_key=zone or None)
        rec.log("effort", f"Due date captured from {source.get('doc', 'the documents')}", save=True)
        diag.activity("capture_key_date")
        host.toast("The effort's due date is set")
        return "due"
    eid = EC.add_entry(rec, kind=values.get("kind", "Other"), date=d.isoformat(), start=start, zone=zone,
                       title=values.get("title", "") or values.get("kind", ""),
                       details=(f"From {where}: " if where else "") + (source.get("text") or "")[:600])
    if eid:
        diag.activity("capture_key_date")
        host.toast(f"{values.get('title') or values.get('kind')} is on the calendar")
    return eid or ""

