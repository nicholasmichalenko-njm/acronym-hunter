"""Shred in passes, the Deliverables pass (4.76.0, finished further in 4.77.0; UX decisions 164, 175, 176; the hand-off "a deliverable marked in the
Shred reaching the Deliverables list" of the Screen Map). Four kinds of thing the customer asks us to hand in: Document
We Write, Form We Fill In, File We Submit, Redline We Return. A mark adds a row to the effort's deliverables list at
once (the same list the Deliverables page shows), with the customer's words attached and a name suggested from them;
a piece already on a deliverable only changes that deliverable's kind. Taking the mark off detaches the piece, and
removes a deliverable the mark itself made when nothing else is on it.

What is the pass's own (Not needed, For the setup, a customer heading, a document that holds nothing of this kind) is
kept as the Compliance pass keeps its own, under "deliv_marks" and "deliv_none". Rules only (No AI); nothing leaves
the PC. Standard library only."""
import re

import deliverables as DL
import setupdoc as SD

KINDS = (("write", "Document We Write"), ("form", "Form We Fill In"), ("file", "File We Submit"), ("redline", "Redline We Return"))
KEYS = tuple(k for k, _n in KINDS)
NAME = dict(KINDS)
LIST_KIND = {"form": "Form", "file": "Attachment", "redline": "Customer file"}      # the Deliverables list's own kinds
MARKS, NONE = "deliv_marks", "deliv_none"
_LEAD = re.compile(r"^\s*(?:\(?[a-z0-9]{1,3}[.)]\s+)?(?:the\s+)?(?:offerors?|contractors?|vendors?|proposers?|respondents?|quoters?)\s+"
                   r"(?:shall|must|will|should|are to|is to)\s+(?:also\s+)?(?:submit|provide|complete(?: and (?:return|submit))?|"
                   r"return|include|furnish|deliver|fill (?:in|out)|sign(?: and return)?|prepare|attach)\s+", re.I)
_CUES = re.compile(r"\b(submit|complete and return|fill (?:in|out)|furnish|attach(?:ment)?|deliver(?:able)?s?|form|certif|redline|mark[- ]?up|"
                   r"questionnaire|template|spreadsheet|workbook|pricing|signed)\b", re.I)


def suggest_name(text):
    """A name for the deliverable from the customer's words: what follows "The Offeror shall submit", cut to a phrase."""
    t = " ".join((text or "").split())
    t = _LEAD.sub("", t)
    t = re.sub(r"^(?:an?|the|its|their|one|a copy of|a completed|a signed)\s+", "", t, flags=re.I)
    t = re.split(r"[.;:]|\s+(?:in accordance with|as described|no later than|by the|which|that|using|with its|with the)\s+", t)[0]
    words = t.strip(" ,-").split()[:9]
    name = " ".join(words)
    return (name[:1].upper() + name[1:]) if name else ""


def of_piece(rec, it):
    """The deliverable a piece sits on, or None."""
    return DL.of_piece(rec, it.get("id", ""))


def kind_of(rec, it):
    """The pass's kind a piece was marked with ("write", "form", "file", "redline"), or ""."""
    d = of_piece(rec, it)
    return (d or {}).get("shred_kind", "") if d else ""


def piece_of(it, file="", page="", loc=""):
    return {"sid": it.get("id", ""), "doc": file or it.get("file", ""), "page": str(page or it.get("page", "") or ""),
            "loc": loc or " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x), "text": it.get("text", "")}


def match(rec, name):
    """("same", deliverable), ("near", deliverable) or ("", None) for a name against the deliverables on the list
    (4.77.0). The same: alike but for capitals, spacing, punctuation and a number in front. Near: the rule the outline's
    marking uses (0.8 alike, or one name's words all inside the other's, two words or more)."""
    import difflib
    import structmark as SM
    n = SM.norm(name)
    if not n:
        return "", None
    best = (0.0, None)
    for d in DL.items(rec):
        c = SM.norm(d.get("name"))
        if not c:
            continue
        if c == n:
            return "same", d
        r = difflib.SequenceMatcher(None, n, c).ratio()
        a, b = set(n.split()), set(c.split())
        if min(len(a), len(b)) >= 2 and (a <= b or b <= a):
            r = max(r, SM.NEAR)
        if r > best[0]:
            best = (r, d)
    return ("near", best[1]) if best[0] >= SM.NEAR else ("", None)


def older(rec, it):
    """A piece marked Deliverable the older way (typed Deliverable on Requirements, or put on a deliverable there) with
    none of the four kinds said. The app never picks one for it."""
    import shredtypes as ST
    d = of_piece(rec, it)
    if d is not None:
        return not d.get("shred_kind")
    return ST.has(it, "deliverable")


def attach(rec, it, did, key="", who=None, ref=""):
    """Put a piece on a deliverable already on the list (4.77.0): no second row. The deliverable takes the kind only
    when it has none of the four yet. Returns "attached" or "same"."""
    d = DL.get(rec, did)
    if d is None:
        return ""
    cur = of_piece(rec, it)
    if cur is not None and cur["id"] == did:
        return "same"
    DL.attach_piece(rec, did, piece_of(it, loc=ref), who=who)
    if key in NAME and not d.get("shred_kind"):
        d["shred_kind"] = key
    if ref and not d.get("cust_ref"):
        d["cust_ref"] = ref
    rec.save()
    return "attached"


def mark_many(rec, rows, key, name="", who=None, to=None, refs=None):
    """Pieces marked together are one deliverable (4.77.0): the first makes it (or `to` names one already on the
    list), the rest are put on it. Returns (deliverable id, "added" or "attached")."""
    refs = refs or {}
    did, how = to, "attached"
    for it in rows:
        ref = refs.get(it.get("id"), "")
        if did is None:
            did, how = mark(rec, it, key, name, who=who, ref=ref)
        else:
            attach(rec, it, did, key, who=who, ref=ref)
    return did, how


def unmark_would_ask(rec, it):
    d = of_piece(rec, it)
    return bool(d is not None and d.get("from_shred") == it.get("id") and touched(d, it.get("id")))


def touched(d, sid=""):
    """Has anything been done to a deliverable beyond the mark that made it: an owner, a file, a note, a status, a
    part, or another piece."""
    return bool(d.get("owner") or d.get("file") or d.get("doc_id") or d.get("notes") or d.get("about") or d.get("parts")
                or (d.get("status") or "Not started") != "Not started" or any(p.get("sid") != sid for p in d.get("pieces", [])))


def mark(rec, it, key, name="", who=None, ref=""):
    """Mark a piece. Returns (deliverable id, "added" or "changed" or "same")."""
    if key not in NAME:
        raise ValueError(key)
    d = of_piece(rec, it)
    if d is not None:
        if d.get("shred_kind") == key:
            return d["id"], "same"
        d["shred_kind"] = key
        if key in LIST_KIND:
            d["kind"] = LIST_KIND[key]
        rec.log("deliverable", f"{d['name']}: {NAME[key]}", ref={"deliverable": d["id"]}, who=who)
        rec.save()
        return d["id"], "changed"
    name = " ".join((name or suggest_name(it.get("text", "")) or NAME[key]).split())[:120]
    did = DL.add(rec, name, kind=LIST_KIND.get(key, ""), req_key=it.get("id", ""), who=who)
    if did is None:
        return None, "same"
    d = DL.get(rec, did)
    d["shred_kind"] = key
    d["from_shred"] = it.get("id", "")
    if ref:
        d["cust_ref"] = ref                           # the customer's reference: the Customer heading above the piece
    DL.attach_piece(rec, did, piece_of(it, loc=ref), who=who)
    rec.save()
    return did, "added"


def unmark(rec, it, who=None, remove=None):
    """Take the mark off. The deliverable goes with it only when this mark made it and nothing has been done to it
    since (it can be brought back on the Deliverables page). When work has been done to one this mark made, the answer
    is "ask" and nothing changes until `remove` says: True removes it, False keeps it without this piece. A deliverable
    made elsewhere only loses the piece. Returns "removed", "detached", "ask" or ""."""
    d = of_piece(rec, it)
    if d is None:
        return ""
    mine = d.get("from_shred") == it.get("id")
    if mine and touched(d, it.get("id")) and remove is None:
        return "ask"
    DL.detach(rec, it.get("id", ""), who=who)
    if mine and (remove or (remove is None and not d.get("pieces"))):
        DL.remove(rec, d["id"], who=who)
        return "removed"
    return "detached"


def marks(M):
    return SD.setup_of(M).setdefault(MARKS, {})


def reads_like(it):
    """A piece whose words ask for something to be handed in: what the pass goes to next."""
    return bool(_CUES.search(it.get("text") or ""))


def open_rows(M, rec, file):
    """The pieces of a document the pass would look at: they read like a hand-in, sit on no deliverable, and were not
    set aside here; headings out."""
    got = marks(M)
    on = {p.get("sid") for d in DL.items(rec) for p in d.get("pieces", [])}
    import shredtypes as ST
    kinded = {p.get("sid") for d in DL.items(rec) if d.get("shred_kind") for p in d.get("pieces", [])}
    return [it for it in M.items if it.get("file") == file and it.get("type") != "Heading" and it.get("id") not in got
            and it.get("id") not in kinded and ((it.get("id") not in on and reads_like(it)) or it.get("id") in on or ST.has(it, "deliverable"))]


def count(rec):
    return sum(1 for d in DL.items(rec) if d.get("shred_kind"))


def docs(M, rec):
    """[{"file", "finds", "none", "state"}] for every customer document in this pass."""
    files = []
    for it in M.items:
        f = it.get("file", "")
        if f and f not in files:
            files.append(f)
    by_id = {it.get("id"): it.get("file", "") for it in M.items}
    finds = {}
    for d in DL.items(rec):
        if d.get("shred_kind"):
            for p in d.get("pieces", []):
                f = by_id.get(p.get("sid"), "")
                finds[f] = finds.get(f, 0) + 1
    none = set(SD.setup_of(M).get(NONE) or [])
    out = []
    for f in files:
        n = finds.get(f, 0)
        out.append({"file": f, "finds": n, "none": f in none and not n,
                    "state": f"Has finds ({n})" if n else ("Nothing of this kind here" if f in none else "Not looked at")})
    return out
