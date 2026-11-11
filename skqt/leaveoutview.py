"""Leave out of the matrix, on Matrix & Outline > Place (4.3.0; leaveout.py): the reason (Covered elsewhere, Duplicate,
Not ours to answer, Information only, Other) and a note, in one small dialog; Put back in the matrix undoes it.
Both are on a piece's right-click in place mode. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit

import diag
import leaveout as LO


class ReasonDialog(QDialog):
    def __init__(self, parent, n):
        super().__init__(parent)
        self.setWindowTitle("Leave out of the matrix")
        f = QFormLayout(self)
        self.reason = QComboBox(); self.reason.addItems(LO.REASONS)
        self.note = QLineEdit(); self.note.setPlaceholderText("Optional; needed for Other")
        f.addRow(f"Why {n} piece(s) stay out of the matrix", self.reason)
        f.addRow("Note", self.note)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def values(self):
        return self.reason.currentText(), self.note.text()


def add_actions(page, m, rows):
    """The right-click menu's Leave out / Put back, in place mode only."""
    if not getattr(page, "place_mode", False) or not rows:
        return
    m.addSeparator()
    if any(LO.is_out(it) for it in rows):
        m.addAction("Put back in the matrix", lambda: put_back(page, rows))
    else:
        m.addAction("Leave out of the matrix...", lambda: leave_out(page, rows))


def leave_out(page, rows, answer=None):
    """answer (tests): (reason, note). Returns how many were left out."""
    if answer is None:
        d = ReasonDialog(page, len(rows))
        if not d.exec():
            return 0
        answer = d.values()
    try:
        page.R.snap("left out of the matrix")
        n = LO.leave_out(page.M, rows, answer[0], answer[1], lambda i, msg: page.M.log(i, msg))
    except ValueError as ex:
        page.host.status("Other needs a note: say why." if "note" in str(ex) else f"Not a reason: {ex}")
        return 0
    diag.activity("left_out", n=n)
    page.host.changed()
    page.after(f"{n} left out of the matrix")
    return n


def put_back(page, rows):
    page.R.snap("back in the matrix")
    n = LO.put_back(page.M, rows, lambda i, msg: page.M.log(i, msg))
    page.host.changed()
    page.after(f"{n} back in the matrix")
    return n
