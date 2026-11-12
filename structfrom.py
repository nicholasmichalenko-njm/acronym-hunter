"""Our response structure from the customer's words, or drafted by us (4.19.0;
claude/stationkeeper-response-structure-plan-4.19.html). Two doors, one outline:

- Door 1, the customer prescribes it: pieces typed Structure in Shred (shredtypes "structure") are read into headings
  (read): a volume named in a piece is an H1 ("Volume II Management"); the items of an "organized as follows" list are
  the next level under the volume they name (or H1 with none); a piece that is itself a heading keeps its H level (or
  sits under the volume above it); a page limit in the words is kept. Each heading says which piece required it and
  where that piece is (Required by). put() writes them into the outline (numbered: volumes "Volume N", sections 1, 1.1
  in each volume), keeps the list of required headings in the matrix's setup, and drift() later says when a required
  heading was renamed, taken out or moved out of order. Nothing is blocked: the outline stays ours to edit.
- Door 2, we build it: draft headings from the customer's headings, the SOW or PWS headings, the evaluation factors,
  or blank (drafts). They are the outline's own sections marked Draft; pieces go to them as to any section;
  use_as_ours() takes Draft off.
Rules only (No AI); nothing leaves the PC."""
import re

import compliance as C

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
_VOL = re.compile(r"\bVolume\s+(?P<n>[IVX]{1,4}|\d{1,2})\b\s*(?:[-–—:(,]\s*|\s+)?"
                  r"(?P<t>(?:[A-Z][A-Za-z/&]+)(?:\s+(?:and|&|of|[A-Z][A-Za-z/&]+)){0,5})?")
_LIST_START = re.compile(r"(?:organi[sz]ed|structured|arranged|in the following order|as follows|the following (?:sections|parts|"
                         r"volumes|tabs|chapters))[^:]*:\s*", re.I)
_ITEM = re.compile(r"(?:^|\s|;)\(?(?:[a-z]|[0-9]{1,2}|[ivx]{1,4})[.)]\s+", re.I)
_MARK = re.compile(r"^\s*\(?(?:[a-z]|[0-9]{1,2}|[ivx]{1,4})[.)]\s+", re.I)
_LIMIT = re.compile(r"(?:not\s+(?:to\s+)?exceed|no\s+more\s+than|limited\s+to|maximum\s+of|up\s+to)\s+(\d{1,3})\s+pages?|"
                    r"\((\d{1,3})\s+pages?\)|(\d{1,3})[- ]page\s+limit", re.I)
_NOT_TITLE = {"Shall", "Will", "Must", "May", "Should", "The", "This", "Each", "All", "Page", "Pages", "Limit"}


def _n(tok):
    tok = (tok or "").upper()
    return ROMAN.get(tok) or (int(tok) if tok.isdigit() else 0)


def _roman(n):
    return next((r for r, v in ROMAN.items() if v == n), str(n))


def _title(t):
    t = " ".join((t or "").split())
    t = _LIMIT.sub("", t)
    t = re.split(r"\s*[;]\s*|\.\s*$|\s+(?:shall|must|will|should)\b", t, maxsplit=1)[0]
    return t.strip(" .,:;-()")


def _limit(t):
    m = _LIMIT.search(t or "")
    return int(next(g for g in m.groups() if g)) if m else 0


def pieces(M):
    """The pieces typed Structure, in the order they sit in the customer's documents."""
    import shredtypes as ST
    return [it for it in M.items if ST.has(it, "structure")]


def _ref(it):
    sec = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
    pg = it.get("page", "")
    return ", ".join(x for x in (sec, f"page {pg}" if pg else "", it.get("id", "")) if x)


def read(M, its=None):
    """Headings from the Structure pieces: [{"title", "level", "limit", "req", "ref", "vol"}] in order."""
    out, vol = [], None
    for it in (pieces(M) if its is None else its):
        text = " ".join(((it.get("lead") or "") + " " + (it.get("text") or "")).split())
        base = {"req": it.get("id", ""), "ref": _ref(it)}
        found = False
        for m in _VOL.finditer(text):
            n = _n(m.group("n"))
            t = _title(m.group("t") or "")
            if t.split()[:1] and t.split()[0] in _NOT_TITLE:
                t = ""
            if not n or any(h.get("vol") == n and h["level"] == 1 for h in out):
                vol = n if n else vol
                continue
            out.append(dict(base, title=f"Volume {_roman(n)}" + (f" {t}" if t else ""), level=1, limit=0, vol=n))
            vol, found = n, True
        lim = _limit(text)
        if lim and found:
            out[-1]["limit"] = lim
        m = _LIST_START.search(text)
        if m:                                             # "organized as follows: (1) Technical Approach; (2) Management"
            rest = text[m.end():]
            parts = [p for p in _ITEM.split(rest) if p and p.strip()]
            if len(parts) == 1:
                parts = [p for p in re.split(r"\s*;\s*|\s*,\s+and\s+|\s*,\s*", rest) if p.strip()]
            for p in parts:
                t = _title(p)
                if t and len(t.split()) <= 12:
                    out.append(dict(base, title=t, level=2 if vol else 1, limit=_limit(p), vol=vol))
                    found = True
            continue
        if found:
            continue
        lv = int(it.get("hlevel") or 0)
        t = _title(_MARK.sub("", it.get("text") or ""))
        if t and len(t.split()) <= 14:
            out.append(dict(base, title=t, level=lv or (2 if vol else 1), limit=lim, vol=vol))
    return _by_volume(out)


def _by_volume(out):
    """Each heading after its volume (a list for Volume II read after Volume III goes back under Volume II)."""
    vols = [h for h in out if h["level"] == 1 and h["title"].startswith("Volume ")]
    if not vols:
        return out
    first = [h for h in out if h not in vols and not h.get("vol")]
    res = list(first)
    for v in vols:
        res.append(v)
        res += [h for h in out if h not in vols and h.get("vol") == v["vol"]]
    res += [h for h in out if h not in res]
    return res


def number(heads):
    """Outline entries [{num, title, level}] for headings: volumes keep "Volume N"; sections are numbered 1, 1.1 in each
    volume (from the top when there is none)."""
    out, counters = [], {}
    for h in heads:
        e = {k: v for k, v in h.items() if k not in ("vol",)}
        if h["title"].startswith("Volume ") and h["level"] == 1:
            e["num"] = " ".join(h["title"].split()[:2])
            e["title"] = " ".join(h["title"].split()[2:]) or e["num"]
            counters = {}
            out.append(e)
            continue
        inv = any(x["title"].startswith("Volume ") for x in heads)
        depth = h["level"] - (1 if inv else 0)
        depth = max(1, depth)
        counters[depth] = counters.get(depth, 0) + 1
        for k in [k for k in counters if k > depth]:
            counters.pop(k)
        e["num"] = ".".join(str(counters.get(k, 1)) for k in range(1, depth + 1))
        out.append(e)
    return out


KEEP = ("req", "req_title", "ref", "draft", "limit", "page")


def _apply(M, ents, replace):
    """Set the outline (structstart.apply goes through the outline's text) and put back what the text cannot hold."""
    import structstart as SS
    before = len(M.outline) if not replace else 0
    SS.apply(M, ents if replace else list(M.outline) + ents)
    new = M.outline[before:]
    for o, e in zip(new, ents):
        if " ".join(o.get("title", "").split()).lower() == " ".join(e.get("title", "").split()).lower():
            o.update({k: e[k] for k in KEEP if e.get(k)})
    return new


def untouched(M):
    """Our outline is empty, or still the start the app made from the customer's headings when it first read them."""
    import setupdoc as SD
    return not M.outline or bool(SD.setup_of(M).get("outline_auto"))


def put(M, heads, replace=None):
    """Write the headings into the outline (replace: it was empty or still the app's own start, or the person said so)
    and keep them as the required structure. Returns the outline entries made."""
    import setupdoc as SD
    ents = number(heads)
    for e in ents:
        e["req_title"] = e["title"]
        if not e.get("limit"):
            e.pop("limit", None)
    if replace is None:
        replace = untouched(M)
    _apply(M, ents, replace)
    SD.setup_of(M).pop("outline_auto", None)
    req = SD.setup_of(M).setdefault("required", [])
    if replace:
        req.clear()
    req.extend({"title": e["title"], "num": e["num"], "level": e["level"], "req": e.get("req", ""), "ref": e.get("ref", "")}
               for e in ents)
    M.pending = True
    return ents


def drift(M):
    """What changed in our outline against the required structure: [(kind, text)], kind "gone", "renamed", "moved"."""
    import setupdoc as SD
    req = SD.setup_of(M).get("required") or []
    issues, last = [], -1
    norm = lambda t: " ".join((t or "").lower().split())          # noqa: E731
    for r in req:
        at = next((k for k, o in enumerate(M.outline) if o.get("req") == r["req"] and norm(o.get("req_title")) == norm(r["title"])), None)
        if at is None:
            at = next((k for k, o in enumerate(M.outline) if norm(o.get("title")) == norm(r["title"])), None)
        if at is None:
            issues.append(("gone", f"{r['title']} (required by {r['ref'] or r['req']}) is not in our outline"))
            continue
        o = M.outline[at]
        if norm(o.get("title")) != norm(r["title"]):
            issues.append(("renamed", f"{r['title']} is now {o.get('title')} (required by {r['ref'] or r['req']})"))
        if at < last:
            issues.append(("moved", f"{r['title']} comes before a heading the customer puts ahead of it"))
        last = max(last, at)
    return issues


# ------------------------------------------------------------------ door 2: drafts
STARTS = (("headings", "The customer's headings"), ("sow", "The SOW or PWS headings"), ("factors", "The evaluation factors"),
          ("blank", "Blank"))


def _sow_files(M, lib=None):
    files = set()
    for h in getattr(M, "headings", []):
        f = h.get("file", "")
        if re.search(r"\b(SOW|PWS|SOO|statement of (?:work|objectives)|performance work)\b", f, re.I):
            files.add(f)
    if lib is not None:
        for d in lib.docs:
            if re.search(r"\b(SOW|PWS|SOO|statement of)", (d.get("type") or "") + " " + d.get("name", ""), re.I):
                files.update(v.get("file", "") for v in d.get("versions", []))
    return files


def drafts(M, start, rec=None, lib=None):
    """Draft headings from a start: [{num, title, level, draft: True}]."""
    if start == "headings":
        import rfpoutline as RO
        ol = RO.as_outline(M) or C.outline_from_headings(getattr(M, "headings", []), "")
    elif start == "sow":
        files = _sow_files(M, lib)
        hs = [h for h in getattr(M, "headings", []) if h.get("file") in files] if files else \
             [h for h in getattr(M, "headings", []) if (h.get("num") or "").startswith("C.")]
        ol = C.outline_from_headings(hs, "")
    elif start == "factors":
        import custfocus as F
        fs = F.factors(rec) if rec is not None else []
        top = {f["id"]: f for f in fs}
        ol = [{"num": "", "title": f["name"], "level": 2 if f.get("parent") in top else 1} for f in fs]
    else:
        ol = []
    out = []
    for o in ol:
        out.append({"num": o.get("num", ""), "title": o.get("title", ""), "level": int(o.get("level") or 1), "draft": True,
                    **({"page": o["page"]} if o.get("page") else {})})
    return out


def put_drafts(M, ents):
    """Draft headings into the outline: the whole of it when it is empty, else after what is there."""
    num = [dict(e) for e in ents]
    if any(not e.get("num") for e in num):
        plain = number([{"title": e["title"], "level": e["level"]} for e in num])
        for e, p in zip(num, plain):
            e["num"] = e.get("num") or p["num"]
    _apply(M, num, untouched(M))
    __import__("setupdoc").setup_of(M).pop("outline_auto", None)
    M.pending = True
    return num


def draft_count(M):
    return sum(1 for o in M.outline if o.get("draft"))


def use_as_ours(M):
    n = 0
    for o in M.outline:
        if o.pop("draft", None):
            n += 1
    M.pending = True
    return n
