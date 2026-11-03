"""Topics of this effort (3.28.0): rename, color, the response sections each maps to, order (the first nine are on keys
1 to 9 in Sort mode) and take out. The rules are topics.py's."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QColorDialog, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLineEdit, QListWidget,
                               QListWidgetItem, QVBoxLayout)

import diag
import topics as TP
from . import design as D


class TopicsDialog(QDialog):
    def __init__(self, parent, rec, labels):
        super().__init__(parent)
        self.rec, self.labels = rec, list(labels or [])
        self.setWindowTitle("Topics of this effort"); self.resize(820, 520)
        v = QVBoxLayout(self)
        v.addWidget(D.label("The first nine topics are on keys 1 to 9 in Sort mode. Map a topic to the response sections that "
                            "answer it: a sentence carrying it goes there when you make it a requirement.", "muted"))
        row = QHBoxLayout(); v.addLayout(row, 1)
        self.list = QListWidget(); self.list.setMinimumWidth(260); self.list.currentRowChanged.connect(lambda _r: self.show_one())
        row.addWidget(self.list)
        right = QVBoxLayout(); row.addLayout(right, 1)
        f = QFormLayout(); right.addLayout(f)
        self.name = QLineEdit(); self.name.editingFinished.connect(lambda: self.rename()); f.addRow("Name", self.name)
        self.color_btn = D.button("Color...", None, lambda: self.pick_color()); f.addRow("Color", self.color_btn)
        right.addWidget(D.label("Response sections it maps to", "label"))
        self.secs = QListWidget(); self.secs.itemChanged.connect(lambda _it: self.set_sections()); right.addWidget(self.secs, 1)
        bh = QHBoxLayout(); right.addLayout(bh)
        bh.addWidget(D.button("Up", "ghost", lambda: self.move(-1)))
        bh.addWidget(D.button("Down", "ghost", lambda: self.move(1)))
        bh.addStretch(1)
        bh.addWidget(D.button("Take out", "danger", lambda: self.remove(), "The topic and its tags come off; sentences keep their decisions"))
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.accept); bb.accepted.connect(self.accept)
        v.addWidget(bb)
        self.fill()

    def current(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def fill(self, keep=None):
        keep = keep or self.current()
        self.list.blockSignals(True); self.list.clear()
        for n, t in enumerate(TP.topics(self.rec)):
            it = QListWidgetItem(D.dot_icon(t["color"]), (f"{n + 1}  " if n < 9 else "") + t["name"])
            it.setData(Qt.UserRole, t["id"]); self.list.addItem(it)
            if t["id"] == keep:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)
        self.show_one()

    def show_one(self):
        t = TP.get(self.rec, self.current())
        self.name.setText(t["name"] if t else "")
        self.secs.blockSignals(True); self.secs.clear()
        for lab in self.labels:
            it = QListWidgetItem(lab); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if t and lab in (t.get("sections") or []) else Qt.Unchecked)
            self.secs.addItem(it)
        self.secs.blockSignals(False)

    def rename(self, name=None):
        tid = self.current()
        if tid and TP.update(self.rec, tid, name=name if name is not None else self.name.text()):
            self.fill(tid)

    def pick_color(self, color=None):
        tid = self.current()
        if not tid:
            return
        if color is None:
            c = QColorDialog.getColor(parent=self)
            if not c.isValid():
                return
            color = c.name()
        TP.update(self.rec, tid, color=color); self.fill(tid)

    def set_sections(self, labels=None):
        tid = self.current()
        if not tid:
            return
        if labels is None:
            labels = [self.secs.item(i).text() for i in range(self.secs.count()) if self.secs.item(i).checkState() == Qt.Checked]
        TP.update(self.rec, tid, sections=labels)
        diag.activity("topic_mapped", n=len(labels))

    def move(self, step):
        tid = self.current()
        if tid and TP.move(self.rec, tid, step):
            self.fill(tid)

    def remove(self):
        tid = self.current()
        if tid:
            TP.remove(self.rec, tid); self.fill()
