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
HINT = "Each customer document is extracted when it is added. Pick one above to see its pages."


def _lib(host):
    import docversions as DV
    return DV.Library(host.ws.p("documents")).load() if host.ws is not None else None


def pending(host, versions=False):
    """[(label, doc id, path)]: the customer documents not extracted yet (4.2.0: every one not left out, whatever its
    role; decision 2). A newer version of a document already extracted is not one of them: it comes in through
    newversion (decision 9), so its unchanged sentences never appear twice. versions=True: only those newer versions."""
    import compliance_read as CR
    lib = _lib(host)
    if lib is None:
        return []
    have = set(host.review.files()) if host.review is not None else set()
    out = []
    for name, _label, path in CR.effort_docs(host.ws):
        d = lib.doc_of_file(os.path.basename(path))
        if d is None or lib.role_of(d) != "matrix" or os.path.basename(path) in have:     # 4.25.2: only what is marked For the shred
            continue
        older = any(v.get("file") in have for v in d.get("versions", [])[:-1])
        if older == versions:
            out.append((name + TAIL, d["id"], path))
    return out


def auto_on():
    """Tests turn it on themselves (SK_AUTO_EXTRACT_TEST): most of them add documents and then read them by hand."""
    return not os.environ.get("AH_TEST") or bool(os.environ.get("SK_AUTO_EXTRACT_TEST"))


def auto_tick(host):
    """4.2.0 (decision 2): adding a customer document extracts it. Run on the window's timer: when Documents' index
    changed and documents wait, extract them all in the background (no page change, no question). Returns the worker."""
    if host.ws is None or not auto_on() or host.read_page.running():
        return None
    if getattr(getattr(host, "acronym_page", None), "worker", None) is not None:
        return None                                       # 4.6.0: one reader at a time (the acronym scan runs)
    try:
        idx = os.path.join(host.ws.p("documents"), "index.json")
        st = (host.ws.root, os.path.getmtime(idx) if os.path.isfile(idx) else 0,
              len(host.review.files()) if host.review is not None else -1)
        if st == getattr(host, "_auto_seen", None):
            return None
        host._auto_seen = st
        from . import docmanage as DM                     # 4.17.0: a replaced file is read again first
        w = DM.reread(host)
        if w is not None:
            return w
        waiting = pending(host)
        if waiting:
            return extract_paths(host, [p for _l, _d, p in waiting], go=False)
        new = pending(host, versions=True)
        if new:
            import newversion as NV
            return NV.extract(host, new[0][1])
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return None


def auto_scan(host):
    """4.6.0 (steps decision 10; the UI audit, E): the customer's documents are scanned for acros and abs as soon as they
    are in and extracted, on the same timer as extraction, so Acros & Abs never says "not scanned" with documents in.
    Waits while an extraction or a scan runs; scans again only when the set of documents changed. Returns the worker."""
    if host.ws is None or not auto_on() or host.read_page.running():
        return None
    try:
        ap = getattr(host, "acronym_page", None)
        if ap is None or ap.worker is not None or getattr(ap, "tool", False):
            return None
        if ap.session is None:
            ap.load()
        if ap.session is None:
            return None
        paths = ap.customer_paths()
        key = (host.ws.root, tuple(sorted(paths)))
        if not paths or key == getattr(host, "_acr_seen", None):
            return None
        host._acr_seen = key
        last = sorted((ap.session.last_scan or {}).get("paths") or [])
        if last and set(paths) <= set(last):
            return None                                   # every document here was in the last scan
        if pending(host):
            host._acr_seen = None                         # extraction first; the scan follows on a later tick
            return None
        diag.activity("acronyms_auto_scan", files=len(paths))
        return ap.scan(paths)
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return None


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


def extract_paths(host, paths, then_file="", out=None, go=True):
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
    elif go:
        host.go("assign")
    else:
        host.status(f"Extracting {len(paths)} document(s) for the shred, in the background.")
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
