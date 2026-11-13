"""Redline (4.8.0; claude/stationkeeper-redline-plan-4.6.md, step 4; claude/stationkeeper-redline-decisions-2026-11-10.md).
A menu item of its own below the six steps, with no number: redlining happens at any point (the draft RFP, Q&A, the
final RFP's terms, amendments, a model contract). Authors redline in Word with Track Changes; the app does what Word
does badly. Three tabs, each with one main button:
- Prepare (4.22.0, Prepare for redline): every PDF and picture in Documents, one row each with its state and one
  Prepare button (redlineprep): a Word file that reads like the PDF, with a reviewer's comments placed as tracked
  changes and Word comments. Put its comments into my Word file... does the same into a copy of a Word file you have.
  Right-click a row for the other layout, a copy without the comments, and where the file is.
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
    """4.22.0: Prepare for redline. Every PDF and picture in Documents is a row, with one Prepare button on it."""
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("page")
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); v.addLayout(top)
        self.say = D.label("", "muted"); top.addWidget(self.say, 1)
        self.bar = CommandBar()
        self.bar.add("Put its comments into my Word file...", lambda: self.into_word(), "You already have the Word file "
                     "of the selected PDF: its comments go into a dated copy of your file, as tracked changes and Word "
                     "comments. Your file is not changed.")
        top.addWidget(self.bar)
        self.table = _table(["Document", "File", "State", ""])
        self.table.setColumnWidth(0, 250); self.table.setColumnWidth(1, 280); self.table.setColumnWidth(2, 330)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(lambda pos: self.row_menu(self.table.rowAt(pos.y()), self.table.viewport().mapToGlobal(pos)))
        v.addWidget(self.table, 1)
        self.empty = D.EmptyState("Nothing is marked Redlined Deliverable", "In Documents, right-click a PDF or a picture the "
                                  "customer wants back redlined: Used for > Redlined Deliverable. It gets a tile on "
                                  "Deliverables and is listed here, ready to become a Word file.", "Go to Documents",
                                  lambda: self.host.go("library"))
        v.addWidget(self.empty); self.empty.hide()
        self.rows = []

    def _folders(self):
        return folder(self.host), (self.host.ws.p("page copies") if self.host.ws is not None else "")

    def refresh(self, select=None):
        import redlineprep as RP
        if self.host.ws is None:
            self.rows = []
        else:
            import docversions as DV
            self.rows = RP.sources(DV.Library(self.host.ws.p("documents")).load())
        f = folder(self.host)
        keep = self.table.currentRow()
        self.table.setRowCount(len(self.rows))
        done = 0
        for r, (did, name, p, _k) in enumerate(self.rows):
            st = RP.state(f, p)
            done += bool(st["copy"])
            for c, val in enumerate((name, os.path.basename(p), RP.said(st))):
                it = QTableWidgetItem(val); it.setData(Qt.UserRole, did); self.table.setItem(r, c, it)
            b = D.button("Prepare again" if st["copy"] else "Prepare", None if st["copy"] else "primary",
                         lambda _=False, r=r: self.prepare(r), "A Word file of this document that reads like it: its pictures, "
                         "headers and footers, fonts and tables, as text that flows. A reviewer's comments on the PDF come in "
                         "where they were made, as tracked changes and Word comments.")
            self.table.setCellWidget(r, 3, b)
            if did == select:
                self.table.selectRow(r)
        if self.rows and select is None:
            self.table.selectRow(keep if 0 <= keep < len(self.rows) else 0)
        self.table.setVisible(bool(self.rows)); self.empty.setVisible(not self.rows); self.bar.setVisible(bool(self.rows))
        self.say.setText(f"{len(self.rows)} document(s) marked Redlined Deliverable, {done} prepared. Prepared files go to "
                         "the effort's Redlines folder." if self.rows else "")

    def select(self, doc_id):
        self.refresh(select=doc_id)
        return any(r[0] == doc_id for r in self.rows)

    def _row(self, r=None):
        r = self.table.currentRow() if r is None else r
        if not (0 <= r < len(self.rows)):
            self.host.status("Pick a document first.")
            return None
        return self.rows[r]

    def row_menu(self, r, pos=None, pick=None):
        """Right-click on a row: the other layout, a copy without the comments, where the prepared file is."""
        import redlineprep as RP
        row = self._row(r)
        if row is None:
            return None
        from PySide6.QtWidgets import QMenu
        st = RP.state(folder(self.host), row[2])
        acts = [("Prepare it anyway (pages still to look at)", lambda: self.prepare(r, anyway=True)),
                ("Prepare it as slides", lambda: self.prepare(r, layout="slides")),
                ("Prepare it as a document", lambda: self.prepare(r, layout="document")),
                ("Prepare it without the comments", lambda: self.prepare(r, comments=False))]
        if st["copy"]:
            acts += [("Open the prepared file", lambda: _open(st["copy"])),
                     ("Show it in its folder", lambda: _open(os.path.dirname(st["copy"])))]
        if pick is not None:
            return dict(acts)[pick]()
        m = QMenu(self)
        for text, fn in acts:
            m.addAction(text, fn)
        m.exec(pos)
        return None

    def to_look_at(self, path):
        """Pages of the document the text check still wants looked at (0 when none, or not known)."""
        try:
            import verifystate as VS
            h = self.host
            pdf = h.verify_page.pdf_of(path, make=False)
            return VS.counts(pdf, VS.Store(h.ws.root), os.path.basename(path))["look"] if pdf else 0
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return 0

    def prepare(self, r=None, layout=None, comments=True, path=None, anyway=False):
        """Prepare a row's document (or a file given by path). Returns the prepared file's path, or None. 4.25.3
        (answer 2): the text check stops only a redline. A document with pages still to look at is not prepared until
        they are looked at, because the Word file is made from that reading; anyway=True (the row's right-click)
        prepares it as read."""
        import redlineprep as RP
        if path is None:
            row = self._row(r)
            if row is None:
                return None
            path = row[2]
            look = 0 if anyway else self.to_look_at(path)
            if look:
                self.host.status(f"{row[1]} has {look} page(s) to look at first: the Word file is made from that reading. "
                                 "Look at them in Shred (Fix text), or right-click the row: Prepare it anyway.")
                return None
        elif not self.rows and self.host.ws is not None:
            self.refresh()
        f, cf = self._folders()
        if r is None and path is not None and not any(path == x[2] for x in self.rows):
            f, cf = os.path.dirname(path), ""               # a file outside the effort (Quick tools): beside the file
        f = f or os.path.dirname(path)
        try:
            if RP.kind(path) == "picture" or RP.page_form(path, cf, make=False) == "":
                self.host.status("Reading the words on its pages first...")
            res = RP.prepare(path, f, cf, layout=layout, comments=comments)
        except ValueError as e:
            self.host.status(str(e) + " Read its pages in Shred first.")
            return None
        except PermissionError:
            self.host.status("The prepared file is open in Word: close it, then prepare it again.")
            return None
        self.host.toast(f"Prepared: {res['slides']} slide(s), {res['paragraphs']} paragraphs" if res.get("slides") else
                        f"Prepared: {res['paragraphs']} paragraphs, {res['headings']} headings"
                        + (f", {res['tables']} table(s)" if res.get("tables") else "")
                        + (f", {res['pictures']} picture(s)" if res.get("pictures") else "") + said_comments(res))
        diag.activity("redline_copy_made", n=res["paragraphs"])
        self.refresh()
        return res["path"]

    def make(self, other=False, pdf=None, layout=None, comments=True):
        """As before 4.22.0 (Documents' menu and the tools call it): prepare the selected row, or a PDF by path."""
        return self.prepare(layout=layout, comments=comments, path=pdf)

    def into_word(self, docx=None, r=None):
        """The selected PDF's comments into a dated copy of a Word file the person has. Returns the result, or None."""
        import redlineprep as RP
        row = self._row(r)
        if row is None:
            return None
        if docx is None:
            docx, _f = QFileDialog.getOpenFileName(self, f"Your Word file of {row[1]}", "", "Word (*.docx)")
            if not docx:
                return None
        f, cf = self._folders()
        try:
            res = RP.into_word(row[2], docx, f or os.path.dirname(docx), cf)
        except ValueError as e:
            self.host.status(str(e))
            return None
        except PermissionError:
            self.host.status("Today's copy of that Word file is open in Word: close it, then try again.")
            return None
        if not res["comments"]:
            self.host.status("This PDF has no comments to put into a Word file.")
            return res
        pdf_w, got = res["words"]
        self.host.toast(f"{len(res['comments'])} comment(s) put into a copy of {os.path.basename(docx)}: {res['changes']} tracked "
                        f"change(s), {res['word_comments']} Word comment(s)"
                        + (f"; {res['nearby']} placed by position (Check lists them)" if res["nearby"] else "")
                        + (f". The Word file does not hold {pdf_w - got} of the PDF's {pdf_w} words: look at Check."
                           if pdf_w and got < 0.98 * pdf_w else ""))
        diag.activity("redline_comments_into_word", n=len(res["comments"]))
        self.refresh()
        return res


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
        """The PDF a prepared file is checked against: its document's PDF, or the page copy a picture was read from."""
        import redlinecopy as RC
        import redlineprep as RP
        side = RC.sidecar(copy) or {}
        name = side.get("source", "")
        if self.host.ws is not None and name:
            import docversions as DV
            for _d, _n, p, _k in RP.sources(DV.Library(self.host.ws.p("documents")).load()):
                if os.path.basename(p) == name:
                    return RP.page_form(p, self.host.ws.p("page copies"), make=False)
        cand = os.path.join(os.path.dirname(copy), name)
        return cand if name and os.path.isfile(cand) else ""

    def fill(self, rows, aside=(), comments=(), pictures=()):
        """The differences, then the lines set aside, then (4.22.0) a picture's own words, then (4.16.0) each comment from the PDF: what it became, the
        words it is on in the copy, its note, its page, the heading above."""
        notes = [{"kind": f"PDF {c['kind']}, {HOW.get(c['how'], c['how'])}", "was": c.get("in_copy") or c.get("marked", ""),
                  "now": f"{c.get('became', '')}: {c.get('note', '')} ({c.get('author', '')})".strip(), "page": c.get("page"),
                  "heading": c.get("heading", "")} for c in comments]
        self.found = list(rows) + [{"page": pg} for pg, _t in aside] + [{"page": pg} for pg, _t in pictures] + notes
        allrows = [(x["kind"], x["was"], x["now"], str(x["page"] or ""), x["heading"]) for x in rows] + \
                  [("Set aside on purpose", t, "", str(pg), "") for pg, t in aside] + \
                  [("In a picture", t, "kept in the picture, not as text", str(pg), "") for pg, t in pictures] + \
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
            self.host.status("Prepare a document first.")
            return None
        pdf = self._source_of(copy)
        if not pdf:
            self.host.status("The copy's PDF is not here, so it cannot be checked.")
            return None
        res = CK.faithful(pdf, copy)
        self.source = pdf
        cms = res.get("comments") or []
        pics = res.get("in_pictures") or []
        self.fill(res["differences"], res["set_aside"], cms, pics)
        n = len(res["differences"])
        self.say.setText((f"{n} difference(s) between the copy and its PDF." if n else "The copy holds every word of its PDF, in order.")
                         + (f" {len(res['set_aside'])} line(s) set aside on purpose in Fix text." if res["set_aside"] else "")
                         + (f" {res['tables']} table(s) were made as Word tables from where the PDF's columns sit: look at "
                            "each beside the PDF (a cell that wrapped, a merged cell)." if res["tables"] else "")
                         + (f" {len(pics)} line(s) are a picture's own words and stay in the picture." if pics else "")
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
