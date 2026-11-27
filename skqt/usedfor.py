"""Purpose and Source on Documents (4.25.2 as Used for; claude/stationkeeper-documents-board-2026-11-12.html, step B;
answers 4 and 6; 4.83.0 in decision 216's words, step D3). A document says what it is for with marks, and may carry
several (215): Customer document or Reference, and Form to fill in, File to submit or Redline to return, each of which
points at a deliverable (asked: the suggestion, another, or New; delivdoor). No mark at all leaves it out. Source says whose it is, Customer or Internal; it
comes from the folder the file is in and can be changed for one file. The marks drive the other screens: Shred offers
the documents marked Customer document to extract, and the rest to read beside.

The saved words do not change (role: matrix, context, reference, not_needed; category: customer, bidders, qa, ours,
graphics and a team's own), so an effort made before reads the same; "returns" is a new key a document may carry.
Rules only (No AI); nothing leaves the PC."""
import diag
import docversions as DV

FILTERS = (("shred", "Customer document"), ("returned", "Returned to the customer"))


def has(lib, d, key):
    """The document carries the mark: shred, reference, fill, submit, redline."""
    if key == "shred":
        return lib.role_of(d) == "matrix"
    if key == "reference":
        return lib.role_of(d) in ("context", "reference")
    return key in lib.returns_of(d)


def text_of(lib, d):
    return ", ".join(lib.marks_of(d))


DOOR = ("fill", "submit", "redline")


def toggle(page, key, ids=None, answer=None, deliverable=None):
    """Tick or untick a mark on the selected documents. Customer document and Reference take each other's place;
    unticking the one a document has leaves it with no mark of that kind (left out of the shred and of search as
    context). 4.83.0 (D3): ticking Form to fill in, File to submit or Redline to return on one document asks which
    deliverable it is (deliverable, for tests: an id or "new"); on several, each takes its suggestion or a new one.
    Returns how many documents changed."""
    lib = page.lib
    ids = ids or page.selected_ids()
    if lib is None or not ids:
        return 0
    first = lib.doc(ids[0])
    on = not has(lib, first, key)
    n = tiles = gone = 0
    if not on and key in DOOR:      # 4.29.2: the mark and the tile go together, asked first
        lose = _tiles_lost(page, lib, ids, key)
        if lose and not _proceed(page, lose, answer):
            return 0
    pick = None
    if on and key in DOOR and page.host.ws is not None:
        if len(ids) == 1:
            pick = deliverable if deliverable is not None else which_deliverable(page, lib, first, key)
            if pick is None:
                return 0
    for i in ids:
        d = lib.doc(i)
        if d is None:
            continue
        if key in ("shred", "reference"):
            want = {"shred": "matrix", "reference": "reference"}[key] if on else "not_needed"
            if DV.use_key(lib.role_of(d)) != want:
                n += bool(lib.set_role(i, want, "Purpose"))
        else:
            cur = lib.returns_of(d)
            new = cur + [key] if on and key not in cur else [k for k in cur if k != key or on]
            if new != cur:
                n += bool(lib.set_returns(i, new))
            if on:
                tiles += bool(_tile(page, lib, lib.doc(i), key, pick if pick is not None else _auto(page, lib.doc(i), key)))
            else:
                gone += bool(_drop(page, lib, i, key))
    diag.activity("library_used_for_set", n=n)
    more = ""
    if key in DOOR:       # 4.25.3: the tile on Deliverables
        more = (f". {tiles} tile(s) made on Deliverables" if tiles else "") if on else (f". {gone} removed from Deliverables" if gone else "")
    page.host.toast(f"{n} document(s): " + ("" if on else "not ") + dict(MARKS)[key] + more)
    page.fill_tree(); page.fill()
    try:
        page.host.assign_page.fill_files() if hasattr(page.host.assign_page, "fill_files") else None
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return n


def split_uses(plan):
    """4.61.0: a document added as Form to fill in, File to submit or Redline to return is kept as Reference and carries
    the mark."""
    for e in plan:
        if e.get("role") in DOOR:
            e["returns"], e["role"] = [e["role"]], "reference"
    return plan


def after_added(page, plan, made):
    """4.61.0: the marks chosen when the documents were added, and each one's deliverable (4.83.0: the one picked in the
    Deliverable field, or a new one; a file added for a Document We Write is attached to it). Returns how many."""
    n = 0
    if isinstance(made, Exception) or page.host.ws is None or not any(e.get("returns") or e.get("deliverable") for e in plan):
        return n
    try:
        import os
        import delivdoor as DD
        import delivnext as DN
        lib = DV.Library(page.lib.folder).load()
        rec = _rec(page)
        for e in plan:
            if e.get("choice") == "skip" or not (e.get("returns") or e.get("deliverable")):
                continue
            d = lib.doc(e.get("made_doc")) if e.get("made_doc") else lib.doc_of_file(os.path.basename(e.get("path", "")))
            if d is None:
                continue
            did = e.get("deliverable")
            for k in e.get("returns") or []:
                DD.link(rec, lib, d["id"], k, did if did and k == e["returns"][0] else DD.NEW)
            if did and did != DD.NEW and not e.get("returns"):
                DN.attach(rec, lib, did, d["id"])
            n += 1
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return n


def _auto(page, d, key):
    """Several documents at once: each takes the deliverable the app suggests for it, or a new one."""
    try:
        import delivdoor as DD
        return DD.default(_rec(page), d.get("name", ""), key)
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return "new"


def which_deliverable(page, lib, d, key, run=True):
    """4.83.0 (D3): which deliverable this document is, asked when one document is given Form to fill in, File to submit
    or Redline to return: the app's suggestion first, the others of that kind, New. Returns an id, "new", or None when
    cancelled. run False (tests): the window, not shown."""
    import delivdoor as DD
    from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout
    rec = _rec(page)
    sugg = DD.suggest(rec, d.get("name", ""), key)
    opts = DD.options(rec, key)
    if not opts:
        return DD.NEW
    dlg = QDialog(page); dlg.setWindowTitle(f"{d.get('name', '')}: {dict(MARKS)[key]}")
    f = QFormLayout(dlg)
    cb = QComboBox()
    if sugg:
        cb.addItem(dict(opts).get(sugg, "") + "  (suggested)", sugg)
    for did, words in opts:
        if did != sugg:
            cb.addItem(words, did)
    cb.addItem("New deliverable", DD.NEW)
    cb.setCurrentIndex(0 if sugg else cb.count() - 1)          # no suggestion: New, never a guess
    from . import design as D
    f.addRow(D.label(f"{d.get('name', '')}: {dict(MARKS)[key]}. Which deliverable is it the file of?", "muted"))
    f.addRow("Deliverable:", cb)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject)
    f.addRow(bb)
    dlg.cb = cb
    if not run:
        return dlg
    return cb.currentData() if dlg.exec() == QDialog.Accepted else None


def _rec(page):
    import effortrec as RR
    return RR.Record(page.host.ws.root)


def _tiles_lost(page, lib, ids, key):
    """The names of the documents whose tile would leave Deliverables: this is their only mark, and they have a tile."""
    try:
        import docreturn as DR
        rec = _rec(page)
        return [d["name"] for d in (lib.doc(i) for i in ids)
                if d is not None and DR.tile_of(rec, d["id"], key) is not None and not DR.tile_of(rec, d["id"], key).get("shred_kind")
                and (key == "submit" or not [m for m in lib.returns_of(d) if m in DR.CUSTOMER_MARKS and m != key])]
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return []


def _proceed(page, names, answer=None):
    """This removes it from Deliverables. Proceed? answer (tests): True or False, no question."""
    if answer is not None:
        return bool(answer)
    from PySide6.QtWidgets import QMessageBox
    what = f"{names[0]}: this removes it from Deliverables." if len(names) == 1 else f"This removes {len(names)} documents from Deliverables."
    box = QMessageBox(QMessageBox.Warning, "Remove from Deliverables", what + " Proceed?", parent=page)
    yes = box.addButton("Proceed", QMessageBox.AcceptRole)
    no = box.addButton(QMessageBox.Cancel)
    box.setDefaultButton(no); box.setEscapeButton(no)
    box.exec()
    return box.clickedButton() is yes


def _drop(page, lib, doc_id, key=None):
    try:
        import docreturn as DR
        return DR.drop_tile(_rec(page), lib, doc_id, mark=key)
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return False


def _tile(page, lib, d, key, did=None):
    """The document's deliverable (4.25.3; 4.83.0: did, the one picked). True when one was made now."""
    try:
        import docreturn as DR
        import effortrec as RR
        _t, made = DR.ensure_tile(RR.Record(page.host.ws.root), lib, d, key, did=did)
        return made
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return False


def open_tile(page, d):
    """Deliverables, on the document's tile."""
    import docreturn as DR
    import effortrec as RR
    t = DR.tile_of(RR.Record(page.host.ws.root), d["id"])
    if t is None:
        return None
    page.host.go("deliverables")
    try:
        page.host.deliverables_page.pick(t["id"])
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return t["id"]


MARKS = (("shred", "Customer document"), ("reference", "Reference"), ("fill", "Form to fill in"), ("submit", "File to submit"),
         ("redline", "Redline to return"))


def menu(page, m, d):
    """The Purpose and Source parts of a document's right-click menu."""
    lib = page.lib
    um = m.addMenu("Purpose")
    for k, n in MARKS:
        a = um.addAction(n, lambda k=k: toggle(page, k)); a.setCheckable(True); a.setChecked(has(lib, d, k))
        if k == "reference":
            um.addSeparator()
    if lib.returns_of(d):
        m.addAction("Open its deliverable", lambda: open_tile(page, d))
    sm = m.addMenu("Source")
    cust = d.get("category", "customer") in ("customer", "bidders", "qa")
    for key, n in (("customer", "Customer"), ("ours", "Internal")):
        a = sm.addAction(n, lambda key=key: set_source(page, key)); a.setCheckable(True)
        a.setChecked(cust == (key == "customer"))
    return um, sm


def set_source(page, side, ids=None):
    """Customer or Internal for the selected documents. Nothing moves on disk: only whose the document is."""
    lib = page.lib
    ids = ids or page.selected_ids()
    n = 0
    for i in ids:
        d = lib.doc(i) if lib is not None else None
        if d is None:
            continue
        now = "customer" if d.get("category", "customer") in ("customer", "bidders", "qa") else "ours"
        if now == side:
            continue
        key = "bidders" if side == "customer" and not (d.get("initial") and d.get("type")) else side
        n += bool(lib.set_category(i, key))     # a document with no type and initial yet reads as the customer's, for reference
    diag.activity("library_source_set", n=n)
    if n:
        page.host.toast(f"{n} document(s): " + ("Customer" if side == "customer" else "Internal"))
        page.fill_tree(); page.fill()
    return n
