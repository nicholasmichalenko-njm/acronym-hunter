"""Undo, off the top bar (4.27.2; Nicholas's recording 2026-11-12 07:05: "undo doesn't need to be here ... control Z
... or an undo in some sort of menu"). Ctrl+Z is unchanged. After a change the foot of the window says what Undo
would put back, as a link: click it to undo, or click History for the steps this page can still undo, newest first,
and go back to any one of them. Rules only; nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QListWidget, QVBoxLayout

import diag
from . import design as D


def install(w):
    """Once: the line at the foot; the top bar's Undo button leaves the bar (it stays for the code that enables it)."""
    w.undo_btn.setVisible(False)
    w.undo_line = QLabel(""); w.undo_line.setTextFormat(Qt.RichText)
    w.undo_line.setToolTip("Ctrl+Z undoes the last change on this page")
    w.undo_line.linkActivated.connect(lambda href: history(w) if href == "h" else w.undo_here())
    w.statusBar().addPermanentWidget(w.undo_line)
    w.undo_line.setVisible(False)
    return w.undo_line


def refresh(w, text):
    """Called whenever the window works out what Undo would put back on the page shown."""
    line = getattr(w, "undo_line", None)
    if line is None:
        return None
    import html
    t = D.tokens()
    more = len(steps(w)) > 1
    line.setText(f"<a href='u' style='color:{t['accent']}'>Undo: {html.escape(text)}</a>"
                 + (f" &nbsp;·&nbsp; <a href='h' style='color:{t['accent']}'>History</a>" if more else "") if text else "")
    line.setVisible(bool(text))
    return text


def steps(w):
    """What this page can still undo, newest first: [label]."""
    from .mainwin import MATRIX_UNDO
    pg = w.stack.currentWidget()
    own = getattr(getattr(pg, "R", None), "undo", None)         # Shred keeps the matrix's steps itself
    if isinstance(own, list) and own:
        return [(u[3] or "a change") for u in reversed(own)]
    if callable(getattr(pg, "undo_here", None)):
        t = w.undo_text()
        return [t] if t else []
    key = next((k for k, p in w.pages.items() if p is pg), "")
    if key in MATRIX_UNDO and w.review is not None:
        return [(u[3] or "a change") for u in reversed(w.review.undo)]
    return []


def undo_to(w, n):
    """Undo the newest n steps. Returns how many were undone."""
    done = 0
    for _ in range(max(0, int(n))):
        if not w.undo_here():
            break
        done += 1
    return done


def history(w, pick=None):
    """The steps this page can still undo. pick (tests): how many to undo, 0 for none. Returns how many were undone."""
    st = steps(w)
    if not st:
        w.status("Nothing to undo on this page.")
        return 0
    if pick is None:
        dlg = QDialog(w); dlg.setWindowTitle("History"); dlg.resize(520, 380)
        v = QVBoxLayout(dlg)
        v.addWidget(D.label("What this page can still undo, newest first. Pick a line: everything from the top down to it "
                            "is undone.", "muted"))
        lw = QListWidget(); lw.addItems([f"{i + 1}.  {s}" for i, s in enumerate(st)]); lw.setCurrentRow(0)
        v.addWidget(lw, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
        bb.button(QDialogButtonBox.Ok).setText("Undo to here")
        v.addWidget(bb)
        if dlg.exec() != QDialog.Accepted:
            return 0
        pick = lw.currentRow() + 1
    n = undo_to(w, pick)
    if n:
        diag.activity("undo_history", n=n)
    return n
