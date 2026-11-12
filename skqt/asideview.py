"""What a read set aside (3.59.0): page headers and footers, and lines repeated on every page (kept once in the
review). Opened from Read into Review after a read; a header or footer can be put back in the review as a sentence of
its own."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem, QVBoxLayout

import diag
from . import design as D

HEADER = "A page header or footer"


def put_back(M, entries):
    """Headers and footers back in the review as sentences of their own (decided by the person). Returns the rows added."""
    import compliance as C
    import compliance_read as CR
    entries = [e for e in entries if e["why"] == HEADER]
    if not entries:
        return []
    items = C.extract([(e["file"], [("", e["text"])]) for e in entries])
    return CR.add_read(M, items, [], [])


class AsideDialog(QDialog):
    def __init__(self, parent, entries, host):
        super().__init__(parent)
        self.host, self.entries = host, list(entries)
        self.setWindowTitle("What the read set aside"); self.resize(900, 520)
        v = QVBoxLayout(self)
        v.addWidget(D.label(f"{len(self.entries)} line(s) not in the shred as pieces. Repeated lines are in it once. "
                            "Select a header or footer and Put back if it says something the response must answer.", "muted"))
        self.t = QTableWidget(0, 4); self.t.setHorizontalHeaderLabels(["File", "Why", "Times", "Text"])
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setSelectionBehavior(QAbstractItemView.SelectRows); self.t.horizontalHeader().setStretchLastSection(True)
        self.t.setColumnWidth(0, 180); self.t.setColumnWidth(1, 220); self.t.setColumnWidth(2, 50)
        for e in self.entries:
            k = self.t.rowCount(); self.t.insertRow(k)
            for c, x in enumerate((e["file"], e["why"], str(e["times"]), e["text"])):
                it = QTableWidgetItem(x); it.setData(Qt.UserRole, k); self.t.setItem(k, c, it)
        v.addWidget(self.t, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.addButton(D.button("Put back in the shred", "primary", lambda: self.put_back()), QDialogButtonBox.ActionRole)
        bb.rejected.connect(self.reject); bb.accepted.connect(self.accept)
        v.addWidget(bb)

    def put_back(self, rows=None):
        R = self.host.review
        if R is None:
            return []
        rows = rows if rows is not None else sorted({i.row() for i in self.t.selectedIndexes()})
        R.snap()
        got = put_back(R.M, [self.entries[r] for r in rows])
        diag.activity("set_aside_put_back", n=len(got))
        self.host.changed()
        self.host.toast(f"{len(got)} line(s) put back in the shred" if got else "Only headers and footers can be put back")
        return got
