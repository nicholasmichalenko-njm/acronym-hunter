"""Used for and Source on Documents (4.25.2; claude/stationkeeper-documents-board-2026-11-12.html, step B; answers 4
and 6). A document says what it is used for with marks, and may carry several: For the shred or Reference, and Return
it, redlined or Filled-in Deliverable. No mark at all leaves it out. Source says whose it is, Customer or Internal; it
comes from the folder the file is in and can be changed for one file. The marks drive the other screens: Shred offers
the documents marked For the shred to extract, and the rest to read beside.

The saved words do not change (role: matrix, context, reference, not_needed; category: customer, bidders, qa, ours,
graphics and a team's own), so an effort made before reads the same; "returns" is a new key a document may carry.
Rules only (No AI); nothing leaves the PC."""
import diag
import docversions as DV

FILTERS = (("shred", "For the shred"), ("returned", "Returned to the customer"))


def has(lib, d, key):
    """The document carries the mark: shred, reference, redline, fill."""
    if key == "shred":
        return lib.role_of(d) == "matrix"
    if key == "reference":
        return lib.role_of(d) in ("context", "reference")
    return key in lib.returns_of(d)


def text_of(lib, d):
    return ", ".join(lib.marks_of(d))


def toggle(page, key, ids=None, answer=None):
    """Tick or untick a mark on the selected documents. For the shred and Reference take each other's place; unticking
    the one a document has leaves it with no mark of that kind (left out of the shred and of search as context).
    Returns how many documents changed."""
    lib = page.lib
    ids = ids or page.selected_ids()
    if lib is None or not ids:
        return 0
    first = lib.doc(ids[0])
    on = not has(lib, first, key)
    n = tiles = gone = 0
    if not on and key in ("redline", "fill"):      # 4.29.2: the mark and the tile go together, asked first
        lose = _tiles_lost(page, lib, ids, key)
        if lose and not _proceed(page, lose, answer):
            return 0
    for i in ids:
        d = lib.doc(i)
        if d is None:
            continue
        if key in ("shred", "reference"):
            want = {"shred": "matrix", "reference": "reference"}[key] if on else "not_needed"
            if DV.use_key(lib.role_of(d)) != want:
                n += bool(lib.set_role(i, want, "Used for"))
        else:
            cur = lib.returns_of(d)
            new = cur + [key] if on and key not in cur else [k for k in cur if k != key or on]
            if new != cur:
                n += bool(lib.set_returns(i, new))
            if on:
                tiles += bool(_tile(page, lib, lib.doc(i), key))
            else:
                gone += bool(_drop(page, lib, i))
    diag.activity("library_used_for_set", n=n)
    more = ""
    if key in ("redline", "fill"):       # 4.25.3: the tile on Deliverables
        more = (f". {tiles} tile(s) made on Deliverables" if tiles else "") if on else (f". {gone} removed from Deliverables" if gone else "")
    page.host.toast(f"{n} document(s): " + ("" if on else "not ") + dict(MARKS)[key] + more)
    page.fill_tree(); page.fill()
    try:
        page.host.assign_page.fill_files() if hasattr(page.host.assign_page, "fill_files") else None
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return n


def _rec(page):
    import effortrec as RR
    return RR.Record(page.host.ws.root)


def _tiles_lost(page, lib, ids, key):
    """The names of the documents whose tile would leave Deliverables: this is their only mark, and they have a tile."""
    try:
        import docreturn as DR
        rec = _rec(page)
        return [d["name"] for d in (lib.doc(i) for i in ids)
                if d is not None and lib.returns_of(d) == [key] and DR.tile_of(rec, d["id"]) is not None]
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


def _drop(page, lib, doc_id):
    try:
        import docreturn as DR
        return DR.drop_tile(_rec(page), lib, doc_id)
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return False


def _tile(page, lib, d, key):
    """The document's tile on Deliverables (4.25.3). True when one was made now."""
    try:
        import docreturn as DR
        import effortrec as RR
        _t, made = DR.ensure_tile(RR.Record(page.host.ws.root), lib, d, key)
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


MARKS = (("shred", "For the shred"), ("reference", "Reference"), ("redline", "Redlined Deliverable"), ("fill", "Filled-in Deliverable"))


def menu(page, m, d):
    """The Used for and Source parts of a document's right-click menu."""
    lib = page.lib
    um = m.addMenu("Used for")
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
