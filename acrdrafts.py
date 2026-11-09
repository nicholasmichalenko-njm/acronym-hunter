"""Acronyms in our drafts (3.88.0; decision 7, Nicholas 2026-11-08 14:57): a volume draft read against the effort's
list, without changing it.

first_use(path, defs) -> [{"term", "status", "where", "change"}] per term the draft uses, in reading order:
    "right"            spelled out at first use ("Ground Support Equipment (GSE)")
    "before"           used before it is spelled out: the change spells it out at first use
    "again"            spelled out again after first use: the change keeps the acronym and drops the spelled-out words
    A volume restarts first use (the effort's rule): each draft is its own volume.
table_check(path, listed_terms) -> {"table": {term: definition}, "listed_not_used": [...], "used_not_listed": [...]}:
    the volume's own Acronyms table (a table whose rows look like "ACR | definition") against what its text uses.
Table of contents lines and the Acronyms table itself never count as a use. Rules only; the files are only read."""
import re, zipfile

from lxml import etree

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % NS_W
_ACR = re.compile(r"^[A-Z][A-Za-z0-9&/\-]{1,11}$")


def _parser():
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)


def _ptext(p):
    return "".join(t.text or "" for t in p.iter(W + "t"))


def _style(p):
    ps = p.find(f"{W}pPr/{W}pStyle")
    return (ps.get(W + "val") if ps is not None else "") or ""


def _read(path):
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"), parser=_parser())
    body = root.find(W + "body")
    tables, acr_tables = [], set()
    for t in body.iter(W + "tbl"):
        rows = [[" ".join(_ptext(p) for p in tc.iter(W + "p")).strip() for tc in tr.findall(W + "tc")] for tr in t.findall(W + "tr")]
        tables.append((t, rows))
        data = [r for r in rows[1:] if len(r) >= 2] if rows else []
        hits = [r for r in data if _ACR.match(r[0]) and r[1]]
        if data and len(hits) >= max(2, 0.6 * len(data)):
            acr_tables.add(id(t))
    paras = []
    for i, p in enumerate(body.iter(W + "p")):
        anc, in_acr = p.getparent(), False
        while anc is not None and anc is not body:
            if anc.tag == W + "tbl" and id(anc) in acr_tables:
                in_acr = True
                break
            anc = anc.getparent()
        if in_acr or _style(p).upper().startswith("TOC"):
            continue
        txt = _ptext(p)
        if txt.strip():
            paras.append((len(paras) + 1, txt))
    table = {}
    for t, rows in tables:
        if id(t) in acr_tables:
            for r in rows[1:]:
                if len(r) >= 2 and _ACR.match(r[0]):
                    table.setdefault(r[0], r[1])
    return paras, table


def _uses(term, text):
    return [m.start() for m in re.finditer(r"(?<![A-Za-z0-9])" + re.escape(term) + r"s?(?![A-Za-z0-9])", text)]


def _spelled(term, definition, text):
    """Where the text spells it out: "Definition (TERM)" or "TERM (Definition)". Returns [(start, end)]."""
    d = re.escape(definition).replace(r"\ ", r"\s+")
    pat = rf"{d}\s*\(\s*{re.escape(term)}s?\s*\)|{re.escape(term)}s?\s*\(\s*{d}\s*\)"
    return [(m.start(), m.end()) for m in re.finditer(pat, text, re.I)]


def first_use(path, defs):
    paras, _table = _read(path)
    out = []
    for term, definition in defs.items():
        if not term or not definition:
            continue
        events = []                                       # (para, pos, spelled)
        for n, text in paras:
            sp = _spelled(term, definition, text)
            covered = [(a, b) for a, b in sp]
            for a, _b in sp:
                events.append((n, a, True))
            for u in _uses(term, text):
                if not any(a <= u < b for a, b in covered):
                    events.append((n, u, False))
        if not events:
            continue
        events.sort()
        first = events[0]
        where = f"paragraph {first[0]}"
        if first[2]:
            out.append({"term": term, "status": "right", "where": where, "change": ""})
        else:
            out.append({"term": term, "status": "before", "where": where,
                        "change": f"Spell it out here: {definition} ({term})"})
        for n, _pos, spelled in events[1:]:
            if spelled:
                out.append({"term": term, "status": "again", "where": f"paragraph {n}",
                            "change": f"Keep {term}; drop the spelled-out words"})
    order = {e["term"]: i for i, e in enumerate(out)}
    return sorted(out, key=lambda e: (order[e["term"]], {"right": 0, "before": 0, "again": 1}[e["status"]]))


def table_check(path, listed_terms):
    paras, table = _read(path)
    text = "\n".join(t for _n, t in paras)
    used = {t for t in listed_terms if _uses(t, text)}
    return {"table": table,
            "listed_not_used": sorted(t for t in table if not _uses(t, text)),
            "used_not_listed": sorted(t for t in used if t not in table)}
