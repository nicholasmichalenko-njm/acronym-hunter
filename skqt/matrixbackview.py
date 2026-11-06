"""Compliance matrix > Bring the edited matrix back... and Merge another copy's matrix... (3.73.0): the workbook read
through the matrix's design, every value the team filled in listed against the export (or, for another copy, against
ours), the changes in both waiting for a pick, rows added or left out in the workbook listed and never applied.
matrixversions holds the rules."""
import os

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QVBoxLayout
import diag
import matrixversions as MV
from . import design as D
from .versionsview import ChangesTable


class MatrixBack(QDialog):
    def __init__(self, page, path, merge=False):
        super().__init__(page)
        self.page, self.host, self.path, self.merge = page, page.host, path, merge
        R = self.host.review
        self.changes = MV.compare(R.M, path, design=getattr(page, "d", None), effort_path=self.host.effort_path or "", merge=merge)
        for c in self.changes:
            c["section"] = str(c.get("label") or "")
        self.setWindowTitle(("Merge another copy's matrix: " if merge else "The edited matrix: ") + os.path.basename(path))
        self.resize(1200, 720)
        v = QVBoxLayout(self)
        vs = MV.versions(R.M)
        v.addWidget(D.label(("Every difference from this copy keeps ours unless you take theirs." if merge else
                             (f"Against the export of {vs[-1]['when']} (version {vs[-1]['v']}). " if vs else "")
                             + "What the team filled in comes back; a value also changed here since the export waits for your pick.")
                            + " Rows added or left out in the workbook are listed, never applied.", "muted"))
        top = QHBoxLayout(); v.addLayout(top)
        n = sum(1 for c in self.changes if c["kind"] == "Changed")
        self.sum = D.label(f"{n} value(s) to bring in, {sum(1 for c in self.changes if c['both'])} changed in both, "
                           f"{len(self.changes) - n} row(s) listed only", None)
        top.addWidget(self.sum, 1)
        self.only = QCheckBox("Only changed in both"); self.only.toggled.connect(lambda on: self.table.fill(True, on))
        top.addWidget(self.only)
        self.table = ChangesTable(self.changes, on_change=lambda: self.ready())
        if merge:                                            # another copy: every difference starts as ours
            self.table.values.update({c["i"]: "ours" for c in self.changes if c["both"]})
            self.table.fill(True)
        v.addWidget(self.table, 1)
        self.wait = D.label("", "muted"); v.addWidget(self.wait)
        bb = QDialogButtonBox()
        self.b_ok = bb.addButton("Bring the values in", QDialogButtonBox.AcceptRole)
        bb.addButton(QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.ready()

    def ready(self):
        w = self.table.waiting()
        self.b_ok.setEnabled(not w)
        self.wait.setText(f"{len(w)} change(s) in both wait for your pick." if w else "Ready.")

    def apply(self):
        R = self.host.review
        R.snap()
        picks = self.table.picks()
        n = MV.accept(R.M, self.changes, picks, self.path, effort_path=self.host.effort_path or "")
        diag.activity("matrix_brought_back", n=n)
        self.host.changed()
        self.page.refresh()
        self.host.toast(f"{n} value(s) brought in from {os.path.basename(self.path)}")
        return n


def bring_back(page, path=None, merge=False, accept=None, picks=None):
    if page.host.review is None:
        return None
    if path is None:
        path, _ = QFileDialog.getOpenFileName(page, "Another copy's matrix" if merge else "The edited matrix", "", "Excel (*.xlsx)")
        if not path:
            return None
    try:
        dlg = MatrixBack(page, path, merge)
    except ValueError as e:
        page.host.status(str(e))
        return None
    page.back_dialog = dlg
    for i, val in (picks or {}).items():
        dlg.table.pick(i, val)
    if accept is None:
        return dlg.apply() if dlg.exec() == QDialog.Accepted else None
    return dlg.apply() if accept else None
