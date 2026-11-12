"""Redline (4.8.0; claude/stationkeeper-redline-plan-4.6.md, step 4; claude/stationkeeper-redline-decisions-2026-11-10.md).
A menu item of its own below the six steps, with no number: redlining happens at any point (the draft RFP, Q&A, the
final RFP's terms, amendments, a model contract). Authors redline in Word with Track Changes; the app does what Word
does badly. Three tabs, each with one main button:
- Prepare: the effort's customer PDFs with the date of each copy made; Make the Word copy (redlinecopy; 4.16.0: the
  PDF's comments come in as tracked changes and Word comments). More: Another PDF..., Make it as slides, Make it as a
  document, Make it without the PDF's comments, Open the Redlines folder. Fix text in Shred first if the page needs it: the copy uses the text as fixed there.
- Check: Check the copy against its PDF, word for word; Check the returned redline... (an edit made with Track Changes
  off). Each finding lists its page and the heading above it; double-click shows it on the page in Shred.
- Exceptions: Read the redline's changes... (each tracked change a row); Export to Excel or Word.
Files go to the effort's Redlines folder. Every role sees it. Rules only (No AI); nothing leaves the PC."""
import datetime, os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

import diag
from . import design as D
from .commandbar import CommandBar


def folder(host):
    import effortfolders as EF
    return EF.folder(host.effort_path, "redlines") if host.ws is not None and getattr(host, "effort_path", "") else ""


def customer_pdfs(host):
    """[(doc id, name, path)] of the effort's customer documents whose latest version is a PDF here."""
    if host.ws is None:
        return []
    import docversions as DV
    lib = DV.Library(host.ws.p("documents")).load()
    out = []
    for d in lib.docs:
        if d.get("category", "customer") not in ("customer", "bidders", "qa") or not d.get("versions"):
            continue
        p = lib.path_of(d["versions"][-1])
        if p and p.lower().endswith(".pdf") and os.path.isfile(p):
            out.append((d["id"], d["name"], p))
    return out


def _table(cols):
    t = QTableWidget(0, len(cols)); t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().setVisible(False); t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setWordWrap(True)
    t.horizontalHeader().setStretchLastSection(True)
    return t


def _page(host):
    w = QWidget(); w.setObjectName("page")
    v = QVBoxLayout(w); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
    return w, v


def _open(path):
    if path and not os.environ.get("AH_TEST"):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    return path


class PreparePage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("page")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); v.addLayout(top)
        self.say = D.label("", "muted"); top.addWidget(self.say, 1)
        self.bar = CommandBar()
        self.bar.primary("Make the Word copy", lambda: self.make(), "A clean Word copy of the selected PDF: real headings, the "
                         "customer's numbers as typed, paragraphs joined, no running headers or page numbers")
        self.bar.more("Another PDF...", lambda: self.make(other=True), "A PDF that is not in Documents, such as a model contract")
        self.bar.more("Make it as slides", lambda: self.make(layout="slides"), "One Word page a slide: the slide's pictures "
                      "behind, each box of text where it sits (a deck saved as PDF is made this way on its own)")
        self.bar.more("Make it as a document", lambda: self.make(layout="document"), "Running text, headings and tables, even "
                      "for a PDF that looks like slides")
        self.bar.more("Make it without the PDF's comments", lambda: self.make(comments=False), "A clean copy: the reviewers' "
                      "highlights, cross-outs, inserts and notes on the PDF left out")
        self.bar.more("Open the Redlines folder", lambda: _open(folder(self.host)))
        top.addWidget(self.bar)
        v.addWidget(D.label("Fix text in Shred first if the page needs it: the copy uses the text as fixed there.", "muted"))
        self.table = _table(["Document", "File", "Copy made"])
        self.table.setColumnWidth(0, 260); self.table.setColumnWidth(1, 320)
        v.addWidget(self.table, 1)
        self.empty = D.EmptyState("No customer PDFs yet", "Add the solicitation's PDFs in Documents; each one can have a clean "
                                  "Word copy to redline.", "Go to Documents", lambda: self.host.go("library"))
        v.addWidget(self.empty); self.empty.hide()
        self.rows = []

    def refresh(self, select=None):
        self.rows = customer_pdfs(self.host)
        f = folder(self.host)
        self.table.setRowCount(len(self.rows))
        for r, (did, name, p) in enumerate(self.rows):
            import redlinecopy as RC
            made = RC.copies(f, os.path.basename(p)) if f else []
            when = os.path.basename(made[0]).rsplit(" - ", 1)[-1][:-5] if made else "not yet"
            for c, val in enumerate((name, os.path.basename(p), when)):
                it = QTableWidgetItem(val); it.setData(Qt.UserRole, did); self.table.setItem(r, c, it)
            if did == select:
                self.table.selectRow(r)
        if self.rows and self.table.currentRow() < 0:
            self.table.selectRow(0)
        self.table.setVisible(bool(self.rows)); self.empty.setVisible(not self.rows)
        self.say.setText(f"{len(self.rows)} customer PDF(s). Copies go to the effort's Redlines folder." if self.rows else "")

    def select(self, doc_id):
        self.refresh(select=doc_id)
        return any(d == doc_id for d, _n, _p in self.rows)

    def make(self, other=False, pdf=None, layout=None, comments=True):
        """Make the copy of the selected PDF (or another one). Returns the copy's path, or None. layout (4.15.0):
        "slides" or "document"; left out, the PDF says which. comments (4.16.0): the PDF's comments come in as tracked
        changes and Word comments; False leaves them out."""
        import redlinecopy as RC
        if pdf is None and other:
            pdf, _f = QFileDialog.getOpenFileName(self, "A PDF to make a Word copy of", "", "PDF (*.pdf)")
            if not pdf:
                return None
        if pdf is None:
            r = self.table.currentRow()
            if not (0 <= r < len(self.rows)):
                self.host.status("Pick a PDF first.")
                return None
            pdf = self.rows[r][2]
        f = folder(self.host) or os.path.dirname(pdf)
        out = os.path.join(f, RC.copy_name(pdf))
        try:
            res = RC.build(pdf, out, layout=layout, comments=comments)
        except ValueError as e:
            self.host.status(str(e) + " Read its pages in Shred first.")
            return None
        except PermissionError:
            self.host.status("The copy is open in Word: close it, then make it again.")
            return None
        self.host.toast(f"Word copy made: {res['slides']} slide(s), {res['paragraphs']} paragraphs" if res.get("slides") else
                        f"Word copy made: {res['paragraphs']} paragraphs, {res['headings']} headings"
                        + (f", {res['tables']} table(s)" if res.get("tables") else "") + said_comments(res))
        diag.activity("redline_copy_made", n=res["paragraphs"])
        self.refresh()
        return out


def said_comments(res):
    """4.16.0: what the PDF's comments became, for the message after Make the Word copy."""
    recs = res.get("comments") or []
    if not recs:
        return ""
    out = f". {len(recs)} comment(s) from the PDF: {res.get('changes', 0)} tracked change(s), {res.get('word_comments', 0)} Word comment(s)"
    if res.get("by_position"):
        out += f"; {res['by_position']} placed by position (Check lists them)"
    return out


HOW = {"words": "on its words", "position": "by position", "left out": "on a line the copy leaves out",
       "nearby words": "on the nearest words", "not placed": "listed only"}


class CheckPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("page")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); v.addLayout(top)
        self.copy = QComboBox(); self.copy.setMinimumWidth(380); top.addWidget(self.copy, 1)
        self.bar = CommandBar()
        self.bar.add("Check the returned redline...", lambda: self.check_returned(), "The redline the authors sent back: an "
                     "edit made with Track Changes off is listed (Word cannot see it)")
        self.bar.primary("Check the copy", lambda: self.check_copy(), "The copy against its PDF, word for word")
        top.addWidget(self.bar)
        self.say = D.label("Pick a Word copy and check it against its PDF, or check a redline that came back.", "muted")
        v.addWidget(self.say)
        self.table = _table(["What", "Was", "Now", "Page", "Under"])
        for c, wdt in enumerate((110, 300, 300, 50)):
            self.table.setColumnWidth(c, wdt)
        self.table.itemDoubleClicked.connect(lambda it: self.show_on_page(it.row()))
        v.addWidget(self.table, 1)
        self.found, self.source = [], ""

    def refresh(self):
        import redlinecopy as RC
        keep = self.copy.currentData()
        self.copy.clear()
        f = folder(self.host)
        for p in RC.copies(f) if f else []:
            self.copy.addItem(os.path.basename(p), p)
        if keep and self.copy.findData(keep) >= 0:
            self.copy.setCurrentIndex(self.copy.findData(keep))

    def _source_of(self, copy):
        import redlinecopy as RC
        side = RC.sidecar(copy) or {}
        name = side.get("source", "")
        for _d, _n, p in customer_pdfs(self.host):
            if os.path.basename(p) == name:
                return p
        cand = os.path.join(os.path.dirname(copy), name)
        return cand if name and os.path.isfile(cand) else ""

    def fill(self, rows, aside=(), comments=()):
        """The differences, then the lines set aside, then (4.16.0) each comment from the PDF: what it became, the
        words it is on in the copy, its note, its page, the heading above."""
        notes = [{"kind": f"PDF {c['kind']}, {HOW.get(c['how'], c['how'])}", "was": c.get("in_copy") or c.get("marked", ""),
                  "now": f"{c.get('became', '')}: {c.get('note', '')} ({c.get('author', '')})".strip(), "page": c.get("page"),
                  "heading": c.get("heading", "")} for c in comments]
        self.found = list(rows) + [{"page": pg} for pg, _t in aside] + notes
        allrows = [(x["kind"], x["was"], x["now"], str(x["page"] or ""), x["heading"]) for x in rows] + \
                  [("Set aside on purpose", t, "", str(pg), "") for pg, t in aside] + \
                  [(x["kind"], x["was"], x["now"], str(x["page"] or ""), x["heading"]) for x in notes]
        self.table.setRowCount(len(allrows))
        for r, vals in enumerate(allrows):
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c == 0:
                    it.setForeground(D.color({"Dropped": "crit", "Added": "warn", "Changed": "warn"}.get(
                        val, "warn" if val.startswith("PDF") and not val.endswith("on its words") else "muted")))
                self.table.setItem(r, c, it)
        self.table.resizeRowsToContents()

    def check_copy(self, copy=None):
        import redlinecheck as CK
        copy = copy or self.copy.currentData()
        if not copy:
            self.host.status("Make a Word copy on Prepare first.")
            return None
        pdf = self._source_of(copy)
        if not pdf:
            self.host.status("The copy's PDF is not here, so it cannot be checked.")
            return None
        res = CK.faithful(pdf, copy)
        self.source = pdf
        cms = res.get("comments") or []
        self.fill(res["differences"], res["set_aside"], cms)
        n = len(res["differences"])
        self.say.setText((f"{n} difference(s) between the copy and its PDF." if n else "The copy holds every word of its PDF, in order.")
                         + (f" {len(res['set_aside'])} line(s) set aside on purpose in Fix text." if res["set_aside"] else "")
                         + (f" {res['tables']} table(s) were made as Word tables from where the PDF's columns sit: look at "
                            "each beside the PDF (a cell that wrapped, a merged cell)." if res["tables"] else "")
                         + (f" {len(cms)} comment(s) from the PDF are listed below the differences; look at the ones not "
                            "placed on their own words." if cms else ""))
        diag.activity("redline_copy_checked", n=n)
        return res

    def check_returned(self, path=None, copy=None):
        import redlinecheck as CK
        copy = copy or self.copy.currentData()
        if not copy:
            self.host.status("Pick the Word copy the redline was made from.")
            return None
        if path is None:
            path, _f = QFileDialog.getOpenFileName(self, "The returned redline", folder(self.host), "Word (*.docx)")
            if not path:
                return None
        res = CK.returned(copy, path)
        self.source = self._source_of(copy)
        self.fill(res["differences"])
        n = len(res["differences"])
        self.say.setText(f"{n} edit(s) made with Track Changes off: Word cannot show them as changes." if n else
                         "Every edit in the returned redline is a tracked change.")
        diag.activity("redline_returned_checked", n=n)
        return res

    def show_on_page(self, row):
        """The finding's page in Shred, on the copy's PDF."""
        if not (0 <= row < len(self.found)) or not self.source:
            return False
        h = self.host
        h.go("assign")
        try:
            h.assign_page.open_file(os.path.basename(self.source))
            cv = getattr(h.assign_page, "canvas", None)
            if cv is not None and self.found[row]["page"]:
                cv.go_page(int(self.found[row]["page"]))
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return False
        return True


class ExceptionsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("page")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); v.addLayout(top)
        self.say = D.label("Read a redline's tracked changes into a table: each change with the customer's number, the "
                           "original and our text, who and when, and the comment on it.", "muted")
        top.addWidget(self.say, 1)
        self.bar = CommandBar()
        self.bar.primary("Read the redline's changes...", lambda: self.read(), "Pick the redline (a Word file with tracked changes)")
        self.bar.export("Exceptions table (Excel)...", lambda: self.export("xlsx"))
        self.bar.export("Exceptions table (Word)...", lambda: self.export("docx"))
        top.addWidget(self.bar)
        import redlineexcept as EX
        self.table = _table(list(EX.COLS[:7]))
        for c, wdt in enumerate((80, 280, 280, 80, 120, 90)):
            self.table.setColumnWidth(c, wdt)
        v.addWidget(self.table, 1)
        self.rows, self.src = [], ""

    def refresh(self):
        return None

    def read(self, path=None):
        import redlineexcept as EX
        if path is None:
            path, _f = QFileDialog.getOpenFileName(self, "The redline", folder(self.host), "Word (*.docx)")
            if not path:
                return None
        self.rows, self.src = EX.rows(path), path
        self.table.setRowCount(len(self.rows))
        for r, row in enumerate(self.rows):
            for c, col in enumerate(EX.COLS[:7]):
                self.table.setItem(r, c, QTableWidgetItem(str(row.get(col, ""))))
        self.table.resizeRowsToContents()
        k = sum(1 for r in self.rows if r.get("Kind") == "Comment")
        self.say.setText(f"{len(self.rows) - k} tracked change(s)" + (f" and {k} comment(s)" if k else "")
                         + f" in {os.path.basename(path)}.")
        diag.activity("redline_exceptions_read", n=len(self.rows))
        return self.rows

    def export(self, ext, path=None):
        import redlineexcept as EX
        if not self.rows:
            self.host.status("Read a redline's changes first.")
            return None
        if path is None:
            stem = os.path.splitext(os.path.basename(self.src))[0].split(" - redline copy - ")[0]
            path = os.path.join(folder(self.host) or os.path.dirname(self.src),
                                f"{stem} - exceptions - {datetime.date.today().isoformat()}.{ext}")
        (EX.to_excel if ext == "xlsx" else EX.to_word)(self.rows, path)
        self.host.toast("Exceptions table written")
        return _open(path)
