"""A customer document that goes back to the customer (4.25.3; Documents board 2026-11-12, step C; answers 2, 25, 32).
A document marked Redlined Deliverable or Filled-in Deliverable has a tile on Deliverables, linked both ways: marking the
document makes the tile (kind Customer file, no owner: someone must take it), and a deliverable filled on a customer
document marks that document. 4.29.2: the marks' names (it is a deliverable of its own, not a return), and the two stay
in step: taking the last mark off removes the tile (asked first), and deleting the tile takes the marks off. The tile remembers the customer's version it was started on, so an amendment shows on it:
a form is filled again on the new version; a redline made on the old version is kept, and a new one is prepared.
Rules only (No AI); nothing leaves the PC."""
import deliverables as DL

WORDS = {"redline": "Redlined Deliverable", "fill": "Filled-in Deliverable"}


def tile_of(rec, doc_id):
    """The deliverable linked to a document, or None."""
    return next((x for x in DL.items(rec) if x.get("doc_id") == doc_id), None) if doc_id else None


def ensure_tile(rec, lib, d, mark, who=None):
    """The document's tile on Deliverables, made when it has none. Returns (deliverable, made)."""
    t = tile_of(rec, d["id"])
    made = False
    if t is None:
        latest = (d.get("versions") or [{}])[-1]
        did = DL.add(rec, d.get("name", "Customer document"), kind="Customer file", doc_id=d["id"], form_version=latest.get("id", ""),
                     owner="", notes=WORDS.get(mark, ""), who=who)
        t = DL.get(rec, did)
        made = True
    if t is not None and t.get("returns") != mark and mark in WORDS:
        t["returns"] = mark
        rec.save()
    return t, made


def sync(rec, lib):
    """Both ways, quietly: a document with a return mark has its tile; a deliverable filled on a customer document
    marks that document Filled-in Deliverable. Returns (tiles made, documents marked)."""
    made = marked = 0
    for d in list(lib.all):
        marks = lib.returns_of(d)
        if marks and tile_of(rec, d["id"]) is None:
            ensure_tile(rec, lib, d, "redline" if "redline" in marks else "fill")
            made += 1
    for x in DL.items(rec):
        d = lib.doc(x.get("doc_id")) if x.get("doc_id") else None
        if d is not None and not lib.returns_of(d):
            lib.set_returns(d["id"], [x.get("returns") if x.get("returns") in WORDS else "fill"])
            marked += 1
    return made, marked


def drop_tile(rec, lib, doc_id, who=None):
    """4.29.2 (Nicholas 2026-11-13 answer 4): the document's last mark came off, so its tile leaves Deliverables (it can
    be put back with Undo there). With a mark left, the tile stays and says that mark. Returns True when a tile left."""
    t = tile_of(rec, doc_id)
    if t is None:
        return False
    d = lib.doc(doc_id)
    left = lib.returns_of(d) if d is not None else []
    if left:
        if t.get("returns") not in left:
            t["returns"] = left[0]
            rec.save()
        return False
    return bool(DL.remove(rec, t["id"], who=who))


def unmark(lib, deliverable):
    """4.29.2: a tile deleted on Deliverables takes its document's marks off. Returns the document's name, or ""."""
    d = lib.doc(deliverable.get("doc_id")) if lib is not None and deliverable.get("doc_id") else None
    if d is None or not lib.returns_of(d):
        return ""
    lib.set_returns(d["id"], [])
    return d.get("name", "")
