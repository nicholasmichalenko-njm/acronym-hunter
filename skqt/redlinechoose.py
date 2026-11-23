"""Redlining's one way in when no document is marked (4.59.2; decision 226, claude/stationkeeper-ux-answers-2026-11-20-
part-226-redlining-with-no-document-marked.md): Choose a document... lists the effort's documents a redline can be
prepared from today (a PDF or a picture, redlineprep.kind) that are not marked yet. Picking one marks it Redlined
Deliverable, gives it its tile on Deliverables (as the right-click does) and lists it in Redlining. A file not yet in
Documents is added there first (decision 183): Add a file goes to Documents. Rules only; nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QListWidgetItem, QVBoxLayout

import diag
from . import design as D


def listed(host):
    """Redlining lists a document (one is marked Redlined Deliverable); its parts show only then (226)."""
    try:
        return bool(host.redline_page.rows) if host.ws is not None else False
    except Exception:  # noqa: BLE001
        return False


def candidates(host):
    """[(doc id, name, file name)] of the effort's documents that could be redlined and are not marked yet."""
    if host.ws is None:
        return []
    import os
    import docversions as DV
    import redlineprep as RP
    lib = DV.Library(host.ws.p("documents")).load()
    return [(did, name, os.path.basename(p)) for did, name, p, _k in RP.sources(lib, marked=False)
            if "redline" not in (lib.doc(did) or {}).get("returns", [])]


def mark(host, doc_id):
    """Mark one document Redlined Deliverable and make its tile; True when it was marked now."""
    import docversions as DV
    import docreturn as DR
    import effortrec as RR
    lib = DV.Library(host.ws.p("documents")).load()
    d = lib.doc(doc_id)
    if d is None or "redline" in lib.returns_of(d):
        return False
    lib.set_returns(doc_id, lib.returns_of(d) + ["redline"])
    try:
        DR.ensure_tile(RR.Record(host.ws.root), lib, lib.doc(doc_id), "redline")
    except Exception:  # noqa: BLE001
        diag.swallowed()
    diag.activity("redline_chosen")
    return True


class ChooseDialog(QDialog):
    def __init__(self, parent, rows):
        super().__init__(parent)
        self.setWindowTitle("Choose a document"); self.setMinimumWidth(480)
        v = QVBoxLayout(self)
        v.addWidget(D.label("The effort's PDFs and pictures. The one you pick is marked Redlined Deliverable.", "muted"))
        self.list = QListWidget(); v.addWidget(self.list)
        for did, name, fname in rows:
            it = QListWidgetItem(f"{name}   ({fname})"); it.setData(Qt.UserRole, did); self.list.addItem(it)
        if rows:
            self.list.setCurrentRow(0)
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.add = bb.addButton("Add a file...", QDialogButtonBox.ActionRole)
        self.added = False
        self.add.clicked.connect(self._add)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _add(self):
        self.added = True
        self.reject()

    def picked(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it is not None else None


def choose(page, pick=None):
    """The button. pick (tests): a doc id, or "add" for Add a file, with no window. Returns the doc id marked, or None."""
    host = page.host
    if host.ws is None:
        host.go("library")
        return None
    rows = candidates(host)
    if pick is None:
        if not rows:
            host.status("No PDF or picture is in Documents yet. Add the file there first.")
            host.go("library")
            return None
        dlg = ChooseDialog(page, rows)
        ok = dlg.exec() == QDialog.Accepted
        pick = "add" if dlg.added else (dlg.picked() if ok else None)
    if pick == "add":
        host.go("library")
        return None
    if pick is None or not any(r[0] == pick for r in rows):
        return None
    mark(host, pick)
    host.go("redline")
    page.select(pick)
    return pick
