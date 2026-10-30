"""Amendments written as instructions (SF 30 style), applied to show the conformed text.

Many amendments do not reissue the document; they say what to change:
- "Section L, paragraph L.4.2, delete "twenty (20) pages" and insert "twenty-five (25) pages"."
- "In paragraph C.3.1, change "monthly" to "quarterly"."
- "Paragraph L.5.3 is deleted in its entirety and replaced with the following: "..."."
- "Paragraph M.2.4 is hereby deleted in its entirety."
- "Add the following new paragraph L.5.6 after paragraph L.5.5: "..."."
- "Delete "CDRL A007" and insert "CDRL A008"" (no paragraph named: everywhere it appears).

parse() finds the instructions in the amendment's text; apply() carries them out on the base document's sentences and
says, for each one, whether it was applied (and to how many sentences) or why not (the paragraph or the words were not
found). The result is a conformed version of the base document that Changes, What changed and Assign treat like any
reissued version; nothing in the original files changes. Rules only (No AI); nothing leaves the PC.
"""
import re

Q_OPEN, Q_CLOSE = "\"“‘'", "\"”’'"
_Q = r"[\"“‘](?P<{n}>.+?)[\"”’](?=[\s.,;:)]|$)"
_SEC = r"(?:section|paragraph|para\.?|clause|subparagraph|item)\s+(?P<{n}>[A-Z]{{0,2}}[-.]?\d[\w.\-]*(?:\([a-z0-9]+\))*|[A-Z](?:\.\d+)*(?:\([a-z0-9]+\))*)"


def _sec(n="sec"):
    return _SEC.format(n=n)


def _q(n):
    return _Q.format(n=n)


PATTERNS = [
    ("words", re.compile(r"(?:in\s+)?" + _sec() + r"[^\"“]{0,80}?\b(?:delete|strike)\s+" + _q("old") +
                         r"\s*,?\s*and\s+(?:insert|substitute|add|replace\s+(?:it\s+)?with)\s+(?:in\s+its\s+place\s+)?" + _q("new"), re.I | re.S)),
    ("words", re.compile(r"(?:in\s+)?" + _sec() + r"[^\"“]{0,80}?\bchange\s+" + _q("old") + r"\s+to\s+(?:read\s+)?" + _q("new"), re.I | re.S)),
    ("words", re.compile(r"(?:in\s+)?" + _sec() + r"[^\"“]{0,80}?\breplace\s+" + _q("old") + r"\s+with\s+" + _q("new"), re.I | re.S)),
    ("section", re.compile(_sec() + r"\s+(?:is|are)\s+(?:hereby\s+)?(?:deleted\s+(?:in\s+its\s+entirety\s+)?and\s+replaced|replaced|revised|amended)"
                           r"\s+(?:in\s+its\s+entirety\s+)?(?:with|to\s+read|as\s+follows)[^\"“]{0,40}?" + _q("new"), re.I | re.S)),
    ("add", re.compile(r"\b(?:add|insert)(?:ed)?\s+(?:the\s+following\s+)?(?:new\s+)?" + _sec() +
                       r"(?:\s*,?\s*(?:after|following)\s+" + _sec("after") + r")?[^\"“]{0,40}?" + _q("new"), re.I | re.S)),
    ("add", re.compile(_sec() + r"\s+(?:is|are)\s+(?:hereby\s+)?added(?:\s+(?:after|following)\s+" + _sec("after") + r")?[^\"“]{0,40}?" + _q("new"),
                       re.I | re.S)),
    ("delete", re.compile(_sec() + r"\s+(?:is|are)\s+(?:hereby\s+)?(?:deleted|removed|rescinded)(?:\s+in\s+its\s+entirety)?(?!\s+and\s+replaced)(?=[\s.;,]|$)",
                          re.I | re.S)),
    ("words", re.compile(r"\b(?:delete|strike)\s+" + _q("old") + r"\s*,?\s*and\s+(?:insert|substitute|replace\s+(?:it\s+)?with)\s+" + _q("new"), re.I | re.S)),
]


def _clean_sec(s):
    return (s or "").strip().rstrip(".,;:")


def parse(text):
    """The instructions in an amendment's text, in the order they appear: [{"op": words|section|add|delete, "sec", "after",
    "old", "new", "said": the instruction's own words}]. A span already taken by one pattern is not read again."""
    t = " ".join((text or "").split())
    found, taken = [], []
    for op, rx in PATTERNS:
        for m in rx.finditer(t):
            a, b = m.span()
            if any(a < y and x < b for x, y in taken):
                continue
            g = m.groupdict()
            head = t[a:b].split("\"")[0].split("\u201c")[0]                # "Section L, paragraph L.4.2, delete...": L.4.2
            named = [_clean_sec(x.group("sec")) for x in re.finditer(_sec(), head, re.I)]
            if g.get("sec") and named and not g.get("after"):
                g["sec"] = named[-1]
            found.append({"op": op, "sec": _clean_sec(g.get("sec")), "after": _clean_sec(g.get("after")), "old": (g.get("old") or "").strip(),
                          "new": (g.get("new") or "").strip(), "said": t[a:b][:400], "at": a})
            taken.append((a, b))
    found.sort(key=lambda x: x["at"])
    for x in found:
        x.pop("at", None)
    return found


def _norm_sec(s):
    return re.sub(r"\s+", "", (s or "")).rstrip(".").upper()


def in_section(sent_sec, sec, children=True):
    """Does a sentence's section ("L.4.2.1") fall under an instruction's ("L.4.2", or "4.2" without the letter)?"""
    a, b = _norm_sec(sent_sec), _norm_sec(sec)
    if not a or not b:
        return False
    if a == b or (children and (a.startswith(b + ".") or a.startswith(b + "("))):
        return True
    if re.match(r"^\d", b):                         # "4.2" matches "L.4.2"
        tail = re.sub(r"^[A-Z]{1,2}[.-]", "", a)
        return tail == b or (children and (tail.startswith(b + ".") or tail.startswith(b + "(")))
    return False


def _split(text):
    """New wording into sentences (as the reader would cut them)."""
    parts = re.split(r"(?<=[.;:])\s+(?=[A-Z(])", " ".join((text or "").split()))
    return [p for p in parts if p.strip()]


def _sec_key(s):
    """A sort key for a section number: L.5.10 after L.5.9."""
    out = []
    for p in re.split(r"[.\-()]", _norm_sec(s)):
        out.append((0, int(p), "") if p.isdigit() else (1, 0, p))
    return out


def apply(sents, instrs, label="the amendment"):
    """Carry out the instructions on the base document's sentences ([{"s", "t", "x", "l"}] as docversions keeps them).
    Returns (conformed sentences, results): each result {"i", "op", "sec", "status": applied | not found, "n", "why"}."""
    out = [dict(s) for s in sents]
    results = []
    for i, ins in enumerate(instrs):
        op, sec = ins["op"], ins.get("sec", "")
        r = {"i": i, "op": op, "sec": sec, "said": ins.get("said", ""), "status": "not found", "n": 0, "why": ""}
        if op == "words":
            old, new = ins.get("old", ""), ins.get("new", "")
            pool = [k for k, s in enumerate(out) if (not sec or in_section(s.get("s", ""), sec)) and old and old.lower() in s["x"].lower()]
            if not pool and sec:
                r["why"] = (f"“{old}” is not in {sec}" if any(in_section(s.get("s", ""), sec) for s in out)
                            else f"{sec} is not in the document")
            for k in pool:
                out[k]["x"] = re.sub(re.escape(old), lambda _m: new, out[k]["x"], flags=re.I)
                out[k]["by"] = label
            r["n"] = len(pool)
        elif op in ("section", "delete"):
            hit = [k for k, s in enumerate(out) if in_section(s.get("s", ""), sec)]
            if not hit:
                r["why"] = f"{sec} is not in the document"
            else:
                first = hit[0]
                title = out[first].get("t", "")
                keep = [s for k, s in enumerate(out) if k not in set(hit)]
                if op == "section":
                    new = [{"s": sec, "t": title, "x": x, "l": out[first].get("l", ""), "by": label} for x in _split(ins.get("new", ""))]
                    before = sum(1 for k in range(first) if k not in set(hit))
                    keep = keep[:before] + new + keep[before:]
                out = keep
                r["n"] = len(hit)
        elif op == "add":
            new = [{"s": sec, "t": "", "x": x, "l": "", "by": label} for x in _split(ins.get("new", ""))]
            pos = None
            if ins.get("after"):
                hits = [k for k, s in enumerate(out) if in_section(s.get("s", ""), ins["after"])]
                pos = hits[-1] + 1 if hits else None
            if pos is None and sec:                      # after the last sentence whose section comes before it
                key = _sec_key(sec)
                prefix = _norm_sec(sec).split(".")[0]
                cands = [k for k, s in enumerate(out) if s.get("s") and _norm_sec(s["s"]).split(".")[0] == prefix and _sec_key(s["s"]) < key]
                pos = cands[-1] + 1 if cands else None
            if pos is None:
                pos = len(out)
                r["why"] = "placed at the end: the paragraph before it was not found"
            out = out[:pos] + new + out[pos:]
            r["n"] = len(new)
        if r["n"]:
            r["status"] = "applied"
        results.append(r)
    return out, results


def summary(results):
    ok = sum(1 for r in results if r["status"] == "applied")
    return f"{ok} of {len(results)} instruction(s) applied" + (f"; {len(results) - ok} not found" if ok < len(results) else "")


OP_WORDS = {"words": "Change words", "section": "Replace the paragraph", "add": "Add a paragraph", "delete": "Delete the paragraph"}


def describe(ins):
    sec = ins.get("sec") or "everywhere"
    if ins["op"] == "words":
        return f"{sec}: “{ins['old']}” becomes “{ins['new']}”"
    if ins["op"] == "section":
        return f"{sec}: replaced with “{ins['new'][:120]}”"
    if ins["op"] == "add":
        return f"{sec} added" + (f" after {ins['after']}" if ins.get("after") else "") + f": “{ins['new'][:120]}”"
    return f"{sec}: deleted"


# ------------------------------------------------------------------ the conformed version in the library
def instructions_of(lib, amend_version):
    return parse(" ".join(s["x"] for s in lib.text(amend_version)))


def conform(lib, amend_doc, base_doc, pick=None, who=None):
    """Apply an amendment's instructions (all, or those numbered in pick) to the latest version of the base document and
    add the result to the library as the base document's next version, "Conformed (Amendment 1)". A text file of the
    conformed sentences (with what was applied and what was not) is written beside the library and is the version's
    file. Returns (document, version, results), or (None, None, results) when nothing applied."""
    import datetime, os
    av = amend_doc["versions"][-1]
    ins = instructions_of(lib, av)
    if pick is not None:
        ins = [x for i, x in enumerate(ins) if i in set(pick)]
    bv = base_doc["versions"][-1]
    label = f"{amend_doc.get('name', 'the amendment')} ({av.get('label', '')})".strip()
    out, results = apply(lib.text(bv), ins, label)
    if not any(r["status"] == "applied" for r in results):
        return None, None, results
    folder = os.path.join(lib.data_dir, "conformed")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    safe = re.sub(r"[^A-Za-z0-9 _-]+", "", f"{base_doc.get('name', 'Document')} conformed {amend_doc.get('initial') or av.get('label', '')}").strip()
    path = os.path.join(folder, f"{safe} {stamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{base_doc.get('name', '')}: conformed through {label}\r\n")
        f.write(f"Base: {bv.get('label', '')} ({bv.get('file', '')}). Made by Stationkeeper {datetime.datetime.now():%Y-%m-%d %H:%M}.\r\n")
        f.write(summary(results) + "\r\n\r\n")
        for r in results:
            f.write(f"  [{r['status']}] {describe(ins[r['i']])}" + (f" ({r['why']})" if r["why"] else "") + "\r\n")
        f.write("\r\n")
        sec = None
        for s in out:
            if s.get("s") and s["s"] != sec:
                f.write(f"\r\n{s['s']} {s.get('t', '')}".rstrip() + "\r\n")
                sec = s["s"]
            f.write(s["x"] + "\r\n")
    d, v = lib.add(path, out, doc_id=base_doc["id"], label=f"Conformed ({amend_doc.get('initial') or av.get('label', '')})", who=who)
    v["conformed_from"] = av["id"]
    v["instructions"] = [{"status": r["status"], "n": r["n"], "what": describe(ins[r["i"]]), "why": r["why"]} for r in results]
    lib.save()
    return d, v, results
