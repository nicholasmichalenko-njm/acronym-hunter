"""Leftovers check (3.57.0, claude/stationkeeper-direction-decisions-2026-11-05.md): what must not go out in a Word
volume. The setup's reference text (the SK styles Make the setup writes: the RFP's words, PM direction, captures, notes)
and the setup's file properties; hidden text; white text on a light background; comments; tracked changes; and
placeholders (TBD, [insert], XXX). Reads the .docx; changes nothing. Rules only; nothing leaves the PC.

check(path) -> {"items": [{"kind", "where", "text"}], "counts": {kind: n}, "authors": {name: n}}"""
import re, zipfile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SETUP = "Setup reference text"
PROPS = "Setup file property"
HIDDEN = "Hidden text"
WHITE = "White text"
COMMENT = "Comment"
TRACKED = "Tracked change"
PLACE = "Placeholder"
KINDS = (SETUP, PROPS, HIDDEN, WHITE, COMMENT, TRACKED, PLACE)
WHY = {SETUP: "The setup's reference text (the RFP's words, PM direction, notes) left in the volume. Plan > Setup > Strip setup... makes a clean copy.",
       PROPS: "A file property the setup wrote. Strip setup... takes it out (or File > Info > Properties).",
       HIDDEN: "Hidden text prints into a PDF when Print hidden text is on, and Document Inspector shows it to anyone.",
       WHITE: "White text on a light page is invisible, but it is still in the file and the PDF.",
       COMMENT: "A comment still in the file.",
       TRACKED: "A tracked change not accepted or rejected.",
       PLACE: "Placeholder text."}
PLACEHOLDER = re.compile(r"\[(?:insert|tbd|tbr|add|placeholder|customer|company|name|xx+)[^\]]*\]|\bTBD\b|\bTBR\b|\bX{3,}\b|"
                         r"\blorem ipsum\b", re.I)
_SETUP_STYLE = re.compile(r"^SK ?(RFP|Customer|Library|PM|Setup|Capture|Topic)")


def _parse(data):
    from lxml import etree
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)
    return etree.fromstring(data, parser=parser)


def _on(el):
    """A toggle property (w:vanish, w:b) that is set: present and not val=0/false."""
    if el is None:
        return False
    return (el.get(W + "val") or "true").lower() not in ("0", "false", "off")


def _dark(fill):
    fill = (fill or "").strip().lower()
    if len(fill) != 6 or fill in ("auto",):
        return False
    try:
        r, g, b = (int(fill[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return False
    return (0.299 * r + 0.587 * g + 0.114 * b) < 140


def _styles(z):
    """{style id: {"name", "hidden", "white", "based"}}."""
    out = {}
    if "word/styles.xml" not in z.namelist():
        return out
    root = _parse(z.read("word/styles.xml"))
    for s in root.iter(W + "style"):
        sid = s.get(W + "styleId") or ""
        nm = s.find(W + "name")
        rpr = s.find(W + "rPr")
        col = rpr.find(W + "color") if rpr is not None else None
        based = s.find(W + "basedOn")
        out[sid] = {"name": nm.get(W + "val") if nm is not None else sid,
                    "hidden": _on(rpr.find(W + "vanish")) if rpr is not None else False,
                    "white": (col.get(W + "val") or "").upper() == "FFFFFF" if col is not None else False,
                    "based": based.get(W + "val") if based is not None else ""}
    return out


def _style_flag(st, sid, key):
    seen = set()
    while sid and sid in st and sid not in seen:
        seen.add(sid)
        if st[sid][key]:
            return True
        sid = st[sid]["based"]
    return False


def _text(el):
    return "".join(t.text or "" for t in el.iter(W + "t"))


def _short(t, n=90):
    t = " ".join((t or "").split())
    return t if len(t) <= n else t[:n - 3] + "..."


def check(path):
    items, authors = [], {}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        st = _styles(z)
        body = _parse(z.read("word/document.xml")).find(W + "body")
        ncom = len(re.findall(rb"<w:comment ", z.read("word/comments.xml"))) if "word/comments.xml" in names else 0
        custom = z.read("docProps/custom.xml").decode("utf-8", "replace") if "docProps/custom.xml" in names else ""
    for m in re.finditer(r'name="(Stationkeeper[^"]*)"', custom):
        items.append({"kind": PROPS, "where": "File properties", "text": m.group(1)})
    head = "(before the first heading)"
    for p in body.iter(W + "p"):
        ppr = p.find(W + "pPr")
        ps = ppr.find(W + "pStyle") if ppr is not None else None
        sid = ps.get(W + "val") if ps is not None else ""
        sname = st.get(sid, {}).get("name", sid)
        text = _text(p)
        if (re.match(r"(?i)heading ?\d|title$", sname or "") or (ppr is not None and ppr.find(W + "outlineLvl") is not None)) \
                and text.strip():
            head = _short(text, 60)
        if not text.strip():
            continue
        if _SETUP_STYLE.match(sname or "") or _SETUP_STYLE.match(sid or ""):
            items.append({"kind": SETUP, "where": head, "text": f"{sname}: {_short(text)}"})
            continue
        cell = next((a for a in p.iterancestors(W + "tc")), None)
        cfill = ""
        if cell is not None:
            shd = cell.find(f"{W}tcPr/{W}shd")
            cfill = shd.get(W + "fill") if shd is not None else ""
        pshd = ppr.find(W + "shd") if ppr is not None else None
        pfill = pshd.get(W + "fill") if pshd is not None else ""
        p_hidden = _style_flag(st, sid, "hidden")
        p_white = _style_flag(st, sid, "white")
        hid, white = [], []
        for r in p.iter(W + "r"):
            t = _text(r)
            if not t.strip():
                continue
            rpr = r.find(W + "rPr")
            v = rpr.find(W + "vanish") if rpr is not None else None
            if (v is not None and _on(v)) or (v is None and p_hidden):
                hid.append(t)
                continue
            col = rpr.find(W + "color") if rpr is not None else None
            rshd = rpr.find(W + "shd") if rpr is not None else None
            hl = rpr.find(W + "highlight") if rpr is not None else None
            is_white = (col.get(W + "val") or "").upper() == "FFFFFF" if col is not None else p_white
            if is_white and not any(_dark(f) for f in (cfill, pfill, rshd.get(W + "fill") if rshd is not None else "")) \
                    and not (hl is not None and (hl.get(W + "val") or "") not in ("none", "white", "yellow")):
                white.append(t)
        if hid:
            items.append({"kind": HIDDEN, "where": head, "text": _short(" ".join(hid))})
        if white:
            items.append({"kind": WHITE, "where": head, "text": _short(" ".join(white))})
        for m in PLACEHOLDER.finditer(text):
            items.append({"kind": PLACE, "where": head, "text": _short(text[max(0, m.start() - 30):m.end() + 30])})
        for tag in ("ins", "del", "moveFrom", "moveTo"):
            for ch in p.iter(W + tag):
                who = ch.get(W + "author") or "unknown"
                authors[who] = authors.get(who, 0) + 1
                t = _text(ch) or "".join(x.text or "" for x in ch.iter(W + "delText"))
                items.append({"kind": TRACKED, "where": head, "text": f"{who}: {_short(t, 60) or '(formatting)'}"})
        for c in p.iter(W + "commentReference"):
            items.append({"kind": COMMENT, "where": head, "text": f"Comment {c.get(W + 'id')}"})
    nref = sum(1 for i in items if i["kind"] == COMMENT)
    for k in range(max(0, ncom - nref)):                       # comments with no anchor in the body
        items.append({"kind": COMMENT, "where": "(not anchored)", "text": "A comment with no place in the text"})
    counts = {k: sum(1 for i in items if i["kind"] == k) for k in KINDS}
    return {"items": items, "counts": counts, "authors": authors}


def summary(result):
    """One plain line: what is left, or that the file is clean."""
    got = [(k, n) for k, n in result["counts"].items() if n]
    if not got:
        return "Nothing left behind."
    return ", ".join(f"{n} {k.lower()}{'s' if n != 1 and not k.endswith('text') else ''}" for k, n in got)


def export(path, results, effort=""):
    """The leftovers report in Excel: one row per item, each file's counts on a Summary sheet. results: [(name, check)]."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    import filesafety as FS
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Summary"
    ws.append(["File", "Effort"] + list(KINDS))
    for name, r in results:
        ws.append([name, effort] + [r["counts"].get(k, 0) for k in KINDS])
    it = wb.create_sheet("Items")
    it.append(["File", "What", "Under", "Text", "Why it matters"])
    for name, r in results:
        for x in r["items"]:
            it.append([name, x["kind"], x["where"], x["text"], WHY.get(x["kind"], "")])
    for sh in (ws, it):
        for c in sh[1]:
            c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1E3A8A")
        for col in sh.columns:
            sh.column_dimensions[col[0].column_letter].width = 22
    it.column_dimensions["D"].width = 70; it.column_dimensions["E"].width = 60
    for row in it.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.save(path)
    return path
