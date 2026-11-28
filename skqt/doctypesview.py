"""Settings > Document types (2.94.0): the team's customer document types and their default initials. Picking a type
when adding a document fills in its initial (numbered for types like Amendment: A1, A2...). A renamed type keeps its
documents. A team pack can carry these and lock them. On this PC only.

4.86.0 (step I4): when the saved list lacks types that came with 4.86.0, a line above the table names them with Add them
(they join the table above Other; Save keeps them, as any change here) and Leave them out (remembered on this PC)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem, QWidget)
import diag
import doctypes as DT
from . import design as D
from .stagesedit import clear_table


def _check(on):
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setAlignment(Qt.AlignCenter)
    cb = QCheckBox(); cb.setChecked(bool(on)); h.addWidget(cb)
    w.box = cb
    return w


class DocTypesCard(D.Card):
    def __init__(self, host):
        super().__init__("Document types",
                         "The kinds of customer document your team works with and the initial each starts with (the type's "
                         "short name: RFP, SOW, Sec L). When you add a document, its type fills in the initial, and a second "
                         "document of a type is numbered by itself (RFP2; amendments count from Amd1). File name words help "
                         "the app guess one of your own types.",
                         actions=[D.button("Put back the built-in ones", "ghost", lambda: self.reset()),
                                  D.button("Save", "primary", lambda: self.save())])
        self.host = host
        self.lock_note = self.add(D.label("", "muted"))
        self.new_box = QWidget(); nb = QHBoxLayout(self.new_box); nb.setContentsMargins(0, 0, 0, 0)      # 4.86.0
        self.new_line = D.label("", "muted"); self.new_line.setWordWrap(True)
        nb.addWidget(self.new_line, 1)
        nb.addWidget(D.button("Leave them out", "ghost", lambda: self.leave_new()))
        nb.addWidget(D.button("Add them", None, lambda: self.add_new()))
        self.body.addWidget(self.new_box)
        self.new_types = []
        t = QTableWidget(0, 5); t.setHorizontalHeaderLabels(["Type", "Initial", "Numbered", "Customer document", "File name words"])
        t.setColumnHidden(2, True)                      # 4.24.0: numbering is automatic; the value is kept as it was saved
        t.verticalHeader().setVisible(False); t.setSelectionBehavior(QAbstractItemView.SelectRows)
        for i, w in enumerate((200, 80, 90, 130, 0)):
            if w:
                t.setColumnWidth(i, w)
        t.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        t.verticalHeader().setDefaultSectionSize(32); t.setProperty("sk_rows_fixed", True); t.setMinimumHeight(300)
        t.horizontalHeaderItem(2).setToolTip("Each document of this type gets the next number: A1, A2, A3")
        t.horizontalHeaderItem(3).setToolTip("New documents of this type are marked Customer document (you can change it per document)")
        t.horizontalHeaderItem(4).setToolTip("Words in a file name that mean this type, with commas between: pricing, cost volume")
        self.table = t
        self.add(t)
        row = QHBoxLayout()
        for text, fn in (("Up", lambda: self.move(-1)), ("Down", lambda: self.move(1)), ("+ Type", lambda: self.add_type()),
                         ("Remove", lambda: self.remove())):
            row.addWidget(D.button(text, "ghost" if text == "Remove" else None, fn))
        row.addStretch(1)
        self.body.addLayout(row)
        self.note = self.add(D.label("", "muted"))
        self.fill()

    def fill(self, types=None):
        types = types if types is not None else DT.load(self.host.config_dir)["types"]
        clear_table(self.table)
        for x in types:
            self._row(x)
        import teampack as TP
        lk = TP.locked(self.host.config_dir, "doctypes")
        self.lock_note.setText(f"Set by the team pack ({lk}). They change when the team sends a new pack." if lk else "")
        self.lock_note.setVisible(bool(lk))
        self.table.setEnabled(not lk)
        self.say_new(None if lk else DT.missing_new(self.host.config_dir))

    def say_new(self, missing):
        """4.86.0: the line that offers the types new in 4.86.0 the saved list does not have."""
        self.new_types = list(missing or [])
        n = len(self.new_types)
        self.new_line.setText(f"{n} type" + (" came" if n == 1 else "s came") + " with 4.86.0 and " + ("is" if n == 1 else "are")
                              + " not in your list: " + ", ".join(t["name"] for t in self.new_types) + "." if n else "")
        self.new_box.setVisible(bool(n))

    def add_new(self):
        """The new types join the table above Other; Save keeps them."""
        if not self.new_types:
            return 0
        t = self.table
        at = next((i for i in range(t.rowCount()) if self._vals(i)["orig"] == "Other"), t.rowCount())
        for k, x in enumerate(self.new_types):
            self._row(dict(x, orig=None), at=at + k)
        n = len(self.new_types)
        diag.activity("qt_doctypes_new_added", n=n)
        self.say_new([])
        self.note.setText(f"{n} type" + ("" if n == 1 else "s") + " added above Other. Save keeps them.")
        return n

    def leave_new(self):
        DT.leave_out(self.host.config_dir, [t["name"] for t in self.new_types])
        diag.activity("qt_doctypes_new_left_out", n=len(self.new_types))
        self.say_new([])
        return True

    def _row(self, x, at=None):
        t = self.table
        i = t.rowCount() if at is None else at
        t.insertRow(i)
        it = QTableWidgetItem(x["name"]); it.setData(Qt.UserRole, x.get("orig", x["name"]))
        if x["name"] == "Other" and x.get("orig", "Other") == "Other":
            it.setFlags(it.flags() & ~Qt.ItemIsEditable); it.setToolTip("Other always stays: a document of no listed type")
        t.setItem(i, 0, it)
        t.setItem(i, 1, QTableWidgetItem(x.get("initial", "")))
        t.setCellWidget(i, 2, _check(x.get("numbered")))
        t.setCellWidget(i, 3, _check(x.get("matrix")))
        t.setItem(i, 4, QTableWidgetItem(x.get("words", "")))
        return i

    def _vals(self, i):
        t = self.table
        return {"name": t.item(i, 0).text().strip() if t.item(i, 0) else "", "orig": t.item(i, 0).data(Qt.UserRole) if t.item(i, 0) else None,
                "initial": t.item(i, 1).text() if t.item(i, 1) else "", "numbered": t.cellWidget(i, 2).box.isChecked(),
                "matrix": t.cellWidget(i, 3).box.isChecked(), "words": t.item(i, 4).text() if t.item(i, 4) else ""}

    def values(self):
        return [self._vals(i) for i in range(self.table.rowCount())]

    def add_type(self, name="New type", initial="New"):
        i = self._row({"name": name, "initial": initial, "numbered": False, "matrix": False, "words": "", "orig": None})
        self.table.setCurrentCell(i, 0)
        return i

    def move(self, d):
        t = self.table; i = t.currentRow(); j = i + d
        if i < 0 or not (0 <= j < t.rowCount()):
            return False
        x = self._vals(i)
        for c in (2, 3):
            t.cellWidget(i, c).hide()
        t.removeRow(i)
        self._row(x, at=j); t.setCurrentCell(j, 0)
        return True

    def remove(self):
        t = self.table; i = t.currentRow()
        if i < 0:
            return False
        if self._vals(i)["orig"] == "Other":
            self.host.status("Other always stays: a document of no listed type is Other.")
            return False
        for c in (2, 3):
            t.cellWidget(i, c).hide()
        t.removeRow(i)
        return True

    def save(self):
        import teampack as TP
        if TP.locked(self.host.config_dir, "doctypes"):
            self.host.status("The team pack set the document types. They change when the team sends a new pack.")
            return False
        vals = self.values()
        why = DT.problems(vals)
        if why:
            self.host.status("Not saved: " + "; ".join(why) + ".")
            return False
        renamed = {x["orig"]: x["name"] for x in vals if x["orig"] and x["orig"] != x["name"]}
        T = DT.save(self.host.config_dir, vals, renamed)["types"]
        diag.activity("qt_doctypes_saved", n=len(T))
        self.host.toast("Document types saved")
        dup = {}
        for x in T:
            dup.setdefault(x["initial"], []).append(x["name"])
        same = [f"{', '.join(v)} share {k}" for k, v in dup.items() if len(v) > 1]
        self.note.setText(("Two types share an initial: " + "; ".join(same) + ". Their documents count up (R, R2...)." if same else "")
                          + (f" Renamed: {', '.join(f'{a} to {b}' for a, b in renamed.items())}; documents already filed follow." if renamed else ""))
        self.fill(T)
        return True

    def reset(self, answer=None):
        if answer is None:
            from PySide6.QtWidgets import QMessageBox
            answer = QMessageBox.question(self, "Document types", "Put back the built-in document types? Your own types are "
                                          "removed when you save.") == QMessageBox.Yes
        if not answer:
            return False
        self.fill([dict(x) for x in DT.BUILT_IN])
        return True
