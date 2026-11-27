"""The Documents door (4.83.0; step D3 of claude/stationkeeper-deliverables-that-act-and-the-documents-door-direction-2026-11-25.md;
UX decisions 176, 183, 215, 216). A file given the purpose Form to fill in, File to submit or Redline to return, on
Documents > Add or later on Documents, says which deliverable it is: the one the app suggests (its name matches the
file's), another from the list, or a new one. The file still lives once, in Documents; the deliverable points at it
(docreturn, delivnext). Rules only (No AI); nothing leaves the PC. Standard library only."""
import difflib, os, re

import deliverables as DL
import docreturn as DR

DOOR_MARKS = ("fill", "submit", "redline")          # the purposes that ask which deliverable
NEW = "new"
_SMALL = {"the", "a", "an", "of", "and", "for", "to"}


def _norm(s):
    s = os.path.splitext(s or "")[0] if re.search(r"\.[a-z0-9]{2,4}$", s or "", re.I) else (s or "")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s.lower()).split())


def alike(a, b):
    """How alike two names are, 0 to 1: the outline marking's rule (0.8 when one name's words are all inside the other's,
    two words or more), as delivnext.suggest uses it the other way round."""
    x, y = _norm(a), _norm(b)
    if not x or not y:
        return 0.0
    r = difflib.SequenceMatcher(None, x, y).ratio()
    wx, wy = set(x.split()) - _SMALL, set(y.split()) - _SMALL
    if min(len(wx), len(wy)) >= 2 and (wx <= wy or wy <= wx):
        r = max(r, 0.8)
    return r


def fits(x, mark):
    """The deliverable is of the kind this purpose feeds (a Form We Fill In for Form to fill in, and so on)."""
    import delivnext as DN
    return DN.kind_key(x) == DR.KIND_OF.get(mark)


def options(rec, mark):
    """[(deliverable id, words)] of the kind this purpose feeds, the ones still without a file first."""
    if rec is None or mark not in DOOR_MARKS:
        return []
    slot = DR.slot_of(mark)
    rows = [x for x in DL.items(rec) if fits(x, mark)]
    rows.sort(key=lambda x: (bool(x.get(slot)), x.get("name", "").casefold()))
    return [(x["id"], x.get("name", "") + ("  (has a file)" if x.get(slot) else "")) for x in rows]


def suggest(rec, name, mark, names=()):
    """The deliverable this file most likely is: of the kind the purpose feeds, its name alike at 0.6 or more to the
    file's name (or its file name), one still without a file before one that has it. "" when none is that alike."""
    if rec is None or mark not in DOOR_MARKS:
        return ""
    slot = DR.slot_of(mark)
    best = (0.0, True, "")
    for x in DL.items(rec):
        if not fits(x, mark):
            continue
        r = max([alike(x.get("name", ""), n) for n in (name, *names) if n] or [0.0])
        key = (r, not x.get(slot))
        if r >= 0.6 and key > (best[0], not best[1]):
            best = (r, bool(x.get(slot)), x["id"])
    return best[2]


def default(rec, name, mark, names=()):
    """The Deliverable field's starting choice: the suggestion, else New."""
    return suggest(rec, name, mark, names) or NEW


def link(rec, lib, doc_id, mark, did=NEW, who=None):
    """Give the document the purpose (if it lacks it) and point the deliverable at it: did, or a new one when did is New
    or empty. Returns (deliverable, made new)."""
    d = lib.doc(doc_id) if lib is not None and doc_id else None
    if d is None or mark not in DOOR_MARKS:
        return None, False
    have = lib.returns_of(d)
    if mark not in have:
        lib.set_returns(doc_id, have + [mark])
        d = lib.doc(doc_id)
    return DR.ensure_tile(rec, lib, d, mark, who=who, did=did if did and did != NEW else None)
