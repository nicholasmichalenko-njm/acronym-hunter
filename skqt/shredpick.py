"""Picking a document in Shred extracts it (4.1.0; claude/stationkeeper-shred-plan-4.1.md, step 3). The document list on
Shred > Requirements names every customer document that builds the matrix; one not extracted yet reads "(not extracted
yet)". Picking it extracts it at once, in the background, with no question: its initial and type come from Documents or
are suggested, a new matrix goes where Settings > Folders and file names puts it, and the structure starts the usual way.
The extract's progress, Stop and how it ended show on Shred (the panel that was on the Extract tab), and the document
opens when it is done. The Extract tab is gone; go("read") lands on Shred.

Rules only (No AI); nothing leaves the PC."""
import os
import diag

TAIL = " (not extracted yet)"
HINT = "Pick a customer document above. Stationkeeper extracts it and opens it here to shred."


def _lib(host):
    import docversions as DV
    return DV.Library(host.ws.p("documents")).load() if host.ws is not None else None


def pending(host):
    """[(label, doc id, path)]: the customer documents that build the matrix and are not extracted yet."""
    import compliance_read as CR
    lib = _lib(host)
    if lib is None:
        return []
    have = set(host.review.files()) if host.review is not None else set()
    out = []
    for name, _label, path in CR.effort_docs(host.ws):
        d = lib.doc_of_file(os.path.basename(path))
        if d is None or lib.role_of(d) != "matrix" or os.path.basename(path) in have:
            continue
        out.append((name + TAIL, d["id"], path))
    return out


def fill(page):
    """Add the documents to extract to Shred's document list (signals blocked by the caller). Returns {label: doc id}."""
    try:
        ents = pending(page.host)
    except Exception:
        diag.swallowed()
        ents = []
    page.extract_entries = {}
    if ents and page.files.count():
        page.files.insertSeparator(page.files.count())
    for lab, did, _p in ents:
        page.files.addItem(lab)
        page.extract_entries[lab] = did
    if page.R is None:                          # nothing extracted: the list asks for a pick, the page says how
        page.files.setCurrentIndex(-1)
        page.files.setPlaceholderText("Pick a document to shred" if ents else "No customer documents yet")
        page.note.setText(HINT if ents else "Add the customer's documents in Documents. They are listed here to shred.")
    return page.extract_entries


def extract(page, doc_id, out=None):
    """Extract one document now, in the background, and open it in Shred when done. Returns the worker or None."""
    h = page.host
    rp = h.read_page
    if rp.running():
        h.status("An extract is running. Wait for it to finish, or press Stop.")
        return None
    ent = next((e for e in pending(h) if e[1] == doc_id), None)
    if ent is None:
        h.status("That document is extracted already, or it is left out.")
        return None
    name, path = ent[0][:-len(TAIL)], ent[2]
    if out is None and h.review is None:
        out = h.out_path("compliance_matrix")
        if out:
            os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    rp.refresh()
    f = os.path.basename(path)
    rp._then = lambda: open_after(page, f)
    w = rp.read(paths=[path], out=out, identities="suggested", start="auto")
    if w is None:
        rp._then = None
        return None
    page.note.setText(f"Extracting {name}. It opens here when it is done; you can keep working meanwhile.")
    diag.activity("shred_extract_on_pick")
    return w


def extract_paths(host, paths, then_file="", out=None):
    """Extract several documents (Documents' Open in Shred, before any matrix): no question, the first opens after."""
    rp = host.read_page
    if rp.running():
        host.status("An extract is running. Wait for it to finish, or press Stop.")
        return None
    if out is None and host.review is None:
        out = host.out_path("compliance_matrix")
        if out:
            os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    rp.refresh()
    page = host.assign_page
    rp._then = (lambda: open_after(page, then_file)) if then_file else None
    w = rp.read(paths=paths, out=out, identities="suggested", start="auto")
    if w is None:
        rp._then = None
    else:
        host.go("assign")
    return w


def extract_file(host, f):
    """Extract a file by name (Text check's Next, Verify's read it again): a document not extracted yet is extracted;
    one extracted already is read again, every decision kept. Opens it in Shred when done. Returns the worker or None."""
    import compliance_read as CR
    page = host.assign_page
    lib = _lib(host)
    d = lib.doc_of_file(os.path.basename(f)) if lib is not None else None
    if d is not None and any(did == d["id"] for _l, did, _p in pending(host)):
        host.go("assign")
        return extract(page, d["id"])
    path = next((p for _n, _l, p in CR.effort_docs(host.ws) if os.path.basename(p) == os.path.basename(f)), "")
    if not path:
        host.status(f"{os.path.basename(f)} is not one of the customer documents: add it in Documents.")
        return None
    return extract_paths(host, [path], then_file=os.path.basename(path))


def open_after(page, f):
    page.note.setText("")
    page.load_files_keep()
    if page.R is not None and f in page.R.files():
        page.files.setCurrentText(f)
    return f
