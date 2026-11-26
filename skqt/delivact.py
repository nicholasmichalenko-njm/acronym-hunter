"""The one action on a Deliverables row, on the screen (4.81.0; step D2; rules in delivnext.py). Redline it and Open the
form open the file where it is (no copy is made, the tabled rule of decision 189's points T1 to T4); Make a Word file
goes through Redlining's Prepare, so the Word copy is where Redlining keeps it; Attach a file... picks from Documents,
never from a path; Open in Outline goes to the Outline. Rules only; nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QListWidgetItem, QVBoxLayout

import diag
import deliverables as DL
import delivnext as DN
from . import design as D


def _host(page):
    return getattr(page, "host", page)


def lib_of(host):
    import docversions as DV
    return DV.Library(host.ws.p("documents")).load() if getattr(host, "ws", None) is not None else None


def copies(host):
    try:
        from .redlinepage import folder
        return folder(host)
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return ""


def _open(path):
    if path and not os.environ.get("AH_TEST"):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
    return path


def doc_line(lib, doc):
    v = (doc.get("versions") or [{}])[-1]
    p = lib.path_of(v) if v else ""
    marks = lib.marks_of(doc)
    return doc.get("name", "") + (f"    ({os.path.basename(p)})" if p else "") + (f"    {', '.join(marks)}" if marks else "")


def pick_doc(parent, lib, suggested="", choose=None, title="Its file"):
    """A document from Documents (decision 176: the file lives once, in Documents). choose (tests): the id to take."""
    if lib is None or not lib.all:
        _host(parent).status("Documents is empty. Add the file there first (Add a file now... on the Shred bar adds and attaches it).")
        return None
    if choose is not None:
        return choose if lib.doc(choose) is not None else None
    dlg = QDialog(parent); dlg.setWindowTitle(title); dlg.setMinimumWidth(560)
    v = QVBoxLayout(dlg)
    v.addWidget(D.label("Pick its file from Documents. The file stays where it is; the deliverable points at it.", "muted"))
    lst = QListWidget(); v.addWidget(lst, 1)
    for doc in lib.all:
        it = QListWidgetItem(doc_line(lib, doc)); it.setData(Qt.UserRole, doc["id"]); lst.addItem(it)
        if doc["id"] == suggested:
            lst.setCurrentItem(it)
    if lst.currentItem() is None and lst.count():
        lst.setCurrentRow(0)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.button(QDialogButtonBox.Ok).setText("Attach")
    bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); v.addWidget(bb)
    lst.itemDoubleClicked.connect(lambda _it: dlg.accept())
    if dlg.exec() != QDialog.Accepted or lst.currentItem() is None:
        return None
    return lst.currentItem().data(Qt.UserRole)


def attach(page, did, choose=None):
    """Attach a file...: pick from Documents, then the row's action follows from it."""
    host = _host(page)
    lib = lib_of(host)
    import effortrec as RR
    rec = RR.Record(host.ws.root)
    d = DL.get(rec, did)
    if d is None:
        return ""
    doc_id = pick_doc(page, lib, DN.suggest(lib, d), choose)
    if not doc_id:
        return ""
    slot = DN.attach(rec, lib, did, doc_id)
    diag.activity("deliverable_file_attached")
    host.status(f"{d['name']}: its file is {lib.doc(doc_id).get('name', '')}.")
    return slot


def make_word(page, d, path):
    """Make a Word file of the customer's PDF through Redlining's Prepare. A redline goes to its row on Prepare (the
    pages still to look at stop it there, as they do on Prepare); a form is prepared the same way into the same
    Redlines folder. Returns the Word file's path, or None."""
    host = _host(page)
    rp = getattr(host, "redline_page", None)
    if rp is None:
        return None
    rp.refresh()
    row = next((i for i, r in enumerate(rp.rows) if r[0] == d.get("doc_id")), -1)
    if row >= 0:
        host.go("redline")
        rp.select(d.get("doc_id"))
        return rp.prepare(row)
    import redlineprep as RP
    f, cf = rp._folders()
    try:
        host.status("Making the Word file...")
        res = RP.prepare(path, f or os.path.dirname(path), cf)
    except ValueError as e:
        host.status(str(e) + " Read its pages in Shred first.")
        return None
    except PermissionError:
        host.status("The Word file is open in Word: close it, then try again.")
        return None
    diag.activity("deliverable_word_made", n=res.get("paragraphs", 0))
    host.toast(f"Word file made: {os.path.basename(res['path'])}, in the effort's Redlines folder")
    return res["path"]


def run(page, did, action=None, choose=None):
    """The row's one action (or the one named). Returns what was done: the action's key, or ""."""
    host = _host(page)
    if getattr(host, "ws", None) is None:
        return ""
    import effortrec as RR
    rec = RR.Record(host.ws.root)
    d = DL.get(rec, did)
    if d is None:
        return ""
    lib = lib_of(host)
    nx = DN.next_of(d, lib, copies(host))
    act = action or nx["action"]
    done = ""
    if act == "attach":
        done = "attach" if attach(page, did, choose) else ""
    elif act == "word":
        done = "word" if make_word(page, d, nx["path"]) else ""
    elif act in ("redline", "form"):
        p = nx["path"]
        if not p or not os.path.isfile(p):
            host.status("The file is not on this PC. Find it in Documents.")
        else:
            _open(p)
            host.status(f"Opened {os.path.basename(p)}." + (" Mark it up in Word with Track Changes on." if act == "redline" else ""))
            done = act
    elif act == "outline":
        host.go("outline")
        done = "outline"
    if done:
        diag.activity("deliverable_action", what=done)
    try:
        if done in ("attach", "word") and getattr(host, "deliverables_page", None) is not None:
            host.deliverables_page.refresh()
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return done
