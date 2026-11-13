"""Used for and Source on Documents (4.25.2; claude/stationkeeper-documents-board-2026-11-12.html, step B; answers 4
and 6). A document says what it is used for with marks, and may carry several: For the shred or Reference, and Return
it, redlined or Return it, filled in. No mark at all leaves it out. Source says whose it is, Customer or Internal; it
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


def toggle(page, key, ids=None):
    """Tick or untick a mark on the selected documents. For the shred and Reference take each other's place; unticking
    the one a document has leaves it with no mark of that kind (left out of the shred and of search as context).
    Returns how many documents changed."""
    lib = page.lib
    ids = ids or page.selected_ids()
    if lib is None or not ids:
        return 0
    first = lib.doc(ids[0])
    on = not has(lib, first, key)
    n = 0
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
    diag.activity("library_used_for_set", n=n)
    page.host.toast(f"{n} document(s): " + ("" if on else "not ") + dict(MARKS)[key])
    page.fill_tree(); page.fill()
    try:
        page.host.assign_page.fill_files() if hasattr(page.host.assign_page, "fill_files") else None
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return n


MARKS = (("shred", "For the shred"), ("reference", "Reference"), ("redline", "Return it, redlined"), ("fill", "Return it, filled in"))


def menu(page, m, d):
    """The Used for and Source parts of a document's right-click menu."""
    lib = page.lib
    um = m.addMenu("Used for")
    for k, n in MARKS:
        a = um.addAction(n, lambda k=k: toggle(page, k)); a.setCheckable(True); a.setChecked(has(lib, d, k))
        if k == "reference":
            um.addSeparator()
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
