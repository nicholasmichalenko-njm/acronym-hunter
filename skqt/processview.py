"""Settings > Stages, gates and roles (2.93.0): the team's default stages for new efforts, the gate choices a stage
offers, and the roles the people on an effort can hold. The three built-in gates (none, soft, hard) always stay: their
names and descriptions can change, what they do cannot. A team pack can carry these and lock them. On this PC only."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QListWidget, QListWidgetItem, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)
import diag
import process as PR
from . import design as D
from .stagesedit import clear_table, set_cell_widget

BEHAVIOR_TEXT = [("", "No hold"), ("soft", "Logged: allowed, open goals are logged"), ("hard", "Held: until the goals are met or overridden")]


def _table(heads, widths):
    t = QTableWidget(0, len(heads)); t.setHorizontalHeaderLabels(heads)
    t.verticalHeader().setVisible(False); t.setSelectionBehavior(QAbstractItemView.SelectRows)
    for i, w in enumerate(widths):
        if w:
            t.setColumnWidth(i, w)
    t.horizontalHeader().setSectionResizeMode(len(heads) - 1, QHeaderView.Stretch)
    t.verticalHeader().setDefaultSectionSize(34); t.setProperty("sk_rows_fixed", True)
    t.setMinimumHeight(260)
    return t


class ProcessCard(D.Card):
    def __init__(self, host):
        super().__init__("Stages, gates and roles",
                         "How your team runs an effort. New efforts start with these stages; efforts already started keep "
                         "their own (Effort Home > Edit stages...). The gate choices show in every effort's stage table; the "
                         "roles in the role drop-downs for the people on an effort.",
                         actions=[D.button("Put back the built-in ones", "ghost", lambda: self.reset()),
                                  D.button("Save", "primary", lambda: self.save())])
        self.host = host
        self.lock_note = self.add(D.label("", "muted"))
        self.tabs = QTabWidget(); self.add(self.tabs)
        # default stages
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(D.label("The stages a new effort starts with, in order, and each one's gate. Double-click a name to change it.", "muted"))
        self.st = _table(["Stage", "Gate"], (260, 0)); v.addWidget(self.st, 1)
        row = QHBoxLayout(); v.addLayout(row)
        for text, fn in (("Up", lambda: self.move_stage(-1)), ("Down", lambda: self.move_stage(1)),
                         ("+ Stage", lambda: self.add_stage()), ("Remove", lambda: self.remove_stage())):
            row.addWidget(D.button(text, "ghost" if text == "Remove" else None, fn))
        row.addStretch(1)
        self.tabs.addTab(w, "Default stages")
        # gate choices
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(D.label("What a stage's gate can be. Add your own (for example Color team sign-off: held) and say what it "
                            "means; the description shows when someone hovers over the choice. The three built-in gates stay; "
                            "rename them if your team calls them something else.", "muted"))
        self.gt = _table(["Gate", "What it does", "What it means"], (280, 300, 0)); v.addWidget(self.gt, 1)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("+ Gate", None, lambda: self.add_gate()))
        row.addWidget(D.button("Remove", "ghost", lambda: self.remove_gate()))
        row.addStretch(1)
        self.tabs.addTab(w, "Gate choices")
        # roles
        w = QWidget(); v = QVBoxLayout(w)
        v.addWidget(D.label("The roles offered for the people on an effort (Effort Record > Team and Effort Home > People and "
                            "roles...). Anyone can still type another. Double-click a role to change it.", "muted"))
        self.rl = QListWidget(); self.rl.setMinimumHeight(260); v.addWidget(self.rl, 1)
        row = QHBoxLayout(); v.addLayout(row)
        for text, fn in (("Up", lambda: self.move_role(-1)), ("Down", lambda: self.move_role(1)), ("+ Role", lambda: self.add_role()),
                         ("Remove", lambda: self.rl.takeItem(self.rl.currentRow()))):
            row.addWidget(D.button(text, "ghost" if text == "Remove" else None, fn))
        row.addStretch(1)
        self.tabs.addTab(w, "Roles")
        self.fill()

    # ------------------------------------------------------------ filling
    def fill(self, P=None):
        P = P or PR.load(self.host.config_dir)
        clear_table(self.gt)
        for g in P["gates"]:
            self._gate_row(g)
        clear_table(self.st)
        for name, gate in P["stages"]:
            self._stage_row(name, gate)
        self.rl.clear()
        for r in P["roles"]:
            self._role(r)
        import teampack as TP
        lk = TP.locked(self.host.config_dir, "process")
        self.lock_note.setText(f"Set by the team pack ({lk}). They change when the team sends a new pack." if lk else "")
        self.lock_note.setVisible(bool(lk))
        for x in (self.st, self.gt, self.rl):
            x.setEnabled(not lk)

    def _gate_names(self):
        out = []
        for i in range(self.gt.rowCount()):
            it = self.gt.item(i, 0)
            if it and it.text().strip():
                out.append((it.data(Qt.UserRole), it.text().strip()))
        return out

    def _gate_combo(self, gate=""):
        cb = QComboBox()
        for gid, name in self._gate_names():
            cb.addItem(name, gid)
        cb.setCurrentIndex(max(0, cb.findData(gate)))
        return cb

    def _stage_row(self, name, gate):
        i = self.st.rowCount(); self.st.insertRow(i)
        self.st.setItem(i, 0, QTableWidgetItem(name))
        self.st.setCellWidget(i, 1, self._gate_combo(gate))
        return i

    def _gate_row(self, g):
        i = self.gt.rowCount(); self.gt.insertRow(i)
        built = g.get("id") in ("", "soft", "hard")
        it = QTableWidgetItem(g["name"]); it.setData(Qt.UserRole, g.get("id"))
        if built:
            it.setToolTip("Built in: rename it if you like; it cannot be removed")
        self.gt.setItem(i, 0, it)
        cb = QComboBox()
        for k, text in BEHAVIOR_TEXT:
            cb.addItem(text, k)
        cb.setCurrentIndex(max(0, cb.findData(g.get("behavior", ""))))
        cb.setEnabled(not built)
        self.gt.setCellWidget(i, 1, cb)
        self.gt.setItem(i, 2, QTableWidgetItem(g.get("about", "")))
        return i

    def _role(self, text):
        it = QListWidgetItem(text); it.setFlags(it.flags() | Qt.ItemIsEditable); self.rl.addItem(it)
        return it

    def _refresh_stage_gates(self):
        for i in range(self.st.rowCount()):
            cur = self.st.cellWidget(i, 1).currentData()
            set_cell_widget(self.st, i, 1, self._gate_combo(cur))

    # ------------------------------------------------------------ editing
    def add_stage(self, name="New stage"):
        i = self._stage_row(name, "")
        self.st.setCurrentCell(i, 0)
        return i

    def remove_stage(self):
        i = self.st.currentRow()
        if i < 0:
            return False
        self.st.cellWidget(i, 1).hide()
        self.st.removeRow(i)
        return True

    def move_stage(self, d):
        t = self.st; i = t.currentRow(); j = i + d
        if i < 0 or not (0 <= j < t.rowCount()):
            return False
        name, gate = t.item(i, 0).text(), t.cellWidget(i, 1).currentData()
        t.cellWidget(i, 1).hide(); t.removeRow(i); t.insertRow(j)
        t.setItem(j, 0, QTableWidgetItem(name)); t.setCellWidget(j, 1, self._gate_combo(gate))
        t.setCurrentCell(j, 0)
        return True

    def add_gate(self, name="New gate", behavior="hard", about=""):
        import uuid
        i = self._gate_row({"id": "g_" + uuid.uuid4().hex[:8], "name": name, "behavior": behavior, "about": about})
        self.gt.setCurrentCell(i, 0)
        self._refresh_stage_gates()
        return i

    def remove_gate(self):
        i = self.gt.currentRow()
        if i < 0:
            return False
        if self.gt.item(i, 0).data(Qt.UserRole) in ("", "soft", "hard"):
            self.host.status("The built-in gates stay. Rename one instead.")
            return False
        self.gt.cellWidget(i, 1).hide(); self.gt.removeRow(i)
        self._refresh_stage_gates()
        return True

    def add_role(self, text="New role"):
        it = self._role(text)
        self.rl.setCurrentItem(it)
        return it

    def move_role(self, d):
        i = self.rl.currentRow(); j = i + d
        if i < 0 or not (0 <= j < self.rl.count()):
            return False
        it = self.rl.takeItem(i); self.rl.insertItem(j, it); self.rl.setCurrentRow(j)
        return True

    # ------------------------------------------------------------ saving
    def values(self):
        gates = []
        for i in range(self.gt.rowCount()):
            it = self.gt.item(i, 0)
            g = {"name": it.text() if it else "", "behavior": self.gt.cellWidget(i, 1).currentData(),
                 "about": self.gt.item(i, 2).text() if self.gt.item(i, 2) else ""}
            if it is not None and it.data(Qt.UserRole) is not None:
                g["id"] = it.data(Qt.UserRole)
            gates.append(g)
        stages = [(self.st.item(i, 0).text() if self.st.item(i, 0) else "", self.st.cellWidget(i, 1).currentData() or "")
                  for i in range(self.st.rowCount())]
        roles = [self.rl.item(i).text() for i in range(self.rl.count())]
        return stages, gates, roles

    def save(self):
        import teampack as TP
        if TP.locked(self.host.config_dir, "process"):
            self.host.status("The team pack set these. They change when the team sends a new pack.")
            return False
        stages, gates, roles = self.values()
        if not [n for n, _g in stages if n.strip()]:
            self.host.status("Keep at least one stage.")
            return False
        P = PR.save(self.host.config_dir, gates=gates, stages=stages, roles=roles)
        diag.activity("qt_process_saved", n=len(P["stages"]))
        self.host.toast("Stages, gates and roles saved")
        self.fill(P)
        return True

    def reset(self, answer=None):
        if answer is None:
            from PySide6.QtWidgets import QMessageBox
            answer = QMessageBox.question(self, "Stages, gates and roles", "Put back the built-in stages, gates and roles? Your own "
                                          "gates and roles are removed. Efforts already started keep their own stages.") == QMessageBox.Yes
        if not answer:
            return False
        self.fill({"stages": list(PR.DEFAULT_STAGES), "gates": [dict(g) for g in PR.BUILT_IN_GATES], "roles": list(PR.DEFAULT_ROLES)})
        return True
