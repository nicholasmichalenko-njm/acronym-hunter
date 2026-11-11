"""Drafts > Status > Volume folders... (4.4.0): one row per volume of the outline, each with its folder (a SharePoint
library synced to this PC). The volume's draft is the newest Word file in it."""
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit, QPushButton,
                               QVBoxLayout)

from . import design as D


class FoldersDialog(QDialog):
    def __init__(self, parent, volumes, current):
        super().__init__(parent)
        self.setWindowTitle("Volume folders")
        self.resize(760, 120 + 40 * len(volumes))
        v = QVBoxLayout(self)
        v.addWidget(D.label("Each volume's folder: usually its SharePoint library, synced to this PC. Its draft is the "
                            "newest Word file there.", "muted"))
        g = QGridLayout(); v.addLayout(g)
        self.edits = {}
        for i, vol in enumerate(volumes):
            g.addWidget(D.label(vol, wrap=False), i, 0)
            e = QLineEdit(current.get(vol, "")); e.setPlaceholderText("No folder yet")
            g.addWidget(e, i, 1)
            b = QPushButton("Browse...")
            b.clicked.connect(lambda _c=False, ed=e, name=vol: self.browse(ed, name))
            g.addWidget(b, i, 2)
            self.edits[vol] = e
        g.setColumnStretch(1, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        row = QHBoxLayout(); row.addStretch(1); row.addWidget(bb); v.addLayout(row)

    def browse(self, ed, name):
        p = QFileDialog.getExistingDirectory(self, f"{name}: its folder", ed.text())
        if p:
            ed.setText(p)

    def answers(self):
        return {vol: e.text().strip() for vol, e in self.edits.items()}


def ask(parent, volumes, current):
    """{volume: folder} or None when cancelled."""
    if not volumes:
        return None
    dlg = FoldersDialog(parent, volumes, current)
    return dlg.answers() if dlg.exec() == QDialog.Accepted else None
