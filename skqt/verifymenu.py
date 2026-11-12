"""Verify's Menu roles (3.84.0): show or hide a role, rename it, change its key, reorder it, add a role of your own with
what it acts as. Save keeps it for this effort; Save as team default puts it in the team's config folder so new efforts
start with it; Reset to defaults puts the built-in menu back. Rules: verifyroles."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLineEdit, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

import verifyroles as VR
from . import design as D

COLS = ("In menu", "Name", "Acts as", "Level", "Key")


class MenuDialog(QDialog):
    def __init__(self, parent, menu, config_dir):
        super().__init__(parent)
        self.setWindowTitle("Menu roles"); self.resize(640, 560)
        self.config_dir, self.m = config_dir, [dict(r) for r in VR.clean(menu)]
        v = QVBoxLayout(self)
        v.addWidget(D.label("What each role acts as decides what happens next: text is split into sentences for Shred, "
                            "headings build the outline, figures and tables are kept as they are, captions link to one, "
                            "and headers, footers and Not needed never reach Shred.", "muted"))
        self.t = QTableWidget(0, len(COLS)); self.t.setHorizontalHeaderLabels(COLS)
        self.t.verticalHeader().setVisible(False); self.t.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.t, 1)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Up", None, lambda: self.move(-1))); row.addWidget(D.button("Down", None, lambda: self.move(1)))
        self.b_remove = D.button("Remove", None, lambda: self.remove(), "Only a role you added can be removed; hide a built-in one")
        row.addWidget(self.b_remove); row.addStretch(1)
        self.new_name = QLineEdit(); self.new_name.setPlaceholderText("A role of your own")
        self.new_acts = QComboBox()
        for a in VR.ACTS:
            self.new_acts.addItem(VR.ACTS_NAME[a], a)
        row.addWidget(self.new_name); row.addWidget(self.new_acts)
        row.addWidget(D.button("Add", None, lambda: self.add()))
        bb = QHBoxLayout(); v.addLayout(bb)
        bb.addWidget(D.button("Reset to defaults", None, lambda: self.reset()))
        bb.addWidget(D.button("Save as team default", None, lambda: self.save_team(),
                              "New efforts start with this menu (kept in the team's config folder)"))
        bb.addStretch(1)
        bb.addWidget(D.button("Cancel", None, self.reject)); bb.addWidget(D.button("Save", "primary", lambda: self.accept()))
        v.addWidget(D.label("Save keeps the menu for this effort.", "muted"))
        self.fill()

    def fill(self):
        self.t.setRowCount(0)
        for r in self.m:
            i = self.t.rowCount(); self.t.insertRow(i)
            cb = QCheckBox(); cb.setChecked(r["on"]); self.t.setCellWidget(i, 0, cb)
            self.t.setCellWidget(i, 1, QLineEdit(r["name"]))
            ac = QComboBox()
            for a in VR.ACTS:
                ac.addItem(VR.ACTS_NAME[a], a)
            ac.setCurrentIndex(VR.ACTS.index(r["acts"])); ac.setEnabled(r["id"] not in VR.BUILTIN)
            self.t.setCellWidget(i, 2, ac)
            lv = QSpinBox(); lv.setRange(1, 6); lv.setValue(r.get("level") or 1); lv.setEnabled(r["acts"] == "heading" and r["id"] not in VR.BUILTIN)
            self.t.setCellWidget(i, 3, lv)
            self.t.setCellWidget(i, 4, QLineEdit(r["key"]))
            it = QTableWidgetItem(); it.setData(Qt.UserRole, r["id"]); self.t.setVerticalHeaderItem(i, it)

    def read(self):
        out = []
        for i, r in enumerate(self.m):
            x = dict(r)
            x["on"] = self.t.cellWidget(i, 0).isChecked()
            x["name"] = self.t.cellWidget(i, 1).text() or r["name"]
            x["acts"] = self.t.cellWidget(i, 2).currentData()
            if x["acts"] == "heading":
                x["level"] = self.t.cellWidget(i, 3).value() if r["id"] not in VR.BUILTIN else r.get("level", 1)
            x["key"] = self.t.cellWidget(i, 4).text().strip()
            out.append(x)
        self.m = VR.clean(out)
        return self.m

    def move(self, d):
        self.read()
        i = self.t.currentRow()
        j = i + d
        if 0 <= i < len(self.m) and 0 <= j < len(self.m):
            self.m[i], self.m[j] = self.m[j], self.m[i]
            self.fill(); self.t.selectRow(j)

    def remove(self):
        self.read()
        i = self.t.currentRow()
        if 0 <= i < len(self.m) and self.m[i]["id"] not in VR.BUILTIN:
            del self.m[i]
            self.fill()
            return True
        return False

    def add(self, name=None, acts=None):
        self.read()
        self.m, rid = VR.add_role(self.m, name if name is not None else self.new_name.text(),
                                  acts if acts is not None else self.new_acts.currentData())
        self.new_name.clear(); self.fill()
        return rid

    def reset(self):
        self.m = VR.defaults(); self.fill()

    def save_team(self):
        VR.save_team(self.config_dir, self.read())

    def result_menu(self):
        return self.read()
