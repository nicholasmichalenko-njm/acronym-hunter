"""Response structure from the customer documents (2.28.0): Start an effort suggests the proposal's volumes and sections.

Rules only (no AI): volumes named in the instructions ("Volume I Technical, Volume II Management, and Volume III Cost",
"Volume II - Management Proposal"), page limits written next to them ("not exceed 25 pages"), and the Section L headings
that describe each volume's content (L.4 TECHNICAL VOLUME > L.4.1 Technical Approach). Proposal numbering follows the
volumes: Volume I's sections are 1.1, 1.2... and each keeps its RFP reference in brackets. When nothing is found the user
types the structure; the result is plain outline text the compliance matrix and Setup read.
"""
import re

_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}
_VOL = re.compile(r"\bVolume\s+(VIII|VII|VI|IV|V|III|II|I|[1-8])\b(?:\s*[-–—:,(]\s*|\s+)"
                  r"((?:(?!Volume\b)[A-Z][A-Za-z/&]+)(?:\s+(?!Volume\b)(?:and\s+)?[A-Z][A-Za-z/&]+){0,3})?")
_PAGES = re.compile(r"(?:not\s+(?:to\s+)?exceed|limited\s+to|maximum\s+of|no\s+more\s+than|up\s+to)?\s*\(?(\d{1,3})\)?\s*"
                    r"(?:-\s*)?(?:single-sided\s+)?pages?\b", re.I)
_GENERAL = re.compile(r"general|instruction|organization|format|submission|preparation|delivery|cover|table of contents|"
                      r"glossary|definitions|questions|due date|electronic|font", re.I)
_TITLE_DROP = re.compile(r"\s+(?:proposal|volume)$", re.I)


def _num(tok):
    return int(tok) if tok.isdigit() else _ROMAN.get(tok.upper(), 0)


def _roman(n):
    return {v: k for k, v in _ROMAN.items()}.get(n, str(n))


def _title(s):
    s = " ".join((s or "").split())
    if s.isupper():
        small = {"and", "of", "the", "for", "to", "in", "on", "a", "an", "or"}
        s = " ".join(w.lower() if i and w.lower() in small else w.capitalize() for i, w in enumerate(s.split()))
    return s


def find_volumes(texts):
    """{number: {"title", "pages", "file"}} from the instruction text of every file (first title found wins)."""
    vols = {}
    for name, text in texts:
        flat = " ".join(text.split())
        for m in _VOL.finditer(flat):
            n = _num(m.group(1))
            if not n:
                continue
            title = _TITLE_DROP.sub("", (m.group(2) or "").strip()).strip()
            title = re.sub(r"^and\s+", "", title)
            v = vols.setdefault(n, {"title": "", "pages": "", "file": name})
            if title and not v["title"] and title.lower() not in ("shall", "will", "must"):
                v["title"] = _title(title)
            window = flat[m.end():m.end() + 160]
            stop = re.search(r"\bVolume\s+(?:VIII|VII|VI|IV|V|III|II|I|[1-8])\b", window)
            window = window[:stop.start()] if stop else window
            p = _PAGES.search(window)
            if p and not v["pages"] and 1 <= int(p.group(1)) <= 500:
                v["pages"] = p.group(1)
    return vols


def suggest(files_chunks, headings=None):
    """files_chunks: [(file name, [(label, text)])]; headings: the RFP's numbered headings (compliance.extract fills them).
    Returns {"text": outline text, "notes": [plain sentences about what was found], "volumes": n, "sections": n}."""
    texts = [(name, "\n".join(t for _l, t in chunks)) for name, chunks in files_chunks]
    vols = find_volumes(texts)
    heads, seen = [], set()
    for h in headings or []:
        if h["num"].startswith("L.") and h["num"] not in seen:
            seen.add(h["num"]); heads.append(h)
    import compliance as C
    heads.sort(key=lambda h: C.sec_key(h["num"]))
    owner = {}                                    # heading number -> volume number
    for h in heads:
        t = h["title"]
        m = re.search(r"\bVolume\s+(VIII|VII|VI|IV|V|III|II|I|[1-8])\b", t, re.I)
        n = _num(m.group(1)) if m else 0           # 1. the heading names the volume
        parent = next((p for p in sorted(owner, key=len, reverse=True) if h["num"].startswith(p + ".")), None)
        if not n and parent:                       # 2. it sits under a heading that belongs to a volume
            n = owner[parent]
        if not n:                                  # 3. it shares the volume's name (TECHNICAL VOLUME -> Technical)
            for vn, v in vols.items():
                key = v["title"].split()[0].lower() if v["title"] else ""
                if key and re.search(r"\b" + re.escape(key) + r"\b", t, re.I):
                    n = vn; break
        if n:
            owner[h["num"]] = n
    lines, notes, sections = [], [], 0
    used = set()
    for n in sorted(vols):
        v = vols[n]
        lines.append(f"Volume {_roman(n)} {v['title'] or ''}".rstrip() + (f" ({v['pages']} pages)" if v["pages"] else ""))
        k = 0
        for h in heads:
            if owner.get(h["num"]) != n:
                continue
            is_volume_head = re.search(r"\bvolume\b", h["title"], re.I) and h["num"].count(".") == 1
            if is_volume_head:
                used.add(h["num"])
                continue
            k += 1
            sections += 1
            used.add(h["num"])
            lines.append(f"    {n}.{k} {_title(h['title'])} [{h['num']}]")
    rest = [h for h in heads if h["num"] not in used and not _GENERAL.search(h["title"])]
    if rest:
        if lines:
            notes.append(f"{len(rest)} Section L heading(s) did not name a volume; they are listed last for you to place.")
        start = len(vols) + 1 if vols else 1
        k = 0
        for h in rest:
            k += 1
            sections += 1
            lines.append(f"{start}.{k} {_title(h['title'])} [{h['num']}]" if vols else f"{k} {_title(h['title'])} [{h['num']}]")
    if vols:
        files = sorted({v["file"] for v in vols.values()})
        notes.insert(0, f"Found {len(vols)} volume(s) in {', '.join(files)}"
                        + (f"; page limits for {sum(1 for v in vols.values() if v['pages'])}" if any(v["pages"] for v in vols.values()) else "")
                        + ".")
    total = None
    for _name, text in texts:
        m = re.search(r"(?:proposals?|responses?|offers?)\s+(?:shall|must|will)\s+not\s+exceed\s+(\d{1,3})\s+(?:total\s+)?pages",
                      " ".join(text.split()), re.I)
        if m:
            total = m.group(1); break
    if total:
        notes.append(f"Page limit for the whole proposal: {total} pages.")
    if heads:
        notes.append(f"Sections come from {len(heads)} Section L heading(s); RFP references are in brackets.")
    if not lines:
        notes.append("No volume instructions or Section L headings were found in the customer documents. Type the structure.")
    return {"text": "\n".join(lines), "notes": notes, "volumes": len(vols), "sections": sections, "total_pages": total}
