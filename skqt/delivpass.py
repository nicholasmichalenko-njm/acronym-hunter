"""Shred in passes, the Deliverables pass on the screen (4.76.0; 4.77.0). The Shred page in the pass's own mode (the
Compliance pass's page and bar, skqt/comppass.py, with these buttons in place of the three kinds): Document We Write,
Form We Fill In, File We Submit, Redline We Return on 1 to 4. A kind's key shows the name the app suggests on the bar,
to change before Enter; a name already on the Deliverables list attaches to that row, a near one asks once (Attach or
Add as new); pieces marked together are one deliverable. The bar names the deliverable a piece is on and opens its
row. (Key date was on this bar from 4.76.0; 4.82.0 moved it to its own pass, skqt/keypass.py.) 4.81.0 (D2, decision
176): once the row is made, the bar asks Its file: the document in Documents the app suggests (Enter), another one from
Documents, Add a file now (through Documents' own Add, attached once it is in), or None yet. Rules only; nothing leaves
the PC."""
import os

from PySide6.QtWidgets import QLabel, QLineEdit

import custstruct as CS
import delivmark as DM
import diag
from . import design as D

KEY = "delivpass"


def _who():
    try:
        import effort as E
        return E.user_name()
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def _later(page):
    __import__("skqt.shredselbar", fromlist=["x"]).later(page)


def asking(page, rows):
    """The name question open for exactly the selected pieces, or None."""
    a = getattr(page, "_deliv_ask", None)
    return a if a and a["ids"] == [it["id"] for it in rows] else None


def file_asking(page, rows):
    """4.81.0: the Its file question open for exactly the selected pieces, or None."""
    a = getattr(page, "_deliv_file", None)
    return a if a and a["ids"] == [it["id"] for it in rows] else None


def _lib(page):
    import docversions as DV
    return DV.Library(page.host.ws.p("documents")).load()


def _short(s, n=24):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n - 3].rstrip() + "..."


def buttons(page, f, rows, M, it, one, col):
    """The pass's own buttons on the bar beside the piece. Returns "ask" when the bar holds only the name question."""
    from . import comppass as CP
    rec = CP.rec_of(page)
    f.kinds, f.on_list, f.keydate, f.before = {}, None, None, None
    f.name_edit, f.name_ok, f.attach, f.add_new = None, None, None, None
    f.file_sugg, f.file_pick, f.file_add, f.file_none = None, None, None, None
    fa = file_asking(page, rows)
    if fa:                                                     # 4.81.0 (176): Its file, Enter takes the suggestion
        lab = QLabel(f"{fa['name']} is on Deliverables. Its file:"); lab.setWordWrap(True)
        col.addWidget(lab)
        if fa.get("sugg"):
            f.file_sugg = D.button(_short(fa["sugg_name"]) + "  Enter", "primary", lambda: file_take(page, "sugg"),
                                   f"{fa['sugg_name']}, in Documents: its name matches the customer's words")
            col.addWidget(f.file_sugg)
        f.file_pick = D.button("A file in Documents...", None, lambda: file_take(page, "pick"), "Pick any document already in Documents")
        f.file_add = D.button("Add a file now...", None, lambda: file_take(page, "add"),
                              "It goes into Documents through Add, and is attached as soon as it is in")
        f.file_none = D.button("None yet" + ("" if fa.get("sugg") else "  Enter"), None if fa.get("sugg") else "primary",
                               lambda: file_take(page, "none"), "Usual for a document we write. Attach it later on Deliverables")
        for b in (f.file_pick, f.file_add, f.file_none):
            col.addWidget(b)
        return "ask"
    a = asking(page, rows)
    if a and a.get("near"):                                    # a near match: asked once
        lab = QLabel(f"{DM.NAME[a['key']]}. Same as \"{a['near_name']}\" on the Deliverables list?"); lab.setWordWrap(True)
        col.addWidget(lab)
        f.attach = D.button("Attach to it  Enter", "primary", lambda: take(page, "attach"), "No second row: the piece goes on that deliverable")
        f.add_new = D.button("Add as new", None, lambda: take(page, "new"), "A row of its own, under the name you gave")
        col.addWidget(f.attach); col.addWidget(f.add_new)
        col.addWidget(D.button("Cancel  Esc", "ghost", lambda: cancel(page)))
        return "ask"
    if a:
        lab = QLabel(DM.NAME[a["key"]] + (f", {len(rows)} pieces as one deliverable" if len(rows) > 1 else "") + ". Its name:"); lab.setWordWrap(True)
        col.addWidget(lab)
        f.name_edit = QLineEdit(a["name"])
        f.name_edit.setToolTip("The name on the Deliverables list, suggested from the customer's words. Change it if it is not what you call it")
        f.name_edit.textChanged.connect(lambda t, a=a: a.__setitem__("name", t))    # what is typed outlives a redraw of the bar
        f.name_edit.returnPressed.connect(lambda: take(page))
        col.addWidget(f.name_edit)
        f.name_ok = D.button("Add to Deliverables  Enter", "primary", lambda: take(page), "A row of the Deliverables list at once. A name already on the list attaches to that row")
        col.addWidget(f.name_ok)
        col.addWidget(D.button("Cancel  Esc", "ghost", lambda: cancel(page)))
        f.name_edit.setFocus(); f.name_edit.selectAll()
        return "ask"
    cur = DM.kind_of(rec, it) if one else ""
    d = DM.of_piece(rec, it) if one else None
    for n, (key, name) in enumerate(DM.KINDS, 1):
        b = D.button(f"{n}   {name}", None, lambda _c=False, k=key: mark(page, k), f"{name} ({n}): a row of the Deliverables list, named before Enter")
        b.setCheckable(True); b.setChecked(key == cur); b.setProperty("sk_switch", True)
        b.setStyleSheet("text-align:left;")
        col.addWidget(b); f.kinds[key] = b
    if one and not cur and DM.older(rec, it):
        f.before = QLabel("Marked Deliverable before, kind not said. Pick one of the four."); f.before.setWordWrap(True)
        col.addWidget(f.before)
    if d is not None:
        f.on_list = D.button("On Deliverables: " + d["name"], "ghost", lambda _c=False, x=d["id"]: open_row(page, x), "Opens this deliverable on the Deliverables page")
        f.on_list.setStyleSheet("text-align:left;")
        col.addWidget(f.on_list)
    return f                                                   # 4.82.0: Key date moved to its own pass (K1)


def open_row(page, did):
    """The tag on the bar: the deliverable's own row on the Deliverables page."""
    page.host.go("deliverables")
    try:
        page.host.deliverables_page.open_deliverable(did)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return did


def _finish(page, msg, n):
    from . import comppass as CP
    page._deliv_ask = None
    diag.activity("deliverable_marked", n=n)
    try:
        page.host.changed()
    except Exception:  # noqa: BLE001
        diag.swallowed()
    CP.done(page, msg)
    page.view.setFocus()


def mark(page, key, remove=None):
    """A kind's button or key. Pieces that all have the kind: off. A piece already on a deliverable: its kind changes.
    Otherwise the bar asks the name, suggested from the customer's words; Enter takes it."""
    from . import comppass as CP
    page._deliv_file = None                                   # 4.81.0: a kind's key answers Its file with None yet
    M = CP.M_of(page)
    rows = page.selected() if M is not None and page.cx is None else []
    if not rows:
        page.host.status("Select a piece of the customer's text first.")
        return None
    rec = CP.rec_of(page)
    who = _who()
    if all(DM.kind_of(rec, it) == key for it in rows):
        if remove is None and any(DM.unmark_would_ask(rec, it) for it in rows):
            remove = ask_remove(page, DM.of_piece(rec, rows[0])["name"])
            if remove is None:
                return None
        for it in rows:
            DM.unmark(rec, it, who, remove=bool(remove) if remove is not None else None)
        _finish(page, "Taken off the Deliverables list." if remove is not False else "The piece is off the deliverable; the deliverable stays.", len(rows))
        return "off"
    if len(rows) == 1 and DM.of_piece(rec, rows[0]) is not None:
        did, _how = DM.mark(rec, rows[0], key, who=who)
        _finish(page, f"{DM.NAME[key]}: {DM.DL.get(rec, did)['name']}.", 1)
        return "changed"
    for it in rows:
        if DM.of_piece(rec, it) is not None:
            page.host.status("One of these pieces is already on a deliverable. Mark it by itself.")
            return None
    page._deliv_ask = {"ids": [it["id"] for it in rows], "key": key, "name": DM.suggest_name(rows[0].get("text", "")) or DM.NAME[key]}
    _later(page)
    return "ask"


def ask_remove(page, name):
    """Work has been done to the deliverable: asked once. True removes it, False keeps it without the piece, None stops."""
    from PySide6.QtWidgets import QMessageBox
    m = QMessageBox(page)
    m.setWindowTitle("Take the mark off")
    m.setText(f"\"{name}\" has work on it (an owner, a file, a note or another piece).")
    keep = m.addButton("Keep the deliverable", QMessageBox.AcceptRole)
    rem = m.addButton("Remove the deliverable", QMessageBox.DestructiveRole)
    m.addButton("Cancel", QMessageBox.RejectRole)
    m.exec()
    return False if m.clickedButton() is keep else True if m.clickedButton() is rem else None


def take(page, how=""):
    """Enter on the name, or Attach / Add as new on the near-match question."""
    from . import comppass as CP
    M = CP.M_of(page)
    rows = page.selected() if M is not None else []
    a = asking(page, rows)
    if not a:
        return None
    f = getattr(page, "sel_bar", None)
    if f is not None and getattr(f, "name_edit", None) is not None:
        a["name"] = " ".join(f.name_edit.text().split()) or a["name"]
    rec = CP.rec_of(page)
    who = _who()
    refs = {it["id"]: CS.ref_of(M, it) for it in rows}
    to = None
    if how == "attach":
        to = a.get("near")
    elif how != "new":
        kind, d = DM.match(rec, a["name"])
        if kind == "same":
            to = d["id"]
        elif kind == "near":
            a["near"], a["near_name"] = d["id"], d["name"]
            _later(page)
            return "near"
    for it in rows:
        DM.marks(M).pop(it["id"], None)
    did, made = DM.mark_many(rec, rows, a["key"], a["name"], who=who, to=to, refs=refs)
    d = DM.DL.get(rec, did) if did else None
    name = d["name"] if d else a["name"]
    if d is not None and not to and made == "added" and not __import__("delivnext").has_file(d):   # 4.81.0 (176): a new row, then Its file
        ask_file(page, rows, d)
    _finish(page, (f"Attached to {name} on the Deliverables list." if to else f"{DM.NAME[a['key']]}: {name} is on the Deliverables list."), len(rows))
    return "attached" if to else made


def ask_file(page, rows, d):
    import delivnext as DN
    lib = _lib(page)
    sugg = "" if DN.kind_key(d) == "write" else DN.suggest(lib, d)
    page._deliv_file = {"ids": [it["id"] for it in rows], "did": d["id"], "name": d["name"], "sugg": sugg,
                        "sugg_name": (lib.doc(sugg) or {}).get("name", "") if sugg else ""}
    return page._deliv_file


def file_take(page, how, choose=None, path=None, intake=True):
    """Its file: "sugg" (Enter with a suggestion), "pick" (from Documents), "add" (a file from the PC, through Documents'
    own Add), "none" (Enter without a suggestion). choose and path are for tests. Returns what was done."""
    from . import comppass as CP
    from . import delivact as DA
    import delivnext as DN
    fa = getattr(page, "_deliv_file", None)
    if not fa:
        return None
    rec, lib = CP.rec_of(page), _lib(page)
    msg, got = "", ""
    if how == "sugg" and fa.get("sugg"):
        got = DN.attach(rec, lib, fa["did"], fa["sugg"], who=_who()) and "attached"
        msg = f"{fa['name']}: its file is {fa['sugg_name']}."
    elif how == "pick":
        doc_id = DA.pick_doc(page, lib, fa.get("sugg", ""), choose)
        if not doc_id:
            return None
        got = DN.attach(rec, lib, fa["did"], doc_id, who=_who()) and "attached"
        msg = f"{fa['name']}: its file is {lib.doc(doc_id).get('name', '')}."
    elif how == "add":
        if path is None:
            from PySide6.QtWidgets import QFileDialog
            path, _f = QFileDialog.getOpenFileName(page, f"The file for {fa['name']}", "", "Documents (*.docx *.pdf *.xlsx *.pptx *.doc *.xls);;Every file (*)")
        if not path:
            return None
        DN.want(rec, fa["did"], path, who=_who())
        got = "waiting"
        msg = f"{fa['name']}: {os.path.basename(path)} goes into Documents now, and is its file once it is in."
    else:
        got, msg = "none", f"{fa['name']}: no file yet. Attach it on Deliverables when there is one."
    page._deliv_file = None
    diag.activity("deliverable_file_asked")
    CP.done(page, msg)
    page.view.setFocus()
    if got == "waiting" and intake:
        try:                                         # 4.83.0 (D3): the row comes in with its purpose and this deliverable
            d = __import__("deliverables").get(rec, fa["did"]) or {}
            mark = {"form": "fill", "file": "submit", "redline": "redline"}.get(DN.kind_key(d), "reference")
            page.host.go("library")
            page.host.library_page.add([path], preset={os.path.basename(path): {"role": mark, "deliverable": fa["did"]}})
        except Exception:  # noqa: BLE001
            diag.swallowed()
    return got


def cancel(page):
    page._deliv_ask = page._deliv_file = None
    _later(page)
    page.view.setFocus()
