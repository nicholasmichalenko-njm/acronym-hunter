"""The Section J check (4.86.0, step I4 of claude/stationkeeper-document-intake-direction-2026-11-24.md, section 6): Section J
of a solicitation lists every attachment and exhibit by title, so it is the customer's own list of the package. The check
reads that list from the package's customer documents and counts how many of them the package holds:
"Section J lists 14 attachments; 13 are in this package." with the missing ones named.

- refs(text)         [(key, ref as written, title)] from Section J's words: "Attachment J-1 Performance Work Statement",
                     "Attachment 3 DD Form 254", "J-4 Wage Determination", "Exhibit A Contract Data Requirements List".
                     J-1 and Attachment 1 are the same attachment.
- listing(lib, d, v) the Section J refs of one version (its pieces whose section is J, or titled List of Attachments), kept
                     by version id for the session.
- check(lib, part)   {"doc", "refs", "here": [(ref, title, document)], "missing": [(ref, title)]} for a package, read
                     from the newest version in force that has a Section J; None when none has one.
- line(r)            the words for it.
A document counts for a ref when its name, or a file name of one of its versions, carries the ref (J-1, Att 1,
Attachment_01, Exhibit A), or when its name has the title's words. Rules only (No AI); nothing leaves the PC."""
import difflib
import re

_CACHE = {}
_ATT = re.compile(r"\b(?:attachment|attachmt|att\.?)\s*(?:no\.?\s*)?(?:(j)\s*[-.]?\s*)?0*(\d{1,3})(?![\d.]\d)", re.I)
_J = re.compile(r"(?<![a-z0-9-])j\s*-\s*0*(\d{1,3})(?![\d.]\d)", re.I)
_EXH = re.compile(r"\bexhibit\s+(?:no\.?\s*)?([a-z]{1,2}|\d{1,3})\b", re.I)
_HEAD = re.compile(r"list\s+of\s+(?:attachments|documents|exhibits)|section\s+j\b", re.I)
_TAIL = re.compile(r"[\s,;:(\[-]*(?:\d+\s*(?:pages?|pp\.?)|dated\b.*|\d{1,2}\s*[a-z]{3,9}\.?\s*\d{2,4}|\d{1,2}/\d{1,2}/\d{2,4})[\s,;:)\]]*$", re.I)
_STOP = {"the", "and", "for", "of", "to", "with", "form", "list", "attachment", "exhibit", "section"}


def refs(text):
    """[(key, ref, title)] in the order written; a ref met again (a table of contents, say) is kept once."""
    t = " ".join(str(text or "").split())
    hits = []
    for m in _ATT.finditer(t):
        hits.append((m.start(), m.end(), ("att", str(int(m.group(2)))), (f"J-{int(m.group(2))}" if m.group(1) else f"Attachment {int(m.group(2))}")))
    for m in _J.finditer(t):
        if not any(a <= m.start() < b for a, b, _k, _r in hits):
            hits.append((m.start(), m.end(), ("att", str(int(m.group(1)))), f"J-{int(m.group(1))}"))
    for m in _EXH.finditer(t):
        x = m.group(1).upper() if not m.group(1).isdigit() else str(int(m.group(1)))
        hits.append((m.start(), m.end(), ("exh", x), f"Exhibit {x}"))
    hits.sort()
    out, seen = [], set()
    for i, (a, b, key, ref) in enumerate(hits):
        if key in seen:
            continue
        nxt = hits[i + 1][0] if i + 1 < len(hits) else len(t)
        title = t[b:nxt].strip(" -:,.;–—")
        title = _TAIL.sub("", title).strip(" -:,.;–—")
        if title.rfind("(") > title.rfind(")"):                      # "Pricing Template (Excel" -> "Pricing Template"
            title = title[:title.rfind("(")]
        title = title.strip(" -:,.;()–—")[:80]
        seen.add(key)
        out.append((key, ref, title))
    return out


def listing(lib, d, v):
    """The Section J refs of one version, or []."""
    k = v.get("id")
    if k in _CACHE:
        return _CACHE[k]
    words = []
    for it in lib.text(v) or []:
        s = str(it.get("s", "")).strip()
        if re.match(r"^j(?:\b|\.|$)", s, re.I) or _HEAD.search(str(it.get("t", ""))) or _HEAD.match(str(it.get("x", ""))):
            words.append(str(it.get("x", "")))
    found = refs(" ".join(words)) if words else []
    _CACHE[k] = found
    return found


def _names(d):
    out = [d.get("name", "")] + [v.get("file", "") for v in d.get("versions") or []]
    return [" ".join(re.sub(r"[_.]+", " ", re.sub(r"\.[a-z0-9]{2,4}$", "", n, flags=re.I)).lower().split()) for n in out if n]


def _has(d, key, title):
    kind, x = key
    names = _names(d)
    if kind == "att":
        pat = re.compile(r"(?<![a-z0-9])(?:j\s*-?\s*0*" + x + r"|att(?:achment)?\s*(?:no\s*)?(?:j\s*-?\s*)?0*" + x + r")(?![0-9])")
    else:
        pat = re.compile(r"(?<![a-z0-9])exh(?:ibit)?\s*" + re.escape(x.lower()) + r"(?![a-z0-9])")
    if any(pat.search(n) for n in names):
        return True
    tw = [w for w in re.findall(r"[a-z0-9]+", (title or "").lower()) if len(w) > 2 and w not in _STOP]
    if not tw:
        return False
    for n in names:
        nw = set(re.findall(r"[a-z0-9]+", n))
        if (len(tw) >= 2 and all(w in nw for w in tw)) or difflib.SequenceMatcher(None, " ".join(tw), n).ratio() >= 0.75:
            return True
    return False


def check(lib, part):
    """The Section J check for a package (see the module's words), or None."""
    import docpackages as DP
    docs = [d for d in lib.all if d.get("category", "customer") in DP.CUSTOMER_SIDE and not d.get("withdrawn") and DP.in_part(d, part)]
    best = None
    for d in docs:
        for v in d.get("versions") or []:
            rs = listing(lib, d, v)
            if rs:
                when = (v.get("arrived_on") or "", v.get("added") or "")
                if best is None or when >= best[0]:
                    best = (when, d, rs)
    if best is None:
        return None
    _w, holder, rs = best
    here, missing = [], []
    for key, ref, title in rs:
        d = next((x for x in docs if x["id"] != holder["id"] and _has(x, key, title)), None)
        (here.append((ref, title, d)) if d is not None else missing.append((ref, title)))
    return {"doc": holder, "refs": rs, "here": here, "missing": missing}


def _kinds(rs):
    exh = sum(1 for k, _r, _t in rs if k[0] == "exh")
    return "exhibits" if exh == len(rs) else ("attachments and exhibits" if exh else "attachments")


def line(r):
    """ "Section J lists 14 attachments; 13 are in this package." """
    if not r:
        return ""
    n, h = len(r["refs"]), len(r["here"])
    k = _kinds(r["refs"])
    if n == 1:
        k = k.rstrip("s").replace("attachments and exhibit", "attachment or exhibit")
    are = "all are" if h == n and n > 1 else ("it is" if h == n else f"{h} " + ("is" if h == 1 else "are"))
    return f"Section J lists {n} {k}; {are} in this package."


def missing_text(r, most=6):
    if not r or not r["missing"]:
        return ""
    bits = [f"{ref} {title}".strip() for ref, title in r["missing"][:most]]
    more = len(r["missing"]) - most
    return "Not here: " + "; ".join(bits) + (f"; and {more} more" if more > 0 else "") + "."


def short(r):
    """For the group line on Documents: "Section J: 13 of 14 here"."""
    return f"Section J: {len(r['here'])} of {len(r['refs'])} here" if r else ""
