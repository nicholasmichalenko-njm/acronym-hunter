"""Shred in passes, the Deliverables pass (4.76.0; UX decisions 164, 175, 176; the hand-off "a deliverable marked in the
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


def mark(rec, it, key, name="", who=None):
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
    DL.attach_piece(rec, did, piece_of(it), who=who)
    rec.save()
    return did, "added"


def unmark(rec, it, who=None):
    """Take the mark off: the piece leaves its deliverable; a deliverable this mark made, with nothing else on it, goes
    (it can be brought back on the Deliverables page). Returns "removed", "detached" or ""."""
    d = of_piece(rec, it)
    if d is None:
        return ""
    DL.detach(rec, it.get("id", ""), who=who)
    if d.get("from_shred") == it.get("id") and not d.get("pieces") and not d.get("doc_id") and not d.get("file"):
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
    return [it for it in M.items if it.get("file") == file and it.get("type") != "Heading" and it.get("id") not in got
            and it.get("id") not in on and reads_like(it)]


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
