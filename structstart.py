"""How a response structure starts (2.69.0): what the RFP prescribes, the RFP's headings (from any document or
section), the effort's typed outline, or blank; and copying one RFP section (with its subsections) into the structure
while reviewing. Most RFPs do not use Sections L and M, so nothing here depends on that lettering: a volume is found by
its words ("Volume II - Management", "TECHNICAL VOLUME"), a prescribed list by its lead-in ("shall be organized as
follows:"), and the RFP's numbering is whatever the document uses. Rules only (No AI); nothing leaves the PC.
"""
import re
import compliance as C

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
_VOL_HEAD = re.compile(r"^\s*Volume\s+(?P<n>[IVX]{1,4}|\d{1,2})\b\s*(?:[-–—:.,]\s*)?(?P<t>.*)$", re.I)
_VOL_TAIL = re.compile(r"^\s*(?P<t>[A-Za-z][A-Za-z/& ]{1,40}?)\s+Volume\s*$", re.I)
_VOL_TEXT = re.compile(r"\bVolume\s+(?P<n>[IVX]{1,4}|\d{1,2})\b\s*(?:[-–—:(]\s*|,\s*|\s+)"
                       r"(?P<t>[A-Z][A-Za-z/&]+(?:\s+(?:and|&|of|[A-Z][A-Za-z/&]+)){0,4})")
_ORGANIZED = re.compile(r"\b(organi[sz]ed|structured|arranged|consists? of|contains? the following|comprised of|"
                        r"in the following order|following (?:sections|parts|volumes|tabs|chapters|order))\b", re.I)
_NOT_TITLE = {"Shall", "Will", "Must", "May", "Should", "The", "This", "Each", "All", "Page", "Pages", "Title", "Limit"}


def _n(tok):
    tok = tok.upper()
    return ROMAN.get(tok) or (int(tok) if tok.isdigit() else 0)


def _roman(n):
    return next((r for r, v in ROMAN.items() if v == n), str(n))


def _title(t):
    t = " ".join((t or "").split()).strip(" -:.,()")
    if t.isupper():
        t = " ".join(w.capitalize() if len(w) > 3 or i == 0 else w.lower() for i, w in enumerate(t.split()))
    return t[:80]


def _heads(M, files=None):
    """The RFP's numbered headings, once each, in document order (optionally from some files only)."""
    seen, out = set(), []
    for h in getattr(M, "headings", []) or []:
        if files and h.get("file") not in files:
            continue
        k = (h.get("file", ""), h["num"], h.get("title", ""))
        if k in seen:
            continue
        seen.add(k)
        out.append(h)
    return out


def _under(heads, i):
    """The headings under heading i (its number and a dot), in order."""
    num = heads[i]["num"]
    return [h for h in heads[i + 1:] if h["num"].startswith(num + ".") and h.get("file") == heads[i].get("file")]


def prescribed(M):
    """The response structure the RFP spells out, as far as rules can tell. Returns (outline, why): outline is
    [{num, title, level}] with "Volume N" headings first-level and their sections numbered 1, 1.1 ... in each volume;
    why is [text] saying where each part came from. ([], []) when the RFP does not say."""
    heads = _heads(M)
    vols = {}                                       # number -> {"title", "children": [heading], "why"}
    order = []
    for i, h in enumerate(heads):
        m = _VOL_HEAD.match(h.get("title", ""))
        t = _VOL_TAIL.match(h.get("title", "")) if not m else None
        if not (m or t):
            continue
        n = _n(m.group("n")) if m else (max(vols) + 1 if vols else 1)
        if not n or n in vols:
            continue
        title = _title(m.group("t") if m else t.group("t"))
        vols[n] = {"title": title, "children": _under(heads, i), "why": f"{h['num']} {h.get('title', '')}".strip()}
        order.append(n)
    for it in M.items:                               # volumes named in the text or a table, not as headings
        for m in _VOL_TEXT.finditer(it.get("text", "")):
            n = _n(m.group("n"))
            t = _title(m.group("t"))
            if not n or n in vols or t.split()[0] in _NOT_TITLE:
                continue
            vols[n] = {"title": t, "children": [], "why": f"{it.get('id', '')}: {it.get('text', '')[:80]}"}
            order.append(n)
    lists = {}                                       # a prescribed list: "shall be organized as follows:"
    for it in M.items:
        lead = it.get("lead", "") or ""
        if lead and _ORGANIZED.search(lead):
            lists.setdefault(lead, []).append(it)
    listed = {}                                      # volume number (0: none named) -> [(title, lead)]
    for lead, its in lists.items():
        mv = re.search(r"\bVolume\s+([IVX]{1,4}|\d{1,2})\b", lead, re.I)
        n = _n(mv.group(1)) if mv else 0
        for it in its:
            t = _title(re.sub(r"^\(?[a-z0-9ivx]{1,4}[.)]\s*", "", it.get("text", ""), flags=re.I).split(";")[0])
            if t:
                listed.setdefault(n, []).append((t, lead))
    for n in [n for n in listed if n and n not in vols]:
        vols[n] = {"title": "", "children": [], "why": listed[n][0][1][:80]}
    out, why = [], []

    def put(entries, lvl0):
        """entries: [(title, depth)] numbered 1, 1.1 ... under the current volume (or from the top)."""
        counters = {}
        for title, depth in entries:
            counters[depth] = counters.get(depth, 0) + 1
            for k in [k for k in counters if k > depth]:
                counters.pop(k)
            out.append({"num": ".".join(str(counters.get(k, 1)) for k in range(1, depth + 1)), "title": title,
                        "level": depth + lvl0})

    for n in sorted(vols):
        v = vols[n]
        out.append({"num": f"Volume {_roman(n)}", "title": v["title"], "level": 1})
        why.append(f"Volume {_roman(n)} {v['title']}".strip() + f": {v['why']}")
        entries = [(t, 1) for t, _l in listed.get(n, [])]       # an organized list says it outright: it comes first
        if entries:
            why.append(f"  {len(entries)} section(s) listed after \"{listed[n][0][1][:70]}\"")
        if v["children"]:
            base = v["children"][0]["num"].count(".")
            have = {t.lower() for t, _d in entries}
            kids = [(_title(ch.get("title", "")), ch["num"].count(".") - base + 1) for ch in v["children"]]
            entries += [(t, d) for t, d in kids if t.lower() not in have]
            why.append(f"  section(s) from the RFP headings under {v['why']}")
        put(entries, 1)
    if listed.get(0):
        put([(t, 1) for t, _l in listed[0]], 0)
        why.append(f"{len(listed[0])} section(s) listed after \"{listed[0][0][1][:70]}\"")
    return out, why


def from_headings(M, letter="", files=None):
    """The RFP's numbered headings (one section letter, or all), from some documents or all, as a starting outline.
    Levels follow the numbering; nothing assumes Sections L and M exist."""
    heads = _heads(M, files)
    if letter and letter not in ("All", ""):
        heads = [h for h in heads if h["num"].startswith(letter + ".") or h["num"] == letter]
    out, seen = [], set()
    for h in heads:
        if h["num"] in seen:
            continue
        seen.add(h["num"])
        num = h["num"]
        lvl = num.count(".") + (0 if num[:1].isalpha() else 1)
        out.append({"num": num, "title": _title(h.get("title", "")), "level": max(1, lvl)})
    if out:                                          # the shallowest heading is the first level
        low = min(o["level"] for o in out)
        for o in out:
            o["level"] -= low - 1
    return out


def files_with_headings(M):
    return list(dict.fromkeys(h.get("file", "") for h in getattr(M, "headings", []) or [] if h.get("file")))


def apply(M, outline):
    """Set a starting structure (sentences in sections no longer there keep their decision, with no section)."""
    import structure_ops as STR
    import setupdoc as SD
    n, lost = STR.apply(M, C.outline_text(outline) if outline else "")
    V = SD.setup_of(M).get("volumes") or {}
    if V.get("mode") == "several":                    # volumes follow the new structure's Volume headings
        SD.set_volumes(M, "", "", [])
    return n, lost


# ------------------------------------------------------------------ copy one RFP section into the structure
def rfp_section_of(M, it):
    """(file, number, title) of the RFP section a sentence is in (a heading row: its own)."""
    return it.get("file", ""), it.get("section", "") or "", it.get("section_title", "") or ""


def subsections(M, file, num):
    """The RFP headings under one section, in order: [(num, title)]."""
    if not num:
        return []
    heads = _heads(M, [file] if file else None)
    return [(h["num"], _title(h.get("title", ""))) for h in heads if h["num"].startswith(num + ".")]


def copy_section(M, it, parent=None, with_subsections=True, place=True):
    """Copy the RFP section a sentence is in into the response structure: a section titled as the RFP titles it,
    under parent (or at the end), its subsections under it when asked. Each RFP section is mapped to the section made
    from it, so its sentences suggest it; with place, its requirements that have no section yet go into it.
    Returns [new labels], first the section itself."""
    import outline_ops as O
    import rfpoutline as RO
    f, num, title = rfp_section_of(M, it)
    title = _title(title) or _title(it.get("text", ""))[:80]
    if not title:
        return []
    made = []
    top = O.add(M, title, parent=parent) if parent else O.add(M, title)
    if top is None:
        return []
    made.append(top)
    rfp = {num: top} if num else {}
    if with_subsections and num:
        for snum, stitle in subsections(M, f, num):
            par = rfp.get(snum.rsplit(".", 1)[0], top)
            lab = O.add(M, stitle or snum, parent=par)
            # new sections go after their siblings, so the ones above keep their numbers
            rfp[snum] = lab
            made.append(lab)
    labels_now = set(O.labels(M))
    for rnum, lab in rfp.items():
        if lab in labels_now:
            RO.map_section(M, rnum, lab)
            o = M.outline[O.index_of(M, lab)]
            o["from"] = rnum                             # where it came from in the RFP
    moved = 0
    if place:
        for x in M.items:
            if x.get("decision") == "Keep" and not x.get("map") and x.get("file") == f and x.get("section") in rfp:
                x["map"] = rfp[x["section"]]
                moved += 1
    M.log("outline", f"RFP section {num or title} copied into the structure as {top}" + (f"; {moved} requirement(s) placed" if moved else ""))
    M.pending = True
    return made

