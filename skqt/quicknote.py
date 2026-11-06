"""Capture from anywhere (3.63.0): Ctrl+Shift+N or Note in the top bar opens a quick note on any page; send it to the
effort's notes, an open question or a deliverable now, or leave it in Notes to sort (the Effort Dashboard's path strip).
quicknote holds the rules."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QVBoxLayout)
import diag
import effortrec as R
import quicknote as QN
from . import design as D

LATER = "later"


def install(host):
    """The shortcut on the main window and the Note button in its top bar."""
    host.note_shortcut = QShortcut(QKeySequence("Ctrl+Shift+N"), host)
    host.note_shortcut.activated.connect(lambda: open_note(host))
    return host.note_shortcut


def _rec(host):
    return R.Record(host.ws.root) if getattr(host, "ws", None) is not None else None


def open_note(host, text=None, target=None, run=True):
    """The quick note. With text given (tests) it is sent to target ('later' keeps it in Notes to sort). Returns what it
    became, or the dialog when run is False and no text is given."""
    rec = _rec(host)
    if rec is None:
        host.status("Open an effort first: a note goes in an effort.")
        return None
    if text is None:
        d = QDialog(host); d.setWindowTitle("Quick note"); d.setMinimumWidth(520)
        v = QVBoxLayout(d)
        d.box = QPlainTextEdit(); d.box.setPlaceholderText("What you heard, decided or need to remember"); v.addWidget(d.box, 1)
        r = QHBoxLayout(); v.addLayout(r)
        r.addWidget(D.label("Send to", None, wrap=False))
        d.where = QComboBox(); d.where.addItem("Notes to sort (decide later)", LATER)
        for k, lab in QN.targets(rec):
            d.where.addItem(lab, k)
        if getattr(host, "_note_to", None):
            d.where.setCurrentIndex(max(0, d.where.findData(host._note_to)))
        r.addWidget(d.where, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
        v.addWidget(bb)
        d.box.setFocus()
        if not run:
            return d
        if d.exec() != QDialog.Accepted:
            return None
        text, target = d.box.toPlainText(), d.where.currentData()
    target = target or LATER
    host._note_to = target
    got = QN.add(rec, text) if target == LATER else QN.send(rec, text, target)
    if got:
        diag.activity("quick_note", n=1)
        host.toast("Kept in Notes to sort" if target == LATER else "Note sent")
        try:
            host.home_page.path.refresh()
        except Exception:  # noqa: BLE001  the dashboard may not be built
            diag.swallowed()
    return got


def inbox_dialog(host, run=True):
    """Notes to sort: each note with Send to and Remove."""
    rec = _rec(host)
    if rec is None:
        return None
    d = QDialog(host); d.setWindowTitle("Notes to sort"); d.resize(620, 420)
    v = QVBoxLayout(d)
    v.addWidget(D.label("Quick notes kept for later. Pick one, choose where it goes, and Send.", "muted"))
    d.list = QListWidget(); d.list.setWordWrap(True); v.addWidget(d.list, 1)
    r = QHBoxLayout(); v.addLayout(r)
    d.where = QComboBox()
    for k, lab in QN.targets(rec):
        d.where.addItem(lab, k)
    r.addWidget(d.where, 1)

    def fill():
        d.list.clear()
        for n in R.Record(host.ws.root).data.get("inbox", []):
            it = QListWidgetItem(f"{n['at'].replace('T', ' ')}  {n['by']}\n{n['text']}"); it.setData(Qt.UserRole, n["id"]); d.list.addItem(it)

    def send(nid=None, target=None):
        it = d.list.currentItem()
        nid = nid or (it.data(Qt.UserRole) if it is not None else None)
        if not nid:
            return None
        got = QN.send_from_inbox(R.Record(host.ws.root), nid, target or d.where.currentData())
        fill()
        return got

    def remove(nid=None):
        it = d.list.currentItem()
        nid = nid or (it.data(Qt.UserRole) if it is not None else None)
        ok = QN.remove(R.Record(host.ws.root), nid) if nid else False
        fill()
        return ok
    r.addWidget(D.button("Send", "primary", lambda: send()))
    r.addWidget(D.button("Remove", "danger", lambda: remove()))
    bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(d.reject); v.addWidget(bb)
    d.fill, d.send, d.remove = fill, send, remove
    fill()
    if run:
        d.exec()
    return d
