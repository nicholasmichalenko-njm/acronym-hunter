"""Matrix > Assign (4.66.0; Nicholas 2026-11-24). The one place a kept requirement or evaluation criterion is linked
to the section of the outline that answers it. On the left the pieces (Not assigned, All, or the ones in the section
picked); on the right the outline with how many each section holds. Pick pieces, pick a section, Assign to section.
Also in this section keeps a piece where it is and adds it here; Take out removes it; Take the suggestions places
every piece that has a suggested section. Nothing else is decided here: what a piece is comes from Shred, the sections
from Outline. The same links as Place on the customer's page (More), the matrix and the setup. The logic is
assignlinks; this is its page. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLineEdit, QSplitter, QTableWidget,
                               QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

import assignlinks as AL
import diag
from . import design as D
from .commandbar import CommandBar

SHOWS = (("unplaced", "Not assigned"), ("all", "All"), ("section", "In the section picked"))


class AssignView(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.data = []
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        self.bar = CommandBar()
        self.b_assign = self.bar.primary("Assign to section", lambda: self.assign(), "The pieces picked go to the section picked")
        self.b_sug = self.bar.add("Take the suggestions", lambda: self.take_suggestions(),
                                  "Every piece not assigned that has a suggested section goes to it (the pieces picked, when some are)")
        self.b_also = self.bar.add("Also in this section", lambda: self.also(), "The pieces picked stay where they are and are in the section picked too")
        self.b_out = self.bar.add("Take out", lambda: self.take_out(), "The pieces picked leave the section picked, or every section when none is picked")
        self.bar.more("Place on the customer's page...", lambda: self.host.go("place"), "The customer's page with the outline beside it")
        v.addWidget(self.bar)
        self.none = D.EmptyState("Nothing to assign yet", "Assign links each requirement kept in Shred to a section of the outline. Keep some in "
                                 "Shred first.", "Open Shred", lambda: self.host.go("assign"))
        v.addWidget(self.none, 1)
        self.body = QSplitter(Qt.Horizontal); v.addWidget(self.body, 1)
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0); lv.setSpacing(D.SPACE["s"])
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"]); lv.addLayout(row)
        self.show_box = QComboBox()
        for k, n in SHOWS:
            self.show_box.addItem(n, k)
        self.show_box.currentIndexChanged.connect(lambda _i: self.fill())
        row.addWidget(self.show_box)
        self.kind_box = QComboBox(); self.kind_box.addItem("Requirements and criteria", "")
        for k in AL.KINDS:
            self.kind_box.addItem(AL.NAMES[k] + ("s" if k == "Requirement" else ""), k)
        self.kind_box.setItemText(2, "Evaluation criteria")
        self.kind_box.currentIndexChanged.connect(lambda _i: self.fill())
        row.addWidget(self.kind_box)
        self.find = QLineEdit(); self.find.setPlaceholderText("Find"); self.find.setClearButtonEnabled(True)
        self.find.textChanged.connect(lambda _t: self.fill())
        row.addWidget(self.find, 1)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["From", "The customer's words", "Section", "Suggested"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)
        h = self.table.horizontalHeader(); h.setStretchLastSection(False)
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents); h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.Interactive); h.setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 170); self.table.setColumnWidth(3, 170)
        self.table.itemSelectionChanged.connect(self.enable)
        lv.addWidget(self.table, 1)
        self.said = D.label("", "muted"); lv.addWidget(self.said)
        self.body.addWidget(left)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Outline", "Pieces"]); self.tree.setRootIsDecorated(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch); self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setStretchLastSection(False)
        self.tree.itemSelectionChanged.connect(self.section_picked)
        self.tree.itemDoubleClicked.connect(lambda _it, _c: self.assign())
        self.tree.setToolTip("Pick a section, then Assign to section. Double-click assigns the pieces picked.")
        self.body.addWidget(self.tree)
        self.body.setStretchFactor(0, 3); self.body.setStretchFactor(1, 1); self.body.setSizes([880, 360])

    # ------------------------------------------------------------------ state
    def _M(self):
        r = getattr(self.host, "review", None)
        return r.M if r is not None else None

    def section(self):
        it = self.tree.currentItem()
        return it.data(0, Qt.UserRole) if it is not None else ""

    def picked(self):
        return [self.data[i.row()]["id"] for i in self.table.selectionModel().selectedRows() if i.row() < len(self.data)]

    # ------------------------------------------------------------------ filling
    def refresh(self):
        M = self._M()
        has = M is not None and bool(M.outline) and bool(AL.pieces(M))
        self.none.setVisible(not has); self.body.setVisible(has); self.bar.setVisible(has)
        if not has:
            self.data = []
            return 0
        keep = self.section()
        per, un, n = AL.counts(M)
        self.tree.blockSignals(True)
        self.tree.clear()
        import compliance as C
        base = min((o.get("level", 1) for o in M.outline), default=1)
        for o in M.outline:
            lab = C.outline_label(o)
            it = QTreeWidgetItem(["    " * max(0, o.get("level", 1) - base) + lab, str(per.get(lab, "") or "")])
            it.setData(0, Qt.UserRole, lab); it.setToolTip(0, lab)
            it.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            self.tree.addTopLevelItem(it)
            if lab == keep:
                self.tree.setCurrentItem(it)
        self.tree.blockSignals(False)
        self.total = (un, n)
        return self.fill()

    def fill(self):
        M = self._M()
        if M is None:
            return 0
        show = self.show_box.currentData()
        sec = self.section()
        self.data = AL.rows(M, sec if show == "section" else show, self.kind_box.currentData() or "", self.find.text()) \
            if not (show == "section" and not sec) else []
        t = self.table
        t.blockSignals(True)
        t.setRowCount(len(self.data))
        for r, d in enumerate(self.data):
            for c, text in enumerate((d["ref"], " ".join(d["text"].split()), "; ".join(d["sections"]), d["suggested"])):
                it = QTableWidgetItem(text); it.setToolTip(d["text"] if c == 1 else text)
                t.setItem(r, c, it)
        t.blockSignals(False)
        t.clearSelection()
        un, n = getattr(self, "total", (0, 0))
        self.said.setText((f"{un} of {n} not assigned." if un else f"All {n} assigned.") +
                          ("  Pick a section on the right to see what is in it." if show == "section" and not sec else ""))
        self.enable()
        return len(self.data)

    def section_picked(self):
        if self.show_box.currentData() == "section":
            self.fill()
        self.enable()

    def enable(self):
        got, sec = bool(self.picked()), bool(self.section())
        self.b_assign.setEnabled(got and sec); self.b_also.setEnabled(got and sec); self.b_out.setEnabled(got)
        self.b_sug.setEnabled(any(d["suggested"] for d in self.data))

    # ------------------------------------------------------------------ the four things
    def _done(self, n, text):
        M = self._M()
        if n:
            M.pending = True
            self.host.changed()
            diag.activity("qt_assign_view")
        self.refresh()
        self.host.status(text)
        return n

    def assign(self):
        ids, sec = self.picked(), self.section()
        if not ids or not sec:
            self.host.status("Pick the pieces on the left and a section on the right.")
            return 0
        n = AL.assign(self._M(), ids, sec)
        return self._done(n, f"{n} assigned to {sec}." if n else f"Already in {sec}.")

    def also(self):
        ids, sec = self.picked(), self.section()
        if not ids or not sec:
            self.host.status("Pick the pieces on the left and a section on the right.")
            return 0
        n = AL.also(self._M(), ids, sec)
        return self._done(n, f"{n} also in {sec}." if n else f"Already in {sec}.")

    def take_out(self):
        ids = self.picked()
        if not ids:
            return 0
        sec = self.section() if self.show_box.currentData() == "section" else ""
        n = AL.take_out(self._M(), ids, sec)
        return self._done(n, (f"{n} taken out of {sec}." if sec else f"{len(ids)} piece(s) taken out of their sections.") if n else "Not in a section.")

    def take_suggestions(self):
        ids = self.picked() or None
        n = AL.take_suggestions(self._M(), ids)
        return self._done(n, f"{n} placed in the section suggested." if n else "No piece has a suggested section.")
