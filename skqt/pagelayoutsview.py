"""Page layouts and numbering, the named ones a template picks (4.42.0; ST29, way A). One window from Template > More:
two lists, Page layouts and Numbering. New... takes one from standards that exist (the Global Standards or a profile);
a page layout's paper and margins can be changed; each row says what it holds and which templates pick it. A template
picks one of each in What goes in. pagelayouts holds the rules; nothing leaves the PC."""
import os

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QInputDialog,
                               QListWidget, QListWidgetItem, QTabWidget, QVBoxLayout, QWidget)
from PySide6.QtCore import Qt

import diag
import pagelayouts as PGL
import prodrules as PRL
from . import design as D


class PageDialog(QDialog):
    """A page layout's paper and four margins."""

    def __init__(self, parent, item):
        super().__init__(parent)
        self.setWindowTitle(f"Change the page: {item['name']}")
        v = (item["values"].get("variables") or {})
        f = QFormLayout(self)
        self.paper = QComboBox()
        for k in PRL.PAGE_SIZES:
            self.paper.addItem(k)
        self.paper.setCurrentIndex(max(0, self.paper.findText(v.get("paper") or "Letter")))
        f.addRow("Paper", self.paper)
        self.m = []
        for key, label in zip(PGL.MARGINS, ("Top margin", "Bottom margin", "Left margin", "Right margin")):
            sp = QDoubleSpinBox(); sp.setRange(0, 5); sp.setSingleStep(0.05); sp.setDecimals(2); sp.setSuffix(" in")
            sp.setValue(float(v.get(key) or 1.0))
            self.m.append(sp); f.addRow(label, sp)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); f.addRow(bb)

    def values(self):
        return self.paper.currentText(), [sp.value() for sp in self.m]


class LayoutsDialog(QDialog):
    def __init__(self, page):
        super().__init__(page)
        self.page, self.host = page, page.host
        self.setWindowTitle("Page layouts and numbering")
        self.resize(760, 520)
        v = QVBoxLayout(self)
        v.addWidget(D.label("A template picks one page layout and one numbering in What goes in. With no pick it reads the "
                            "Global Standards. A volume's checks read the volume's standards, so the app says when the two differ.",
                            "muted"))
        self.tabs = QTabWidget(); v.addWidget(self.tabs, 1)
        self.lists, self.btns = {}, {}
        for kind, _one, many in PGL.KINDS:
            w = QWidget(); wv = QVBoxLayout(w)
            lw = QListWidget(); lw.setWordWrap(True); lw.currentItemChanged.connect(lambda *_a: self.sync()); wv.addWidget(lw, 1)
            h = QHBoxLayout()
            b = {"new": D.button("New...", "primary", lambda k=kind: self.new(k), "Take one from the Global Standards or a profile")}
            if kind == "layout":
                b["page"] = D.button("Change the page...", None, lambda: self.change_page(), "Paper and the four margins")
            b["rename"] = D.button("Rename...", None, lambda k=kind: self.rename(k))
            b["remove"] = D.button("Remove", None, lambda k=kind: self.remove(k), "Only when no template picks it")
            for x in b.values():
                h.addWidget(x)
            h.addStretch(1); wv.addLayout(h)
            self.lists[kind], self.btns[kind] = lw, b
            self.tabs.addTab(w, many)
        self.said = D.label("", "muted"); v.addWidget(self.said)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.accept); bb.accepted.connect(self.accept); v.addWidget(bb)
        self.fill()

    def fill(self, select=None):
        cfg = self.host.config_dir
        for kind, _one, _many in PGL.KINDS:
            lw = self.lists[kind]
            keep = select if select else self.current(kind)
            lw.blockSignals(True); lw.clear()
            for it in PGL.every(cfg, kind):
                used = PGL.used_by(cfg, kind, it["id"])
                row = QListWidgetItem(f"{it['name']}\n{PGL.words(kind, it['values'])}\n"
                                      + ("Picked by: " + ", ".join(used) if used else "No template picks it yet"))
                row.setData(Qt.UserRole, it["id"]); lw.addItem(row)
                if it["id"] == keep:
                    lw.setCurrentItem(row)
            lw.blockSignals(False)
        self.sync()

    def current(self, kind):
        it = self.lists[kind].currentItem()
        return it.data(Qt.UserRole) if it is not None else None

    def can_change(self):
        return self.page.can_change() if hasattr(self.page, "can_change") else True     # 4.43.1 (ST48)

    def sync(self):
        can = self.can_change()
        for kind, _one, _many in PGL.KINDS:
            on = self.current(kind) is not None
            for k, b in self.btns[kind].items():
                b.setEnabled(can and (on or k == "new"))
        if not can and not self.said.text():
            self.said.setText("Proposal managers and production leads change page layouts and numbering.")

    def _done(self, text, select=None):
        self.said.setText(text)
        self.fill(select)
        if hasattr(self.page, "fill"):
            self.page.fill()

    def new(self, kind, name=None, source=None):
        """A new one, taken from a source (a label of pagelayouts.sources). Returns it, or None."""
        if not self.can_change():
            return None
        cfg = self.host.config_dir
        srcs = PGL.sources(cfg)
        one = dict((k, o) for k, o, _m in PGL.KINDS)[kind].lower()
        if source is None:
            source, ok = QInputDialog.getItem(self, "New " + one, "Take it from", [s for s, _ in srcs], 0, False)
            if not ok:
                return None
        std = dict(srcs).get(source)
        if std is None:
            return None
        if name is None:
            name, ok = QInputDialog.getText(self, "New " + one, "Its name", text=PGL.words(kind, PGL.extract(std, kind)).split(";")[0][:60])
            if not ok:
                return None
        it = PGL.new(cfg, kind, name, std)
        if it is None:
            self.said.setText("That name is empty or already used. Give it another.")
            return None
        diag.activity("named_layout_new")
        self._done(f"{it['name']} is added, taken from {source}.", it["id"])
        return it

    def change_page(self, paper=None, margins=None):
        if not self.can_change():
            return None
        iid = self.current("layout")
        it = PGL.get(self.host.config_dir, "layout", iid)
        if it is None:
            return None
        if paper is None and margins is None:
            dlg = PageDialog(self, it)
            if os.environ.get("AH_TEST") or not dlg.exec():
                return None
            paper, margins = dlg.values()
        got = PGL.set_page(self.host.config_dir, iid, paper, margins)
        if got is None:
            self.said.setText("Margins are between 0 and 5 inches.")
            return None
        used = PGL.used_by(self.host.config_dir, "layout", iid)
        diag.activity("named_layout_changed")
        self._done(f"{got['name']} is changed." + (f" Make {', '.join(used)} again to take it." if used else ""), iid)
        return got

    def rename(self, kind, name=None):
        if not self.can_change():
            return None
        iid = self.current(kind)
        it = PGL.get(self.host.config_dir, kind, iid)
        if it is None:
            return False
        if name is None:
            name, ok = QInputDialog.getText(self, "Rename", "Its name", text=it["name"])
            if not ok:
                return False
        if not PGL.rename(self.host.config_dir, kind, iid, name):
            self.said.setText("That name is empty or already used. Give it another.")
            return False
        self._done("Renamed.", iid)
        return True

    def remove(self, kind):
        if not self.can_change():
            return None
        iid = self.current(kind)
        it = PGL.get(self.host.config_dir, kind, iid)
        if it is None:
            return False
        used = PGL.used_by(self.host.config_dir, kind, iid)
        if used or not PGL.remove(self.host.config_dir, kind, iid):
            self.said.setText(f"{it['name']} is picked by {', '.join(used)}. Pick another there first.")
            return False
        diag.activity("named_layout_removed")
        self._done(f"{it['name']} is removed.")
        return True


def layouts(page, modal=True, kind=None):
    dlg = LayoutsDialog(page)
    page.layouts_dialog = dlg
    if kind:
        dlg.tabs.setCurrentIndex([k for k, _o, _m in PGL.KINDS].index(kind))
    if modal and not os.environ.get("AH_TEST"):
        dlg.exec()
    return dlg
