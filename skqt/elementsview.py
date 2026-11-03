"""Settings > Response elements (3.30.0): the team's elements (name, part, what fills it, pages, whether it counts, the
library item it uses, its order in its part, shown in Add elements or not) and the kit each effort type starts with."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLineEdit, QListWidget,
                               QListWidgetItem, QSpinBox, QTableWidget, QTabWidget, QVBoxLayout, QWidget)
import diag
import responseelements as RE
from . import design as D

COLS = ["Element", "Part", "What fills it", "Pages", "Counts", "Library item", "Shown"]


class ElementsDialog(QDialog):
    def __init__(self, parent, host):
        super().__init__(parent)
        self.host = host
        self.data = RE.load(host.config_dir)
        self.setWindowTitle("Response elements"); self.resize(1080, 620)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Each element goes in its part of a volume, in this order. The Structure Builder's Add elements "
                            "lists them; Make templates builds them from what fills them.", "muted"))
        tabs = QTabWidget(); v.addWidget(tabs, 1)
        w1 = QWidget(); l1 = QVBoxLayout(w1)
        self.t = QTableWidget(0, len(COLS)); self.t.setHorizontalHeaderLabels(COLS)
        self.t.verticalHeader().setVisible(False); self.t.setSelectionBehavior(QTableWidget.SelectRows)
        for i, wd in enumerate((230, 120, 250, 60, 60, 200, 60)):
            self.t.setColumnWidth(i, wd)
        l1.addWidget(self.t, 1)
        r = QHBoxLayout(); l1.addLayout(r)
        r.addWidget(D.button("+ Element", None, lambda: self.add()))
        r.addWidget(D.button("Up", None, lambda: self.move(-1), "Earlier in its part"))
        r.addWidget(D.button("Down", None, lambda: self.move(1), "Later in its part"))
        r.addWidget(D.button("Take out", "ghost", lambda: self.remove(), "Take out one of the team's own elements"))
        r.addStretch(1)
        tabs.addTab(w1, "Elements")
        w2 = QWidget(); l2 = QVBoxLayout(w2)
        l2.addWidget(D.label("The elements a volume starts with, by effort type. Add elements ticks them for a volume that "
                             "has none yet.", "muted"))
        self.et = QComboBox(); self.et.addItem("Any effort type (the team's kit)", "")
        try:
            import prodrules as PRL
            for e in PRL.load(host.config_dir).get("effort_types", []):
                self.et.addItem(e["name"], e["id"])
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.et.currentIndexChanged.connect(lambda _i: self.fill_kit())
        l2.addWidget(self.et)
        self.kit = QListWidget(); l2.addWidget(self.kit, 1)
        self.kit.itemChanged.connect(lambda _i: self.read_kit())
        tabs.addTab(w2, "Kits by effort type")
        b = QHBoxLayout(); v.addLayout(b)
        b.addWidget(D.button("Back to the built-in elements", "ghost", lambda: self.reset()))
        b.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.save); bb.rejected.connect(self.reject); b.addWidget(bb)
        self.fill()
        self.fill_kit()

    def _lib(self, shelf):
        try:
            import templatelib as TL
            return [i["name"] for i in TL.Library(self.host.config_dir).items if i["kind"] == shelf]
        except Exception:  # noqa: BLE001
            return []

    def fill(self):
        self._sync = True
        self.t.setRowCount(0)
        for e in self.data["elements"]:
            r = self.t.rowCount(); self.t.insertRow(r)
            name = QLineEdit(e["name"]); name.setProperty("eid", e["id"]); self.t.setCellWidget(r, 0, name)
            part = QComboBox()
            for k, t in RE.PARTS:
                part.addItem(t, k)
            part.setCurrentIndex(part.findData(e["part"])); self.t.setCellWidget(r, 1, part)
            src = QComboBox()
            for k, t in RE.SOURCES:
                src.addItem(t, k)
            src.setCurrentIndex(src.findData(e["source"])); self.t.setCellWidget(r, 2, src)
            pg = QSpinBox(); pg.setRange(0, 200); pg.setValue(e["pages"]); self.t.setCellWidget(r, 3, pg)
            cn = QCheckBox(); cn.setChecked(e["counts"]); self.t.setCellWidget(r, 4, cn)
            lib = QComboBox(); lib.setEditable(True)
            shelf = RE.LIB_SHELF.get(e["source"])
            lib.addItem("")
            for n in (self._lib(shelf) if shelf else []):
                lib.addItem(n)
            lib.setCurrentText(e.get("lib", "")); lib.setEnabled(bool(shelf)); self.t.setCellWidget(r, 5, lib)
            sh = QCheckBox(); sh.setChecked(e.get("shown", True)); self.t.setCellWidget(r, 6, sh)
        self._sync = False

    def read(self):
        """The table back into the elements."""
        by = {e["id"]: e for e in self.data["elements"]}
        for r in range(self.t.rowCount()):
            e = by.get(self.t.cellWidget(r, 0).property("eid"))
            if e is None:
                continue
            e["name"] = self.t.cellWidget(r, 0).text().strip() or e["name"]
            e["part"] = self.t.cellWidget(r, 1).currentData()
            e["source"] = self.t.cellWidget(r, 2).currentData()
            e["pages"] = self.t.cellWidget(r, 3).value()
            e["counts"] = self.t.cellWidget(r, 4).isChecked()
            e["lib"] = self.t.cellWidget(r, 5).currentText().strip()
            e["shown"] = self.t.cellWidget(r, 6).isChecked()

    def _cur(self):
        r = self.t.currentRow()
        return self.t.cellWidget(r, 0).property("eid") if r >= 0 else None

    def add(self, name="New element"):
        self.read()
        e = RE.add(self.data, name)
        self.data = {"elements": sorted(self.data["elements"], key=lambda x: ([k for k, _t in RE.PARTS].index(x["part"]), x["order"])),
                     "kits": self.data["kits"]}
        self.fill()
        return e

    def move(self, d):
        self.read()
        eid = self._cur()
        if eid and RE.move(self.data, eid, d):
            self.data["elements"].sort(key=lambda x: ([k for k, _t in RE.PARTS].index(x["part"]), x["order"]))
            self.fill()
            self.t.selectRow(next(i for i, e in enumerate(self.data["elements"]) if e["id"] == eid))
            return True
        return False

    def remove(self):
        self.read()
        eid = self._cur()
        if eid and RE.remove(self.data, eid):
            self.fill(); self.fill_kit()
            return True
        self.host.status("A built-in element stays: untick Shown to keep it out of Add elements.")
        return False

    def fill_kit(self):
        self._sync = True
        self.kit.clear()
        ids = RE.kit(self.data, self.et.currentData() or "")
        for e in self.data["elements"]:
            it = QListWidgetItem(f"{e['name']}   ({RE.PART_NAME[e['part']]})")
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if e["id"] in ids else Qt.Unchecked)
            it.setData(Qt.UserRole, e["id"])
            self.kit.addItem(it)
        self._sync = False

    def read_kit(self):
        if getattr(self, "_sync", False):
            return
        RE.set_kit(self.data, self.et.currentData() or "", [self.kit.item(i).data(Qt.UserRole) for i in range(self.kit.count())
                                                             if self.kit.item(i).checkState() == Qt.Checked])

    def reset(self):
        self.data = RE.reset(self.host.config_dir)
        self.fill(); self.fill_kit()

    def save(self):
        self.read()
        RE.save(self.host.config_dir, self.data)
        diag.activity("response_elements_saved")
        self.host.status("Response elements saved.")
        self.accept()
