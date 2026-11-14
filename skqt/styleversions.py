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
    n_old = SH.number(page.lib, old)
    _after(page, new["id"], f"{page.lib.base_of(new)}: version {n_old} is the latest again, as version {SH.number(page.lib, new)}."
           + (f" {', '.join(sets)} use{'s' if len(sets) == 1 else ''} it." if sets else ""))
    return new


def versions(page, iid, run=True):
    """Versions...: the style's history. Returns the dialog."""
    lib = page.lib
    dlg = QDialog(page); dlg.setWindowTitle(f"{lib.base_of(lib.get(iid))}: versions"); dlg.resize(860, 480)
    v = QVBoxLayout(dlg)
    others = [(t, sets) for t, sets in SH.lines(lib, iid) if SH.line_of(t) != SH.line_of(lib.get(iid))]
    mine = [k["name"] for k in __import__("stylelib").sets_of(lib, SH.top(lib, iid)["id"])]
    head = D.label("The latest version is the one in use" + (f", in {', '.join(mine)}. " if mine else ", and no set uses it yet. ")
                   + "Restoring an earlier one puts its values on top as a new version; nothing is removed."
                   + ("".join(f" Another version of this name is for {', '.join(sets) or 'no set'}, with its own list." for _t, sets in others)), "muted")
    head.setWordWrap(True); v.addWidget(head)
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
            for j, text in enumerate((lib.base_of(top), f"version {SH.number(lib, top)}", f"version {SH.number(lib, then)}")):
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


def another(page, iid, set_ids=None, run=True):
    """Create another version... (ST26): another style of this name for the sets ticked. Each of those sets gives up
    the one it had, so no set holds two; the new one opens to be changed. set_ids given (tests): made at once.
    Returns the new style, or None."""
    from PySide6.QtWidgets import QCheckBox
    import stylelib as SL
    lib = page.lib
    it = lib.get(iid)
    if it is None:
        return None

    def do(ids):
        new, names = SH.create_version(lib, iid, ids)
        diag.activity("style_version_created")
        _after(page, new["id"], f"{lib.base_of(new)}: another version" + (f", for {', '.join(names)}. Those sets use it now; the others keep theirs."
                                                                          if names else ", in no set yet. Add it to a set from its row."))
        return new

    if set_ids is not None:
        return do(set_ids)
    dlg = QDialog(page); dlg.setWindowTitle(f"{lib.base_of(it)}: create another version"); dlg.resize(520, 360)
    v = QVBoxLayout(dlg)
    v.addWidget(D.label(f"Another {lib.base_of(it)} under the same name, starting with this one's values. Tick the sets it is for. "
                        "A set holds one style of a name, so each ticked set uses the new one and gives up the one it had. "
                        "The two are told apart by their sets.", "muted", wrap=True))
    boxes = []
    for k in SL.sets(lib):
        has = [k2 for k2 in SL.sets_of(lib, iid) if k2["id"] == k["id"]]
        cb = QCheckBox(k["name"] + ("   (uses this one now)" if has else "")); cb.setProperty("sid", k["id"]); v.addWidget(cb); boxes.append(cb)
    if not boxes:
        v.addWidget(D.label("There are no sets yet. The new version is kept in no set until you add it to one.", "muted", wrap=True))
    v.addStretch(1)
    row = QHBoxLayout(); b = D.button("Create it", "primary"); row.addStretch(1); row.addWidget(D.button("Cancel", None, dlg.reject)); row.addWidget(b)
    v.addLayout(row)
    b.clicked.connect(dlg.accept)
    dlg.boxes, dlg.b_go = boxes, b
    page.another_dialog = dlg
    if not run:
        return dlg
    if dlg.exec() != QDialog.Accepted:
        return None
    new = do([cb.property("sid") for cb in boxes if cb.isChecked()])
    page.review(new["id"])
    return new
