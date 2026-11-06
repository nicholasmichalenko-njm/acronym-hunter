"""Add to this effort... (3.70.0): another copy of the same effort merged in, or files added to its Library. Pick where
from (another effort on this PC, archived ones included; an effort's folder; an effort package; or files and folders),
keep or untick the parts, Merge. One summary follows: what was added, what was already the same, and what to review (ours
kept, theirs beside it). effortmerge holds the rules; the source is only read."""
import os

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHeaderView, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)
import diag
import effortmerge as EM
from . import design as D

FOLDER, PACKAGE, FILES = "__folder__", "__package__", "__files__"


class MergeDialog(QDialog):
    def __init__(self, host, target):
        super().__init__(host)
        self.host, self.target = host, target
        self.setWindowTitle(f"Add to {target}")
        v = QVBoxLayout(self)
        v.addWidget(D.label(f"Bring work into {target} from another copy of it: someone else's, an earlier one, or one on "
                            "another PC. The other copy is only read. A file already here is not copied again; anything "
                            "changed in both copies keeps ours and is listed for you to review.", "muted"))
        v.addWidget(D.label("From", "label"))
        self.src = QComboBox(); self.src.setMinimumWidth(420)
        for n in host.efforts.names():
            info = host.efforts.get(n) or {}
            if n != target and not info.get("unfiled") and info.get("path"):
                self.src.addItem(n + ("  (archived)" if info.get("archived") else ""), n)
        self.src.addItem("An effort's folder...", FOLDER)
        self.src.addItem("An effort package (.skpkg)...", PACKAGE)
        self.src.addItem("Files or a folder (into the Library)", FILES)
        v.addWidget(self.src)
        v.addWidget(D.label("What to bring", "label"))
        self.parts = {}
        for k in EM.PARTS:
            cb = QCheckBox(EM.PART_NAMES[k]); cb.setChecked(True); v.addWidget(cb); self.parts[k] = cb
        self.src.currentIndexChanged.connect(lambda _i: [cb.setEnabled(self.src.currentData() != FILES) for cb in self.parts.values()])
        bb = QDialogButtonBox(); bb.addButton("Merge", QDialogButtonBox.AcceptRole); bb.addButton(QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); v.addWidget(bb)

    def values(self):
        src = self.src.currentData()
        if src == FOLDER:
            src = QFileDialog.getExistingDirectory(self, "The other copy's folder")
        elif src == PACKAGE:
            src, _ = QFileDialog.getOpenFileName(self, "The effort package", "", "Stationkeeper effort package (*.skpkg *.ahpkg)")
        return {"source": src, "parts": [k for k, cb in self.parts.items() if cb.isChecked()]}


class Summary(QDialog):
    def __init__(self, host, target, out):
        super().__init__(host)
        self.setWindowTitle(f"Merged into {target}")
        self.resize(900, 520)
        v = QVBoxLayout(self)
        self.line = D.label(f"From {out['source']}: {EM.summary(out)}.", None); v.addWidget(self.line)
        rv = out.get("review") or []
        v.addWidget(D.label("To review: ours was kept; theirs is beside it. Change ours where theirs is right." if rv
                            else "Nothing to review: everything merged cleanly.", "muted"))
        self.table = QTableWidget(len(rv), 4); self.table.setHorizontalHeaderLabels(["What", "Item", "Ours (kept)", "Theirs"])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for i, r in enumerate(rv):
            for j, val in enumerate((r["part"], r["item"], r["ours"], r["theirs"])):
                it = QTableWidgetItem(str(val)); it.setToolTip(r.get("why", "")); self.table.setItem(i, j, it)
        self.table.setVisible(bool(rv)); v.addWidget(self.table, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject); bb.accepted.connect(self.accept); v.addWidget(bb)


def add_to_effort(host, target, answer=None, show=True):
    """Merge into target. answer (tests): {"source": effort name, folder or .skpkg, "parts": [...]}. Returns the report."""
    if answer is None:
        dlg = MergeDialog(host, target)
        if dlg.exec() != QDialog.Accepted:
            return None
        answer = dlg.values()
    if not answer.get("source"):
        return None
    if answer["source"] == FILES:                        # files and folders go in through the Library, as always
        if host.effort_name != target and not host.open_effort(target):
            return None
        host.go("library")
        return {"ok": True, "library": True}
    was_open = host.effort_name == target
    if was_open:
        host.save_now()
        host.close_effort()
    try:
        out = EM.merge(host.efforts, target, answer["source"], answer.get("parts") or EM.PARTS, who=getattr(host, "my_name", None) or None)
    except Exception as e:  # noqa: BLE001  a damaged copy: say so, change nothing more
        diag.swallowed()
        out = {"ok": False, "why": f"The other copy could not be read ({type(e).__name__})."}
    if was_open:
        host.open_effort(target)
    if not out.get("ok"):
        host.status(out.get("why", "Nothing was merged."))
        return out
    diag.activity("effort_merged", n=len(out.get("review") or []))
    host.toast(f"Merged into {target}: {EM.summary(out)}")
    if show:
        s = Summary(host, target, out)
        out["dialog"] = s
        if not os.environ.get("AH_TEST"):
            s.exec()
    return out


__all__ = ["MergeDialog", "Summary", "add_to_effort"]
