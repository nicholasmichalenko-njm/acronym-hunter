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


# ------------------------------------------------------------------ 3.64.0 the Sort page
STARTER = ("Program Management", "Transition", "Staffing", "Cybersecurity", "Quality", "Reporting")
SORTABLE_SKIP = ("Heading", "Context")


def sortable(items):
    """The sentences that need a home on the Sort page: not headings, not context, not dropped."""
    return [it for it in items if it.get("type") not in SORTABLE_SKIP and it.get("header") != "Yes" and it.get("decision") != "Drop"
            and it.get("decision") != "Context"]


def unsorted(rec, items):
    tags = rec.data.get("topic_tags", {})
    return [it for it in sortable(items) if not tags.get(it.get("id"))]


def children(rec, tid):
    return [t for t in topics(rec) if t.get("parent") == tid]


def roots(rec):
    have = {t["id"] for t in topics(rec)}
    return [t for t in topics(rec) if not t.get("parent") or t["parent"] not in have]


def set_parent(rec, tid, parent):
    """Make a topic a subtopic of another ('' makes it a topic of its own again). One level only."""
    t, p = get(rec, tid), get(rec, parent) if parent else None
    if t is None or (parent and (p is None or parent == tid or p.get("parent"))) or children(rec, tid) and parent:
        return False
    t["parent"] = parent or ""
    rec.save()
    return True


def primary(rec, sid):
    """The sentence's home topic (the first it carries), or None."""
    ids = rec.data.get("topic_tags", {}).get(sid) or []
    return next((t for t in topics(rec) if ids and t["id"] == ids[0]), None)


def file_under(rec, sids, tid, keep_others=True):
    """Make tid the home topic of the sentences (first in their list); with keep_others the other topics stay as
    cross-references, else they are taken off."""
    if get(rec, tid) is None or not sids:
        return 0
    tags = rec.data.setdefault("topic_tags", {})
    for s in sids:
        rest = [x for x in (tags.get(s) or []) if x != tid] if keep_others else []
        tags[s] = [tid] + rest
    rec.save()
    return len(sids)


def merge(rec, keep, gone):
    """gone's sentences and subtopics move to keep; gone's name becomes one of keep's other names. Returns True."""
    k, g = get(rec, keep), get(rec, gone)
    if k is None or g is None or keep == gone:
        return False
    tags = rec.data.setdefault("topic_tags", {})
    for sid, ids in tags.items():
        if gone in ids:
            new = []
            for x in ids:
                x = keep if x == gone else x
                if x not in new:
                    new.append(x)
            tags[sid] = new
    for c in children(rec, gone):
        c["parent"] = keep if not k.get("parent") else k["parent"]
    k.setdefault("aliases", [])
    if g["name"] not in k["aliases"]:
        k["aliases"].append(g["name"])
    k["sections"] = list(dict.fromkeys((k.get("sections") or []) + (g.get("sections") or [])))
    rec.data["topics"] = [t for t in rec.data.get("topics", []) if t.get("id") != gone]
    rec.log("effort", f"Topic {g['name']} merged into {k['name']}")
    rec.save()
    return True


def find(rec, name):
    """A topic by its name or one of its other names (case does not matter)."""
    n = _clean(name).casefold()
    return next((t for t in topics(rec) if t["name"].casefold() == n or n in [a.casefold() for a in t.get("aliases") or []]), None)


def add_starter(rec, names=STARTER):
    out = [add(rec, n, save=False) for n in names]
    rec.save()
    return [x for x in out if x]


def from_factors(rec):
    """A topic for each evaluation factor (Evaluation Criteria), subfactors under their factor. Returns the ids."""
    import custfocus as F
    made, by = [], {}
    for f in F.factors(rec):
        tid = add(rec, f["name"], save=False)
        by[f["id"]] = tid
        if f.get("parent") and by.get(f["parent"]):
            t = get(rec, tid)
            if t is not None and not children(rec, tid):
                t["parent"] = by[f["parent"]]
        made.append(tid)
    rec.save()
    return made


def carry_split(rec, old_id, new_ids):
    """A sentence split into parts: each part keeps the old sentence's topics."""
    tags = rec.data.setdefault("topic_tags", {})
    ids = tags.pop(old_id, None)
    if ids:
        for n in new_ids:
            tags[n] = list(ids)
        rec.save()
    return bool(ids)


def overview(rec, items):
    """[{id, name, total, by_strength {Mandatory, Desired, Optional, other}, by_type {Instruction, Evaluation, SOW, other}}]
    for each topic of its own (its subtopics counted in), then Unsorted."""
    by = {it.get("id"): it for it in sortable(items)}
    tags = rec.data.get("topic_tags", {})
    out = []

    def count(sids):
        rows = [by[s] for s in sids if s in by]
        st, ty = {"Mandatory": 0, "Desired": 0, "Optional": 0, "other": 0}, {"Instruction": 0, "Evaluation": 0, "SOW": 0, "other": 0}
        for it in rows:
            st[it.get("strength") if it.get("strength") in st else "other"] += 1
            ty[it.get("type") if it.get("type") in ty else "other"] += 1
        return len(rows), st, ty
    for t in roots(rec):
        ids = {t["id"]} | {c["id"] for c in children(rec, t["id"])}
        sids = [s for s, xs in tags.items() if xs and xs[0] in ids]
        n, st, ty = count(sids)
        out.append({"id": t["id"], "name": t["name"], "total": n, "by_strength": st, "by_type": ty})
    n, st, ty = count([it["id"] for it in unsorted(rec, items)])
    out.append({"id": "", "name": "Unsorted", "total": n, "by_strength": st, "by_type": ty})
    return out


def read_back(rec, items, path):
    """A matrix workbook edited in Excel: its ID and Topic columns file each sentence (topics separated by ';', the first
    its home; a new name becomes a topic). Returns {"rows", "filed", "new_topics", "unknown_ids"}."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    have = {it.get("id") for it in items}
    out = {"rows": 0, "filed": 0, "new_topics": 0, "unknown_ids": 0}
    tags = rec.data.setdefault("topic_tags", {})
    for ws in wb.worksheets:
        rows = ws.iter_rows(values_only=True)
        head = None
        for r in rows:
            cells = [str(c).strip() if c is not None else "" for c in r]
            if head is None:
                low = [c.casefold() for c in cells]
                if "id" in low and ("topic" in low or "topics" in low):
                    head = (low.index("id"), low.index("topic") if "topic" in low else low.index("topics"))
                continue
            sid, cell = cells[head[0]] if head[0] < len(cells) else "", cells[head[1]] if head[1] < len(cells) else ""
            if not sid:
                continue
            out["rows"] += 1
            if sid not in have:
                out["unknown_ids"] += 1
                continue
            names = [n.strip() for n in cell.split(";") if n.strip()]
            if not names:
                continue
            ids = []
            for n in names:
                t = find(rec, n)
                if t is None:
                    tid = add(rec, n, save=False); out["new_topics"] += 1
                else:
                    tid = t["id"]
                if tid not in ids:
                    ids.append(tid)
            tags[sid] = ids
            out["filed"] += 1
        if head is not None:
            break
    wb.close()
    rec.log("effort", f"Topics read back from a matrix workbook: {out['filed']} sentence(s)")
    rec.save()
    return out


# ------------------------------------------------------------------ 3.65.0 Sort II: structure, fit and suggestions
FIT = ("", "Strong", "Partial", "Gap")


def set_fit(rec, tid, fit):
    t = get(rec, tid)
    if t is None or fit not in FIT:
        return False
    t["fit"] = fit
    rec.save()
    return True


def set_keywords(rec, tid, words):
    """The words that point at a topic (a list, or text with commas between them)."""
    t = get(rec, tid)
    if t is None:
        return False
    if isinstance(words, str):
        words = words.split(",")
    t["keywords"] = [w for w in dict.fromkeys(_clean(x, 60) for x in words) if w]
    rec.save()
    return True


_STOP = {"the", "and", "for", "with", "management", "support", "services", "plan", "system", "systems"}


def _words(t):
    """A topic's pointing words: its keywords, then the longer words of its name and other names."""
    out = list(t.get("keywords") or [])
    for n in [t["name"]] + list(t.get("aliases") or []):
        out += [w for w in re.findall(r"[A-Za-z][A-Za-z-]{3,}", n) if w.casefold() not in _STOP]
    return [w for w in dict.fromkeys(out) if w]


def suggest(rec, items):
    """{sentence id: (topic id, reason)} for each unsorted sentence whose words point at one topic more than any other.
    Keywords count twice a name word. Never files anything: the person takes a suggestion."""
    ts = [(t, _words(t)) for t in topics(rec)]
    out = {}
    for it in unsorted(rec, items):
        low = " " + " ".join(str(it.get("text") or "").split()).casefold() + " "
        best, why, second = None, [], 0
        for t, ws in ts:
            hit = [w for w in ws if re.search(r"(?<![a-z0-9])" + re.escape(w.casefold()) + r"(?![a-z0-9])", low)]
            score = sum(2 if w in (t.get("keywords") or []) else 1 for w in hit)
            if score > (best[1] if best else 0):
                second = best[1] if best else 0
                best, why = (t, score), hit
            elif best and score == best[1]:
                second = score
        if best and best[1] > second:
            out[it["id"]] = (best[0]["id"], "matched: " + ", ".join(why[:4]))
    return out


def structure_rows(rec, items, labels=()):
    """[{id, name, parent, sections, home, kept, placed, fit}] for every topic: its requirements (home), how many are
    kept, how many kept ones are in a section, and the sections it fills."""
    tags = rec.data.get("topic_tags", {})
    by = {it.get("id"): it for it in sortable(items)}
    have = set(labels)
    out = []
    for t in roots(rec):
        for x in [t] + children(rec, t["id"]):
            sids = [s for s, xs in tags.items() if xs and xs[0] == x["id"] and s in by]
            kept = [by[s] for s in sids if by[s].get("decision") == "Keep"]
            out.append({"id": x["id"], "name": x["name"], "parent": x.get("parent", ""), "fit": x.get("fit", ""),
                        "sections": [s for s in (x.get("sections") or []) if not have or s in have],
                        "home": len(sids), "kept": len(kept), "placed": sum(1 for it in kept if it.get("map"))})
    return out


def gaps(rec, items, labels=()):
    """What the structure still misses: topics with requirements and no section, kept requirements with a topic and no
    section, sections no topic fills."""
    rows = structure_rows(rec, items, labels)
    filled = {s for r in rows for s in r["sections"]}
    return {"no_section": [r["name"] for r in rows if r["home"] and not r["sections"]],
            "unplaced": sum(r["kept"] - r["placed"] for r in rows),
            "empty_sections": [l for l in labels if l not in filled]}


def map_section(rec, tid, label, add=True):
    """The topic fills the section (first section first); add=False makes it the only one."""
    t = get(rec, tid)
    if t is None or not label:
        return False
    cur = list(t.get("sections") or [])
    t["sections"] = (cur if label in cur else cur + [label]) if add else [label]
    rec.save()
    return True


def make_subsections(rec, M, tids, parent=""):
    """A section for each topic named, under parent (a volume or a section), its subtopics as subsections under it;
    each topic then fills its section. Returns {topic id: section label}."""
    import outline_ops as O
    made = {}
    for tid in tids:
        t = get(rec, tid)
        if t is None:
            continue
        lab = O.add(M, t["name"], parent=parent) if parent else O.add(M, t["name"])
        t["sections"] = [lab] + [s for s in (t.get("sections") or []) if s != lab]
        made[tid] = lab
        for c in children(rec, tid):
            if c["id"] in tids:
                continue
            cl = O.add(M, c["name"], parent=lab)
            c["sections"] = [cl] + [s for s in (c.get("sections") or []) if s != cl]
            made[c["id"]] = cl
    rec.log("effort", f"Sections from topics: {len(made)}")
    rec.save()
    return made


def to_place(rec, items):
    """{section label: [kept sentences with no section]} by their home topic's first section."""
    tags = rec.data.get("topic_tags", {})
    secs = {t["id"]: (t.get("sections") or [""])[0] for t in topics(rec)}
    out = {}
    for it in sortable(items):
        xs = tags.get(it["id"]) or []
        if it.get("decision") == "Keep" and not it.get("map") and xs and secs.get(xs[0]):
            out.setdefault(secs[xs[0]], []).append(it)
    return out
