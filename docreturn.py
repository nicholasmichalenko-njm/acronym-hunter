"""A customer document that goes back to the customer (4.25.3; Documents board 2026-11-12, step C; answers 2, 25, 32).
A document marked Return it, redlined or Return it, filled in has a tile on Deliverables, linked both ways: marking the
document makes the tile (kind Customer file, no owner: someone must take it), and a deliverable filled on a customer
document marks that document. The tile remembers the customer's version it was started on, so an amendment shows on it:
a form is filled again on the new version; a redline made on the old version is kept, and a new one is prepared.
Rules only (No AI); nothing leaves the PC."""
import deliverables as DL

WORDS = {"redline": "Return it, redlined", "fill": "Return it, filled in"}


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
    marks that document Return it, filled in. Returns (tiles made, documents marked)."""
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
