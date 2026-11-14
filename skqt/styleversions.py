"""A style's versions on screen (4.35.0; ST15, ST16): Versions... on a style's row lists every version with its date,
who, and what changed, Latest first; Restore this version puts an earlier one on top as a new Latest. Restore every
style as of... does the same for every style at once, and Undo the restore puts back what was Latest before it.
Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QTableWidget, QTableWidgetItem, QVBoxLayout

import diag
import stylehistory as SH
from . import design as D


def _changes_text(row):
    if not row["changes"]:
        return row["note"]
    said = "; ".join(f"{w}: {a} to {b}" for w, a, b in row["changes"][:6]) + (f"; {len(row['changes']) - 6} more" if len(row["changes"]) > 6 else "")
    return (row["note"] + ". " if row["note"] else "") + said


def _after(page, iid, said):
    page.shown_ver[(page.lib.get(iid) or {}).get("family")] = iid
    page.host.toast(said)
    page.fill_sets(); page.fill_rows(); page.select(iid)


def restore(page, iid):
    """That version's values become the style's Latest. Returns the new version, or None."""
    old = page.lib.get(iid)
    new, sets = SH.restore(page.lib, iid)
    if new is None:
        return None
    diag.activity("style_restored")
    _after(page, new["id"], f"{page.lib.base_of(new)}: version {old.get('version', 1)} is the latest again, as version {new['version']}."
           + (f" {', '.join(sets)} use{'s' if len(sets) == 1 else ''} it." if sets else ""))
    return new


def versions(page, iid, run=True):
    """Versions...: the style's history. Returns the dialog."""
    lib = page.lib
    dlg = QDialog(page); dlg.setWindowTitle(f"{lib.base_of(lib.get(iid))}: versions"); dlg.resize(860, 480)
    v = QVBoxLayout(dlg)
    head = D.label("The latest version is the one in use, in every set that uses this style. Restoring an earlier one puts its values "
                   "on top as a new version; nothing is removed.", "muted"); head.setWordWrap(True); v.addWidget(head)
    t = QTableWidget(0, 4); t.setHorizontalHeaderLabels(["Version", "When", "Who", "What changed"])
    t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection); t.horizontalHeader().setStretchLastSection(True); v.addWidget(t, 1)
    row = QHBoxLayout(); b = D.button("Restore this version", "primary"); row.addStretch(1); row.addWidget(D.button("Close", None, dlg.reject)); row.addWidget(b)
    v.addLayout(row)
    dlg.rows = []

    def fill(family_iid):
        dlg.rows = SH.history(lib, family_iid)
        t.setRowCount(len(dlg.rows))
        for i, r in enumerate(dlg.rows):
            for j, text in enumerate((f"{r['version']}" + ("  Latest" if r["latest"] else ""), r["at"], r["by"], _changes_text(r))):
                t.setItem(i, j, QTableWidgetItem(text))
        t.resizeColumnsToContents()
        sync()

    def picked():
        rows = sorted({i.row() for i in t.selectionModel().selectedRows()})
        return dlg.rows[rows[0]] if rows else None

    def sync():
        r = picked()
        b.setEnabled(bool(r) and not r["latest"])

    def go():
        r = picked()
        if r and not r["latest"]:
            new = restore(page, r["id"])
            if new is not None:
                fill(new["id"])

    t.itemSelectionChanged.connect(sync); b.clicked.connect(go)
    dlg.table, dlg.b_restore, dlg.fill, dlg.head = t, b, fill, head
    fill(iid)
    page.versions_dialog = dlg
    if run:
        dlg.exec()
    return dlg


def restore_all(page, when=None, run=True):
    """Restore every style as of...: pick a time; the dialog says which styles would change; nothing changes before
    Restore. With when given (tests) it is done at once. Returns how many styles were restored, or the dialog."""
    lib = page.lib

    def do(w):
        token = SH.restore_as_of(lib, w)
        page.restore_token = token
        if token:
            diag.activity("styles_restored_as_of", n=len(token))
        page.host.toast(f"{len(token)} style{'s' if len(token) != 1 else ''} restored to {w}. More > Undo the restore puts back what was latest."
                        if token else f"Every style is already as it was on {w}.")
        page.fill_sets(); page.fill_rows()
        return len(token)

    if when is not None:
        return do(when)
    dlg = QDialog(page); dlg.setWindowTitle("Restore every style as of..."); dlg.resize(620, 460)
    v = QVBoxLayout(dlg)
    v.addWidget(D.label("Pick a time. Each style that has changed since goes back to how it was then, as a new latest version. "
                        "A style made after that time stays as it is.", "muted", wrap=True))
    pick = QComboBox()
    for m in SH.moments(lib):
        pick.addItem(m, m)
    v.addWidget(pick)
    t = QTableWidget(0, 3); t.setHorizontalHeaderLabels(["Style", "Latest now", "Goes back to"])
    t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.horizontalHeader().setStretchLastSection(True); v.addWidget(t, 1)
    row = QHBoxLayout(); b = D.button("Restore", "primary"); row.addStretch(1); row.addWidget(D.button("Close", None, dlg.reject)); row.addWidget(b)
    v.addLayout(row)

    def fill():
        pairs = SH.as_of(lib, pick.currentData()) if pick.count() else []
        t.setRowCount(len(pairs))
        for i, (top, then) in enumerate(pairs):
            for j, text in enumerate((lib.base_of(top), f"version {top.get('version', 1)}", f"version {then.get('version', 1)}")):
                t.setItem(i, j, QTableWidgetItem(text))
        t.resizeColumnsToContents()
        b.setText(f"Restore {len(pairs)} style{'s' if len(pairs) != 1 else ''}"); b.setEnabled(bool(pairs))

    def go():
        do(pick.currentData()); dlg.accept()

    pick.currentIndexChanged.connect(lambda _i: fill()); b.clicked.connect(go)
    dlg.pick, dlg.table, dlg.b_go = pick, t, b
    fill()
    page.restore_dialog = dlg
    if run:
        dlg.exec()
    return dlg


def undo_restore(page):
    """Undo the restore: what was latest before it is latest again (new versions; nothing is removed)."""
    n = SH.undo(page.lib, getattr(page, "restore_token", None))
    page.restore_token = []
    page.host.toast(f"{n} style{'s' if n != 1 else ''} put back to what was latest before the restore." if n else "There is no restore to undo.")
    page.fill_sets(); page.fill_rows()
    return n
