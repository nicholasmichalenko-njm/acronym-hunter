"""Production > Templates (3.52.0): every Word template the Effort Profiles make, one row per effort type, profile and
volume, Ready, Needs review, Blocked or Not made yet, with why. Make .dotx makes one; Make all ready makes every row
that nothing stops and that changed or was never made; Open opens the last one made (Word on this PC). The templates go
in the output folder's Templates\\<effort type> folder. Making templates is a Preview tool until the team turns it on.
Rules only (templatesboard.py); nothing leaves the PC."""
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

import diag
import templatesboard as TB
from . import design as D

TONE = {TB.READY: "ok", TB.REVIEW: "warn", TB.BLOCKED: "crit", TB.NEW: "muted"}
COLS = ["Effort type", "Profile", "Volume", "State", "Why", ""]


class TemplatesPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.rows = []
        outer = QVBoxLayout(self); outer.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        outer.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); outer.addLayout(top)
        top.addWidget(D.label("The list follows from your Effort Profiles: each profile names its volumes. A changed library item "
                              "marks every template that uses it Needs review.", "muted"), 1)
        top.addWidget(D.label("Show", "label", wrap=False))
        self.f_et = QComboBox(); self.f_et.currentIndexChanged.connect(lambda _i: self.fill()); top.addWidget(self.f_et)
        self.b_all = D.button("Make all ready", "primary", lambda: self.make_all(), "Every template nothing stops that changed or was never made")
        self.b_folder = D.button("Open the folder", "ghost", lambda: self.open_folder())
        top.addWidget(self.b_all); top.addWidget(self.b_folder)
        self.sum = D.label("", "muted"); outer.addWidget(self.sum)
        self.t = QTableWidget(0, len(COLS)); self.t.setHorizontalHeaderLabels(COLS)
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows); self.t.setWordWrap(True)
        self.t.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        for i, w in enumerate((170, 170, 190, 110)):
            self.t.setColumnWidth(i, w)
        self.t.setColumnWidth(5, 230)
        outer.addWidget(self.t, 1)

    def folder(self):
        import app_gui
        import prodcopy as PCY
        return os.path.join(PCY.output_folder(app_gui.load_settings() or {}, app_gui.DATA_DIR), "Templates")

    def refresh(self):
        self.rows = TB.rows(self.host.config_dir)
        keep = self.f_et.currentData()
        self.f_et.blockSignals(True); self.f_et.clear(); self.f_et.addItem("Every effort type", "")
        for eid, name in dict((r["eid"], r["ename"]) for r in self.rows).items():
            self.f_et.addItem(name, eid)
        i = self.f_et.findData(keep)
        self.f_et.setCurrentIndex(max(0, i)); self.f_et.blockSignals(False)
        self.fill()

    def shown(self):
        eid = self.f_et.currentData()
        return [r for r in self.rows if not eid or r["eid"] == eid]

    def fill(self):
        rows = self.shown()
        self.t.setRowCount(0)
        for r_ in rows:
            r = self.t.rowCount(); self.t.insertRow(r)
            for c, text in enumerate((r_["ename"], r_["pname"], r_["volume"], r_["state"], r_["why"])):
                it = QTableWidgetItem(text); it.setData(Qt.UserRole, r)
                if c == 3:
                    it.setForeground(D.color(TONE.get(r_["state"], "muted")))
                self.t.setItem(r, c, it)
            cell = QWidget(); h = QHBoxLayout(cell); h.setContentsMargins(2, 0, 2, 0); h.setSpacing(4)
            mk = D.button("Make .dotx", None, lambda _=False, x=r_: self.make(x))
            mk.setEnabled(r_["state"] != TB.BLOCKED)
            h.addWidget(mk)
            if r_.get("path") and os.path.isfile(r_["path"]):
                h.addWidget(D.button("Open in Word", "ghost", lambda _=False, x=r_: self.open(x)))
            h.addStretch(1)
            self.t.setCellWidget(r, 5, cell)
        self.t.resizeRowsToContents()
        n = {s: sum(1 for x in rows if x["state"] == s) for s in (TB.READY, TB.REVIEW, TB.BLOCKED, TB.NEW)}
        self.sum.setText(f"{len(rows)} template(s): {n[TB.READY]} ready, {n[TB.REVIEW]} need review, {n[TB.BLOCKED]} blocked, "
                         f"{n[TB.NEW]} not made yet.")

    def _allowed(self):
        import roleaccess as RA
        if RA.preview_on(self.host.config_dir, "template"):
            return True
        self.host.status("Making templates is a Preview tool: turn it on in Settings > Preview tools.")
        return False

    def make(self, row, word=None):
        if row["state"] == TB.BLOCKED or not self._allowed():
            return None
        if word is None and sys.platform.startswith("win"):
            import prodword
            word = prodword.update_fields
        try:
            job = TB.make(self.host.config_dir, self.folder(), row, word=word)
        except Exception as e:  # noqa: BLE001
            diag.swallowed()
            self.host.status(f"The template was not made ({type(e).__name__}).")
            return None
        diag.activity("template_made_from_board")
        self.host.status(f"Made {os.path.basename(job.copy)}")
        self.refresh()
        return job

    def make_all(self, word=None):
        todo = [r for r in self.shown() if r["state"] in (TB.REVIEW, TB.NEW)]
        if not todo:
            self.host.status("Nothing to make: every template is ready or blocked.")
            return []
        if not self._allowed():
            return []
        out = [j for j in (self.make(r, word=word) for r in todo) if j is not None]
        self.host.status(f"{len(out)} template(s) made in {self.folder()}.")
        return out

    def open(self, row):
        if row.get("path") and os.path.isfile(row["path"]) and sys.platform.startswith("win"):
            os.startfile(row["path"])                       # noqa: S606  a template this PC made
        return row.get("path")

    def open_folder(self):
        f = self.folder()
        os.makedirs(f, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(f)                                 # noqa: S606  the output folder
        return f
