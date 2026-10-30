"""Settings > Document types (2.94.0): the team's customer document types and their default initials. Picking a type
when adding a document fills in its initial (numbered for types like Amendment: A1, A2...). A renamed type keeps its
documents. A team pack can carry these and lock them. On this PC only."""
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
                         "The kinds of customer document your team works with and the initial each starts with. When you "
                         "add a document, its type fills in the initial (numbered types count up: A1, A2...). File name words "
                         "help the app guess one of your own types.",
                         actions=[D.button("Put back the built-in ones", "ghost", lambda: self.reset()),
                                  D.button("Save", "primary", lambda: self.save())])
        self.host = host
        self.lock_note = self.add(D.label("", "muted"))
        t = QTableWidget(0, 5); t.setHorizontalHeaderLabels(["Type", "Initial", "Numbered", "Builds the matrix", "File name words"])
        t.verticalHeader().setVisible(False); t.setSelectionBehavior(QAbstractItemView.SelectRows)
        for i, w in enumerate((200, 80, 90, 130, 0)):
            if w:
                t.setColumnWidth(i, w)
        t.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        t.verticalHeader().setDefaultSectionSize(32); t.setProperty("sk_rows_fixed", True); t.setMinimumHeight(300)
        t.horizontalHeaderItem(2).setToolTip("Each document of this type gets the next number: A1, A2, A3")
        t.horizontalHeaderItem(3).setToolTip("New documents of this type build the compliance matrix (you can change it per document)")
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

    def add_type(self, name="New type", initial="N"):
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
