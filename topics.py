"""Topics (3.28.0): the sorting layer of Review. A topic answers "what is this about" (a decision answers "what must we
do"); a sentence can carry several topics and keeps its one decision. Topics come from you, the kickoff, the RFP's
own headings or the library documents' tags. A topic maps to one or more response sections: when a sentence that
carries it becomes a requirement with no section yet, it goes to the topic's first section.

Kept in the effort record (record.json: "topics" and "topic_tags" {sentence id: [topic ids]}). Sort mode puts the
first nine topics on keys 1 to 9. An RFI effort opens in Sort mode, and Customer interest stands in for L and M.
Rules only (No AI); nothing leaves the PC."""
import datetime, getpass, re, uuid

COLORS = ("#4338CA", "#0E7490", "#B45309", "#BE185D", "#15803D", "#1D4ED8", "#9F1239", "#4D7C0F", "#6D28D9", "#C2410C")
# 3.28.0: what an RFI says when it names what the Government wants to learn (Suggest, RFI efforts)
RFI_PHRASES = ("the government is interested in", "the government is seeking", "the government seeks", "respondents should describe",
               "respondents should provide", "respondents are encouraged", "please describe", "please provide", "describe your",
               "capability to", "capabilities to", "interested parties should", "responses should address", "the government requests")


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _clean(t, n=80):
    return " ".join(str(t or "").split())[:n]


def topics(rec):
    return [t for t in rec.data.get("topics", []) if isinstance(t, dict) and t.get("id") and t.get("name")]


def get(rec, tid):
    return next((t for t in topics(rec) if t["id"] == tid), None)


def add(rec, name, color="", sections=(), about="", who=None, save=True):
    """A topic of this effort. Returns its id; a name already there returns that topic's id."""
    name = _clean(name)
    if not name:
        return None
    hit = next((t for t in topics(rec) if t["name"].casefold() == name.casefold()), None)
    if hit:
        return hit["id"]
    used = {t.get("color") for t in topics(rec)}
    color = color or next((c for c in COLORS if c not in used), COLORS[len(used) % len(COLORS)])
    t = {"id": uuid.uuid4().hex[:8], "name": name, "color": color, "sections": [s for s in sections if s], "about": _clean(about, 300),
         "at": _now(), "by": who or getpass.getuser()}
    rec.data.setdefault("topics", []).append(t)
    if save:
        rec.log("effort", f"Topic added: {name}", who=who)
        rec.save()
    return t["id"]


def update(rec, tid, **f):
    t = get(rec, tid)
    if t is None:
        return False
    if "name" in f and _clean(f["name"]):
        t["name"] = _clean(f["name"])
    if "color" in f and f["color"]:
        t["color"] = f["color"]
    if "sections" in f:
        t["sections"] = [s for s in (f["sections"] or []) if s]
    if "about" in f:
        t["about"] = _clean(f["about"], 300)
    rec.save()
    return True


def move(rec, tid, step):
    lst = rec.data.get("topics", [])
    i = next((n for n, t in enumerate(lst) if t.get("id") == tid), None)
    if i is None or not (0 <= i + step < len(lst)):
        return False
    lst[i], lst[i + step] = lst[i + step], lst[i]
    rec.save()
    return True


def remove(rec, tid):
    rec.data["topics"] = [t for t in rec.data.get("topics", []) if t.get("id") != tid]
    tags = rec.data.get("topic_tags", {})
    for sid in list(tags):
        tags[sid] = [x for x in tags[sid] if x != tid]
        if not tags[sid]:
            del tags[sid]
    rec.save()
    return True


# ------------------------------------------------------------------ sentences and their topics
def of(rec, sid):
    ids = rec.data.get("topic_tags", {}).get(sid) or []
    return [t for t in topics(rec) if t["id"] in ids]


def sids_of(rec, tid):
    return [sid for sid, ids in rec.data.get("topic_tags", {}).items() if tid in ids]


def tag(rec, sids, tid, on=None):
    """The topic on the sentences (on=None: on for all unless every one has it, then off). Returns True when on."""
    if get(rec, tid) is None or not sids:
        return None
    tags = rec.data.setdefault("topic_tags", {})
    if on is None:
        on = not all(tid in (tags.get(s) or []) for s in sids)
    for s in sids:
        cur = [x for x in (tags.get(s) or []) if x != tid]
        if on:
            cur.append(tid)
        if cur:
            tags[s] = cur
        else:
            tags.pop(s, None)
    rec.save()
    return on


def untag(rec, sids):
    tags = rec.data.setdefault("topic_tags", {})
    for s in sids:
        tags.pop(s, None)
    rec.save()


# ------------------------------------------------------------------ where topics come from
def from_headings(rec, items, max_level=2):
    """A topic for each RFP heading (sentences the reader marked as headings), numbering taken off; the sentences under
    each heading carry its topic. items: the review's items in reading order. Returns the topic ids made or found."""
    made, cur = [], None
    tags = rec.data.setdefault("topic_tags", {})
    for it in items:
        if it.get("type") == "Heading":
            txt = it.get("section_title") or re.sub(r"^\s*(?:section\s+)?[A-Z]?[\d.]*[\d)]?\s*[-:.)]?\s*", "",
                                                    str(it.get("text") or ""), flags=re.I)
            lvl = str(it.get("section") or "").strip(".").count(".") + 1
            if not txt.strip() or lvl > max_level:
                continue
            cur = add(rec, txt, save=False)
            if cur not in made:
                made.append(cur)
            continue
        if cur and it.get("id"):
            lst = tags.setdefault(it["id"], [])
            if cur not in lst:
                lst.append(cur)
    if made:
        rec.log("effort", f"Topics from the RFP's headings: {len(made)}")
    rec.save()
    return made


def from_tags(rec, tag_names):
    """A topic for each library tag (the tags of the effort's documents). Returns the topic ids."""
    out = [add(rec, n, save=False) for n in tag_names if _clean(n)]
    rec.save()
    return [x for x in out if x]


# ------------------------------------------------------------------ coverage and the response structure
def coverage(rec, items, section_of=None):
    """{topic id: {"sentences", "decided", "open", "in_section"}}; section_of(item) gives a requirement's section."""
    by = {it.get("id"): it for it in items}
    out = {}
    for t in topics(rec):
        s = [by[x] for x in sids_of(rec, t["id"]) if x in by]
        decided = [it for it in s if it.get("decision")]
        ins = [it for it in s if it.get("decision") == "Keep" and (section_of(it) if section_of else it.get("map"))]
        out[t["id"]] = {"sentences": len(s), "decided": len(decided), "open": len(s) - len(decided), "in_section": len(ins)}
    return out


def section_for(rec, sid):
    """The first section of the first topic the sentence carries that maps to one, else ""."""
    for t in of(rec, sid):
        if t.get("sections"):
            return t["sections"][0]
    return ""


def interest(text):
    """3.28.0: an RFI sentence naming what the Government wants to learn: the phrase found, else ""."""
    low = " ".join(str(text or "").split()).casefold()
    return next((p for p in RFI_PHRASES if p in low), "")


def is_rfi(ws):
    """An RFI effort: its effort type is RFI response (Production Standards, set when the effort starts)."""
    try:
        eff = (ws.get("prod_std", {}) or {}) if ws is not None else {}
    except Exception:  # noqa: BLE001
        return False
    return (eff.get("effort_type") or "") == "rfi"
