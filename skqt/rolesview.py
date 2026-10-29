"""People and roles on an effort (2.93.0): every name that shows in the effort with a role drop-down (the team's roles
from Settings > Stages, gates and roles, or any typed). A role saves the moment it is picked; nothing else to press.
Used in Effort Record > Team and in Effort Home > People and roles... Nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)
import diag
import effortrec as R
import process as PR
from . import design as D
from .stagesedit import clear_table


def role_combo(roles, current=""):
    cb = QComboBox(); cb.setEditable(True); cb.setInsertPolicy(QComboBox.NoInsert)
    cb.addItem("")
    for r in roles:
        cb.addItem(r)
    if current and cb.findText(current) < 0:
        cb.addItem(current)
    cb.setCurrentText(current)
    cb.lineEdit().setPlaceholderText("Pick or type a role")
    return cb


class TeamRoles(QWidget):
    """The names in the effort, each with a role that saves when picked."""

    def __init__(self, host, on_change=None):
        super().__init__()
        self.host, self.on_change = host, on_change
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 2); self.table.setHorizontalHeaderLabels(["Name", "Role on this effort"])
        self.table.verticalHeader().setVisible(False); self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setColumnWidth(0, 260); self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(34); self.table.setProperty("sk_rows_fixed", True)
        self.table.setMinimumHeight(180)
        v.addWidget(self.table, 1)
        self.note = D.label("", "muted"); v.addWidget(self.note)

    @property
    def rec(self):
        return R.Record(self.host.ws.root) if self.host.ws else None

    def fill(self):
        r = self.rec
        t = self.table
        clear_table(t)
        if r is None:
            return
        roles = PR.load(self.host.config_dir)["roles"]
        names = self.host.authors.for_effort(self.host.effort_name)
        for n in names:
            i = t.rowCount(); t.insertRow(i)
            it = QTableWidgetItem(n); it.setFlags(it.flags() & ~Qt.ItemIsEditable); t.setItem(i, 0, it)
            cb = role_combo(roles, r.role_of(n))
            cb.activated.connect(lambda _k, name=n, c=cb: self.save_role(name, c.currentText()))
            cb.lineEdit().editingFinished.connect(lambda name=n, c=cb: self.save_role(name, c.currentText()))
            t.setCellWidget(i, 1, cb)
        self.note.setText("Roles save as you pick them. The role list is in Settings > Stages, gates and roles; type any other."
                          if names else f"No names show in {self.host.effort_name} yet. Choose people adds names from the "
                          "author list; add new names in Settings > Author list.")

    def save_role(self, name, role):
        r = self.rec
        if r is None:
            return False
        if r.set_role(name, role):
            diag.activity("qt_role_set")
            self.host.status(f"{name}: {role or 'no role'} on {self.host.effort_name}")
            if self.on_change:
                self.on_change()
            return True
        return False

    def role_box(self, name):
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).text() == name:
                return self.table.cellWidget(i, 1)
        return None


class PeopleRolesDialog(QDialog):
    """Effort Home > People and roles...: who works on this effort and in what role."""

    def __init__(self, host, parent=None):
        super().__init__(parent)
        self.host = host
        self.setWindowTitle(f"People and roles on {host.effort_name}")
        self.resize(640, 480)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Pick each person's role on this effort. Choose people... adds or removes names from the author list.", "muted"))
        self.roles = TeamRoles(host); v.addWidget(self.roles, 1)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Choose people...", None, lambda: self.choose()))
        row.addWidget(D.button("Edit the role list...", "ghost", lambda: self.edit_list()))
        row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.accept); bb.accepted.connect(self.accept)
        v.addWidget(bb)
        self.roles.fill()

    def choose(self, answer=None):
        got = self.host.record_page.choose_team(answer=answer)
        self.roles.fill()
        return got

    def edit_list(self):
        self.accept()
        self.host.go("settings")
        self.host.settings_page.focus_process()
        self.host.settings_page.process_card.tabs.setCurrentIndex(2)
