"""Where does it go? (4.51.0): the home a dropped file goes to, asked in the same step as the tool (decisions 9, 44, 60).
WhereBox lists the open effort or program first, the other efforts, the other programs, a new effort and a new program;
a new one takes a name, filled in from the file's name, and a new effort the folder it is saved in (4.79.0). settle opens the home picked (making a new one first).
NameItDialog names what Unfiled holds, from before, as an effort or a program. The rules are homes'. Rules only (No AI);
nothing leaves the PC."""
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QRadioButton,
                               QVBoxLayout, QWidget)

import diag
import homes as HM
from . import design as D


class WhereBox(QWidget):
    """The where-question: a list of homes and, for a new one, its name."""

    def __init__(self, registry, open_name="", paths=None, programs=True, host=None):
        super().__init__()
        self.registry, self.open_name, self.paths, self.host = registry, open_name or "", list(paths or []), host
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(4)
        v.addWidget(D.label("Where does it go?", "label"))
        self.combo = QComboBox(); v.addWidget(self.combo)
        self.name = QLineEdit(); self.name.setPlaceholderText("Its name"); v.addWidget(self.name)
        from .starteffort import SavedIn                    # 4.79.0 (UX decision 184): a new effort asks where it is saved
        self.saved_label = D.label("Saved in", "label"); v.addWidget(self.saved_label)
        self.saved = SavedIn(host); v.addWidget(self.saved)
        self.saved.changed.connect(self.update_state)
        self.reason = D.label("", "warn"); v.addWidget(self.reason)
        self.name.setText(HM.free_name(registry, HM.suggest_name(self.paths)))
        self.combo.currentIndexChanged.connect(lambda _i: self.update_state())
        self.name.textChanged.connect(lambda _t: self.update_state())
        self.on_change = None
        self.fill(programs)

    def fill(self, programs=True):
        """Fill the list (the open home first and picked); a pick already made is kept when it is still listed."""
        keep = self.combo.currentData()
        self.combo.blockSignals(True)
        self.combo.clear()
        for c in HM.choices(self.registry, self.open_name, self.paths, programs=programs):
            self.combo.addItem(c["label"], c["key"])
        i = self.combo.findData(keep) if keep is not None else -1
        self.combo.setCurrentIndex(i if i >= 0 else 0)
        self.combo.blockSignals(False)
        self.update_state()
        return [self.combo.itemData(k) for k in range(self.combo.count())]

    def kind(self):
        return (self.combo.currentData() or (None, None))[0]

    def why(self):
        """Why the new name cannot be used ('' when it can, or when no new home is picked)."""
        if self.kind() not in (HM.NEW_EFFORT, HM.NEW_PROGRAM):
            return ""
        why = HM.check_new(self.registry, self.name.text(), "program" if self.kind() == HM.NEW_PROGRAM else "effort")
        if not why and self.kind() == HM.NEW_EFFORT:
            from .starteffort import saved_in_problem
            why = saved_in_problem(self.host, self.saved.folder())
        return why

    def update_state(self):
        self.name.setVisible(self.kind() in (HM.NEW_EFFORT, HM.NEW_PROGRAM))
        self.saved_label.setVisible(self.kind() == HM.NEW_EFFORT); self.saved.setVisible(self.kind() == HM.NEW_EFFORT)
        why = self.why()
        self.reason.setText(why)
        self.reason.setVisible(bool(why))
        if self.on_change:
            self.on_change()
        return why

    def ok(self):
        return self.kind() is not None and not self.why()

    def picked(self):
        k, name = self.combo.currentData() or (None, None)
        if k == HM.NEW_EFFORT:
            return (k, self.name.text().strip(), self.saved.folder())
        if k == HM.NEW_PROGRAM:
            return (k, self.name.text().strip())
        return (k, name) if k else None


def _new_effort(host, name, folder):
    """An effort made from its name and the folder it is saved in, as the Start an effort form makes one (4.79.0)."""
    from .starteffort import list_path, saved_in_problem, start_effort
    why = saved_in_problem(host, folder)
    if why:
        host.status(why)
        return None
    return start_effort(host, {"name": name, "path": list_path(folder, name), "first_use": "volume"})


def settle(host, picked):
    """Open the home picked, making a new one first. Returns the name of the home open afterwards, or None (the status
    line says why)."""
    import unfiled as UF
    reg = host.efforts
    kind, name = tuple(picked)[:2] if picked else (None, None)
    folder = tuple(picked)[2] if picked and len(picked) > 2 else ""          # 4.79.0: a new effort's Saved in
    name = (name or "").strip()
    if kind == HM.HOME:
        info = reg.get(name) or {}
        if not info or info.get("archived") or info.get("unfiled") or name == UF.NAME:
            host.status("Pick where it goes: an effort or a program.")
            return None
        if (host.ws is None or host.effort_name != name) and not host.open_effort(name):
            return None
        host.effort_box.setCurrentText(name)
        return name
    if kind in (HM.NEW_EFFORT, HM.NEW_PROGRAM):
        why = HM.check_new(reg, name, "program" if kind == HM.NEW_PROGRAM else "effort")
        if why:
            host.status(why)
            return None
        if kind == HM.NEW_PROGRAM:
            from .programsview import new_program
            got = new_program(host, name)
        else:
            got = _new_effort(host, name, folder)
        if got:
            diag.activity("home_made_for_file", n=1 if kind == HM.NEW_PROGRAM else 0)
        return got or None
    host.status("Pick where it goes: an effort or a program.")
    return None


class NameItDialog(QDialog):
    """Name what Unfiled holds, from before: a name, An effort or A program, Name it or Not now."""

    def __init__(self, parent, name, sentence="", registry=None):
        super().__init__(parent)
        self.registry = registry
        self.setWindowTitle("Name it"); self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        if sentence:
            s = QLabel(sentence); s.setWordWrap(True); v.addWidget(s)
        v.addWidget(D.label("Its name", "label"))
        self.name = QLineEdit(name); v.addWidget(self.name)
        row = QHBoxLayout(); v.addLayout(row)
        self.effort = QRadioButton("An effort"); self.program = QRadioButton("A program")
        self.effort.setChecked(True)
        row.addWidget(self.effort); row.addWidget(self.program); row.addStretch(1)
        self.reason = D.label("", "warn"); v.addWidget(self.reason)
        bb = QDialogButtonBox()
        self.go = bb.addButton("Name it", QDialogButtonBox.AcceptRole)
        bb.addButton("Not now", QDialogButtonBox.RejectRole)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.name.textChanged.connect(lambda _t: self.check())
        self.program.toggled.connect(lambda _on: self.check())
        self.check()

    def check(self):
        kind, name = self.values()
        why = HM.check_new(self.registry, name, kind) if self.registry is not None else ("" if name else "Give it a name.")
        self.reason.setText(why); self.reason.setVisible(bool(why))
        self.go.setEnabled(not why)
        return why

    def values(self):
        return ("program" if self.program.isChecked() else "effort"), self.name.text().strip()
