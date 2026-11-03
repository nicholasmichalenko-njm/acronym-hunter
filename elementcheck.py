"""Final Checks on the response elements (3.32.0): for each volume, the elements the RFP names that the volume lacks,
elements out of the order the RFP lists them in, and elements outside their part (a Table of Contents in the response).

The RFP's words are its sentences in the matrix (every one but those dropped). A sentence placed in a section speaks
for that section's volume; one that names a volume speaks for it; any other speaks for every volume. A volume has an
element when the structure holds it (Add elements) or a section of that name (an Executive Summary heading). The order
comes from a sentence that names two or more elements ("a cover page, a table of contents and a list of figures"). Rules
only; nothing leaves the PC."""
import re

PATTERNS = {
    "cover": r"\bcover (?:page|sheet)s?\b",
    "title": r"\btitle pages?\b",
    "letter": r"\b(?:cover|transmittal) letters?\b",
    "toc": r"\btables? of contents\b",
    "lof": r"\blists? of (?:figures|illustrations|exhibits)\b",
    "lot": r"\blists? of tables\b",
    "loa": r"\blists? of (?:appendices|attachments)\b",
    "acr": r"\b(?:lists? of acronyms|acronyms?(?: and abbreviations)? (?:lists?|tables?)|glossary|acronyms and abbreviations)\b",
    "uom": r"\b(?:(?:lists?|tables?) of units(?: of measure(?:ment)?)?|units of measure(?:ment)? (?:lists?|tables?))\b",
    "matrix": r"\b(?:compliance|cross[- ]reference|traceability) matri(?:x|ces)\b",
    "exec": r"\bexecutive summar(?:y|ies)\b",
}
CHECKS = ("Missing", "Order", "Part")
IN_PART = {"cover": "the cover", "title": "the title page", "front": "front matter", "body": "the response",
           "appendix": "the appendices", "back": "the back cover"}


def patterns(data):
    """{element id: compiled pattern}: the built-in ones, and each team element by its name (two words or more)."""
    out = {}
    for e in (data or {}).get("elements") or []:
        p = PATTERNS.get(e["id"])
        if p is None and not e.get("builtin") and len(str(e.get("name", "")).split()) >= 2:
            p = r"\b" + r"\s+".join(re.escape(w) for w in e["name"].split()) + r"\b"
        if p:
            out[e["id"]] = re.compile(p, re.I)
    return out


def _vol_words(M, head):
    import outline_ops as O
    o = M.outline[O.index_of(M, head)] if O.index_of(M, head) >= 0 else {}
    out = []
    t = str(o.get("title") or "").strip()
    if len(t) >= 4:
        out.append(re.compile(r"\b" + re.escape(t) + r"\b", re.I))
    n = str(o.get("num") or "").strip()
    if n.lower().startswith("vol"):
        out.append(re.compile(r"\b" + re.escape(n) + r"\b", re.I))
    return out


def where(it):
    loc = str(it.get("loc") or "")
    return (it.get("id", "") + (f" ({loc})" if loc else "")).strip()


def check(M, data):
    """[{"volume", "check", "element", "detail", "where"}]: Missing, Order and Part, volume by volume."""
    import compliance as C
    import setupdoc as SD
    import structparts as SP
    pats = patterns(data)
    els = {e["id"]: e for e in (data or {}).get("elements") or []}
    groups = SD.volume_groups(M)
    mode, _name, heads = SD.volumes_of(M)
    several = mode == "several" and bool(heads)
    vol_of = SD.volume_of_sections(M)
    placed = {i: lab for lab, ids in SD.placed_in(M).items() for i in ids}
    vwords = {g: _vol_words(M, g) for g, _e in groups} if several else {}
    named = {}                                          # (volume, element id) -> the first sentence naming it
    pairs = {}                                          # (volume, a, b) -> sentence: a listed before b
    for it in getattr(M, "items", []) or []:
        if it.get("decision") == "Drop" or it.get("type") == "Heading":
            continue
        text = str(it.get("text") or "")
        hits = sorted((m.start(), eid) for eid, p in pats.items() for m in [p.search(text)] if m)
        if not hits:
            continue
        if not several:
            vols = [g for g, _e in groups]
        elif it.get("id") in placed and vol_of.get(placed[it["id"]]):
            vols = [vol_of[placed[it["id"]]]]
        else:
            vols = [g for g, ws in vwords.items() if any(w.search(text) for w in ws)] or [g for g, _e in groups]
        for v in vols:
            for _pos, eid in hits:
                named.setdefault((v, eid), it)
            for i in range(len(hits)):
                for j in range(i + 1, len(hits)):
                    if hits[i][1] != hits[j][1]:
                        pairs.setdefault((v, hits[i][1], hits[j][1]), it)
    out = []
    for g, entries in groups:
        have, order = {}, []
        for o in entries:
            lab = C.outline_label(o)
            eid = o.get("element") or ""
            if not eid:
                title = str(o.get("title") or lab)
                eid = next((k for k, p in pats.items() if p.fullmatch(title.strip()) or title.strip().casefold() == els.get(k, {}).get("name", "").casefold()), "")
            if eid and eid not in have:
                have[eid] = o
                order.append(eid)
            if o.get("element") and o["element"] in els:
                want = els[o["element"]].get("part")
                part = SP.part_of(o)
                if want and part != want and not (want in ("cover", "title") and part in ("cover", "title", "front")):
                    out.append({"volume": g, "check": "Part", "element": els[o["element"]]["name"],
                                "detail": f"It is in {IN_PART.get(part, part)}; it belongs in {IN_PART.get(want, want)}.",
                                "where": lab})
        for (v, eid), it in named.items():
            if v == g and eid not in have and eid in els:
                out.append({"volume": g, "check": "Missing", "element": els[eid]["name"],
                            "detail": "The RFP names it; this volume does not have it. Add elements puts it in.",
                            "where": where(it)})
        rank = {e: k for k, e in enumerate(order)}
        for (v, a, b), it in pairs.items():
            if v == g and a in rank and b in rank and rank[a] > rank[b] and a in els and b in els:
                out.append({"volume": g, "check": "Order", "element": els[a]["name"],
                            "detail": f"The RFP lists {els[a]['name']} before {els[b]['name']}; this volume has it after.",
                            "where": where(it)})
    return out


def export(path, rows, effort=""):
    """The check as an Excel file: one row a finding."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "Elements"
    ws.append([f"Response elements check{(': ' + effort) if effort else ''}"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append(["Volume", "Check", "Element", "What", "Where (the RFP or the structure)"])
    for c in ws[2]:
        c.font = Font(bold=True)
    for r in rows:
        ws.append([r["volume"], r["check"], r["element"], r["detail"], r["where"]])
    for col, w in zip("ABCDE", (28, 10, 28, 70, 40)):
        ws.column_dimensions[col].width = w
    wb.save(path)
    return path
