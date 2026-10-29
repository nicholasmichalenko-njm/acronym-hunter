"""Acronym scan and review in Qt (2.64.0): scan files or a folder for acronyms, abbreviations, units and symbols (typed
text and text in pictures), then review every term: its status, its definition and where it came from (customer
documents, customer list, master database), where it was found, and the effort list. Choose a definition, add to the
effort list, approve, mark as needing the author, say it is not a term, exclude it, export the report. The rules are
the classic window's own (acrsession.py); results are shared with it. Rules only (No AI); nothing leaves the PC."""
import datetime, os
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLineEdit, QPlainTextEdit, QScrollArea,
                               QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import app_gui as A
import acrsession as S
from . import design as D

COLS = ["Term", "Type", "Count", "Found in", "Status", "Definition", "Known in", "Effort list"]
KIND_TONE = {"choice": "warn", "candidate": "cust", "resolved": "ok", "error": "crit", "excluded": "head", "other": "accent"}


class ScanWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, session, paths, folder=None):
        super().__init__()
        self.session, self.paths, self.folder = session, paths, folder

    def run(self):
        try:
            rec = self.session.scan(self.paths, lambda m: (A.check_cancel(), self.progress.emit(str(m))), folder=self.folder)
            self.finished_ok.emit(rec)
        except A.ScanCancelled:
            self.failed.emit("cancelled")
        except Exception as e:
            diag.swallowed()
            self.failed.emit(type(e).__name__)


class AcronymPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.session = None
        self.worker = None
        self.terms = []
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.where = D.label("<b>START</b> &nbsp;What the customer's documents use. Add the terms to the effort list; the lists you "
                             "submit come from Submission check and Lists to submit.", "muted")
        self.where.setTextFormat(Qt.RichText); v.addWidget(self.where)                  # 2.86.0: which end this page serves
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.b_cust = D.button("Scan the customer documents", "primary", lambda: self.scan_customer(),
                               "Every customer document in the Library (the newest version of each), no picking")
        top.addWidget(self.b_cust)
        self.b_files = D.button("Scan files...", None, lambda: self.pick_files())
        self.b_folder = D.button("Scan a folder...", None, lambda: self.pick_folder())
        self.b_again = D.button("Scan again", None, lambda: self.scan_again(), "The same files again: new choices and definitions apply")
        self.b_cancel = D.button("Cancel", "danger", lambda: self.cancel()); self.b_cancel.hide()
        for b in (self.b_files, self.b_folder, self.b_again, self.b_cancel):
            top.addWidget(b)
        self.progress = D.label("", "muted", wrap=False); top.addWidget(self.progress, 1)
        top.addWidget(D.button("Customer acronym lists...", None, lambda: self.client_lists(),
                               "The customer's own acronym lists: their terms are found and their definitions come first"))
        self.p_active = D.Pill("0 terms", "accent"); self.p_choice = D.Pill("0 need a choice", "ok"); self.p_new = D.Pill("0 new", "ok")
        for p in (self.p_active, self.p_choice, self.p_new):
            top.addWidget(p)
        f = QHBoxLayout(); f.setSpacing(D.SPACE["s"]); v.addLayout(f)
        self.f_type = QComboBox(); self.f_type.addItem(A.ALL_TYPES)
        self.f_status = QComboBox(); self.f_status.addItems(A.STATUS_FILTERS)
        self.f_found = QComboBox(); self.f_found.addItems(list(A.FOUND_FILTERS))
        self.f_search = QLineEdit(); self.f_search.setPlaceholderText("Search terms and definitions"); self.f_search.setClearButtonEnabled(True)
        self.f_excl = QCheckBox("Show excluded")
        for w in (self.f_type, self.f_status, self.f_found):
            w.currentIndexChanged.connect(lambda _i: self.fill())
        self.f_search.textChanged.connect(lambda _t: self.fill())
        self.f_excl.toggled.connect(lambda _on: self.fill())
        for w in (self.f_type, self.f_status, self.f_found):
            f.addWidget(w)
        f.addWidget(self.f_search, 1); f.addWidget(self.f_excl)
        self.showing = D.label("", "muted", wrap=False); f.addWidget(self.showing)
        f.addWidget(D.button("Export the report...", None, lambda: self.export(), "Exactly the rows shown, as a CSV that opens in Excel"))
        split = QSplitter(Qt.Horizontal)
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(5, QHeaderView.Stretch)
        for i, w in enumerate((100, 130, 54, 70, 150, 0, 110, 90)):
            if i != 5:
                self.table.setColumnWidth(i, w)
        self.table.itemSelectionChanged.connect(self.show_detail)
        split.addWidget(self.table)
        self.card_area = QScrollArea(); self.card_area.setWidgetResizable(True); self.card_area.setMinimumWidth(380)
        self.card = D.Card("Term")
        self.card_area.setWidget(self.card)
        self.body = QVBoxLayout(); self.body.setSpacing(D.SPACE["s"]); self.card.body.addLayout(self.body)
        split.addWidget(self.card_area)
        split.setSizes([1000, 420])
        v.addWidget(split, 1)
        self.empty = D.EmptyState("No terms yet", "Scan the customer documents: every acronym, abbreviation, unit "
                                                  "and symbol they use, in typed text and in pictures.", "Scan the customer documents",
                                   lambda: self.scan_customer())
        v.addWidget(self.empty)

    # ------------------------------------------------------------ the effort
    def load(self):
        """Open the effort's acronym results (the classic window's last results, if any)."""
        h = self.host
        self.session = None
        if h.ws is not None:
            try:
                import app_gui
                self.session = S.AcronymSession(h.ws, h.effort_path, h.efforts, app_gui.load_settings())
                self.session.restore()
            except Exception:
                diag.swallowed()
                self.session = None
                h.status("The effort's acronym list could not be opened.")
        self.refresh()

    def refresh(self):
        h = self.host
        if self.session is not None and (h.ws is None or self.session.ws.root != h.ws.root):
            self.session = None
        if self.session is None and h.ws is not None and self.worker is None:
            self.load()
            return
        self.setEnabled(h.ws is not None)
        self.fill_types()
        self.fill()

    def fill_types(self):
        keep = self.f_type.currentText()
        types = sorted({A.base_type(d["category"]) for d in (self.session.results.values() if self.session else [])})
        self.f_type.blockSignals(True)
        self.f_type.clear(); self.f_type.addItems([A.ALL_TYPES] + types)
        self.f_type.setCurrentText(keep if keep in types else A.ALL_TYPES)
        self.f_type.blockSignals(False)

    def rows(self):
        s = self.session
        if s is None:
            return []
        ftype, fstat, ffound = self.f_type.currentText(), self.f_status.currentText(), self.f_found.currentText()
        q = self.f_search.text().strip().casefold()
        out = []
        for term, d in s.results.items():
            if d.get("excluded") and not (self.f_excl.isChecked() or fstat == "Excluded"):
                continue
            if ftype != A.ALL_TYPES and A.base_type(d["category"]) != ftype:
                continue
            if fstat != A.STATUS_FILTERS[0] and not s.status_matches(d, fstat):
                continue
            if ffound != A.FOUND_FILTERS[0] and s.found_in(d) != ffound.split()[0]:
                continue
            if q and q not in term.casefold() and q not in d.get("selected_definition", "").casefold():
                continue
            out.append(term)
        return sorted(out, key=lambda t: s.sort_key(t, s.results[t]))

    def fill(self):
        s = self.session
        keep = self.current()
        self.terms = self.rows()
        has = bool(s and s.results)
        self.empty.setVisible(not has and self.worker is None)
        self.table.setVisible(has or self.worker is not None)
        self.card_area.setVisible(has)
        self.table.setRowCount(len(self.terms))
        for i, t in enumerate(self.terms):
            d = s.results[t]
            kind = "excluded" if d.get("excluded") else A.status_kind(d.get("status", ""))
            vals = [t, d.get("category", ""), d.get("count", 0), s.found_in(d), A.status_text(d.get("status", "")),
                    d.get("selected_definition", ""), s.known_cell(t, d), d.get("effort", "")]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                if c == 4:
                    it.setForeground(D.color(KIND_TONE.get(kind, "accent")))
                if c == 0 and d.get("excluded"):
                    it.setForeground(D.color("faint"))
                self.table.setItem(i, c, it)
        n = s.counts() if s else {"active": 0, "choice": 0, "candidate": 0, "excluded": 0}
        self.p_active.setText(f"{n['active']} terms"); self.p_choice.setText(f"{n['choice']} need a choice")
        self.p_choice.set_tone("warn" if n["choice"] else "ok")
        self.p_new.setText(f"{n['candidate']} new candidates"); self.p_new.set_tone("cust" if n["candidate"] else "ok")
        self.showing.setText(f"Showing {len(self.terms)} of {len(s.results)}" if has else "")
        self.b_again.setEnabled(bool(s and s.last_scan) and self.worker is None)
        if keep in self.terms:
            self.select(keep)
        else:
            self.show_detail()

    def current(self):
        i = self.table.currentRow()
        return self.terms[i] if 0 <= i < len(self.terms) else None

    def selected_terms(self):
        rows = sorted({ix.row() for ix in self.table.selectedIndexes()})
        return [self.terms[r] for r in rows if r < len(self.terms)]

    def select(self, term):
        if term in self.terms:
            self.table.selectRow(self.terms.index(term))
            self.table.scrollToItem(self.table.item(self.terms.index(term), 0))
            return True
        return False

    # ------------------------------------------------------------ the card
    def _clear(self):
        while self.body.count():
            it = self.body.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None); w.deleteLater()
            elif it.layout() is not None:
                lay = it.layout()
                while lay.count():
                    x = lay.takeAt(0).widget()
                    if x is not None:
                        x.setParent(None); x.deleteLater()

    def show_detail(self):
        self._clear()
        s = self.session
        terms = self.selected_terms()
        if s is None or not terms:
            self.card.title.setText("Term")
            self.body.addWidget(D.label("Select a term to see its definitions, where it was found and the effort list.", "muted"))
            return
        if len(terms) > 1:
            self.card.title.setText(f"{len(terms)} terms")
            self._actions(terms)
            return
        t = terms[0]
        d = s.results[t]
        self.card.title.setText(t)
        kind = "excluded" if d.get("excluded") else A.status_kind(d.get("status", ""))
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"])
        row.addWidget(D.Pill(A.status_text(d.get("status", "")), KIND_TONE.get(kind, "accent")))
        if d.get("effort"):
            row.addWidget(D.Pill(f"Effort list: {d['effort']}", "ok" if d["effort"] == "Approved" else "accent"))
        row.addStretch(1)
        self.body.addLayout(row)
        self.body.addWidget(D.label(f"{d.get('category', '')}  |  found {d.get('count', 0)} time(s)"
                                    + (f"  |  known in: {s.known_cell(t, d)}" if s.known_cell(t, d) else ""), "muted"))
        self.body.addWidget(D.SectionTitle("Definition"))
        self.body.addWidget(D.label(d.get("selected_definition", "") or "(none)"))
        defs = [x for x in d.get("definitions", []) if x]
        if defs:
            self.body.addWidget(D.SectionTitle("Possible definitions"))
            cust = set(d.get("customer_definitions", []))
            for x in defs:
                r = QHBoxLayout(); r.setSpacing(D.SPACE["s"])
                r.addWidget(D.label(x + ("   (customer document)" if x in cust else "")), 1)
                r.addWidget(D.button("Use this", "ghost", lambda _=False, x=x: self.choose(t, x)))
                self.body.addLayout(r)
            if len(defs) > 1:
                self.body.addWidget(D.button("Keep all possibilities", "ghost", lambda: self.choose(t, "Keep All Possibilities")), 0, Qt.AlignLeft)
        self.typed = QLineEdit(); self.typed.setPlaceholderText("Type a definition to add with it")
        self.body.addWidget(D.SectionTitle("Effort list"))
        self.body.addWidget(self.typed)
        self._actions([t])
        locs = d.get("locations", [])
        if locs:
            self.body.addWidget(D.SectionTitle(f"Where it was found ({len(locs)})"))
            box = QPlainTextEdit("\n".join(locs[:200]) + (f"\n... and {len(locs) - 200} more" if len(locs) > 200 else ""))
            box.setReadOnly(True); box.setMinimumHeight(140)
            self.body.addWidget(box)
        self.body.addStretch(1)

    def _actions(self, terms):
        r1 = QHBoxLayout(); r1.setSpacing(D.SPACE["s"])
        r1.addWidget(D.button("Add to effort list", "primary", lambda: self.add(terms)))
        r1.addWidget(D.button("Approve...", None, lambda: self.approve(terms)))
        r1.addWidget(D.button("Needs author", None, lambda: self.set_status(terms, "Needs author")))
        self.body.addLayout(r1)
        r2 = QHBoxLayout(); r2.setSpacing(D.SPACE["s"])
        r2.addWidget(D.button("Not a term", "danger", lambda: self.set_status(terms, "Rejected"), "Rejected in the effort list: hidden in this effort"))
        excl = all(self.session.results[t].get("excluded") for t in terms)
        r2.addWidget(D.button("Include" if excl else "Exclude", "ghost", lambda: self.exclude(terms, not excl)))
        r2.addStretch(1)
        self.body.addLayout(r2)

    # ------------------------------------------------------------ decisions
    def choose(self, term, choice):
        self.session.choose(term, choice)
        diag.activity("qt_acronym_choice")
        self.fill()
        return self.session.results[term]["status"]

    def add(self, terms, definition=None):
        typed = definition if definition is not None else (self.typed.text().strip() if len(terms) == 1 and hasattr(self, "typed") else "")
        msg = self.session.add(terms, typed)
        diag.activity("qt_acronym_added", n=len(terms))
        self.host.toast(msg or "Added to the effort list")
        self.fill()
        return msg

    def approve(self, terms, approver=None):
        if approver is None:
            from PySide6.QtWidgets import QInputDialog
            approver, ok = QInputDialog.getText(self, "Approve", "SS Approver (one name, or several separated by ;):",
                                                QLineEdit.Normal, getattr(self.session, "_last_approver", ""))
            if not ok:
                return 0
        self.session._last_approver = approver
        return self.set_status(terms, "Approved", approver)

    def set_status(self, terms, status, approver=""):
        n = self.session.set_status(terms, status, approver)
        self.host.toast(f"Effort list: {n} {status.lower()}" + ("" if not self.session.effort.pending else ". NOT SAVED yet: close the list in Excel."))
        self.fill()
        return n

    def exclude(self, terms, on=True):
        n = self.session.exclude(terms, on)
        diag.activity("qt_acronym_excluded", n=n)
        self.fill()
        return n

    # ------------------------------------------------------------ the scan
    def pick_files(self):
        exts = " ".join("*" + e for e in sorted(A.SUPPORTED_EXTS))
        paths, _ = QFileDialog.getOpenFileNames(self, "Scan files", "", f"Documents and pictures ({exts})")
        if paths:
            self.scan(paths)

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Scan a folder")
        if folder:
            self.scan(self.folder_files(folder), folder)

    def customer_paths(self):
        """2.86.0: the newest version of every customer document in the Library that is on this PC."""
        if self.host.ws is None:
            return []
        import docversions as DV
        lib = DV.Library(self.host.ws.p("documents")).load()
        out = []
        for d in lib.docs:
            v = lib.latest(d)
            p = lib.path_of(v) if v else ""
            if p and os.path.isfile(p) and os.path.splitext(p)[1].lower() in A.SUPPORTED_EXTS:
                out.append(p)
        return out

    def scan_customer(self):
        paths = self.customer_paths()
        if not paths:
            self.host.status("No customer documents on this PC yet: add them in Library.")
            return None
        diag.activity("customer_terms_scan", files=len(paths))
        return self.scan(paths)

    @staticmethod
    def folder_files(folder):
        return [os.path.join(r, f) for r, _, fs in os.walk(folder) for f in fs
                if not f.startswith("~$") and os.path.splitext(f)[1].lower() in A.SUPPORTED_EXTS]

    def scan_again(self):
        s = self.session
        last = (s.last_scan or {}) if s else {}
        folder = last.get("folder")
        paths = self.folder_files(folder) if folder and os.path.isdir(folder) else [p for p in last.get("paths", []) if os.path.isfile(p)]
        if not paths:
            self.host.status("The files from the last scan are no longer there.")
            return None
        return self.scan(paths, folder)

    def scan(self, paths, folder=None):
        if self.session is None or self.worker is not None or not paths:
            return None
        diag.activity("qt_scan_started", files=len(paths))
        self.worker = ScanWorker(self.session, list(paths), folder)
        self.worker.progress.connect(self.progress.setText)
        self.worker.finished_ok.connect(self.scan_done)
        self.worker.failed.connect(self.scan_failed)
        for b in (self.b_files, self.b_folder, self.b_again, self.b_cust):
            b.setEnabled(False)
        self.b_cancel.show()
        self.worker.start()
        return self.worker

    def cancel(self):
        A.CANCEL.set()
        self.progress.setText("Stopping after the current page...")

    def _end(self):
        if self.worker is not None:
            self.worker.wait(2000)
        self.worker = None
        for b in (self.b_files, self.b_folder, self.b_cust):
            b.setEnabled(True)
        self.b_cancel.hide()

    def scan_done(self, rec):
        self._end()
        self.progress.setText("")
        self.fill_types()
        self.fill()
        n = self.session.counts()
        msg = f"Scan done: {n['active']} terms, {n['choice']} need a choice, {n['candidate']} new candidates"
        if rec:
            msg += f". Effort list: {rec['found']} found again, {rec['new']} new, {rec['gone']} no longer found"
        self.host.toast(msg)
        return rec

    def scan_failed(self, why):
        self._end()
        self.progress.setText("")
        self.host.status("Scan stopped." if why == "cancelled" else f"The scan failed ({why}). Details are in the logs (no file names or content).")
        self.fill()

    # ------------------------------------------------------------ export
    def export(self, path=None):
        s = self.session
        if s is None:
            return None
        terms = list(self.terms)
        if self.f_status.currentText() != "Found in omit list":
            terms = [t for t in terms if not s.results[t].get("known")]
        if not terms:
            self.host.status("No rows are showing. Change the filters, then export.")
            return None
        if path is None:
            name = f"{self.host.effort_name}_Acronym_Report_{datetime.date.today().isoformat()}.csv".replace(" ", "_")
            path, _ = QFileDialog.getSaveFileName(self, "Export the acronym report", os.path.join(os.path.dirname(self.host.effort_path), name),
                                                  "CSV report (*.csv)")
            if not path:
                return None
        try:
            n = A.write_acronym_report(path, terms, s.results, s.known_cell)
        except PermissionError:
            self.host.status("That file is open in Excel. Close it, then export again.")
            return None
        diag.activity("qt_acronym_report", n=n)
        self.host.toast(f"{n} rows exported")
        return path


# ---------------------------------------------------------------- the customer's acronym lists (2.67.0)
def _client_lists(self, add_paths=None, paste=None, remove=None, run=True):
    """The customer's acronym lists for this effort. add_paths, paste (name, text), remove (index) act at once (tests)."""
    import datetime as DT
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QInputDialog, QListWidget
    s = self.session
    if s is None:
        return None
    lists = list(s.client_lists)

    def stamp():
        return DT.datetime.now().strftime("%Y-%m-%d %H:%M")

    def save(note):
        s.set_client_lists(lists)
        s.ws.set("client_lists", lists)
        diag.activity("client_lists_changed", n=len(lists))
        self.host.toast(note + (". Scan again to apply them." if s.results else ""))

    def add_files(paths):
        got = []
        for p in paths:
            try:
                rows = A.parse_client_list(p)
            except Exception:
                A.log_error("Client list could not be read", ext=os.path.splitext(p)[1].lower())
                rows = []
            if rows:
                lists.append({"name": os.path.basename(p), "rows": [list(r) for r in rows], "added": stamp()})
                got.append(f"{os.path.basename(p)} ({len(rows)})")
        if got:
            save("Added: " + ", ".join(got))
        else:
            self.host.status("No acronym and definition pairs were found. Lists work best as two columns: acronym, definition.")
        return got

    def add_text(name, text):
        rows = A.parse_client_text(text)
        if rows:
            lists.append({"name": name or f"Pasted list {stamp()}", "rows": rows, "added": stamp()})
            save(f"Added: {lists[-1]['name']} ({len(rows)})")
        return rows
    if add_paths is not None:
        return add_files(add_paths)
    if paste is not None:
        return add_text(*paste)
    if remove is not None:
        gone = lists.pop(remove)
        save(f"Removed {gone['name']}")
        return gone
    dlg = QDialog(self); dlg.setWindowTitle("Customer acronym lists"); dlg.setMinimumSize(680, 460)
    v = QVBoxLayout(dlg)
    v.addWidget(D.label("Acronym lists from the customer (an RFP's acronym list, for example). Their terms are found in your documents "
                        "even when the database does not hold them, and the customer's definition comes first. Kept with this effort.", "muted"))
    lw = QListWidget(); v.addWidget(lw, 1)

    def fill():
        lw.clear()
        for x in lists:
            lw.addItem(f"{x['name']}   ({len(x['rows'])} acronyms, added {x.get('added', '')})")
    fill()
    row = QHBoxLayout()

    def do_add():
        exts = " ".join("*" + e for e in sorted(A.CLIENT_IMAGE_EXTS))
        paths, _ = QFileDialog.getOpenFileNames(dlg, "Add customer acronym list(s)", "",
                                                f"Acronym lists (*.csv *.tsv *.txt *.xlsx *.docx *.pdf);;Pictures of a list ({exts})")
        if paths:
            add_files(paths); fill()

    def do_paste():
        text, ok = QInputDialog.getMultiLineText(dlg, "Paste or type the customer's terms",
                                                 "One per line: ACR - definition, ACR: definition, or rows copied from Excel or Word:")
        if ok and text.strip():
            add_text("", text); fill()

    def do_view():
        i = lw.currentRow()
        if i >= 0:
            QInputDialog.getMultiLineText(dlg, lists[i]["name"], "Terms:", "\n".join(f"{t}\t{d}" for t, d in lists[i]["rows"]))

    def do_remove():
        i = lw.currentRow()
        if i >= 0:
            gone = lists.pop(i); save(f"Removed {gone['name']}"); fill()
    for text, kind, fn in (("Add list...", "primary", do_add), ("Paste or type...", None, do_paste), ("View terms", None, do_view),
                           ("Remove", "danger", do_remove)):
        row.addWidget(D.button(text, kind, fn))
    row.addStretch(1)
    v.addLayout(row)
    bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(dlg.reject); v.addWidget(bb)
    if run:
        dlg.exec()
    return dlg


AcronymPage.client_lists = _client_lists
