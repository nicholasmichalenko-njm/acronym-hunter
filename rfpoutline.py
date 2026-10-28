"""The RFP's own outline (2.54.0): its sections and subsections, numbered or not, in the order they appear.

Where a sentence came from (its RFP section) and where it goes (our proposal section) are two outlines:
- headers: the RFP section headers in document order: numbered headings the reader found, lines marked as headers
  (Section header..., key H) and capitalized title lines; each with its number, title, level and file. A header the
  RFP did not number is numbered by its order (3, 3.1, 3.2) and can be renamed.
- every sentence takes the number and title of the header above it, up to the next header (compliance.mark_header);
- suggested headers: short title lines the reader did not treat as headers, to confirm or dismiss with one click;
- mapping: an RFP section mapped to a proposal section makes it the first suggestion for its sentences.
Kept in the matrix's setup data: header levels, dismissed suggestions, the mapping. Rules only (No AI).
"""
import re

_MODAL = re.compile(r"\b(shall|must|will|should|may|required|is to|are to)\b", re.I)
_SMALL = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with", "vs", "per"}


def _S(M):
    import setupdoc as SD
    S = SD.setup_of(M)
    S.setdefault("header_levels", {})
    S.setdefault("header_no", [])
    S.setdefault("rfp_map", {})
    return S


def guess_level(num):
    """L -> 1, L.4 -> 2, L.4.2 -> 3; 3 -> 1, 3.1 -> 2; no number -> 1."""
    num = (num or "").strip().rstrip(".")
    if not num:
        return 1
    return min(6, len([p for p in num.split(".") if p]))


def headers(M):
    """[{"id", "num", "title", "level", "file", "pos"}] in document order. pos: the index of the header row in the
    matrix (or of the first sentence under a numbered heading that has no row of its own)."""
    S = _S(M)
    out, seen = [], set()
    for i, it in enumerate(M.items):
        f = it.get("file", "")
        sec = it.get("section", "") or ""
        if it.get("type") == "Heading":
            num = sec
            title = it.get("section_title", "") or it.get("text", "")
            key = (f, num, title)
            if key in seen and num:
                continue
            seen.add(key)
            out.append({"id": it.get("id", ""), "num": num, "title": title, "file": f, "pos": i,
                        "level": int(S["header_levels"].get(it.get("id", ""), guess_level(num)))})
        elif sec and (f, sec) not in {(h["file"], h["num"]) for h in out}:
            key = (f, sec, it.get("section_title", ""))
            if key in seen:
                continue
            seen.add(key)                                 # a numbered heading the reader used as a section title
            out.append({"id": "", "num": sec, "title": it.get("section_title", ""), "file": f, "pos": i, "level": guess_level(sec)})
    return out


def counts(M):
    """{(file, num): [requirements, support]} for the sentences under each header."""
    c = {}
    for it in M.items:
        d = it.get("decision")
        if d in ("Keep", "Context") and it.get("section"):
            k = c.setdefault((it.get("file", ""), it["section"]), [0, 0])
            k[0 if d == "Keep" else 1] += 1
    return c


def auto_number(M, idx, level, file):
    """The number for a header the RFP did not number, from the headers before it in the same file: the next one at
    its level under its parent (3, 3.1, 3.2)."""
    before = [h for h in headers(M) if h["file"] == file and h["pos"] < idx and re.fullmatch(r"\d+(?:\.\d+)*", h["num"] or "")]
    parent = next((h for h in reversed(before) if h["level"] < level), None)
    if level <= 1 or parent is None:
        tops = [h for h in before if h["level"] <= 1]
        n = max([int(h["num"].split(".")[0]) for h in tops] + [0]) + 1
        return str(n)
    sibs = [h for h in before if h["pos"] > parent["pos"] and h["level"] == level and h["num"].startswith(parent["num"] + ".")]
    last = max([int(h["num"].split(".")[-1]) for h in sibs] + [0])
    return f"{parent['num']}.{last + 1}"


def set_level(M, iid, level):
    _S(M)["header_levels"][iid] = max(1, min(6, int(level)))
    M.pending = True


def candidates(M):
    """Suggested headers: short title lines (no period at the end, most words capitalized, no compliance word) the
    reader kept as ordinary sentences. Dismissed ones stay dismissed."""
    S = _S(M)
    no = set(S["header_no"])
    out = []
    for it in M.items:
        if it.get("type") == "Heading" or it.get("decision") in ("Keep",) or it.get("id") in no:
            continue
        t = " ".join((it.get("text") or "").split())
        words = t.split()
        if not 1 <= len(words) <= 10 or len(t) > 90 or re.search(r"[.;,?!]$", t) or _MODAL.search(t):
            continue
        alpha = [w for w in words if re.match(r"[A-Za-z]", w)]
        if len(alpha) < 1 or any(c.isdigit() for c in t[:1]) and not re.match(r"^\d+(\.\d+)*\s+\S", t):
            continue
        caps = sum(1 for w in alpha if w[0].isupper() or w.lower() in _SMALL)
        if caps / len(alpha) < 0.8 or all(w.lower() in _SMALL for w in alpha):
            continue
        if re.search(r"@|\(\d{3}\)|\d{3}-\d{4}", t):           # an e-mail address or a phone number
            continue
        out.append(it.get("id", ""))
    return out


def dismiss(M, iid):
    S = _S(M)
    if iid not in S["header_no"]:
        S["header_no"].append(iid)
    M.pending = True


def unmark(M, iid):
    """Take a header back: the line is a sentence again; the sentences under it take the header above it."""
    i = next((k for k, it in enumerate(M.items) if it.get("id") == iid), None)
    if i is None:
        return []
    h = M.items[i]
    f = h.get("file", "")
    prev = next((x for x in reversed(M.items[:i]) if x.get("file", "") == f and x.get("type") == "Heading"), None)
    num, title = (prev.get("section", ""), prev.get("section_title", "")) if prev else ("", "")
    h.update(type="Context", header="")
    if h.get("decision") == "Drop":
        h["decision"] = ""
    h["section"], h["section_title"] = num, title
    done = []
    for it in M.items[i + 1:]:
        if it.get("file", "") != f:
            continue
        if it.get("type") == "Heading":
            break
        it["section"], it["section_title"] = num, title
        done.append(it.get("id", ""))
    _S(M)["header_levels"].pop(iid, None)
    M.pending = True
    return done


def map_section(M, num, label):
    """An RFP section mapped to a proposal section (or "" to clear)."""
    S = _S(M)
    if label:
        S["rfp_map"][num] = label
    else:
        S["rfp_map"].pop(num, None)
    M.pending = True


def mapped(M, num):
    return _S(M)["rfp_map"].get(num or "", "")


def as_outline(M):
    """The RFP outline as a starting response structure: [{num, title, level}]."""
    out, seen = [], set()
    for h in headers(M):
        k = (h["num"], h["title"])
        if k in seen or not (h["num"] or h["title"]):
            continue
        seen.add(k)
        out.append({"num": h["num"], "title": h["title"], "level": h["level"]})
    return out
