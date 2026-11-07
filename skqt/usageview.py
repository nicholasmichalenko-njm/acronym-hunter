"""Settings > Our data > Button use on this PC... (3.74.0): what the count holds, most pressed first, by screen; count on
or off; clear it; export it to Excel to plan which commands stay in view. Nothing leaves the PC unless you send the file."""
import datetime, os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QHeaderView,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

import diag
from . import design as D
from . import usage as U


def screen_name(key):
    try:
        from .pagetitles import TITLES
        return TITLES[key][0] if key in TITLES else key
    except Exception:  # noqa: BLE001
        return key


class UsageReport(QDialog):
    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.counter = getattr(host, "usage", None)
        self.setWindowTitle("Button use on this PC")
        self.resize(760, 620)
        v = QVBoxLayout(self)
        self.top = D.label("", "muted"); v.addWidget(self.top)
        r = QHBoxLayout(); v.addLayout(r)
        self.on = QCheckBox("Count button use on this PC")
        self.on.toggled.connect(lambda on: self.set_on(on))
        r.addWidget(self.on)
        r.addStretch(1)
        r.addWidget(D.label("Screen", None, wrap=False))
        self.pick = QComboBox(); self.pick.setMinimumWidth(220); self.pick.currentIndexChanged.connect(lambda _i: self.fill())
        r.addWidget(self.pick)
        self.table = QTableWidget(0, 3); self.table.setHorizontalHeaderLabels(["Screen", "Button or menu item", "Presses"])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 200); self.table.setColumnWidth(2, 70)
        v.addWidget(self.table, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject)
        bb.addButton("Export (Excel)...", QDialogButtonBox.ActionRole).clicked.connect(lambda: self.export())
        bb.addButton("Clear the count", QDialogButtonBox.ResetRole).clicked.connect(lambda: self.clear())
        v.addWidget(bb)
        self.load()

    def data(self):
        if self.counter is not None:
            self.counter.flush()
            return self.counter.d
        return U.load(self.host.config_dir)

    def load(self):
        d = self.data()
        self.on.blockSignals(True); self.on.setChecked(bool(d.get("on", True)) and not U.scif()); self.on.blockSignals(False)
        self.on.setEnabled(not U.scif())
        rows = U.rows(d)
        self.top.setText(("SCIF-ready: nothing is counted." if U.scif() else
                          f"Counted on this PC since {d.get('since')}: {sum(n for _s, _w, n in rows)} press(es) on "
                          f"{len({s for s, _w, _n in rows})} screen(s). Nothing leaves the PC unless you send the file."))
        keep = self.pick.currentData()
        self.pick.blockSignals(True); self.pick.clear(); self.pick.addItem("Every screen", "")
        for s in sorted({s for s, _w, _n in rows}, key=screen_name):
            self.pick.addItem(screen_name(s), s)
        self.pick.setCurrentIndex(max(0, self.pick.findData(keep)))
        self.pick.blockSignals(False)
        self.fill()

    def fill(self):
        want = self.pick.currentData() or ""
        rows = [r for r in U.rows(self.data()) if not want or r[0] == want]
        self.table.setRowCount(len(rows))
        for i, (s, w, n) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(screen_name(s)))
            self.table.setItem(i, 1, QTableWidgetItem(w))
            it = QTableWidgetItem(str(n)); it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter); self.table.setItem(i, 2, it)
        return len(rows)

    def set_on(self, on):
        if self.counter is not None:
            self.counter.set_on(on)
        else:
            d = U.load(self.host.config_dir); d["on"] = bool(on); U.save(self.host.config_dir, d)
        diag.activity("button_use_on" if on else "button_use_off")

    def clear(self):
        if self.counter is not None:
            self.counter.clear()
        else:
            U.save(self.host.config_dir, {"format": U.FORMAT, "since": datetime.date.today().isoformat(), "on": True, "counts": {}})
        diag.activity("button_use_cleared")
        self.load()

    def export(self, path=None):
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Export button use", os.path.expanduser("~/Button use.xlsx"), "Excel (*.xlsx)")
            if not path:
                return None
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "Button use"
        ws.append(["Screen", "Button or menu item", "Presses"])
        for s, w, n in U.rows(self.data()):
            ws.append([screen_name(s), w, n])
        ws.column_dimensions["A"].width = 28; ws.column_dimensions["B"].width = 48
        wb.save(path)
        diag.activity("button_use_exported")
        self.host.toast("Button use saved: " + os.path.basename(path))
        return path


def open_report(host, modal=True):
    dlg = UsageReport(host)
    host.usage_dialog = dlg
    if modal:
        dlg.exec()
    else:
        dlg.show()
    return dlg
