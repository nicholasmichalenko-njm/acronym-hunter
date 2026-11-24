"""Setup > Order under each heading... (4.63.0; Nicholas 2026-11-23). One list of the kinds of text a section holds,
each with the style it is written in, moved Up and Down into the order they are written under a heading. For: the
whole setup, or one heading that differs. Use this order keeps it; the button beside it puts a heading back on the whole
setup's order, or the whole setup back to how it was always written. The logic is setuporder; this is its window."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QListWidget, QListWidgetItem, QVBoxLayout

import diag
import setupdoc as SD
import setuporder as SO
from . import design as D

WHOLE_TEXT = "The whole setup"


class OrderDialog(QDialog):
    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.M = page._M()
        self.S = SD.setup_of(self.M)
        self.setWindowTitle("Order under each heading")
        self.setMinimumSize(560, 460)
        v = QVBoxLayout(self); v.setSpacing(D.SPACE["s"])
        v.addWidget(D.label("The order the kinds of text are written in under a heading. Within a kind, the pieces keep the "
                            "order of the customer's document.", "muted"))
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.label("For", "label", wrap=False))
        self.where = QComboBox(); self.where.addItem(WHOLE_TEXT, SO.WHOLE)
        for lab in SD.labels(self.M):
            self.where.addItem(lab + ("   (its own order)" if SO.own(self.S, lab) else ""), lab)
        self.where.currentIndexChanged.connect(lambda _i: self.fill())
        row.addWidget(self.where, 1)
        mid = QHBoxLayout(); v.addLayout(mid, 1)
        self.rows = QListWidget(); mid.addWidget(self.rows, 1)
        side = QVBoxLayout(); mid.addLayout(side)
        self.b_up = D.button("Up", None, lambda: self.move(-1)); side.addWidget(self.b_up)
        self.b_down = D.button("Down", None, lambda: self.move(1)); side.addWidget(self.b_down)
        side.addStretch(1)
        self.said = D.label("", "muted"); v.addWidget(self.said)
        foot = QHBoxLayout(); v.addLayout(foot)
        self.b_back = D.button("", "ghost", lambda: self.back()); foot.addWidget(self.b_back)
        foot.addStretch(1)
        foot.addWidget(D.button("Close", None, self.reject))
        self.b_use = D.button("Use this order", "primary", lambda: self.use()); foot.addWidget(self.b_use)
        try:
            self.styles = {k: o.get("style", "") for k, o in page.setup_opts().items()}
        except Exception:  # noqa: BLE001
            diag.swallowed(); self.styles = {}
        self.fill()

    def label(self):
        return self.where.currentData() or SO.WHOLE

    def fill(self):
        lab = self.label()
        self.rows.clear()
        for k in SO.shown(self.S, lab):
            it = QListWidgetItem(SO.NAMES[k] + (f"      style: {self.styles[k]}" if self.styles.get(k) else ""))
            it.setData(Qt.UserRole, k)
            self.rows.addItem(it)
        self.rows.setCurrentRow(0)
        mine = SO.own(self.S, lab) is not None
        if lab:
            self.b_back.setText("Same as the whole setup"); self.b_back.setEnabled(mine)
            self.said.setText("This heading has its own order." if mine else "This heading follows the whole setup's order.")
        else:
            self.b_back.setText("As it was written before"); self.b_back.setEnabled(mine)
            self.said.setText("Each heading is written in this order." if mine else
                              "No order is set: each piece is written where it always was (a note under its requirement).")
        return self.order()

    def order(self):
        return [self.rows.item(i).data(Qt.UserRole) for i in range(self.rows.count())]

    def move(self, delta):
        i = self.rows.currentRow()
        j = i + delta
        if i < 0 or not (0 <= j < self.rows.count()):
            return self.order()
        it = self.rows.takeItem(i)
        self.rows.insertItem(j, it)
        self.rows.setCurrentRow(j)
        return self.order()

    def _saved(self, text):
        self.M.pending = True
        self.page.host.changed()
        diag.activity("qt_setup_order_set")
        i = self.where.currentIndex()
        lab = self.label()
        if lab:
            self.where.setItemText(i, lab + ("   (its own order)" if SO.own(self.S, lab) else ""))
        self.fill()
        self.page.host.status(text)

    def use(self):
        lab = self.label()
        got = SO.set_order(self.S, self.order(), lab)
        self._saved("The order is kept" + (f" for {lab}." if lab else " for the whole setup.") + " Make the setup to write it.")
        return got

    def back(self):
        lab = self.label()
        had = SO.clear(self.S, lab)
        if had:
            self._saved((f"{lab} follows the whole setup's order." if lab else "The setup is written as before."))
        return had


def open_order(page, run=True):
    """The window, or None with nothing shredded. run False (tests): made, not shown."""
    if page._M() is None:
        page.host.status("Shred a customer document first: the setup is made from its pieces.")
        return None
    d = OrderDialog(page)
    if run:
        d.exec()
    return d
