"""Effort types (3.18.2): add, rename, order and take out the team's effort types (RFP response, RFI response, white
paper, ...), and choose the one new efforts start with. Opened from Start an effort and from Production Standards.
Kept on this PC with the production standards (production_standards.json); a team pack carries them with the standards.
An effort that used a type taken out keeps its own values."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QInputDialog, QListWidget, QListWidgetItem,
                               QVBoxLayout)
import diag
import prodrules as PRL
from . import design as D


class EffortTypesDialog(QDialog):
    def __init__(self, parent, config_dir):
        super().__init__(parent)
        self.cfg = config_dir
        self.data = PRL.load(config_dir)
        self.changed = False
        self.setWindowTitle("Effort types")
        self.resize(560, 460)
        v = QVBoxLayout(self)
        v.addWidget(D.label("The kinds of effort your team works on. Each one can carry its own formatting in Production "
                            "Standards. New efforts start with the default.", "muted"))
        row = QHBoxLayout(); v.addLayout(row, 1)
        self.list = QListWidget(); row.addWidget(self.list, 1)
        self.list.itemDoubleClicked.connect(lambda _i: self.rename())
        col = QVBoxLayout(); row.addLayout(col)
        self.btns = {}
        for key, text, fn, tip in (("add", "Add...", lambda: self.add(), "A new effort type (for example Sources sought)"),
                                   ("rename", "Rename...", lambda: self.rename(), "A new name; efforts using it keep it"),
                                   ("up", "Move up", lambda: self.move(-1), "Earlier in the lists"),
                                   ("down", "Move down", lambda: self.move(1), "Later in the lists"),
                                   ("default", "Make default", lambda: self.make_default(), "New efforts start with it"),
                                   ("remove", "Take out", lambda: self.remove(), "Efforts that used it keep their own values")):
            b = D.button(text, "danger" if key == "remove" else None, fn, tip)
            self.btns[key] = b; col.addWidget(b)
        col.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.accept); bb.accepted.connect(self.accept)
        v.addWidget(bb)
        self.fill()

    def fill(self, keep=None):
        keep = keep or self.current()
        self.list.clear()
        for e in self.data.get("effort_types", []):
            it = QListWidgetItem(e["name"] + ("  (default)" if e["id"] == self.data.get("default_effort_type") else ""))
            it.setData(Qt.UserRole, e["id"])
            self.list.addItem(it)
            if e["id"] == keep:
                self.list.setCurrentItem(it)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)

    def current(self):
        it = self.list.currentItem() if hasattr(self, "list") else None
        return it.data(Qt.UserRole) if it is not None else ""

    def names(self):
        return [e["name"] for e in self.data.get("effort_types", [])]

    def _save(self, keep=None):
        PRL.save(self.cfg, self.data)
        self.changed = True
        self.fill(keep)

    def add(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "New effort type", "Its name (for example: Sources sought, Task order response):")
            if not ok:
                return None
        e = PRL.add_effort_type(self.data, name)
        if e is None:
            return None
        diag.activity("effort_type_added")
        self._save(e["id"])
        return e["id"]

    def rename(self, name=None):
        eid = self.current()
        e = PRL.effort_type_of(self.data, eid)
        if e is None:
            return False
        if name is None:
            name, ok = QInputDialog.getText(self, "Rename effort type", "New name:", text=e["name"])
            if not ok:
                return False
        if not PRL.rename_effort_type(self.data, eid, name):
            return False
        diag.activity("effort_type_renamed")
        self._save(eid)
        return True

    def move(self, step):
        eid = self.current()
        if PRL.move_effort_type(self.data, eid, step):
            self._save(eid)
            return True
        return False

    def make_default(self):
        eid = self.current()
        if not eid:
            return False
        self.data["default_effort_type"] = eid
        self._save(eid)
        return True

    def remove(self):
        eid = self.current()
        if not PRL.remove_effort_type(self.data, eid):
            return False
        diag.activity("effort_type_removed")
        self._save()
        return True


def manage(parent, config_dir, run=True):
    """Open the dialog; returns it (run=False: not shown, for tests)."""
    d = EffortTypesDialog(parent, config_dir)
    if run:
        d.exec()
    return d
