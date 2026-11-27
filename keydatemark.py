"""Shred in passes, the Submission Formatting Requirements pass: Key Date (4.82.0; step K1 of
claude/stationkeeper-key-dates-and-the-submission-formatting-pass-direction-2026-11-25.md; UX decisions 164, 169, 211).
A key date marked on the customer's words asks one thing, its kind, with the app's reading as the suggestion. Seven
kinds: Proposal due; Questions due; Answers expected; Intent to bid due; Site visit or industry day; Oral
presentations; Other (named, and offered again in that effort). The date, the time and the time zone are read from the
words (captures.key_date_guess); a date it cannot read is typed.

Where a key date goes, at once:
- Proposal due and Questions due are Customer information facts (one value, two places): the mark fills the fact
  (custinfo; Proposal due is also the effort's due date since 4.78.0). The calendar shows them from the fact.
- The other five are entries on the effort's calendar (effortcal), each keeping the piece it came from.
- Proposal due, Questions due, Answers expected and Intent to bid due have one date each: a different date from another
  piece (an amendment) asks once, Replace or keep, and the calendar shows the newer one and what it replaced.
- A key date makes no task.

What is the pass's own (Not needed, For the setup, a customer heading, a key date, a document that holds nothing of this
kind) is kept in the matrix's setup under "subm_marks", "subm_none" and "key_dates", as the other passes keep theirs.
Taking the mark off (the same key again) takes away a calendar entry the mark made and puts back the one it replaced;
a fact stays as it is (it is changed on Customer information). Rules only (No AI); nothing leaves the PC. Standard
library only."""
import re

import setupdoc as SD

KINDS = (("proposal", "Proposal due"), ("questions", "Questions due"), ("answers", "Answers expected"),
         ("intent", "Intent to bid due"), ("visit", "Site visit or industry day"), ("orals", "Oral presentations"),
         ("other", "Other"))
KEYS = tuple(k for k, _n in KINDS)
NAME = dict(KINDS)
FACT = {"proposal": "Proposal due", "questions": "Questions due"}        # Customer information facts
SINGLE = ("proposal", "questions", "answers", "intent")                  # one date each
CAL_KIND = {"answers": "Milestone", "intent": "Due", "visit": "Meeting", "orals": "Orals", "other": "Other"}
MARKS, NONE, DATES, OWN = "subm_marks", "subm_none", "key_dates", "key_date_names"
KEYDATE = "k"

_READ = ((r"\bquestions?\b.{0,40}\b(due|submitted|received|no later|deadline)", "questions"),
         (r"\banswers?\b|\bresponses? to (the |all )?questions\b", "answers"),
         (r"\bintent to (bid|propose|submit)\b|\bnotice of intent\b", "intent"),
         (r"\bsite (visit|survey)s?\b|\bindustry day\b|\bpre-?proposal conference\b|\bbidders'? conference\b", "visit"),
         (r"\boral (presentation|proposal)s?\b|\borals\b", "orals"),
         (r"\b(proposals?|offers?|responses?|quot(?:e|ation)s?|submissions?)\b.{0,60}\b(due|submitted|received|no later)", "proposal"))


def _clean(s, n=300):
    return " ".join(str(s or "").split())[:n]


def kind_read(text):
    """The kind the words read as, or "" (no suggestion)."""
    t = _clean(text, 2000)
    for pat, key in _READ:
        if re.search(pat, t, re.I):
            return key
    return ""


def when_of(text):
    """{"date", "start" ('' when no time is written), "zone"} read from the words, or None without a date."""
    import captures as CP
    g = CP.key_date_guess(text)
    return {"date": g["date"], "start": g["start"], "zone": g["zone"]} if g else None


def read(text):
    """What the bar shows before Enter: {"date", "start", "zone", "kind"} or None when no date is written."""
    w = when_of(text)
    if w is None:
        return None
    w["kind"] = kind_read(text)
    return w


def when_text(v):
    """'Mar 1, 2027, 2:00 p.m. ET', or 'Mar 1, 2027' with no time."""
    import datetime
    try:
        d = datetime.date.fromisoformat(v.get("date", ""))
    except ValueError:
        return v.get("date", "")
    out = f"{d.strftime('%b')} {d.day}, {d.year}"
    st = v.get("start") or ""
    if re.fullmatch(r"\d{2}:\d{2}", st):
        h, m = int(st[:2]), int(st[3:])
        out += f", {h % 12 or 12}:{m:02d} {'a.m.' if h < 12 else 'p.m.'}"
    if v.get("zone"):
        out += f" {v['zone']}"
    return out


def fact_value(v):
    """The value a fact gets: the effort's way of writing a due date (Proposal due needs a time: 5:00 p.m. when none)."""
    return when_text(v)


def setup(M):
    return SD.setup_of(M)


def marks(M):
    return setup(M).setdefault(MARKS, {})


def dates(M):
    return setup(M).setdefault(DATES, {})


def of_piece(M, it):
    """The key date a piece was marked as: {"kind", "name", "date", "start", "zone", "eid", "was"} or None."""
    return (setup(M).get(DATES) or {}).get(it.get("id"))


def older(M, it):
    """A piece typed Key Date before this pass (the Requirements tab's D): marked before, kind not said."""
    import shredtypes as ST
    return of_piece(M, it) is None and ST.has(it, "date")


def own_names(rec):
    """The names given to Other in this effort, offered again."""
    return list(rec.data.get(OWN) or [])


def add_own(rec, name):
    name = _clean(name, 80)
    if name and name.casefold() not in (n.casefold() for n in own_names(rec)):
        rec.data.setdefault(OWN, []).append(name)
    return name


def _event(rec, eid):
    return next((e for e in rec.data.get("events", []) or [] if e.get("id") == eid), None)


def earlier(rec, key, sid, name=""):
    """The calendar entry already holding a one-date kind from another piece (not itself replaced), or None."""
    if key not in SINGLE or key in FACT:
        return None
    for e in rec.data.get("events", []) or []:
        if e.get("key_kind") == key and e.get("key_sid") != sid and not e.get("replaced_by"):
            return e
    return None


def file_event(rec, M, it, key, v, name="", source=None, replace=None, who=None):
    """A key date of one of the five calendar kinds, onto the calendar. replace: the entry it takes the place of (an
    amendment). Returns the entry id, or "" when the date cannot be read."""
    import effortcal as EC
    src = source or {}
    title = _clean(name, 120) if key == "other" and name else NAME[key]
    where = ", ".join(x for x in (src.get("doc", ""), ("page " + str(src["page"])) if src.get("page") else "") if x)
    eid = EC.add_entry(rec, who=who, kind=CAL_KIND[key], date=v.get("date", ""), start=v.get("start", ""), zone=v.get("zone", ""),
                       title=title, details=(f"From {where}: " if where else "") + _clean(it.get("text"), 600))
    if not eid:
        return ""
    e = _event(rec, eid)
    e.update({"source": "shred", "key_kind": key, "key_sid": it.get("id", ""), "key_doc": src.get("doc", "") or it.get("file", ""),
              "key_page": str(src.get("page", "") or "")})
    if replace is not None:
        e["replaces"] = replace["id"]
        e["replaces_when"] = when_text(replace)
        replace["replaced_by"] = eid
    if key == "other" and name:
        add_own(rec, name)
    rec.save()
    return eid


def mark(M, it, key, v, name="", eid="", was=""):
    """Keep the pass's mark on the piece: its kind and when, and the entry it made (eid; "fact" for the two facts)."""
    dates(M)[it["id"]] = {"kind": key, "name": _clean(name, 120), "date": v.get("date", ""), "start": v.get("start", ""),
                          "zone": v.get("zone", ""), "eid": eid, "was": _clean(was, 120)}
    marks(M)[it["id"]] = KEYDATE
    M.pending = True
    return dates(M)[it["id"]]


def unmark(rec, M, it):
    """The same key again: the mark is off. A calendar entry it made goes, and one it replaced is back on the calendar.
    A fact stays (returns "fact" then, so the bar can say where it is changed)."""
    d = of_piece(M, it)
    if d is None:
        return None
    out = "off"
    if d.get("eid") == "fact":
        out = "fact"
    elif d.get("eid"):
        e = _event(rec, d["eid"])
        if e is not None:
            before = _event(rec, e.get("replaces", "")) if e.get("replaces") else None
            if before is not None:
                before.pop("replaced_by", None)
            rec.data["events"].remove(e)
            rec.log("effort", f"Calendar: removed {e['title']} ({e['date']}), its key date taken off in Shred")
            rec.save()
    dates(M).pop(it["id"], None)
    if marks(M).get(it["id"]) == KEYDATE:
        marks(M).pop(it["id"])
    M.pending = True
    return out


def reads_like(it):
    """A piece whose words hold a date: what the pass goes to next."""
    return when_of(it.get("text") or "") is not None


def open_rows(M, file):
    """The pieces of a document the pass would look at: they hold a date or were typed Key Date before, and were not
    marked or set aside here; headings out."""
    import shredtypes as ST
    got, kd = marks(M), setup(M).get(DATES) or {}
    return [it for it in M.items if it.get("file") == file and it.get("type") != "Heading" and it.get("id") not in got
            and it.get("id") not in kd and (ST.has(it, "date") or reads_like(it))]


def count(M):
    return len(setup(M).get(DATES) or {}) if M is not None else 0


def docs(M):
    """[{"file", "finds", "none", "state"}] for every customer document in this pass."""
    files, finds = [], {}
    kd = setup(M).get(DATES) or {}
    for it in M.items:
        f = it.get("file", "")
        if f and f not in files:
            files.append(f)
        if it.get("id") in kd:
            finds[f] = finds.get(f, 0) + 1
    none = set(setup(M).get(NONE) or [])
    out = []
    for f in files:
        n = finds.get(f, 0)
        out.append({"file": f, "finds": n, "none": f in none and not n,
                    "state": f"Has finds ({n})" if n else ("Nothing of this kind here" if f in none else "Not looked at")})
    return out


# ------------------------------------------------------------------ the calendar's side
def fact_when(text):
    """A fact's value read back as a date: {"date", "start", "zone"} or None."""
    return when_of(text)


def sources_on(rec, day):
    """The key dates on a day that came from a piece in Shred: [{"text", "sid", "file", "page"}], for the calendar's way
    back to the sentence. day: a date."""
    import custinfo as CI
    iso = day.isoformat()
    out = []
    for e in rec.data.get("events", []) or []:
        if e.get("key_sid") and e.get("date") == iso and not e.get("replaced_by"):
            out.append({"text": e.get("title", ""), "sid": e["key_sid"], "file": e.get("key_doc", ""), "page": e.get("key_page", "")})
    for label in FACT.values():
        f = CI.fact(rec, label)
        s = f.get("source") or {}
        if f.get("how") != "captured" or not s.get("sid"):
            continue
        w = fact_when(f.get("value", "")) if label != "Proposal due" else ({"date": (rec.data.get("due") or "")[:10]} if rec.data.get("due") else None)
        if w and w["date"] == iso:
            out.append({"text": label, "sid": s["sid"], "file": s.get("doc", ""), "page": str(s.get("page", "") or "")})
    return out


def questions_from_fact(rec):
    """(date, "questions", text) for the calendar from the Questions due fact, or None when it holds no date."""
    import custinfo as CI
    import datetime
    f = CI.fact(rec, "Questions due")
    w = fact_when(f.get("value", "")) if f.get("value") else None
    if not w:
        return None
    try:
        d = datetime.date.fromisoformat(w["date"])
    except ValueError:
        return None
    t = when_text(w).split(", ", 2)
    tail = t[2] if len(t) > 2 else ""
    was = f.get("was", "")
    text = (tail or "To the customer") + (f" (replaces {was})" if was else "")       # the kind's own word, Questions due, is beside it
    return (d, "questions", text)
