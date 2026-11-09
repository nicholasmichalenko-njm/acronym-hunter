"""Compare on the page (3.89.0, claude/stationkeeper-compare-on-the-page-plan-3.89.md): the rules behind the screen.

editorial(r)                   only punctuation, spacing, capitals or a heading's number changed
changed_words(r)               which words of the new sentence are new or changed (by position, as the page counts them)
suggest(r, links, M, tags, snap) -> {"kind", "target", "why"} or None: what the change most likely means. Suggest,
                               never decide: the screen shows it first, and a person takes it or picks another.
touches(rows, links, M, new_snap) -> {key: {"items": [ids], "how": "changed"|"removed"|"added", "heading": num}}: the placed
                               sentences each change touches (decision 6); an added sentence touches every sentence placed
                               from its customer heading.
flags(M, rv)                   {item id: [{"text", "pk", "key"}]}: placed sentences with a change still to decide, from every
                               comparison recorded; they keep their place.
place(pdf, rows)               {key: {"page", "rects", "words", "changed"}} on the new version's page copy; a removed sentence
                               is marked where it stood (just before the next sentence still there).
page_status(placed, rows, decided) -> {page: "todo" | "done"} for the strip.
Rules only (No AI); nothing leaves the PC."""
import difflib, re

_WORD = re.compile(r"[A-Za-z0-9]+")
_REQ = re.compile(r"\b(?:shall|must|will|is required to|are required to)\b", re.I)
_LEAD_NUM = re.compile(r"^\s*(?:[A-Z]\.)?\d+(?:\.\d+)*\.?\s+|^\s*[A-Z]\.\d+(?:\.\d+)*\.?\s+")


def _letters(s):
    return " ".join(w.lower() for w in _WORD.findall(s or ""))


def editorial(r):
    """True when a changed sentence keeps every word: punctuation, spacing or capitals only, or only a heading's number
    (renumbered). A number inside a sentence ("50 pages" to "40 pages") is never editorial."""
    if r.get("kind") != "changed":
        return False
    old, new = r.get("old") or "", r.get("new") or ""
    if _letters(old) == _letters(new):
        return True
    a, b = _LEAD_NUM.sub("", old, count=1), _LEAD_NUM.sub("", new, count=1)
    return a != old and b != new and _letters(a) == _letters(b) and len(_WORD.findall(a)) <= 14


def changed_words(r):
    """Indexes of the new sentence's words (as [A-Za-z0-9]+ runs, the page's own count) that are new or changed."""
    new = _WORD.findall(r.get("new") or "")
    if r.get("kind") == "added":
        return list(range(len(new)))
    if r.get("kind") != "changed":
        return []
    old = [w.lower() for w in _WORD.findall(r.get("old") or "")]
    out = []
    sm = difflib.SequenceMatcher(None, old, [w.lower() for w in new], autojunk=False)
    for op, _i1, _i2, j1, j2 in sm.get_opcodes():
        if op in ("replace", "insert"):
            out += list(range(j1, j2))
    return out


def heading(r, snap_new=None, snap_old=None):
    """(number, title) of the customer heading the change sits under."""
    src = None
    if r.get("nj") is not None and snap_new:
        src = snap_new[r["nj"]]
    elif r.get("oi") is not None and snap_old:
        src = snap_old[r["oi"]]
    if src:
        return (src.get("s") or "").strip(), (src.get("t") or "").strip()
    sec = (r.get("section") or "").strip()
    num = sec.split(" ", 1)[0] if sec and re.match(r"^[A-Z]?\.?\d|^[A-Z]\.", sec) else ""
    return num, sec[len(num):].strip()


def _placed(links):
    return [h for h in links or () if h.get("map")]


def suggest(r, links, M=None, tags=(), snap_new=None):
    kind = r.get("kind")
    if kind == "same":
        return None
    if editorial(r):
        return {"kind": "none", "target": "", "why": "Only punctuation, spacing, capitals or numbering changed"}
    placed = _placed(links)
    if kind == "changed" and links:
        h = placed[0] if placed else links[0]
        where = f" in {h['map']}" if h.get("map") else ""
        return {"kind": "updates", "target": h["id"], "why": f"{h['id']}{where} has the old wording"}
    if kind == "removed" and links:
        h = placed[0] if placed else links[0]
        where = f" is placed in {h['map']}" if h.get("map") else " is in the matrix"
        return {"kind": "removes", "target": h["id"], "why": f"{h['id']}{where}; the customer took the sentence out"}
    if "rule" in (tags or ()):
        return {"kind": "rule", "target": "", "why": "It changes a submission rule"}
    if kind == "added" and _REQ.search(r.get("new") or ""):
        num, title = heading(r, snap_new)
        label = ""
        if M is not None and num:
            import homesuggest as HS
            h = HS.home(M, {"section": num, "section_title": title, "text": r.get("new", ""), "decision": ""})
            label = h["label"] if h else ""
        if label:
            return {"kind": "new", "target": label, "why": f"A new requirement under {num}; {num} is answered by {label}"}
        return {"kind": "new", "target": "", "why": "A new requirement" + (f" under {num}" if num else "") + ": pick its section on the right"}
    return None


def touches(rows, links, M=None, snap_new=None):
    out = {}
    by_head = {}
    if M is not None:
        import homesuggest as HS
        for it in M.items:
            if it.get("map"):
                by_head.setdefault(HS.heading_of(it)[0], []).append(it["id"])
    for i, r in enumerate(rows):
        if r.get("kind") == "same" or editorial(r):
            continue
        ids = [h["id"] for h in _placed(links[i] if i < len(links) else [])]
        num = heading(r, snap_new)[0]
        if ids:
            out[r["key"]] = {"items": ids, "how": r["kind"], "heading": num}
        elif r["kind"] == "added" and num and by_head.get(num):
            out[r["key"]] = {"items": list(by_head[num]), "how": "added", "heading": num}
    return out


def flag_text(t, label):
    if t["how"] == "removed":
        return f"Removed in {label}"
    if t["how"] == "added":
        return f"{label} added text under {t['heading']}" if t.get("heading") else f"{label} added text here"
    return f"Changed in {label}"


def flags(M, rv):
    """Placed sentences with an amendment change still to decide (decision 6): they keep their place."""
    out = {}
    have = {it["id"] for it in M.items if it.get("map")} if M is not None else None
    for pk, p in (rv.pairs or {}).items():
        label = (p.get("labels") or ["", ""])[-1] or "the new version"
        dec = p.get("decisions", {})
        for key, t in (p.get("touch") or {}).items():
            if dec.get(key):
                continue
            for iid in t.get("items", []):
                if have is None or iid in have:
                    out.setdefault(iid, []).append({"text": flag_text(t, label), "pk": pk, "key": key})
    return out


def place(pdf, rows):
    """Where each change sits on the new version's page copy."""
    import pagesent as PS
    items = [{"id": r["key"], "text": r["new"]} for r in rows if r.get("nj") is not None and r.get("new")]
    if not items:
        return {}
    found = PS.place_all(pdf, items)
    pages = sorted({sp[0] for pl, _lead in found.values() for sp in PS.parse_place(pl)})
    out, anchors = {}, {}
    with_place = [dict(it, place=found[it["id"]][0], lead_place=found[it["id"]][1]) for it in items if it["id"] in found]
    for n in pages:
        for x in PS.place_map(pdf, n, with_place)["items"]:
            e = out.setdefault(x["id"], {"page": n, "rects": [], "words": [], "changed": []})
            if x["part"] == "end" and e["page"] != n:
                continue                                  # a sentence that runs on: drawn where it starts
            e["rects"] += x["rects"]; e["words"] += x["words"]
    by_key = {r["key"]: r for r in rows}
    for k in [k for k in out if by_key[k]["kind"] == "same"]:
        anchors[k] = out.pop(k)                           # kept only to mark where a removed sentence stood
    for k, e in out.items():
        cw = changed_words(by_key[k])
        e["changed"] = [e["words"][i] for i in cw if i < len(e["words"])]
    nxt = None                                            # removed sentences: where they stood
    for r in reversed(rows):
        here = out.get(r["key"]) or anchors.get(r["key"])
        if r.get("nj") is not None and here:
            nxt = here
        elif r.get("kind") == "removed" and nxt is not None and nxt["rects"]:
            l, t, rr, b = nxt["rects"][0]
            out[r["key"]] = {"page": nxt["page"], "rects": [(l, t - 3.5, l + 90, t - 1.5)], "words": [], "changed": [], "removed": True}
    return out


def page_status(placed, rows, decided):
    """{page: "todo" | "done"}: a page with a change still to decide is "todo"; with changes all decided, "done"."""
    st = {}
    for r in rows:
        if r.get("kind") == "same" or r["key"] not in placed:
            continue
        n = placed[r["key"]]["page"]
        if not decided(r["key"]):
            st[n] = "todo"
        else:
            st.setdefault(n, "done")
    return st
