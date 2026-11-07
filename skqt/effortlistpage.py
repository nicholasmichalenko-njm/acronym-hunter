"""The effort's acronym list in Qt (2.64.0): every term in the effort list workbook, scanned or not, with its definition,
status and where it was found. 3.76.0: no approval (a term is in the list or Not a term; one with no definition shows
No definition yet); Import a list... merges any Excel or CSV list; one command bar (Rule 8). Change a definition, take a
term out, and export the acronym lists (the whole effort, per volume, or both: Word and Excel).
The workbook is the same one the classic window keeps. Rules only (No AI); nothing leaves the PC."""
import os
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLineEdit,
                               QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import effortfolders as EF
import effort as E
from . import design as D
from .adaptive import FlowLayout

COLS = ["Term", "Definition", "Type", "Status", "Found in", "Notes"]
TONE = {"In the list": "ok", "Not a term": "faint", "No definition yet": "warn"}
NODEF = "No definition yet"


class EffortListPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.terms = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); outer.setSpacing(D.SPACE["m"])
        from PySide6.QtCore import Qt
        # 3.37.0: one page for the effort's list and the lists you submit (Lists to Submit folded in)
        sw = QHBoxLayout(); sw.setSpacing(D.SPACE["xs"])
        sw.addWidget(D.label("Show", "label", wrap=False))
        self.view_group = QButtonGroup(self)
        self.b_list = QPushButton("The effort's list"); self.b_submit = QPushButton("Lists to submit, by volume")
        for i, b in enumerate((self.b_list, self.b_submit)):
            b.setCheckable(True); self.view_group.addButton(b, i); sw.addWidget(b)
        self.b_list.setChecked(True)
        self.b_list.setToolTip("Every term with its definition and where it was found: what writers work from")
        self.b_submit.setToolTip("The lists that go in the submission: only the terms each volume uses, from the latest Submission check")
        self.view_group.idClicked.connect(lambda i: self.show_view("submit" if i == 1 else "list"))
        sw.addStretch(1)
        outer.addLayout(sw)
        self.views = QStackedWidget(); outer.addWidget(self.views, 1)
        self.list_view = QWidget(); self.views.addWidget(self.list_view)
        from .listspage import ListsPage
        self.submit = ListsPage(host); self.views.addWidget(self.submit)
        if self.submit.layout() is not None:
            self.submit.layout().setContentsMargins(0, 0, 0, 0)
        v = QVBoxLayout(self.list_view); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["m"])
        self.where = D.label("<b>THROUGHOUT</b> &nbsp;The effort's acronym list: acronyms, abbreviations, units and symbols with "
                             "the definitions writers work from. Lists to submit, by volume, holds only the terms your "
                             "volumes use.", "muted")
        self.where.setTextFormat(Qt.RichText); v.addWidget(self.where)                  # 2.86.0
        from .commandbar import CommandBar
        from . import effortlistextras as LX
        from . import acrimportview as IV
        self.bar = CommandBar()                                          # 3.76.0: one bar (Rule 8)
        self.bar.primary("Edit definition...", lambda: self.edit_definition(), "The selected term's definition (double-click works too)")
        self.bar.add("Import a list...", lambda: IV.import_list(self), "Any Excel or CSV list, merged into this one: new terms "
                     "come in, the same meaning fills empty fields, a second meaning is kept for review")
        self.bar.add("Not a term", lambda: self.set_status("Not a term"), "The selected terms are not terms in this effort")
        self.bar.add("Scan...", lambda: self.host.go("acronyms"), "Scan the customer's documents or your drafts")
        self.bar.more("Put back in the list", lambda: self.set_status("In the list"))
        self.bar.more("Take out of the list", lambda: self.remove())
        self.bar.more_sep()
        self.bar.more("Check first use...", lambda: self.host.go("qa"), "Submission Check: first use in the running text of your volumes")
        self.bar.more("Import a volume's list...", lambda: LX.import_volume(self), "A volume's own acronym list (Word) into this list")
        self.bar.more("Volumes...", lambda: LX.assign_volumes(self), "Name volumes and say which use the selected terms")
        self.bar.more("Activity", lambda: LX.activity(self), "What was added or changed, by whom and when")
        self.bar.more("New in the last scan", lambda: LX.new_terms(self))
        self.bar.more("Show in scan", lambda: LX.show_in_scan(self))
        self.bar.more("Open in Excel", lambda: LX.open_in_excel(self))
        self.bar.more("Reload", lambda: LX.reload(self), "Read the workbook again (after editing it in Excel)")
        self.bar.more("Add to this PC's database...", lambda: LX.to_database(self), "Usually after submission: the terms "
                      "with a definition, for every effort")
        self.scope = QComboBox()                                         # kept for export(): set by the Export menu
        for k, text in (("whole", "The whole effort"), ("volume", "One list per volume"), ("both", "Both")):
            self.scope.addItem(text, k)
        self.approved_only = QCheckBox("Only terms with a definition")
        for k, text in (("whole", "The whole effort's list..."), ("volume", "One list per volume..."), ("both", "Both...")):
            self.bar.export(text, lambda _=False, k=k: self.export(scope=k), "Word and Excel")
        self.bar.export("Choose columns and volumes...", lambda: LX.export_picker(self))
        self.bar.export("Every effort's list...", lambda: LX.export_all(self), "Every effort's acronym list in one workbook")
        v.addWidget(self.bar)
        top = FlowLayout(); top.setSpacing(D.SPACE["m"]); v.addLayout(top)
        self.pills = {k: D.Pill(f"0 {k.lower()}", TONE[k]) for k in E.STATUSES + [NODEF]}
        for p in self.pills.values():
            top.addWidget(p)
        self.p_unused = D.Pill("", "accent"); self.p_unused.hide(); top.addWidget(self.p_unused)
        top.addStretch(1)
        f = FlowLayout(); f.setSpacing(D.SPACE["s"]); v.addLayout(f)
        self.f_status = QComboBox(); self.f_status.addItems(["All statuses"] + E.STATUSES + [NODEF])
        self.f_status.currentIndexChanged.connect(lambda _i: self.fill())
        self.f_kind = QComboBox(); self.f_kind.addItem("All kinds", "")                      # 3.37.0: by kind
        for k in ("Acronym", "Abbreviation", "Unit", "Symbol"):
            self.f_kind.addItem(k + "s", k)
        self.f_kind.currentIndexChanged.connect(lambda _i: self.fill())
        self.f_use = QComboBox()                                                            # 2.86.0: in the submission or not
        self.f_use.addItems(["In the submission or not", "Used in the submission volumes", "Not used in any submission volume"])
        self.f_use.setToolTip("From the latest Submission check: terms no volume uses stay out of the lists you submit")
        self.f_use.currentIndexChanged.connect(lambda _i: self.fill())
        self.f_search = QLineEdit(); self.f_search.setPlaceholderText("Search terms and definitions"); self.f_search.setClearButtonEnabled(True)
        from . import symbols as SYM
        SYM.attach(self.f_search)
        self.f_search.setMinimumWidth(280)
        self.f_search.textChanged.connect(lambda _t: self.fill())
        f.addWidget(self.f_status); f.addWidget(self.f_kind); f.addWidget(self.f_use); f.addWidget(self.f_search, 1)
        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for i, wd in enumerate((110, 0, 110, 110, 260, 160)):
            if i != 1:
                self.table.setColumnWidth(i, wd)
        self.table.cellDoubleClicked.connect(lambda r, c: self.edit_definition() if c == 1 else None)
        v.addWidget(self.table, 1)
        self.empty = D.EmptyState("The acronym list is empty", "Add terms from the Scan tab: each one keeps its definition, "
                                                              "and where it was found here and in the effort's workbook. Import a list... brings in one you have.")
        v.addWidget(self.empty)

    @property
    def session(self):
        return self.host.acronym_page.session

    @property
    def L(self):
        s = self.session
        return s.effort if s is not None else None

    def show_view(self, which):
        """3.37.0: the effort's list, or the lists you submit (by volume)."""
        sub = which == "submit"
        self.views.setCurrentWidget(self.submit if sub else self.list_view)
        (self.b_submit if sub else self.b_list).setChecked(True)
        if sub:
            self.submit.refresh()
        else:
            self.fill()
        return sub

    def refresh(self):
        h = self.host
        if h.ws is not None and self.session is None:
            h.acronym_page.load()
        self.setEnabled(h.ws is not None)
        self.fill()
        if self.views.currentWidget() is self.submit:
            self.submit.refresh()

    def fill(self):
        L = self.L
        rows = L.rows if L is not None else {}
        st, q = self.f_status.currentText(), self.f_search.text().strip().casefold()
        kind = self.f_kind.currentData() or ""
        keep = set(self.selected())
        unused = self.unused_terms()
        use = self.f_use.currentIndex()
        self.terms = [t for t in (L.order if L is not None else []) if t in rows
                      and (st == "All statuses" or self.status_of(rows[t]) == st)
                      and (not kind or str(rows[t].get("Type", "") or "").casefold().startswith(kind.casefold()))
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
                val = self.status_of(r) if col == "Status" else str(r.get(col, "") or "")
                if col == "Found in" and not val and t not in ((self.session.results if self.session else {}) or {}):
                    val = "not found in this effort's documents yet"
                it = QTableWidgetItem(val)
                if col == "Status":
                    it.setForeground(D.color(TONE.get(val, "accent")))
                self.table.setItem(i, c, it)
            if t in keep:
                self.table.selectRow(i)
        for k, p in self.pills.items():
            n = sum(1 for r in rows.values() if (self.status_of(r) == k or (k == E.IN and r["Status"] == E.IN)))
            p.setText(f"{n} {k.lower()}")

    @staticmethod
    def status_of(r):
        """In the list, Not a term, or No definition yet (shown, not set: in the list with no definition)."""
        if r.get("Status") == E.IN and not (r.get("Definition") or "").strip():
            return NODEF
        return r.get("Status", "")

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
            from . import symbols as SYM                             # 3.50.0: with the Symbols button
            text, ok = SYM.ask_text(self, "Definition", f"Definition of {term}:", self.L.rows[term].get("Definition", ""))
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

    def export(self, folder=None, scope=None):
        s = self.session
        if s is None or s.effort is None:
            return None
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Folder for the acronym lists", self.host.out_path("acronym_lists") if self.host.effort_path else EF.out(s.effort.path))
            if not folder:
                return None
        try:
            os.makedirs(folder, exist_ok=True)
            made = s.export_effort_lists(folder=folder, scope=scope or self.scope.currentData(), approved_only=self.approved_only.isChecked())
        except PermissionError:
            self.host.status("A list with that name is open in Word or Excel. Close it, then export again.")
            return None
        self.host.toast(f"Acronym lists exported: {len(made or [])} file(s)")
        return made
