"""The doors in the window (4.52.0; decisions 7, 80, 8, 9): Acronyms, Shred to setup and Check a document, from the Overview's
landing (nothing open), its compact row (something open) and Ctrl+K. A door and where the work goes are asked in one small
window, every time: the doors that take the files, then the 4.51.0 where-question (the open effort or program first and
picked). run() opens the home picked (homeask.settle) and hands the files on:
- Acronyms: the Acronyms page scans them in that home (toolshome.hand, the use "acronyms", shared with Quick tools).
- Shred to setup: Documents adds them as the customer's documents (its own reading, the table to check them and Add);
  once added, the window goes to Shred, where each is extracted for the shred. Efforts only.
- Check a document: Audit against the standards (toolshome.hand, the use "audit"); changes nothing.
Every function that would ask takes the answer (tests). Rules only (No AI); nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QListWidget, QListWidgetItem, QVBoxLayout

import diag
import doors as DR
import homes as HM
from . import design as D

REFUSE_SHRED = "Shred to setup works in an effort. Pick an effort, or a new one."
CANNOT_READ = "Stationkeeper does not read that kind of file."


def kind_now(host):
    """The kind of home open now: "none", "effort" or "program"."""
    return DR.home_kind(host.efforts, host.ws is not None, getattr(host, "effort_name", ""))


def _is_program_pick(host, picked):
    import programs as PG
    if not picked:
        return False
    return picked[0] == HM.NEW_PROGRAM or (picked[0] == HM.HOME and PG.is_program(host.efforts, picked[1]))


def run(host, door, paths, picked, choices=None):
    """Open the home picked and hand the files to the door. choices (tests): Documents' table answers for Shred to setup.
    Returns the name of the home the work went to, or None (the status line says why)."""
    from .homeask import settle
    from . import toolshome as TH
    paths = [p for p in (paths or []) if p]
    if door not in DR.KEYS or not paths:
        return None
    if not DR.takes(door, paths):
        host.status(CANNOT_READ)
        return None
    if door == "shred" and _is_program_pick(host, picked):
        host.status(REFUSE_SHRED)
        return None
    name = settle(host, picked)
    if not name:
        return None
    diag.activity("door_used", n=DR.KEYS.index(door))
    if door == "acronyms":
        TH.hand(host, "acronyms", paths)
    elif door == "check":
        TH.hand(host, "audit", paths)
    else:
        shred(host, name, paths, choices)
    return name


def shred(host, name, paths, choices=None):
    """Add the files to the effort's Documents as the customer's documents; once added, go to Shred. Returns Documents'
    worker (or what its add gave)."""
    lp = host.library_page
    stems = {os.path.splitext(os.path.basename(p))[0].casefold() for p in paths}

    def then(made):
        files = [os.path.splitext(os.path.basename(str((v or {}).get("file") or (d or {}).get("name") or "")))[0].casefold()
                 for d, v in (made or [])]
        if host.ws is not None and host.effort_name == name and (not made or any(any(f.startswith(s) for s in stems) for f in files)):
            host.go("assign")
    host.go("library")
    lp.then = then
    got = lp.add(paths, category="customer", choices=choices)
    if got is None:
        lp.then = None
    return got


class DoorDialog(QDialog):
    """One step: the files, the door, and where the work goes."""

    def __init__(self, parent, host, paths, door=None):
        super().__init__(parent)
        from .homeask import WhereBox
        self.host, self.paths = host, list(paths or [])
        self.setWindowTitle("What do you want to do?"); self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        names = ", ".join(os.path.basename(p) for p in self.paths[:3]) + (f" and {len(self.paths) - 3} more" if len(self.paths) > 3 else "")
        v.addWidget(D.label(names, "label"))
        self.list = QListWidget(); self.list.setMaximumHeight(110); v.addWidget(self.list)
        for k in DR.doors_for(kind_now(host), self.paths):
            it = QListWidgetItem(f"{DR.NAMES[k]}: {DR.WHAT[k]}"); it.setData(Qt.UserRole, k)
            self.list.addItem(it)
        self.where = WhereBox(host.efforts, host.effort_name if host.ws is not None else "", self.paths, host=host)
        v.addWidget(self.where)
        self.all_btn = D.button("All tools...", "ghost", lambda: self.all_tools(), "Every tool that takes these files, in Quick tools")
        v.addWidget(self.all_btn, 0, Qt.AlignLeft)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        self.ok_btn = bb.button(QDialogButtonBox.Ok)
        v.addWidget(bb)
        self.where.on_change = self.settle_ok
        self.list.currentItemChanged.connect(lambda *_a: self.door_changed())
        self.list.itemDoubleClicked.connect(lambda _i: self.accept() if self.ok_btn.isEnabled() else None)
        keys = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        if keys:
            self.list.setCurrentRow(keys.index(door) if door in keys else 0)
        self.handed = False
        self.door_changed()

    def door_changed(self):
        d = self.picked()
        if d is not None:
            self.where.fill(programs=DR.wants_programs(d))
        return self.settle_ok()

    def settle_ok(self):
        ok = self.picked() is not None and self.where.ok()
        self.ok_btn.setEnabled(ok)
        return ok

    def picked(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it is not None else None

    def all_tools(self):
        """Hand the files to Quick tools' own question instead."""
        self.handed = True
        self.reject()
        self.host.go("tools")
        return self.host.tools_page.files_in(self.paths)


def ask(host, paths, door=None, answer=None):
    """Ask which door and where (one step), then run it. answer (tests): (door, picked) instead of asking. Returns the
    home the work went to, or None."""
    paths = [p for p in (paths or []) if p]
    if not paths:
        return None
    if answer is None:
        if not DR.doors_for(kind_now(host), paths):
            host.status(CANNOT_READ)
            return None
        d = DoorDialog(host, host, paths, door)
        if d.exec() != QDialog.Accepted:
            return None
        answer = (d.picked(), d.where.picked())
    return run(host, answer[0], paths, answer[1])


def file_filter(door=None):
    import app_gui as A
    exts = sorted(DR.exts(door)) if door else sorted(A.SUPPORTED_EXTS)
    label = DR.NAMES.get(door, "Documents and pictures")
    return f"{label} ({' '.join('*' + e for e in exts)})"


def choose(host, door=None, paths=None, answer=None):
    """A file dialog filtered to what the door reads (every file Stationkeeper reads when door is None), then ask.
    paths, answer (tests): the files chosen and the answer to the door's question."""
    if paths is None:
        paths, _ = QFileDialog.getOpenFileNames(host, "Choose a document", "", file_filter(door))
    if not paths:
        return None
    return ask(host, paths, door, answer)
