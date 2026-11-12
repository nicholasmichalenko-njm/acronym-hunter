"""Settings > Units of measurement (3.31.0): the team's units (unit, what it means, its system, and whether it goes in
every volume's Units of Measurement table). Units captured in Review join the table of their own effort."""
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLineEdit, QTableWidget,
                               QVBoxLayout)
import diag
import units as UN
from . import design as D


class UnitsDialog(QDialog):
    def __init__(self, parent, host):
        super().__init__(parent)
        self.host = host
        self.setWindowTitle("Units of measurement"); self.resize(820, 520)
        v = QVBoxLayout(self)
        v.addWidget(D.label("The team's units. Those ticked In every table go in each volume's Units of Measurement table; "
                            "the units captured in Shred (Unit of measurement, under More...) join their own effort's table.", "muted"))
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(["Unit", "What it means", "System", "In every table"])
        self.t.verticalHeader().setVisible(False)
        for i, w in enumerate((120, 400, 140, 110)):
            self.t.setColumnWidth(i, w)
        v.addWidget(self.t, 1)
        r = QHBoxLayout(); v.addLayout(r)
        r.addWidget(D.button("+ Unit", None, lambda: self.add()))
        r.addWidget(D.button("Take out", "ghost", lambda: self.remove()))
        r.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.save); bb.rejected.connect(self.reject); r.addWidget(bb)
        for u in UN.load(host.config_dir):
            self.add(u)

    def add(self, u=None):
        u = u or {"unit": "", "meaning": "", "system": "", "always": False}
        r = self.t.rowCount(); self.t.insertRow(r)
        self.t.setCellWidget(r, 0, QLineEdit(u["unit"]))
        self.t.setCellWidget(r, 1, QLineEdit(u["meaning"]))
        cb = QComboBox(); cb.addItems(list(UN.SYSTEMS)); cb.setCurrentText(u["system"]); self.t.setCellWidget(r, 2, cb)
        ch = QCheckBox(); ch.setChecked(u["always"]); self.t.setCellWidget(r, 3, ch)
        return r

    def remove(self):
        r = self.t.currentRow()
        if r >= 0:
            self.t.removeRow(r)

    def rows(self):
        return [{"unit": self.t.cellWidget(r, 0).text(), "meaning": self.t.cellWidget(r, 1).text(),
                 "system": self.t.cellWidget(r, 2).currentText(), "always": self.t.cellWidget(r, 3).isChecked()}
                for r in range(self.t.rowCount())]

    def save(self):
        UN.save(self.host.config_dir, self.rows())
        diag.activity("units_saved", n=self.t.rowCount())
        self.host.status("Units of measurement saved.")
        self.accept()
