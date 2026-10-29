"""The effort's acronym list in Qt (2.64.0): every term in the effort list workbook, scanned or not, with its definition,
status, approver and where it was found. Approve (with the approver), Needs author, Proposed, Not a term, change a
definition, take a term out, and export the acronym lists (the whole effort, per volume, or both: Word and Excel).
The workbook is the same one the classic window keeps. Rules only (No AI); nothing leaves the PC."""
import os
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLineEdit,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import effort as E
from . import design as D

COLS = ["Term", "Definition", "Type", "Status", "SS Approver", "Approved on", "Found in", "Notes"]
TONE = {"Approved": "ok", "Needs author": "warn", "Proposed": "accent", "Rejected": "faint"}


class EffortListPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.terms = []
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        from PySide6.QtCore import Qt
        self.where = D.label("<b>THROUGHOUT</b> &nbsp;The effort's glossary: approved definitions writers work from. It is not the "
                             "list you submit: Lists to submit holds only the terms your volumes use.", "muted")
        self.where.setTextFormat(Qt.RichText); v.addWidget(self.where)                  # 2.86.0
        top = QHBoxLayout(); top.setSpacing(D.SPACE["m"]); v.addLayout(top)
        self.pills = {k: D.Pill(f"0 {k.lower()}", TONE[k]) for k in E.STATUSES}
        for p in self.pills.values():
            top.addWidget(p)
        top.addStretch(1)
        top.addWidget(D.label("Export", "label", wrap=False))
        self.scope = QComboBox()
        for k, text in (("whole", "The whole effort"), ("volume", "One list per volume"), ("both", "Both")):
            self.scope.addItem(text, k)
        top.addWidget(self.scope)
        self.approved_only = QCheckBox("Approved only"); top.addWidget(self.approved_only)
        top.addWidget(D.button("Export the effort list...", None, lambda: self.export(),
                               "The glossary in Word and Excel. The lists for your volumes are in Lists to submit."))
        f = QHBoxLayout(); f.setSpacing(D.SPACE["s"]); v.addLayout(f)
        self.f_status = QComboBox(); self.f_status.addItems(["All statuses"] + E.STATUSES)
        self.f_status.currentIndexChanged.connect(lambda _i: self.fill())
        self.f_use = QComboBox()                                                            # 2.86.0: in the submission or not
        self.f_use.addItems(["In the submission or not", "Used in the submission volumes", "Not used in any submission volume"])
        self.f_use.setToolTip("From the latest Submission check: terms no volume uses stay out of the lists you submit")
        self.f_use.currentIndexChanged.connect(lambda _i: self.fill())
        self.f_search = QLineEdit(); self.f_search.setPlaceholderText("Search terms and definitions"); self.f_search.setClearButtonEnabled(True)
        self.f_search.textChanged.connect(lambda _t: self.fill())
        f.addWidget(self.f_status); f.addWidget(self.f_use); f.addWidget(self.f_search, 1)
        self.p_unused = D.Pill("", "accent"); self.p_unused.hide(); top.insertWidget(len(E.STATUSES), self.p_unused)
        for text, kind, fn in (("Approve...", "primary", lambda: self.approve()), ("Needs author", None, lambda: self.set_status("Needs author")),
                               ("Proposed", None, lambda: self.set_status("Proposed")), ("Not a term", "danger", lambda: self.set_status("Rejected")),
                               ("Edit definition...", None, lambda: self.edit_definition()), ("Take out", "ghost", lambda: self.remove())):
            f.addWidget(D.button(text, kind, fn))
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for i, wd in enumerate((110, 0, 110, 110, 120, 100, 260, 160)):
            if i != 1:
                self.table.setColumnWidth(i, wd)
        self.table.cellDoubleClicked.connect(lambda r, c: self.edit_definition() if c == 1 else None)
        v.addWidget(self.table, 1)
        self.empty = D.EmptyState("The effort list is empty", "Add terms from Scan and review: each one keeps its definition, "
                                                              "status and approver here and in the effort's workbook.")
        v.addWidget(self.empty)

    @property
    def session(self):
        return self.host.acronym_page.session

    @property
    def L(self):
        s = self.session
        return s.effort if s is not None else None

    def refresh(self):
        h = self.host
        if h.ws is not None and self.session is None:
            h.acronym_page.load()
        self.setEnabled(h.ws is not None)
        self.fill()

    def fill(self):
        L = self.L
        rows = L.rows if L is not None else {}
        st, q = self.f_status.currentText(), self.f_search.text().strip().casefold()
        keep = set(self.selected())
        unused = self.unused_terms()
        use = self.f_use.currentIndex()
        self.terms = [t for t in (L.order if L is not None else []) if t in rows
                      and (st == "All statuses" or rows[t]["Status"] == st)
                      and (use == 0 or unused is None or ((t in unused) == (use == 2)))
                      and (not q or q in t.casefold() or q in rows[t].get("Definition", "").casefold())]
        if unused is None:
            self.p_unused.hide()
        else:
            self.p_unused.setText(f"{len(unused)} not used in the submission"); self.p_unused.show()
        self.terms.sort(key=str.casefold)
        self.empty.setVisible(not rows); self.table.setVisible(bool(rows))
        self.table.setRowCount(len(self.terms))
        for i, t in enumerate(self.terms):
            r = rows[t]
            for c, col in enumerate(COLS):
                it = QTableWidgetItem(str(r.get(col, "") or ""))
                if col == "Status":
                    it.setForeground(D.color(TONE.get(r["Status"], "accent")))
                self.table.setItem(i, c, it)
            if t in keep:
                self.table.selectRow(i)
        for k, p in self.pills.items():
            n = sum(1 for r in rows.values() if r["Status"] == k)
            p.setText(f"{n} {k.lower()}")

    def unused_terms(self):
        """2.86.0: effort-list terms no submission volume uses (the latest check), or None before any check."""
        s = self.session
        r = s.volume_report if s is not None else None
        if not r:
            return None
        return {x["term"] for x in r.get("unused", [])}

    def selected(self):
        rows = sorted({ix.row() for ix in self.table.selectedIndexes()})
        return [self.terms[r] for r in rows if r < len(self.terms)]

    def select(self, terms):
        self.table.clearSelection()
        for t in terms:
            if t in self.terms:
                self.table.selectRow(self.terms.index(t))

    # ------------------------------------------------------------ decisions
    def approve(self, approver=None, terms=None):
        terms = terms or self.selected()
        if not terms:
            return 0
        s = self.session
        if approver is None:
            approver, ok = QInputDialog.getText(self, "Approve", "SS Approver (one name, or several separated by ;):",
                                                QLineEdit.Normal, getattr(s, "_last_approver", ""))
            if not ok:
                return 0
        s._last_approver = approver
        return self.set_status("Approved", terms, approver)

    def set_status(self, status, terms=None, approver=""):
        terms = terms or self.selected()
        if not terms:
            return 0
        n = self.session.list_status(terms, status, approver)
        self.host.toast(f"{n} set to {status.lower()}" + ("" if not self.L.pending else ". NOT SAVED yet: close the list in Excel."))
        self.fill()
        return n

    def edit_definition(self, text=None, term=None):
        term = term or (self.selected() or [None])[0]
        if term is None:
            return False
        if text is None:
            text, ok = QInputDialog.getText(self, "Definition", f"Definition of {term}:", QLineEdit.Normal,
                                            self.L.rows[term].get("Definition", ""))
            if not ok:
                return False
        ok = self.session.list_definition(term, text)
        diag.activity("qt_effort_definition_set")
        self.fill()
        return ok

    def remove(self, terms=None):
        terms = terms or self.selected()
        if not terms:
            return 0
        n = self.session.list_remove(terms)
        self.host.toast(f"{n} taken out of the effort list")
        self.fill()
        return n

    def export(self, folder=None):
        s = self.session
        if s is None or s.effort is None:
            return None
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Folder for the acronym lists", os.path.dirname(s.effort.path))
            if not folder:
                return None
        try:
            os.makedirs(folder, exist_ok=True)
            made = s.export_effort_lists(folder=folder, scope=self.scope.currentData(), approved_only=self.approved_only.isChecked())
        except PermissionError:
            self.host.status("A list with that name is open in Word or Excel. Close it, then export again.")
            return None
        self.host.toast(f"Acronym lists exported: {len(made or [])} file(s)")
        return made
