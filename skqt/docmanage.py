"""Documents: replace a document's file, read it again, delete a document or one version, and the Trash (4.17.0;
claude/stationkeeper-documents-replace-delete-plan-4.17.html).

- Replace the file... (a document's right-click and its More): the picked file takes the old one's place and name; it
  is the same document and the same version (docreplace). Read it again: the file was edited where it sits.
- After either, the shred reads the file again on the window's timer (reread): sentences that stayed keep their pieces
  and decisions; new ones arrive as new pieces; pieces whose sentence is gone go to the Trash.
- Delete... (and Delete this version... on a version's right-click): asks first, naming what goes (versions, files, pieces
  with decisions), Cancel the default; everything moves to the effort's Trash. Undo (Ctrl+Z on Documents) puts the
  last one back.
- Documents > More > Trash...: what was deleted or replaced, newest first, with Restore and Empty the Trash...
Rules only (No AI); nothing leaves the PC."""
import os

from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

import diag


def _lib(host):
    import docversions as DV
    return DV.Library(host.ws.p("documents")).load()


def _M(host):
    return host.review.M if getattr(host, "review", None) is not None else None


def _log(host, text, ref=None):
    try:
        import effortrec as R
        rec = R.Record(host.ws.root)
        rec.log("customer", text, ref=ref or {})
        rec.save()
    except Exception:  # noqa: BLE001  the timeline is a record, never a reason to fail
        diag.swallowed()


def replace_file(page, d, path=None):
    """Pick the edited file (or take path) and put it in place of d's latest version. Returns the result or None."""
    import docreplace as RP
    host = page.host
    if path is None:
        path, _f = QFileDialog.getOpenFileName(page, f"The new file for {d['name']}", "")
        if not path:
            return None
    lib = _lib(host)
    res = RP.replace(host.ws, lib, d["id"], new_path=path, M=_M(host))
    if res is None:
        host.status("The document's file is not here to replace.")
        return None
    _log(host, f"{d['name']}: {res['version'].get('label', '')} replaced by {os.path.basename(path)}; the old file is in the Trash",
         {"version": res["version"]["id"]})
    diag.activity("document_file_replaced")
    _after(page, d, f"{d['name']}: the file is replaced. The shred reads it again; the old file is in the Trash.")
    return res


def read_again(page, d):
    """The file was edited where it sits: read it as the same version."""
    import docreplace as RP
    host = page.host
    res = RP.replace(host.ws, _lib(host), d["id"], new_path=None, M=_M(host))
    if res is None:
        return None
    _log(host, f"{d['name']}: read again (the file was edited)", {"version": res["version"]["id"]})
    diag.activity("document_read_again")
    _after(page, d, f"{d['name']}: read again. The shred reads it again.")
    return res


def _after(page, d, msg):
    host = page.host
    try:
        page.refresh()
    except Exception:  # noqa: BLE001
        diag.swallowed()
    w = reread(host, d["id"])
    host.status(msg if w is not None or getattr(host, "review", None) is None else msg)


def reread(host, doc_id=None):
    """Read again, into the shred, a document whose file was replaced (its latest version marked "reread"). A document
    not in the shred yet is left to the usual extraction. Returns the worker, or None."""
    import docreplace as RP
    if host.ws is None:
        return None
    rp = host.read_page
    if rp.running():
        return None
    lib = _lib(host)
    have = set(host.review.files()) if getattr(host, "review", None) is not None else set()
    for d in lib.docs:
        v = lib.latest(d)
        if v is None or not v.get("reread") or (doc_id and d["id"] != doc_id):
            continue
        path = lib.path_of(v)
        f = v.get("file", "")
        if f not in have or not path or not os.path.isfile(path):
            v.pop("reread", None)                          # not in the shred: extraction picks it up as any document
            lib.save()
            continue
        vid = v["id"]

        def merge(items, heads, src, f=f, vid=vid, name=d["name"]):
            got = RP.merge(host.review.M, f, items, heads, src, ws=host.ws, trash_name=f"{name}: pieces whose text is gone")
            lb = _lib(host)
            for dd in lb.all:
                for vv in dd.get("versions", []):
                    if vv["id"] == vid:
                        vv.pop("reread", None)
            lb.save()
            host.status(f"{name} read again: {got['kept']} pieces kept, {got['changed']} changed (decisions kept), "
                        f"{got['added']} new, {got['gone']} to the Trash.")
            return got["rows"]
        rp.refresh()
        rp._merge = merge
        w = rp.read(paths=[path], identities="suggested", start="auto")
        if w is None:
            rp._merge = None
        return w
    return None


# ------------------------------------------------------------------ delete, undo, the Trash
def delete(page, d, vid=None, answer=None):
    """Ask, then move the document (or one version) and its pieces to the Trash. answer (tests): True deletes, False
    cancels. Returns the Trash entry id, or None."""
    import docremove as DR
    host = page.host
    lib = _lib(host)
    M = _M(host)
    info = DR.what_goes(lib, M, d["id"], vid)
    if info is None:
        return None
    if answer is None:
        box = QMessageBox(QMessageBox.Warning, "Delete this version" if vid and not info["whole"] else "Delete this document",
                          DR.question(info, vid), parent=page)
        yes = box.addButton("Delete", QMessageBox.DestructiveRole)
        no = box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(no); box.setEscapeButton(no)
        box.exec()
        answer = box.clickedButton() is yes
    if not answer:
        return None
    try:                                             # 4.23.3: the files' names, for Acros & Abs to forget them
        _d, _vs, _whole = DR._scope(lib, d["id"], vid)
        going = list(DR._files_going(lib, _d, _vs)[0]) if _d is not None else []
    except Exception:  # noqa: BLE001
        diag.swallowed(); going = []
    eid = DR.delete(host.ws, lib, M, d["id"], vid)
    if eid is None:
        return None
    try:
        ap = getattr(host, "acronym_page", None)
        if ap is not None and ap.session is not None and going:
            ap.session.forget_files(going)
            ap.fill()
    except Exception:  # noqa: BLE001
        diag.swallowed()
    if M is not None:
        host.changed()
    page.trashed_now = getattr(page, "trashed_now", []) + [eid]
    shred_list(host)
    _log(host, f"{info['name']}: {'deleted' if info['whole'] else ', '.join(info['versions']) + ' deleted'}; in the Trash")
    if info["whole"]:
        diag.activity("document_deleted")
    else:
        diag.activity("document_version_deleted")
    try:
        page.refresh()
    except Exception:  # noqa: BLE001
        diag.swallowed()
    host.toast(f"Deleted {info['name']}" + ("" if info["whole"] else f" ({', '.join(info['versions'])})")
               + ". It is in the Trash; Undo (Ctrl+Z) puts it back.")
    try:
        host.refresh_undo()
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return eid


def shred_list(host):
    """4.23.2: after a document is deleted or put back, Shred's document list is filled again, so it never offers a
    document that is gone (it kept the names until the effort was opened again). When the document Shred had open is
    the one that went, Shred opens afresh."""
    ap = getattr(host, "assign_page", None)
    if ap is None or not hasattr(ap, "files"):
        return False
    try:
        cur = ap.files.currentText()
        ap.load_files_keep()
        if cur and ap.files.findText(cur) < 0:
            ap.load()
        return True
    except Exception:  # noqa: BLE001  Shred fills its list when it opens next
        diag.swallowed()
        return False


def install(page):
    """Documents' Undo (the top bar and Ctrl+Z ask the page first), and a version's right-click: Delete this version..."""
    page.trashed_now = []
    page.undo_text = lambda: undo_text(page)
    page.undo_here = lambda: undo(page)
    lst = getattr(page, "d_versions", None)
    if lst is not None:
        from PySide6.QtCore import Qt
        lst.setContextMenuPolicy(Qt.CustomContextMenu)
        lst.customContextMenuRequested.connect(lambda pos: version_menu(page, lst.indexAt(pos).row(), lst.mapToGlobal(pos)))


def version_menu(page, row, at=None, run=True):
    """The versions list's right-click: Delete this version... (the newest is listed first). Returns the menu."""
    from PySide6.QtWidgets import QMenu
    m = QMenu(page)
    d = page.lib.doc(page.current_id()) if page.lib and page.current_id() else None
    vs = list(reversed(d["versions"])) if d else []
    if 0 <= row < len(vs):
        v = vs[row]
        m.addAction("Delete this version...", lambda: delete(page, d, v["id"]))
    page._vmenu = m
    if run and at is not None and m.actions():
        m.exec(at)
    return m


def undo_text(page):
    import doctrash as T
    if not getattr(page, "trashed_now", None) or page.host.ws is None:
        return ""
    e = T.entry(page.host.ws, page.trashed_now[-1])
    return f"Delete {e['name']}" if e else ""


def undo(page):
    label = undo_text(page)
    if not label:
        page.host.status("Nothing to undo on this page.")
        return None
    eid = page.trashed_now.pop()
    if restore(page, eid) is None:
        return None
    page.host.status(f"Undone: {label}")
    return label


def restore(page, eid):
    """Put a Trash entry back (a document, a version, a replaced file, or pieces). Returns the entry or None."""
    import docremove as DR
    import docreplace as RP
    import doctrash as T
    host = page.host
    e = T.entry(host.ws, eid)
    if e is None:
        return None
    lib, M = _lib(host), _M(host)
    if e["kind"] in ("document", "version"):
        got = DR.restore(host.ws, lib, M, eid)
    elif e["kind"] == "replaced":
        got = RP.restore(host.ws, lib, M, eid)
    elif e["kind"] == "pieces" and M is not None:
        got = T.take_back(host.ws, eid)
        import compliance as C
        taken = {it.get("id") for it in M.items}
        for it in got["payload"].get("items", []):
            if it.get("id") in taken:
                it["id"] = ""
            M.items.append(it)
        C.assign_ids(M.items)
        M.pending = True
    else:
        return None
    if got is not None and M is not None:
        host.changed()
    shred_list(host)
    _log(host, f"{e['name']}: put back from the Trash")
    diag.activity("trash_restored")
    try:
        page.refresh()
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return got


KIND = {"document": "Document", "version": "Version", "replaced": "File before it was replaced", "pieces": "Shred pieces"}


class TrashDialog(QDialog):
    """What was deleted or replaced, newest first: Restore puts the selected entry back; Empty the Trash... removes
    everything in it for good, after asking."""
    def __init__(self, page):
        super().__init__(page)
        import doctrash as T
        from . import design as D
        self.page = page
        self.setWindowTitle("Trash")
        self.resize(820, 420)
        v = QVBoxLayout(self)
        self.say = QLabel(); self.say.setWordWrap(True); v.addWidget(self.say)
        self.table = QTableWidget(0, 4); self.table.setHorizontalHeaderLabels(["What", "Kind", "When", "Who"])
        self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 380); self.table.setColumnWidth(1, 170); self.table.setColumnWidth(2, 140)
        v.addWidget(self.table, 1)
        row = QHBoxLayout(); v.addLayout(row)
        row.addWidget(D.button("Empty the Trash...", "danger", lambda: self.empty()))
        row.addStretch(1)
        row.addWidget(D.button("Close", None, self.accept))
        row.addWidget(D.button("Restore", "primary", lambda: self.restore()))
        self.T = T
        self.fill()

    def fill(self):
        ws = self.page.host.ws
        self.items = self.T.entries(ws)
        self.table.setRowCount(len(self.items))
        for r, e in enumerate(self.items):
            for c, val in enumerate((e["name"], KIND.get(e["kind"], e["kind"]), e["when"].replace("T", " ")[:16], e.get("who", ""))):
                self.table.setItem(r, c, QTableWidgetItem(val))
        mb = self.T.size(ws) / 1e6
        self.say.setText(f"{len(self.items)} item(s) in the effort's Trash ({mb:.1f} MB). Restore puts the selected one back "
                         "where it was." if self.items else "The Trash is empty.")
        if self.items:
            self.table.selectRow(0)

    def restore(self, row=None):
        r = self.table.currentRow() if row is None else row
        if not (0 <= r < len(self.items)):
            return None
        got = restore(self.page, self.items[r]["id"])
        self.fill()
        return got

    def empty(self, answer=None):
        if answer is None:
            box = QMessageBox(QMessageBox.Warning, "Empty the Trash", f"Remove the {len(self.items)} item(s) in the Trash for "
                              "good? Their files and records cannot be put back after this.", parent=self)
            yes = box.addButton("Empty the Trash", QMessageBox.DestructiveRole)
            no = box.addButton(QMessageBox.Cancel)
            box.setDefaultButton(no); box.setEscapeButton(no)
            box.exec()
            answer = box.clickedButton() is yes
        if not answer:
            return 0
        n = self.T.empty(self.page.host.ws)
        _log(self.page.host, f"Trash emptied: {n} item(s) removed for good")
        self.fill()
        return n


def show_trash(page, run=True):
    dlg = TrashDialog(page)
    page._trash = dlg
    if run and not os.environ.get("AH_TEST"):
        dlg.exec()
    return dlg
