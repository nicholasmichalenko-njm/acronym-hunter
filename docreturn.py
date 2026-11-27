"""A document that goes back to the customer (4.25.3; Documents board 2026-11-12, step C; answers 2, 25, 32).
A document given the purpose Redline to return, Form to fill in or File to submit (4.83.0, decision 216's words; until
then the marks read Redlined Deliverable and Filled-in Deliverable) has its deliverable on Deliverables, linked both
ways: giving the purpose links it to a deliverable (4.83.0, step D3: the one the person picks, or a new one, which has no
owner: someone must take it), and a deliverable given the customer's file marks that document. 4.29.2: the two stay in
step: taking the last purpose off removes a deliverable the purpose made (asked first), and deleting the deliverable takes
the purpose off. 4.83.0: a deliverable made in Shred is never removed that way; it only lets go of the file. The
deliverable remembers the customer's version it was started on, so an amendment shows on it: a form is filled again on
the new version; a redline made on the old version is kept, and a new one is prepared.
Where the file sits on the deliverable: the customer's (doc_id) for a form or a redline; ours (our_doc) for a file we
submit. Rules only (No AI); nothing leaves the PC."""
import deliverables as DL

WORDS = {"redline": "Redline to return", "fill": "Form to fill in", "submit": "File to submit"}
CUSTOMER_MARKS = ("redline", "fill")          # the file is the customer's: doc_id
KIND_OF = {"redline": "redline", "fill": "form", "submit": "file"}     # the mark, and the deliverable's kind (delivnext)


def slot_of(mark):
    return "our_doc" if mark == "submit" else "doc_id"


def _kind(x):
    import delivnext as DN
    return DN.kind_key(x)


def tile_of(rec, doc_id, mark=None):
    """The deliverable linked to a document (for that mark when one is given), or None."""
    if not doc_id:
        return None
    for x in DL.items(rec):
        if mark is None or mark in CUSTOMER_MARKS:
            if x.get("doc_id") == doc_id and (mark is None or _kind(x) in ("form", "redline", "")):
                return x
        if mark in (None, "submit") and x.get("our_doc") == doc_id and _kind(x) == "file":
            return x
    return None


def ensure_tile(rec, lib, d, mark, who=None, did=None):
    """The document's deliverable for this mark, made when it has none. did: link to that deliverable (4.83.0, the
    Documents door); "new" or None: a new one when the document has none. Returns (deliverable, made)."""
    import delivnext as DN
    if did and did != "new" and DL.get(rec, did) is not None:
        DN.attach(rec, lib, did, d["id"], who=who)
        return DL.get(rec, did), False
    t = tile_of(rec, d["id"], mark)
    made = False
    if t is None:
        latest = (d.get("versions") or [{}])[-1]
        if mark == "submit":
            nid = DL.add(rec, d.get("name", "File to submit"), kind="Attachment", owner="", notes=WORDS["submit"], who=who)
            if nid is not None:
                DL.get(rec, nid)["our_doc"] = d["id"]
                rec.save()
        else:
            nid = DL.add(rec, d.get("name", "Customer document"), kind="Customer file", doc_id=d["id"], form_version=latest.get("id", ""),
                         owner="", notes=WORDS.get(mark, ""), who=who)
        t = DL.get(rec, nid) if nid else None
        made = t is not None
    if t is not None and mark in CUSTOMER_MARKS and t.get("returns") != mark and not t.get("shred_kind"):
        t["returns"] = mark
        rec.save()
    return t, made


def sync(rec, lib):
    """Both ways, quietly: a document with a purpose that goes back has its deliverable; a deliverable given a customer
    document marks it (Form to fill in when it does not say); a File We Submit given a document marks it File to submit
    (4.83.0). Returns (deliverables made, documents marked)."""
    made = marked = 0
    for d in list(lib.all):
        marks = lib.returns_of(d)
        cust = [m for m in marks if m in CUSTOMER_MARKS]
        if cust and tile_of(rec, d["id"], cust[0]) is None and tile_of(rec, d["id"], "redline" if "redline" in cust else "fill") is None:
            ensure_tile(rec, lib, d, "redline" if "redline" in cust else "fill")
            made += 1
        if "submit" in marks and tile_of(rec, d["id"], "submit") is None:
            ensure_tile(rec, lib, d, "submit")
            made += 1
    for x in DL.items(rec):
        d = lib.doc(x.get("doc_id")) if x.get("doc_id") else None
        if d is not None and not [m for m in lib.returns_of(d) if m in CUSTOMER_MARKS]:
            lib.set_returns(d["id"], lib.returns_of(d) + [x.get("returns") if x.get("returns") in CUSTOMER_MARKS else "fill"])
            marked += 1
        o = lib.doc(x.get("our_doc")) if x.get("our_doc") and _kind(x) == "file" else None
        if o is not None and "submit" not in lib.returns_of(o):
            lib.set_returns(o["id"], lib.returns_of(o) + ["submit"])
            marked += 1
    return made, marked


def _let_go(rec, t, slot, who=None):
    """A deliverable made in Shred (or with work on it) keeps its row and only lets go of the file."""
    t[slot] = ""
    if slot == "doc_id":
        t.pop("returns", None) if not t.get("shred_kind") else None
    rec.log("deliverable", f"{t['name']}: no file yet (its file's purpose was taken off in Documents)", ref={"deliverable": t["id"]}, who=who)
    rec.save()


def drop_tile(rec, lib, doc_id, who=None, mark=None):
    """4.29.2 (Nicholas 2026-11-13 answer 4): the document's last mark of this kind came off, so the deliverable that mark
    made leaves Deliverables (it can be put back with Undo there). With a customer mark left, it stays and says that mark.
    4.83.0: a deliverable made in Shred stays and lets go of the file. Returns True when a deliverable left."""
    d = lib.doc(doc_id)
    left = lib.returns_of(d) if d is not None else []
    if mark == "submit":
        t = tile_of(rec, doc_id, "submit")
        if t is None or "submit" in left:
            return False
        if t.get("shred_kind") or t.get("from_shred"):
            _let_go(rec, t, "our_doc", who)
            return False
        return bool(DL.remove(rec, t["id"], who=who))
    t = tile_of(rec, doc_id, mark if mark in CUSTOMER_MARKS else None)
    if t is None or t.get("our_doc") == doc_id and t.get("doc_id") != doc_id:
        return False
    cust = [m for m in left if m in CUSTOMER_MARKS]
    if cust:
        if t.get("returns") not in cust and not t.get("shred_kind"):
            t["returns"] = cust[0]
            rec.save()
        return False
    if t.get("shred_kind") or t.get("from_shred"):
        _let_go(rec, t, "doc_id", who)
        return False
    return bool(DL.remove(rec, t["id"], who=who))


def unmark(lib, deliverable):
    """4.29.2: a deliverable deleted on Deliverables takes its document's purpose off (only the one it gave: 4.83.0).
    Returns the document's name, or ""."""
    if lib is None:
        return ""
    for slot, marks in (("doc_id", CUSTOMER_MARKS), ("our_doc", ("submit",))):
        d = lib.doc(deliverable.get(slot)) if deliverable.get(slot) else None
        if d is None or (slot == "our_doc" and _kind(deliverable) != "file"):
            continue
        have = lib.returns_of(d)
        if any(m in have for m in marks):
            lib.set_returns(d["id"], [m for m in have if m not in marks])
            return d.get("name", "")
    return ""
