"""Cross-reference and numbering check (3.4.0) for a Word draft: figure, table and exhibit numbers in order with no
gaps or repeats; every "Figure 7" or "Table 3" the text mentions has a caption; every caption is mentioned somewhere;
pictures and tables with no caption next to them; and Word's own broken references ("Error! Reference source not
found." and "Error! Bookmark not defined.") left in the text. Numbers like 3-2 or 3.2 (chapter, then number) restart
by chapter. Reads the .docx; changes nothing. Rules only."""
import re, zipfile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
KINDS = ("Figure", "Table", "Exhibit")
_CAP = re.compile(r"^\s*(Figure|Table|Exhibit)\s+([A-Z]?\d+(?:[.\-‐-–]\d+)?)\b", re.I)
_REF = re.compile(r"\b(Figures?|Tables?|Exhibits?)\s+([A-Z]?\d+(?:[.\-‐-–]\d+)?(?:\s*(?:,|and|through|to|-)\s*[A-Z]?\d+(?:[.\-]\d+)?)*)", re.I)
_BROKEN = re.compile(r"Error!\s+(Reference source not found|Bookmark not defined|No text of specified style in document|"
                     r"Not a valid bookmark self-reference)\.?", re.I)


def _norm(n):
    return re.sub(r"[‐-–]", "-", n.upper())


def _kind(word):
    w = word.lower().rstrip("s")
    return {"figure": "Figure", "table": "Table", "exhibit": "Exhibit"}.get(w, "")


def blocks(path):
    """The document body in order: [{"type": "p"|"table", "text", "style", "heading", "picture"}]."""
    from lxml import etree
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"), parser=parser)
    body = root.find(f"{W}body")
    out = []
    for el in body if body is not None else []:
        if el.tag == f"{W}p":
            st = el.find(f"{W}pPr/{W}pStyle")
            style = st.get(f"{W}val") if st is not None else ""
            text = "".join(t.text or "" for t in el.iter(f"{W}t"))
            ol = el.find(f"{W}pPr/{W}outlineLvl")
            pic = el.find(f".//{W}drawing") is not None or el.find(f".//{W}pict") is not None
            out.append({"type": "p", "text": " ".join(text.split()), "style": style,
                        "heading": ol is not None or style.lower().startswith("heading"), "picture": pic})
        elif el.tag == f"{W}tbl":
            out.append({"type": "table", "text": " ".join("".join(t.text or "" for t in el.iter(f"{W}t")).split())[:120],
                        "style": "", "heading": False, "picture": False})
    return out


_CAP_PUNCT = re.compile(r"^\s*(Figure|Table|Exhibit)\s+[A-Z]?\d+(?:[.\-\u2010-\u2013]\d+)?\s*(?:[.:\u2013\u2014-]\s|[.:]?$)", re.I)


def _is_caption(b):
    """A caption: the Caption style, or "Figure 3. Title" / "Table 2: Title" (punctuation after the number; "Figure 3
    shows..." is a sentence that mentions it)."""
    if b["type"] != "p" or not _CAP.match(b["text"]):
        return False
    return b["style"].lower().startswith("caption") or bool(_CAP_PUNCT.match(b["text"]))


def _expand(kind, spec):
    """'3, 4 and 6' -> ['3','4','6']; '3 through 5' -> ['3','4','5'] (plain numbers only)."""
    parts = re.split(r"\s*(?:,|and)\s*", spec)
    out = []
    for p in parts:
        m = re.match(r"^([A-Z]?\d+(?:[.\-]\d+)?)\s*(?:through|to|-)\s*([A-Z]?\d+(?:[.\-]\d+)?)$", p.strip(), re.I)
        if m and m.group(1).isdigit() and m.group(2).isdigit() and int(m.group(2)) - int(m.group(1)) < 50:
            out += [str(k) for k in range(int(m.group(1)), int(m.group(2)) + 1)]
        elif p.strip():
            out.append(_norm(p.strip()))
    return out


def check(path):
    """{"captions": {kind: [numbers in order]}, "problems": [{"kind", "where", "text"}]} for one draft."""
    bl = blocks(path)
    caps = {k: [] for k in KINDS}
    cap_at = set()
    heading = ""
    problems = []
    for i, b in enumerate(bl):
        if b["heading"] and b["text"]:
            heading = b["text"]
        if _is_caption(b):
            m = _CAP.match(b["text"])
            caps[m.group(1).capitalize()].append((_norm(m.group(2)), heading, b["text"][:90]))
            cap_at.add(i)
        for m in _BROKEN.finditer(b["text"]):
            problems.append({"kind": "Broken reference", "where": heading, "text": f"“{m.group(0)}”: a cross-reference whose "
                             "target was deleted or renamed. Fix it, then update fields (Ctrl+A, F9)."})
    # numbering in order
    for kind, lst in caps.items():
        seen = {}
        prev = None
        for num, where, text in lst:
            if num in seen:
                problems.append({"kind": f"{kind} number repeated", "where": where, "text": f"{kind} {num} appears twice: {text}"})
            seen[num] = True
            if prev is not None:
                a, b_ = _split(prev), _split(num)
                if a and b_ and not _follows(a, b_):
                    problems.append({"kind": f"{kind} out of order", "where": where, "text": f"{kind} {num} follows {kind} {prev}"})
            prev = num
    # mentions point at captions, and captions are mentioned
    have = {k: {n for n, _w, _t in v} for k, v in caps.items()}
    mentioned = {k: set() for k in KINDS}
    heading = ""
    for i, b in enumerate(bl):
        if b["heading"] and b["text"]:
            heading = b["text"]
        if i in cap_at or b["type"] != "p":
            continue
        for m in _REF.finditer(b["text"]):
            kind = _kind(m.group(1))
            for n in _expand(kind, m.group(2)):
                mentioned[kind].add(n)
                if n not in have[kind]:
                    problems.append({"kind": f"{kind} not found", "where": heading,
                                     "text": f"the text mentions {kind} {n}, but no caption has that number: “{b['text'][:120]}”"})
    for kind, lst in caps.items():
        for num, where, text in lst:
            if num not in mentioned[kind]:
                problems.append({"kind": f"{kind} never mentioned", "where": where, "text": f"{kind} {num} is not referred to in the text: {text}"})
    # pictures and tables with no caption next to them (each caption belongs to one: below it first, then above)
    heading = ""
    used = set()
    for i, b in enumerate(bl):
        if b["heading"] and b["text"]:
            heading = b["text"]
        if b["picture"] or b["type"] == "table":
            if b["type"] == "p" and i in cap_at:
                used.add(i)
                continue
            fits = ("table", "exhibit") if b["type"] == "table" else ("figure", "exhibit")
            mine = next((k for k in (i + 1, i - 1, i + 2, i - 2) if k in cap_at and k not in used
                         and _CAP.match(bl[k]["text"]).group(1).lower() in fits
                         and not any(bl[j]["heading"] for j in range(min(i, k) + 1, max(i, k)))), None)
            if mine is not None:
                used.add(mine)
            else:
                what = "picture" if b["picture"] else "table"
                problems.append({"kind": f"{what.capitalize()} with no caption", "where": heading,
                                 "text": f"a {what} with no Figure or Table caption beside it" + (f": “{b['text'][:80]}”" if b["text"] else "")})
    return {"captions": {k: [n for n, _w, _t in v] for k, v in caps.items()}, "problems": problems}


def _split(num):
    m = re.match(r"^([A-Z]?)(\d+)(?:[.\-](\d+))?$", num)
    if not m:
        return None
    return (m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else None)


def _follows(a, b):
    """True when b is the next number after a: 4 after 3; 3-2 after 3-1; 4-1 after 3-x (a new chapter)."""
    if a[0] != b[0]:
        return True                              # an appendix letter: a new series
    if a[2] is None and b[2] is None:
        return b[1] == a[1] + 1
    if a[2] is not None and b[2] is not None:
        return (b[1] == a[1] and b[2] == a[2] + 1) or (b[1] > a[1] and b[2] == 1)
    return True


def export(path, results, effort=""):
    """results: [(draft name, check result)]."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Cross-references"
    ws.append(["Draft", "Problem", "Section", "Detail"])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1E3A8A")
    for name, r in results:
        for p in r["problems"]:
            ws.append([name, p["kind"], p["where"], p["text"]])
    for i, w in enumerate([30, 26, 30, 90], 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    if effort:
        wb.properties.title = f"{effort} cross-reference check"
    wb.save(path)
    return path
