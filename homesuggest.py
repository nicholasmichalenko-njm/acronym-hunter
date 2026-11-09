"""Where a customer sentence goes (3.85.0, claude/stationkeeper-review-and-structure-2026-11-08.md): its home in our
response structure, suggested with the reason, and the offer that maps a whole customer heading after one placement.

home(M, it, rec=None) -> {"label", "why", "kind"} or None. In order (3.87.1: first, support goes where the requirement it
supports was placed):
    1 the customer heading's map ("L.3.5 is answered by 2.1")
    2 a parent heading's map (L.3 for L.3.5.2)
    3 a reference the sentence makes ("see L.3.7"), when that heading is mapped
    4 a section of ours with the heading's title
    5 the Sort topic's section
offer(M, it, label) -> {"num", "title", "label", "rest": [ids]} or None: after a placement, the other sentences under the
    same customer heading that could follow it (not a sentence that names another section, not a format rule for the whole
    volume, not one already placed). take_offer(M, offer, how): "place" (map and place them), "map" (map only: the rest
    are suggested), "once" (just this one: the app does not ask again for that heading).
map_heading(M, num, label) / heading_of(it) / coverage(M) / crossref_rows(M) / left(M)
Remapping changes only suggestions: placed sentences stay where they are. Rules only; nothing leaves the PC."""
import re

import rfpoutline as RO
import setupdoc as SD

_REF = re.compile(r"\b(?:(?:Section|Sect\.|para(?:graph)?\.?|see)\s+([A-Z]?\.?\d+(?:\.\d+)*)|([A-Z]\.\d+(?:\.\d+)*))\b", re.I)


def _refs(text):
    return [(a or b).strip(".") for a, b in _REF.findall(text or "")]
_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"the", "and", "of", "a", "an", "to", "for", "in", "on", "with", "by"}
REQ = {"Keep"}                                   # what a placed requirement's decision reads as


def _S(M):
    S = SD.setup_of(M)
    S.setdefault("rfp_map", {})
    S.setdefault("map_declined", [])
    return S


def heading_of(it):
    return (it.get("section") or "").strip(), (it.get("section_title") or "").strip()


def _parents(num):
    parts = num.split(".")
    for k in range(len(parts) - 1, 0, -1):
        yield ".".join(parts[:k])


def _words(t):
    return {w for w in _WORD.findall((t or "").lower()) if w not in _STOP}


def _title_of(label):
    return re.sub(r"^\s*[A-Z]?\d+(?:\.\d+)*\.?\s+", "", label or "")


def home(M, it, rec=None):
    S = _S(M)
    labels = set(_labels(M))
    num, title = heading_of(it)
    m = S["rfp_map"]
    if it.get("decision") == "Context" and it.get("context_for"):       # 3.87.1: support follows its requirement
        import compliance as C
        by = {x["id"]: x for x in M.items}
        for rid in C.cf_ids(it.get("context_for", "")):
            req = by.get(rid)
            if req is not None and req.get("map") in labels:
                return {"label": req["map"], "why": f"It supports {req.get('ref') or rid}, placed in {req['map']}", "kind": "support"}
    if num and m.get(num) in labels:
        return {"label": m[num], "why": f"{num} is answered by {m[num]}", "kind": "map"}
    for p in _parents(num) if num else ():
        if m.get(p) in labels:
            return {"label": m[p], "why": f"{p}, above {num}, is answered by {m[p]}", "kind": "parent"}
    for ref in _refs(it.get("text")):
        if ref != num and m.get(ref) in labels:
            return {"label": m[ref], "why": f"It names {ref}, which is answered by {m[ref]}", "kind": "ref"}
    if title:
        want = _words(title)
        best, score = None, 0.0
        for lab in labels:
            have = _words(_title_of(lab))
            if want and have:
                s = len(want & have) / len(want | have)
                if s > score:
                    best, score = lab, s
        if best and score >= 0.6:
            return {"label": best, "why": f"Its heading, {title}, matches the section {best}", "kind": "title"}
    if rec is not None:
        try:
            import topics as TP
            sec = TP.section_for(rec, it.get("id", ""))
            if sec in labels:
                return {"label": sec, "why": f"Its Sort topic goes to {sec}", "kind": "topic"}
        except Exception:  # noqa: BLE001
            pass
    return None


def _labels(M):
    try:
        import outline_ops as O
        return O.labels(M)
    except Exception:  # noqa: BLE001
        return []


def _own_reason(it, num):
    """A sentence that points to another section, or a rule for the whole volume, keeps its own home."""
    refs = _refs(it.get("text"))
    if any(r and r != num for r in refs):
        return True
    t = (it.get("text") or "").lower()
    return bool(re.search(r"\b(font|margin|page limit|pages? shall not exceed|point|single[- ]spaced|line spacing)\b", t))


def offer(M, it, label):
    num, title = heading_of(it)
    S = _S(M)
    if not num or not label or S["rfp_map"].get(num) or num in S["map_declined"]:
        return None
    rest = [x["id"] for x in M.items if x is not it and heading_of(x)[0] == num and x.get("file") == it.get("file")
            and x.get("type") != "Heading" and not x.get("map") and x.get("decision") in ("", None, "Keep")
            and not _own_reason(x, num)]
    return {"num": num, "title": title, "label": label, "rest": rest}


def map_heading(M, num, label):
    RO.map_section(M, num, label)
    S = _S(M)
    if label and num in S["map_declined"]:
        S["map_declined"].remove(num)


def take_offer(M, off, how, place=None):
    """how: "place" maps the heading and places the rest (place(ids, label) does the placing, so Review's own steps and
    undo apply); "map" maps it only; "once" leaves it unmapped and stops asking. Returns how many were placed."""
    if not off:
        return 0
    if how in ("place", "map"):
        map_heading(M, off["num"], off["label"])
    if how == "place" and place is not None and off["rest"]:
        return place(off["rest"], off["label"]) or 0
    if how == "once":
        S = _S(M)
        if off["num"] not in S["map_declined"]:
            S["map_declined"].append(off["num"])
        M.pending = True
    return 0


def coverage(M):
    """Every customer heading with sentences that are requirements: answered (mapped, or a requirement placed) or not.
    [{"num", "title", "file", "answered", "to": [labels]}]."""
    out, by = [], {}
    for it in M.items:
        num, title = heading_of(it)
        if not num or it.get("type") == "Heading":
            continue
        k = (it.get("file", ""), num)
        e = by.setdefault(k, {"num": num, "title": title, "file": k[0], "to": set(), "reqs": 0})
        if it.get("decision") in REQ:
            e["reqs"] += 1
            if it.get("map"):
                e["to"].add(it["map"])
    m = _S(M)["rfp_map"]
    for e in by.values():
        if m.get(e["num"]):
            e["to"].add(m[e["num"]])
        if e["reqs"] or m.get(e["num"]):
            out.append({"num": e["num"], "title": e["title"], "file": e["file"], "answered": bool(e["to"]), "to": sorted(e["to"])})
    return out


def crossref_rows(M):
    """The cross-reference table: customer heading, its title, where we answer it."""
    return [(c["num"], c["title"], "; ".join(c["to"]) or "Not answered yet") for c in coverage(M)]


def left(M):
    """What Review still has: sentences not decided, and requirements decided but placed nowhere."""
    undecided = [it["id"] for it in M.items if it.get("type") != "Heading" and not it.get("decision")]
    unplaced = [it["id"] for it in M.items if it.get("decision") in REQ and not it.get("map")]
    return {"undecided": undecided, "unplaced": unplaced}
