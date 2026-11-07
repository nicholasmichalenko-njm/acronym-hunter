"""Check a Draft > Apply in Word > Drift report... (3.79.0): pick a draft; every dated copy beside it, against the draft as it
is now: the copy's changes taken up, still to take, or in a passage that changed; the paragraphs changed since the copy;
and whether to make the copy again. Export to Excel. Reads only. Rules only; nothing leaves the PC."""
import os
from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout
import diag
import drift as DR
from . import design as D

TONE = {DR.TAKEN: "ok", DR.OPEN: "warn", DR.MOVED: "crit"}


def show(page, draft=None, run=True):
    """The report's window. Returns the dialog (with .reports) or None."""
    if draft is None:
        draft, _ = QFileDialog.getOpenFileName(page, "The draft (its dated copies sit beside it)", "", "Word (*.docx)")
        if not draft:
            return None
    reps = DR.reports(draft)
    diag.activity("drift_report", n=len(reps))
    dlg = QDialog(page); dlg.setWindowTitle(f"Drift report: {os.path.basename(draft)}"); dlg.resize(980, 620)
    dlg.reports = reps
    v = QVBoxLayout(dlg)
    if not reps:
        v.addWidget(D.label("No dated copies beside this draft. Apply in Word's Make the copy with tracked changes, or Fix a "
                            "Copy, makes one; then come back here as the author writes.", "muted"))
    t = QTableWidget(len(reps), 6); t.setHorizontalHeaderLabels(["Copy", "Made", "Taken up", "Still to take", "The passage changed", "Advice"])
    t.verticalHeader().setVisible(False); t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch); t.setColumnWidth(0, 320)
    for i, r in enumerate(reps):
        vals = [os.path.basename(r["copy"]), r["when"].strftime("%Y-%m-%d %H:%M") if r["when"] else "", str(r["taken"]),
                str(r["open"]), str(r["moved"]), f"{r['advice']} ({r['paras_changed']} of {r['paras']} paragraphs changed)"]
        for c, x in enumerate(vals):
            t.setItem(i, c, QTableWidgetItem(x))
    v.addWidget(t, 1)
    v.addWidget(D.SectionTitle("The newest copy's changes"))
    ch = QTableWidget(0, 4); ch.setHorizontalHeaderLabels(["Paragraph", "Was", "Copy says", "In the draft now"])
    ch.verticalHeader().setVisible(False); ch.setEditTriggers(QTableWidget.NoEditTriggers)
    ch.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch); ch.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
    for c in (reps[0]["changes"] if reps else []):
        n = ch.rowCount(); ch.insertRow(n)
        for k, x in enumerate((str(c["para"] + 1), c["old"], c["new"], c["state"])):
            it = QTableWidgetItem(x)
            if k == 3:
                it.setForeground(D.color(TONE.get(c["state"], "accent")))
            ch.setItem(n, k, it)
    v.addWidget(ch, 1)
    dlg.table, dlg.changes = t, ch
    row = QHBoxLayout(); v.addLayout(row); row.addStretch(1)

    def export(path=None):
        if path is None:
            path, _ = QFileDialog.getSaveFileName(dlg, "Drift report", os.path.splitext(draft)[0] + " - drift report.xlsx", "Excel (*.xlsx)")
            if not path:
                return None
        try:
            return DR.write_xlsx(reps, path)
        except PermissionError:
            page.host.status("That file is open in Excel. Close it, then export again.")
            return None
    dlg.export = export
    row.addWidget(D.button("Export to Excel...", None, lambda: export()))
    row.addWidget(D.button("Close", "primary", dlg.accept))
    if run:
        dlg.exec()
    return dlg
