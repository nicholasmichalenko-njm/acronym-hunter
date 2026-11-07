"""Acronym List > Import a list... (3.76.0): pick an Excel or CSV list, confirm the columns guessed from its headings
(Stationkeeper's own exports read with no questions), and merge it into the effort's list. Rules only; nothing leaves
the PC."""
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QLabel, QVBoxLayout
import diag
import acrimport as AI
from . import design as D


def confirm_columns(page, book, run=True):
    """The columns dialog. Returns {field: index} or None (cancelled). run=False returns the dialog's guess untouched."""
    dlg = QDialog(page); dlg.setWindowTitle("Import a list: the columns")
    v = QVBoxLayout(dlg)
    v.addWidget(D.label(f"{book['name']}: {len(book['rows'])} row(s). Say which column holds each part; the term is needed.", "muted"))
    form = QFormLayout(); v.addLayout(form)
    boxes = {}
    for field in AI.FIELDS:
        cb = QComboBox(); cb.addItem("(none)", -1)
        for i, h in enumerate(book["headings"]):
            cb.addItem(h or f"Column {i + 1}", i)
        g = book["guess"].get(field)
        if g is not None:
            cb.setCurrentIndex(g + 1)
        form.addRow(QLabel(field), cb)
        boxes[field] = cb
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.button(QDialogButtonBox.Ok).setText("Import")
    bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
    page._import_dialog = dlg
    if run and dlg.exec() != QDialog.Accepted:
        return None
    cols = {f: cb.currentData() for f, cb in boxes.items() if cb.currentData() is not None and cb.currentData() >= 0}
    return cols if "Term" in cols else None


def import_list(page, path=None, columns=None, run=True):
    """Pick, confirm, merge. Returns the merge report or None."""
    s = page.session
    L = s.effort if s is not None else None
    if L is None:
        page.host.status("Open an effort first: a list is imported into the effort's acronym list.")
        return None
    if path is None:
        path, _ = QFileDialog.getOpenFileName(page, "Import a list", "", "Lists (*.xlsx *.xlsm *.csv *.txt)")
        if not path:
            return None
    try:
        book = AI.read(path)
    except Exception:                                        # noqa: BLE001: a file that is not a list
        diag.swallowed()
        page.host.status("That file could not be read as a list (Excel or CSV).")
        return None
    if columns is None and not book["ours"]:
        columns = confirm_columns(page, book, run)
        if columns is None:
            return None
    rows = AI.to_rows(book, columns)
    if not rows:
        page.host.status("No terms in that list (no column held the terms).")
        return None
    try:
        n = AI.merge(L, rows, book["name"])
    except PermissionError:
        page.host.status("The acronym list is open in Excel. Close it, then import again.")
        return None
    diag.activity("acronym_list_imported", n=n["added"] + n["filled"])
    s.apply_effort()
    s.save()
    page.host.toast(f"Imported: {n['added']} new, {n['filled']} filled in, {n['same']} the same, "
                    f"{len(n['review'])} with two meanings (ours kept; theirs under Other definitions)")
    page.fill()
    return n
