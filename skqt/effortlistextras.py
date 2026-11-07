"""The effort acronym list's tools brought back from the classic window (3.51.0).

export_picker      choose the columns, the format (Word, Excel, CSV), which statuses and which volumes
export_approvals   the terms waiting for approval, with an empty approver column, for the approvers to fill in
export_all         every effort's list in one workbook, a sheet each
import_volume      a volume's own acronym list (a table or ACR<tab>meaning lines) into the effort's list, as Proposed
assign_volumes     name volumes and say which volumes use the selected terms
activity           what was added, changed or approved, by whom and when (the list's History)
new_terms          the terms the latest scan added
show_in_scan       the selected term on the Scan tab
open_in_excel      the workbook in Excel; reload reads it again
to_database        chosen terms (approved by default) into this PC's database, usually after submission
Rules only; nothing leaves the PC."""
import csv
import os

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QGridLayout, QLabel, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QVBoxLayout)
from PySide6.QtCore import Qt

import diag
import effort as E
from . import design as D

FORMATS = (("docx", "Word table"), ("xlsx", "Excel"), ("csv", "CSV"))


def _volumes(L):
    out = []
    for r in L.rows.values():
        for v in str(r.get("Used in volumes") or "").split(";"):
            v = v.strip()
            if v and v not in out:
                out.append(v)
    return out


def rows_for(L, columns, statuses=None, volumes=None):
    """[[values]] of the list for the columns chosen, the statuses and the volumes (a term used in any of them)."""
    out = []
    for t in L.order:
        r = L.rows.get(t)
        if r is None or (statuses and r.get("Status") not in statuses):
            continue
        if volumes:
            used = {v.strip() for v in str(r.get("Used in volumes") or "").split(";")}
            if not used & set(volumes):
                continue
        out.append([str(r.get(c, "") if c != "Term" else t) for c in columns])
    return out


def write(rows, columns, path):
    low = path.lower()
    if low.endswith(".docx"):
        import volcheck as V
        if columns[:2] == ["Term", "Definition"] and len(columns) == 2:
            V.write_docx([(r[0], r[1]) for r in rows], path)
        else:
            V.write_docx([(r[0], " | ".join(x for x in r[1:] if x)) for r in rows], path)
    elif low.endswith(".xlsx"):
        import openpyxl
        from openpyxl.styles import Font
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Acronyms"
        ws.append(columns)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append(r)
        wb.save(path)
    else:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(columns); w.writerows(rows)
    return len(rows)


def export_picker(page, path=None, columns=None, statuses=None, volumes=None, run=True):
    """The list exported as chosen. With path given (tests), no dialog. Returns the path."""
    L = page.L
    if L is None:
        return None
    if path is None:
        dlg = QDialog(page); dlg.setWindowTitle("Export the acronym list"); dlg.resize(560, 520)
        v = QVBoxLayout(dlg)
        v.addWidget(D.label("Columns", "label"))
        g = QGridLayout(); v.addLayout(g)
        boxes = {}
        for i, c in enumerate(E.COLUMNS):
            cb = QCheckBox(c); cb.setChecked(c in ("Term", "Definition")); g.addWidget(cb, i // 3, i % 3); boxes[c] = cb
        v.addWidget(D.label("Statuses", "label"))
        st = {}
        for sname in E.STATUSES:
            cb = QCheckBox(sname); cb.setChecked(sname == E.IN); v.addWidget(cb); st[sname] = cb
        vols = _volumes(L)
        vl = QListWidget(); vl.setMaximumHeight(110)
        for x in vols:
            it = QListWidgetItem(x); it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Unchecked); vl.addItem(it)
        if vols:
            v.addWidget(D.label("Only terms used in these volumes (none ticked: every term)", "label")); v.addWidget(vl)
        fmt = QComboBox()
        for k, t in FORMATS:
            fmt.addItem(t, k)
        v.addWidget(fmt)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if not run or dlg.exec() != QDialog.Accepted:
            return None
        columns = [c for c in E.COLUMNS if boxes[c].isChecked()] or ["Term", "Definition"]
        statuses = [k for k, cb in st.items() if cb.isChecked()]
        volumes = [vl.item(i).text() for i in range(vl.count()) if vl.item(i).checkState() == Qt.Checked]
        ext = fmt.currentData()
        path, _ = QFileDialog.getSaveFileName(page, "Export the acronym list", page.host.out_path("acronym_list")[:-4] + "." + ext,
                                              f"{dict(FORMATS)[ext]} (*.{ext})")
        if not path:
            return None
    try:
        n = write(rows_for(L, columns or ["Term", "Definition"], statuses, volumes), columns or ["Term", "Definition"], path)
    except PermissionError:
        page.host.status("That file is open. Close it, then export again.")
        return None
    diag.activity("effort_list_exported", n=n)
    page.host.toast(f"{n} term(s) exported.")
    return path


def export_approvals(page, path=None):
    """3.76.0: no approval; kept for older callers: the terms in the list with no definition yet."""
    L = page.L
    if L is None:
        return None
    if path is None:
        path, _ = QFileDialog.getSaveFileName(page, "For approval", page.host.out_path("acronyms_for_approval")[:-4] + ".xlsx", "Excel (*.xlsx)")
        if not path:
            return None
    cols = ["Term", "Definition", "Type", "Status", "Notes"]
    rows = [r for r in rows_for(L, cols, [E.IN]) if not str(r[1] or "").strip()]
    write(rows, cols, path)
    return path


def export_all(page, path=None):
    """Every effort's acronym list in one workbook, a sheet each."""
    host = page.host
    if path is None:
        path, _ = QFileDialog.getSaveFileName(page, "Every effort's acronym list", host.out_path("all_acronym_lists")[:-4] + ".xlsx", "Excel (*.xlsx)")
        if not path:
            return None
    import openpyxl
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    n = 0
    for name in host.efforts.names():
        info = host.efforts.get(name) or {}
        p = info.get("path")
        if not p or not os.path.isfile(p):
            continue
        L = E.EffortList(p, name).load()
        ws = wb.create_sheet(("".join(ch for ch in name if ch not in "[]:*?/\\") or "Effort")[:31])
        ws.append(["Term", "Definition", "Type", "Status", "Approver"])
        for t in L.order:
            r = L.rows[t]
            ws.append([t, r.get("Definition", ""), r.get("Type", ""), r.get("Status", ""), r.get("Approver", "")])
        n += 1
    if not n:
        page.host.status("No effort's acronym list is on this PC yet.")
        return None
    wb.save(path)
    return path


def import_volume(page, path=None):
    """A volume's own acronym list into the effort's list (Proposed, with where it came from). Returns how many."""
    s, L = page.session, page.L
    if L is None:
        return 0
    if path is None:
        path, _ = QFileDialog.getOpenFileName(page, "A volume with its own acronym list", "", "Word (*.docx)")
        if not path:
            return 0
    import custdefs
    got = custdefs.acronym_list(path)
    vol = os.path.basename(path)
    n = 0
    for term, defn in (got.get("entries") or {}).items():
        if term not in L.rows:
            L.add_or_update(term, change_note=f"from the acronym list in {vol}", Definition=defn, Status=E.IN,
                            Notes=f"From {vol}")
            n += 1
    if n:
        s._save_effort_list()
        s.apply_effort()
        s.save()
    page.fill()
    page.host.toast(f"{n} term(s) added from {vol}'s acronym list, as Proposed.")
    return n


def assign_volumes(page, terms=None, volumes=None):
    """Says which volumes use the selected terms (Used in volumes). With volumes given (tests), no dialog."""
    L = page.L
    terms = terms or page.selected()
    if L is None or not terms:
        return 0
    if volumes is None:
        from PySide6.QtWidgets import QInputDialog
        have = _volumes(L)
        text, ok = QInputDialog.getText(page, "Volumes", "The volumes that use the selected term(s), separated by ; "
                                        f"(known: {'; '.join(have) or 'none yet'}):", text="; ".join(have[:1]))
        if not ok:
            return 0
        volumes = [x.strip() for x in text.split(";") if x.strip()]
    for t in terms:
        if t in L.rows:
            L.rows[t]["Used in volumes"] = "; ".join(volumes)
            L._hist(t, "volumes: " + ("; ".join(volumes) or "none"))
    page.session._save_effort_list()
    page.fill()
    return len(terms)


def activity(page, run=True):
    """What was added, changed or approved, newest first. Returns the text."""
    L = page.L
    if L is None:
        return ""
    lines = [f"{h[0]}  {h[1]}  {h[2]}: {h[3]}" for h in reversed(L.history[-2000:])]
    text = "\n".join(lines) or "Nothing has happened to this list yet."
    if run:
        dlg = QDialog(page); dlg.setWindowTitle("Acronym list activity"); dlg.resize(820, 560)
        v = QVBoxLayout(dlg); box = QPlainTextEdit(text); box.setReadOnly(True); v.addWidget(box)
        v.addWidget(D.button("Close", "ghost", dlg.accept)); dlg.exec()
    return text


def new_terms(page):
    """The terms the latest scan added (status New in this scan), selected in the list."""
    L = page.L
    if L is None:
        return []
    got = [t for t in L.order if str(L.rows[t].get("Scan status") or "").startswith(E.SCAN_NEW)]
    page.f_status.setCurrentIndex(0); page.f_search.setText(""); page.fill()
    page.select(got)
    page.host.toast(f"{len(got)} term(s) new in the latest scan" + (": selected." if got else "."))
    return got


def show_in_scan(page):
    terms = page.selected()
    ap = page.host.acronym_page
    if not terms or ap.session is None or terms[0] not in ap.session.results:
        page.host.status("That term is not in the latest scan.")
        return None
    page.host.go("acronyms")
    ap.f_search.setText(""); ap.f_status.setCurrentIndex(0); ap.f_excl.setChecked(True)
    ap.select(terms[0])
    return terms[0]


def open_in_excel(page):
    L = page.L
    if L is None or not os.path.isfile(L.path):
        return False
    import sys
    if sys.platform.startswith("win"):
        os.startfile(L.path)                                 # noqa: S606  the effort's own workbook
    return True


def reload(page):
    L = page.L
    if L is None:
        return False
    if E.open_in_excel(L.path):
        page.host.status("The workbook is open in Excel: close it there first, then Reload.")
        return False
    L.load()
    page.session.apply_effort()
    page.fill()
    return True


def to_database(page, terms=None, run=True):
    """Chosen terms of the list (those in the list with a definition, by default) into this PC's database."""
    import acrmore as AM
    L = page.L
    if L is None:
        return None
    if terms is None:
        approved = [t for t in L.order if E.ready(L.rows[t])]
        dlg = QDialog(page); dlg.setWindowTitle("Add to this PC's database"); dlg.resize(560, 520)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Usually after submission: the terms worth knowing in every effort. Untick any to leave out."))
        lw = QListWidget()
        for t in approved:
            it = QListWidgetItem(f"{t}: {L.rows[t].get('Definition', '')}"); it.setData(Qt.UserRole, t)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked); lw.addItem(it)
        v.addWidget(lw, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        v.addWidget(bb)
        if not run or dlg.exec() != QDialog.Accepted:
            return None
        terms = [lw.item(i).data(Qt.UserRole) for i in range(lw.count()) if lw.item(i).checkState() == Qt.Checked]
    try:
        got = AM.add_list_to_database(page.session, terms)
    except PermissionError:
        import app_gui as A
        page.host.status(A.DB_LOCKED_MSG)
        return None
    page.host.toast(f"This PC's database: {got['added']} added, {got['updated']} updated, {got['same']} already there.")
    return got


def buttons(page):
    """The extras as a row of buttons for the list's page."""
    return [D.button("Export...", None, lambda: export_picker(page), "Choose the columns, the format and the volumes"),
            D.button("Every effort...", None, lambda: export_all(page), "Every effort's acronym list in one workbook"),
            D.button("Import a volume's list...", None, lambda: import_volume(page), "A volume's own acronym list into this list"),
            D.button("Volumes...", None, lambda: assign_volumes(page), "Name volumes and say which use the selected terms"),
            D.button("Activity", None, lambda: activity(page), "What was added or changed, by whom and when"),
            D.button("New in the last scan", None, lambda: new_terms(page)),
            D.button("Show in scan", None, lambda: show_in_scan(page)),
            D.button("Open in Excel", "ghost", lambda: open_in_excel(page)),
            D.button("Reload", "ghost", lambda: reload(page), "Read the workbook again (after editing it in Excel)"),
            D.button("Add to this PC's database...", None, lambda: to_database(page), "Usually after submission: chosen terms, "
                     "those with a definition by default, for every effort")]
