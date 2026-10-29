"""Editing an effort's stages (2.92.0): the stage table (name, planned start and end, gate) with Up, Down, + Stage and
Remove, shared by Effort Record and Effort Home's Edit stages... The current stage cannot be removed. The rules are the
effort record's. Nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)
import diag
import effortrec as R
from . import design as D


def stage_table():
    t = QTableWidget(0, 4); t.setHorizontalHeaderLabels(["Stage", "Planned start", "Planned end", "Gate"])
    t.verticalHeader().setVisible(False); t.setSelectionBehavior(QAbstractItemView.SelectRows)
    for i, w in enumerate((0, 150, 150, 300)):
        if i:
            t.setColumnWidth(i, w)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    return t


class StageTableMixin:
    """Needs self.stage_table, self.rec (an effort record), self.host and self.refresh()."""

    def fill_stages(self, r):
        t = self.stage_table
        t.setRowCount(0)
        for s in r.stages:
            self._stage_row(s["id"], s["name"], s.get("planned", ""), s.get("planned_end", ""), r.gate_of(s), s["id"] == r.data["stage"])

    def _stage_row(self, sid, name, start, end, gate, current=False, at=None):
        t = self.stage_table
        i = t.rowCount() if at is None else at
        t.insertRow(i)
        it = QTableWidgetItem(name); it.setData(Qt.UserRole, sid)
        if current:
            it.setToolTip("The current stage"); it.setForeground(D.color("accent"))
        t.setItem(i, 0, it)
        for c, val in ((1, start), (2, end)):
            d = R.parse_date(val) if val else None
            t.setItem(i, c, QTableWidgetItem(R.short_date(d.isoformat()) + f", {d.year}" if d else (val or "")))
        cb = QComboBox()
        for k, text in R.GATES.items():
            cb.addItem(text, k)
        cb.setCurrentIndex(max(0, cb.findData(gate)))
        t.setCellWidget(i, 3, cb)
        return i

    def _stage_values(self, i):
        t = self.stage_table
        it = t.item(i, 0)
        return (it.data(Qt.UserRole) if it else None, it.text() if it else "", t.item(i, 1).text() if t.item(i, 1) else "",
                t.item(i, 2).text() if t.item(i, 2) else "", t.cellWidget(i, 3).currentData())

    def move_row(self, d):
        t = self.stage_table
        i = t.currentRow()
        j = i + d
        if i < 0 or not (0 <= j < t.rowCount()):
            return False
        vals = self._stage_values(i)
        cur = t.item(i, 0).toolTip() == "The current stage"
        t.removeRow(i)
        self._stage_row(vals[0], vals[1], vals[2], vals[3], vals[4], cur, at=j)
        t.setCurrentCell(j, 0)
        return True

    def add_stage(self, name="New stage"):
        i = self._stage_row(None, name, "", "", "")
        self.stage_table.setCurrentCell(i, 0)
        return i

    def remove_stage(self):
        t = self.stage_table
        i = t.currentRow()
        if i < 0:
            return False
        if t.item(i, 0).toolTip() == "The current stage":
            self.host.status("The current stage cannot be removed.")
            return False
        t.removeRow(i)
        return True

    def save_stages(self):
        r = self.rec
        rows, gates, bad = [], [], []
        for i in range(self.stage_table.rowCount()):
            sid, name, start, end, gate = self._stage_values(i)
            ds, de = (R.parse_date(start) if start.strip() else None), (R.parse_date(end) if end.strip() else None)
            if (start.strip() and ds is None) or (end.strip() and de is None):
                bad.append(name)
            rows.append((sid, name, ds.isoformat() if ds else "", de.isoformat() if de else ""))
            gates.append(gate)
        if bad:
            self.host.status("Dates not understood for: " + ", ".join(bad) + ". Write them like Nov 3, 2026.")
            return False
        try:
            new = r.edit_stages(rows)
        except ValueError as e:
            self.host.status(str(e))
            return False
        for s, g in zip(new, gates):
            r.set_gate(s["id"], g)
        diag.activity("qt_stages_saved")
        self.host.toast("Stages saved")
        self.refresh()
        return True



class StagesDialog(StageTableMixin, QDialog):
    """Effort Home > Edit stages...: rename, add, remove and reorder the effort's stages, with their planned dates and
    gates. Nothing changes until Save."""

    def __init__(self, page):
        super().__init__(page)
        self.page, self.host = page, page.host
        self.setWindowTitle(f"Stages of {self.host.effort_name}")
        self.resize(820, 460)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Double-click a stage's name or a date to change it. Dates as Nov 3, 2026. The current stage "
                            "cannot be removed. Gates: none; soft (moving on with open goals is logged); hard (held until "
                            "the goals are met, or overridden with a reason).", "muted"))
        self.stage_table = stage_table(); v.addWidget(self.stage_table, 1)
        row = QHBoxLayout(); v.addLayout(row)
        for text, fn in (("Up", lambda: self.move_row(-1)), ("Down", lambda: self.move_row(1)), ("+ Stage", lambda: self.add_stage()),
                         ("Remove", lambda: self.remove_stage())):
            row.addWidget(D.button(text, None if text != "Remove" else "ghost", fn))
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.save); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.saved = False
        self.fill_stages(self.rec)

    @property
    def rec(self):
        return R.Record(self.host.ws.root)

    def refresh(self):
        pass

    def save(self):
        if self.save_stages():
            self.saved = True
            self.accept()
            return True
        return False
