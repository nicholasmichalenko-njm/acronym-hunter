"""Settings > Our data and backups > Effort values beyond Effort Formatting... (3.82.0): the count, with Copy, so the
sections efforts use get rows on Effort Formatting before Every setting... goes. Counts only. Nothing leaves the PC."""
import os
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QPlainTextEdit, QVBoxLayout
import diag
import effortvalues as EV
from . import design as D


def show(page, run=True):
    rep = EV.report(os.path.join(page.host.config_dir, "efforts.json"))
    diag.activity("effort_values_report", n=len(rep["sections"]))
    text = EV.write_text(rep)
    dlg = QDialog(page); dlg.setWindowTitle("Effort values beyond Effort Formatting"); dlg.resize(640, 420)
    v = QVBoxLayout(dlg)
    v.addWidget(D.label("Each section of the old full editor that holds an effort's own value Effort Formatting does not "
                        "list, and in how many efforts. Counts only: no setting's name or value. Copy it into the chat.", "muted"))
    box = QPlainTextEdit(); box.setReadOnly(True); box.setPlainText(text); v.addWidget(box, 1)
    row = QHBoxLayout(); row.addStretch(1); v.addLayout(row)
    row.addWidget(D.button("Copy", None, lambda: QApplication.clipboard().setText(text)))
    row.addWidget(D.button("Close", "primary", dlg.accept))
    dlg.report, dlg.text = rep, text
    if run:
        dlg.exec()
    return dlg
