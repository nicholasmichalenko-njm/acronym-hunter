"""Settings > Review: decisions and captures (3.29.0): every decision and capture Review offers, the team's way: name,
key, color, shown or hidden, on the capture bar or in More, in what order; which decisions each effort type hides or
shows; the team's own captures (add, change, take out). Keys used twice or kept by Review are named. The rules are
reviewitems.py's."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QHBoxLayout, QHeaderView, QInputDialog, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton, QTableWidget, QTabWidget, QVBoxLayout, QWidget)

import diag
import excerpts as EX
import reviewitems as RI
from . import design as D


def _color_btn(color, on_pick):
    b = QPushButton(color)
    b.setStyleSheet(f"QPushButton{{border-left:14px solid {color};padding-left:6px;}}")

    def pick():
        c = QColorDialog.getColor(QColor(b.text()), b)
        if c.isValid():
            b.setText(c.name()); b.setStyleSheet(f"QPushButton{{border-left:14px solid {c.name()};padding-left:6px;}}")
            on_pick()
    b.clicked.connect(pick)
    return b


class ReviewItemsDialog(QDialog):
    def __init__(self, parent, host):
        super().__init__(parent)
        self.host = host
        self.data = RI.load(host.config_dir)
        self.setWindowTitle("Review: decisions and captures"); self.resize(1080, 680)
        v = QVBoxLayout(self)
        v.addWidget(D.label("What Review offers and how it looks. A built-in still does what it always did (a contact goes to "
                            "Customer information); its name, key, color and showing are yours. Saved on this PC; a team pack "
                            "carries the team's captures.", "muted"))
        self.tabs = QTabWidget(); v.addWidget(self.tabs, 1)
        # decisions
        w = QWidget(); dv = QVBoxLayout(w)
        self.dt = QTableWidget(0, 5); self.dt.setHorizontalHeaderLabels(["Name (button and legend)", "Short", "Key", "Color", "Shows"])
        self.dt.verticalHeader().setVisible(False); self.dt.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        dv.addWidget(self.dt, 1)
        eh = QHBoxLayout(); dv.addLayout(eh)
        eh.addWidget(D.label("Effort type", "label", wrap=False))
        self.et = QComboBox(); eh.addWidget(self.et)
        eh.addWidget(D.label("hides", "label", wrap=False))
        self.et_hide = QListWidget(); self.et_hide.setMaximumHeight(120); eh.addWidget(self.et_hide, 1)
        eh.addWidget(D.label("and shows", "label", wrap=False))
        self.et_show = QListWidget(); self.et_show.setMaximumHeight(120); eh.addWidget(self.et_show, 1)
        self.et.currentIndexChanged.connect(lambda _i: self.fill_et())
        self.et_hide.itemChanged.connect(lambda _it: self.read_et())
        self.et_show.itemChanged.connect(lambda _it: self.read_et())
        self.tabs.addTab(w, "Decisions")
        # captures
        w2 = QWidget(); cv = QVBoxLayout(w2)
        self.ct = QTableWidget(0, 6); self.ct.setHorizontalHeaderLabels(["Name", "Key", "Color", "Shows", "Where", "What it does"])
        self.ct.verticalHeader().setVisible(False); self.ct.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.ct.setSelectionBehavior(QTableWidget.SelectRows)
        cv.addWidget(self.ct, 1)
        oh = QHBoxLayout(); cv.addLayout(oh)
        oh.addWidget(D.button("Up", "ghost", lambda: self.move(-1))); oh.addWidget(D.button("Down", "ghost", lambda: self.move(1)))
        oh.addStretch(1)
        cv.addWidget(D.label("The team's own captures (every effort on this PC; a team pack carries them)", "label"))
        self.team = QListWidget(); self.team.setMaximumHeight(140); cv.addWidget(self.team)
        th = QHBoxLayout(); cv.addLayout(th)
        th.addWidget(D.button("+ Capture...", None, lambda: self.add_team()))
        th.addWidget(D.button("Rename...", "ghost", lambda: self.rename_team()))
        th.addWidget(D.button("Color...", "ghost", lambda: self.color_team()))
        th.addWidget(D.button("Take out", "danger", lambda: self.remove_team()))
        th.addStretch(1)
        self.tabs.addTab(w2, "Captures")
        bh = QHBoxLayout(); v.addLayout(bh)
        self.clash = D.label("", "muted"); bh.addWidget(self.clash, 1)
        bh.addWidget(D.button("Back to the built-in values", "ghost", lambda: self.reset()))
        bh.addWidget(D.button("Save", "primary", lambda: self.save()))
        bh.addWidget(D.button("Close", "ghost", lambda: self.reject()))
        self.fill()

    # ------------------------------------------------------------------ filling
    def fill(self):
        self.loading = True
        d = self.data["decisions"]
        self.dt.setRowCount(0)
        for code, *_r in RI.DECISIONS:
            x = d[code]
            r = self.dt.rowCount(); self.dt.insertRow(r)
            for c, k in ((0, "name"), (1, "short"), (2, "key")):
                e = QLineEdit(x[k]); e.textEdited.connect(lambda _t: self.read()); self.dt.setCellWidget(r, c, e)
            self.dt.setCellWidget(r, 3, _color_btn(x["color"], self.read))
            cb = QCheckBox(); cb.setChecked(x["shown"]); cb.toggled.connect(lambda _v: self.read()); self.dt.setCellWidget(r, 4, cb)
        self.et.blockSignals(True); self.et.clear()
        try:
            import prodrules as PRL
            for e in PRL.load(self.host.config_dir).get("effort_types", []):
                self.et.addItem(e["name"], e["id"])
        except Exception:  # noqa: BLE001
            diag.swallowed()
        if self.et.findData("rfi") < 0:
            self.et.addItem("RFI response", "rfi")
        self.et.blockSignals(False)
        self.fill_et()
        self.ct.setRowCount(0)
        for key in self.data["order"]:
            x = self.data["captures"][key]
            r = self.ct.rowCount(); self.ct.insertRow(r)
            e = QLineEdit(x["name"]); e.textEdited.connect(lambda _t: self.read()); self.ct.setCellWidget(r, 0, e)
            e.setProperty("key", key)
            k = QLineEdit(x["keyseq"]); k.setPlaceholderText("none"); k.textEdited.connect(lambda _t: self.read()); self.ct.setCellWidget(r, 1, k)
            self.ct.setCellWidget(r, 2, _color_btn(x["color"], self.read))
            cb = QCheckBox(); cb.setChecked(x["shown"]); cb.toggled.connect(lambda _v: self.read()); self.ct.setCellWidget(r, 3, cb)
            pl = QComboBox(); pl.addItem("On the bar", "bar"); pl.addItem("In More...", "more")
            pl.setCurrentIndex(max(0, pl.findData(x["place"]))); pl.currentIndexChanged.connect(lambda _i: self.read())
            self.ct.setCellWidget(r, 4, pl)
            from PySide6.QtWidgets import QTableWidgetItem
            it = QTableWidgetItem(x["does"]); it.setFlags(Qt.ItemIsEnabled); self.ct.setItem(r, 5, it)
        self.ct.resizeColumnsToContents()
        self.fill_team()
        self.loading = False
        self.show_clash()

    def fill_et(self):
        et = self.et.currentData() or ""
        hide, show = set(self.data["hide"].get(et, [])), set(self.data["show"].get(et, []))
        for lst, on in ((self.et_hide, hide), (self.et_show, show)):
            lst.blockSignals(True); lst.clear()
            for code, *_r in RI.DECISIONS:
                it = QListWidgetItem(self.data["decisions"][code]["name"]); it.setData(Qt.UserRole, code)
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked if code in on else Qt.Unchecked)
                lst.addItem(it)
            lst.blockSignals(False)

    def read_et(self):
        et = self.et.currentData() or ""
        for lst, k in ((self.et_hide, "hide"), (self.et_show, "show")):
            self.data[k][et] = [lst.item(i).data(Qt.UserRole) for i in range(lst.count()) if lst.item(i).checkState() == Qt.Checked]

    def fill_team(self):
        self.team.clear()
        for b in EX.team_bins(self.host.config_dir):
            it = QListWidgetItem(D.dot_icon(b["color"]), b["name"]); it.setData(Qt.UserRole, b["name"]); self.team.addItem(it)

    # ------------------------------------------------------------------ reading
    def read(self):
        if getattr(self, "loading", False):
            return
        for r, (code, *_x) in enumerate(RI.DECISIONS):
            d = self.data["decisions"][code]
            d["name"] = self.dt.cellWidget(r, 0).text().strip() or d["name"]
            d["short"] = self.dt.cellWidget(r, 1).text().strip() or d["short"]
            d["key"] = self.dt.cellWidget(r, 2).text().strip().upper()[:12]
            d["color"] = self.dt.cellWidget(r, 3).text()
            d["shown"] = self.dt.cellWidget(r, 4).isChecked()
        for r in range(self.ct.rowCount()):
            key = self.ct.cellWidget(r, 0).property("key")
            c = self.data["captures"][key]
            c["name"] = self.ct.cellWidget(r, 0).text().strip() or c["name"]
            c["keyseq"] = self.ct.cellWidget(r, 1).text().strip().upper()[:12]
            c["color"] = self.ct.cellWidget(r, 2).text()
            c["shown"] = self.ct.cellWidget(r, 3).isChecked()
            c["place"] = self.ct.cellWidget(r, 4).currentData()
        self.show_clash()

    def show_clash(self):
        cl = RI.clashes(self.data)
        self.clash.setText(("Keys to fix: " + "; ".join(f"{k} is {' and '.join(n)}" for k, n in cl)) if cl else "No key is used twice.")
        return cl

    def move(self, step):
        r = self.ct.currentRow()
        if r < 0 or not (0 <= r + step < len(self.data["order"])):
            return
        self.read()
        o = self.data["order"]
        o[r], o[r + step] = o[r + step], o[r]
        self.fill(); self.ct.selectRow(r + step)

    # ------------------------------------------------------------------ the team's own captures
    def _team(self):
        return EX.team_bins(self.host.config_dir)

    def add_team(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "New capture for the team", "Its name (for example Transition risk):")
            if not ok:
                return None
        name = " ".join((name or "").split())
        if not name or name.casefold() in {b["name"].casefold() for b in self._team()} or name.casefold() in {n.casefold() for n in EX.NAME.values()}:
            return None
        used = {b["color"] for b in self._team()}
        color = next((c for c in EX.COLORS if c not in used), EX.COLORS[0])
        EX.save_team_bins(self.host.config_dir, self._team() + [{"name": name, "color": color, "feeds": ["setup"], "shared": True}])
        diag.activity("team_capture_added")
        self.fill_team()
        return name

    def _cur(self):
        it = self.team.currentItem()
        return it.data(Qt.UserRole) if it else None

    def rename_team(self, new=None):
        old = self._cur()
        if not old:
            return False
        if new is None:
            new, ok = QInputDialog.getText(self, "Rename", "New name:", text=old)
            if not ok:
                return False
        lst = self._team()
        for b in lst:
            if b["name"] == old and new.strip():
                b["name"] = " ".join(new.split())
        EX.save_team_bins(self.host.config_dir, lst); self.fill_team()
        return True

    def color_team(self, color=None):
        name = self._cur()
        if not name:
            return False
        if color is None:
            c = QColorDialog.getColor(parent=self)
            if not c.isValid():
                return False
            color = c.name()
        lst = self._team()
        for b in lst:
            if b["name"] == name:
                b["color"] = color
        EX.save_team_bins(self.host.config_dir, lst); self.fill_team()
        return True

    def remove_team(self):
        name = self._cur()
        if not name:
            return False
        EX.save_team_bins(self.host.config_dir, [b for b in self._team() if b["name"] != name]); self.fill_team()
        return True

    # ------------------------------------------------------------------ keeping it
    def reset(self):
        self.data = RI.reset(self.host.config_dir)
        self.fill()
        self.apply()

    def save(self):
        self.read(); self.read_et()
        RI.save(self.host.config_dir, self.data)
        diag.activity("review_items_saved")
        self.apply()
        self.host.toast("Review's decisions and captures saved")
        return True

    def apply(self):
        try:
            self.host.assign_page.apply_items()
        except Exception:  # noqa: BLE001
            diag.swallowed()
