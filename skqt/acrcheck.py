"""Acronym Findings: Why is a term missing? and Save as the acronym set's answer key (3.61.0)."""
import os

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QTextBrowser, QVBoxLayout
import html

import diag
from . import design as D


def why_window(page, term=None, run=True):
    """Type a term you expected; the reasons it is not listed. Returns the dialog (tests read .answer)."""
    dlg = QDialog(page); dlg.setWindowTitle("Why is a term missing?"); dlg.resize(620, 380)
    v = QVBoxLayout(dlg)
    v.addWidget(D.label("Type a term you expected to see. The answer comes from this PC: the Exclusion List, Omit, plurals "
                        "and forms you set, the filters, and what the last scan read.", "muted"))
    r = QHBoxLayout(); v.addLayout(r)
    dlg.q = QLineEdit(term or page.f_search.text().strip()); r.addWidget(dlg.q, 1)
    dlg.answer = QTextBrowser(); v.addWidget(dlg.answer, 1)

    def ask():
        import acrwhy as W
        out = W.why(page.session, dlg.q.text(), shown=set(getattr(page, "terms", []) or []))
        body = "".join(f"<li>{html.escape(x)}</li>" for x in out["reasons"])
        dlg.answer.setHtml(f"<p><b>{html.escape(out['verdict'])}</b></p>" + (f"<ul>{body}</ul>" if body else ""))
        dlg.result_ = out
        diag.activity("acronym_why", n=1)
        return out
    r.addWidget(D.button("Check", "primary", ask))
    dlg.q.returnPressed.connect(ask)
    dlg.ask = ask
    if dlg.q.text():
        ask()
    if run:
        dlg.exec()
    return dlg


def save_key(page, folder=None):
    """Write the answer key for this scan into the acronym set folder. Returns the path or ""."""
    import acreval as AE
    s = page.session
    if s is None or not s.results:
        page.host.status("Scan the set's files and decide the terms first.")
        return ""
    if folder is None:
        from PySide6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(page, "The acronym set folder (outside the repository)", AE.default_folder())
        if not folder:
            return ""
    p, n = AE.save_key(s, folder)
    page.host.toast(f"Answer key saved: {n} row(s) for these files in {os.path.basename(folder)}. Each build scores the set.")
    diag.activity("acronym_key_saved", n=n)
    return p
