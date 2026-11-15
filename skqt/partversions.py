"""A Quick Part's versions on screen (4.40.0; ST28 of 2026-11-14: as styles have them). Versions... on a Quick Part's
row lists every version with its date, who made it and the sets that use it, Latest first; Restore this version puts an
earlier one on top as a new Latest. Create another version... makes another Quick Part of the same name for the part
sets you tick. parthistory holds the rules; nothing leaves the PC."""
from PySide6.QtWidgets import QAbstractItemView, QCheckBox, QDialog, QHBoxLayout, QTableWidget, QTableWidgetItem, QVBoxLayout

import diag
import parthistory as PH
import stylelib as SL
from . import design as D


def _after(page, it, said):
    page.lib.fresh() if hasattr(page.lib, "fresh") else None
    pid = "q:" + it["id"]
    page.shown_ver["q:" + (it.get("family") or it["id"])] = pid
    page.cur = pid
    page.host.toast(said)
    page.fill_sets(); page.fill_rows(); page.select(pid)


def _uses(sets):
    return f" {', '.join(sets)} use{'s' if len(sets) == 1 else ''} it." if sets else ""


def restore(page, iid):
    """That version becomes the Quick Part's Latest. Returns the new version, or None."""
    old = page.lib.get(iid)
    n_old = PH.number(page.lib, old) if old else 0
    new, sets = PH.restore(page.lib, iid)
    if new is None:
        return None
    diag.activity("part_restored")
    _after(page, new, f"{page.lib.base_of(new)}: version {n_old} is the latest again, as version {PH.number(page.lib, new)}." + _uses(sets))
    return new


def versions(page, iid, run=True):
    """Versions...: the Quick Part's history. Returns the dialog."""
    lib = page.lib
    dlg = QDialog(page); dlg.setWindowTitle(f"{lib.base_of(lib.get(iid))}: versions"); dlg.resize(820, 460)
    v = QVBoxLayout(dlg)
    here = PH.line_of(lib.get(iid))
    mine = next((sets for t, sets in PH.lines(lib, iid) if PH.line_of(t) == here), [])
    others = [sets for t, sets in PH.lines(lib, iid) if PH.line_of(t) != here]
    head = D.label("The latest version is the one in use" + (f", in {', '.join(mine)}. " if mine else ", and no set uses it yet. ")
                   + "Restoring an earlier one puts it on top as a new version; nothing is removed."
                   + "".join(f" Another version of this name is for {', '.join(s) or 'no set'}, with its own list." for s in others), "muted")
    head.setWordWrap(True); v.addWidget(head)
    t = QTableWidget(0, 5); t.setHorizontalHeaderLabels(["Version", "When", "Who", "What it is", "Sets that use it"])
    t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection); t.horizontalHeader().setStretchLastSection(True); v.addWidget(t, 1)
    row = QHBoxLayout(); b = D.button("Restore this version", "primary")
    row.addStretch(1); row.addWidget(D.button("Close", None, dlg.reject)); row.addWidget(b)
    v.addLayout(row)
    dlg.rows = []

    def fill(of):
        dlg.rows = PH.history(lib, of)
        t.setRowCount(len(dlg.rows))
        for i, r in enumerate(dlg.rows):
            for j, text in enumerate((f"{r['version']}" + ("  Latest" if r["latest"] else ""), r["at"], r["by"], r["note"], ", ".join(r["sets"]))):
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


def another(page, iid, set_ids=None, run=True):
    """Create another version...: tick the part sets it is for. With set_ids given it is made at once. Returns the new
    Quick Part, or the dialog (run=False), or None."""
    lib = page.lib

    def do(ids):
        new, names = PH.create_version(lib, iid, ids)
        if new is None:
            return None
        diag.activity("part_another_version", n=len(names))
        _after(page, new, f"Another {lib.base_of(new)}" + (f", for {', '.join(names)}" if names else ", in no set yet")
               + ". Right-click it: Change it... to make it differ. The other one is as it was.")
        return new

    if set_ids is not None:
        return do(set_ids)
    dlg = QDialog(page); dlg.setWindowTitle(f"Create another version of {lib.base_of(lib.get(iid))}"); dlg.resize(520, 380)
    v = QVBoxLayout(dlg)
    v.addWidget(D.label("Another Quick Part of the same name, for the part sets you tick. It starts as this one and has its own "
                        "versions from there. A set holds one Quick Part of a name, so a ticked set gives up the one it had.", "muted"))
    dlg.boxes = []
    on = set(PH.sets_on(lib, iid))
    for k in SL.sets(lib, "part"):
        c = QCheckBox(k["name"] + ("  (uses this one now)" if k["name"] in on else "")); c.setProperty("sid", k["id"])
        v.addWidget(c); dlg.boxes.append(c)
    if not dlg.boxes:
        v.addWidget(D.label("There is no part set yet. Make one first: More > New part set...", None))
    v.addStretch(1)
    row = QHBoxLayout(); go = D.button("Create another version", "primary")
    row.addStretch(1); row.addWidget(D.button("Cancel", None, dlg.reject)); row.addWidget(go)
    v.addLayout(row)
    dlg.made = None

    def press():
        dlg.made = do([c.property("sid") for c in dlg.boxes if c.isChecked()])
        dlg.accept()

    go.clicked.connect(press)
    dlg.b_go = go
    page.another_dialog = dlg
    if run:
        dlg.exec()
        return dlg.made
    return dlg


def tab_text(lib, pid):
    """A version line's tab on the row: the sets it is for."""
    sets = next((names for t, names in PH.lines(lib, pid[2:]) if t["id"] == pid[2:]), [])
    return "for " + ", ".join(sets) if sets else "in no set"


def notice(page):
    """A sentence for part sets still on an earlier version of a Quick Part ('' when there is none)."""
    b = PH.behind(page.lib)
    if not b:
        return ""
    sets = []
    for k, _it, _t in b:
        if k["name"] not in sets:
            sets.append(k["name"])
    return (f"{len(b)} Quick Part{'' if len(b) == 1 else 's'} in {', '.join(sets)} {'is' if len(b) == 1 else 'are'} on an earlier version. "
            "More > Use the latest Quick Parts in every set moves them.")


def use_latest(page):
    n = PH.use_latest(page.lib)
    page.host.toast(f"{n} Quick Part{'' if n == 1 else 's'} moved to the latest version." if n else "Every set uses the latest already.")
    page.fill_sets(); page.fill_rows()
    return n
