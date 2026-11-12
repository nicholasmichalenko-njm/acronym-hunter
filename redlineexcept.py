"""The exceptions table from a redline's tracked changes (4.8.0; claude/stationkeeper-redline-plan-4.6.md, step 3;
decision 4). Every tracked change becomes a row: the customer's number (the number of the nearest heading above), the
original text, our text, the kind (Inserted, Deleted, Replaced: a deletion followed at once by an insertion; Comment: a
comment on no change, 4.16.0), the author, the date, and the comment anchored on it (its replies after it). It exports to Excel and to Word (a table). Word has no such report.
Rules only (No AI); nothing leaves the PC."""
import re, zipfile

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
COLS = ("Number", "Original text", "Our text", "Kind", "Author", "Date", "Comment", "Heading")
_NUM = re.compile(r"^\s*((?:[A-Z]\.)?\d+(?:\.\d+)*\.?|[A-Z]\.(?:\d+(?:\.\d+)*)?|(?:SECTION|Section|PART|Part)\s+[A-Z0-9]+)")


def number_of(heading):
    m = _NUM.match(heading or "")
    return m.group(1).rstrip(".") if m else ""


def _comments(path):
    """{id: {"text", "author", "date", "parent", "range"}} with each reply folded into its comment's text."""
    import redlinemarks as RM
    try:
        cs = RM.read_back(path)["comments"]
    except (KeyError, OSError, etree.XMLSyntaxError):
        return {}
    by = {c["id"]: dict(c, text=(c["text"] or "").strip()) for c in cs}
    for c in cs:
        if c["parent"] in by and c["text"].strip():
            by[c["parent"]]["text"] += f"; Reply from {c['author']}: {c['text'].strip()}"
    return by


def _skip(el):
    """A comment's marks and its reference run sit between a deletion and its insertion without parting them."""
    if el.tag in (W + "commentRangeStart", W + "commentRangeEnd", W + "bookmarkStart", W + "bookmarkEnd"):
        return True
    return el.tag == W + "r" and el.find(W + "commentReference") is not None and el.find(W + "t") is None


def rows(path):
    """[{column: value}] for every tracked change in the Word file, in document order. A deletion followed at once by an
    insertion is one Replaced row. The comments open on a change are its Comment; a comment on no change is a row of
    its own, Kind Comment, with the words it is on (4.16.0: a PDF's comments brought in by Prepare are rows too)."""
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    comments = _comments(path)
    out, heading, open_c, used = [], "", [], set()
    ranged = {el.get(W + "id") for el in root.iter(W + "commentRangeStart")}
    for p in root.iter(W + "p"):
        sty = p.find(f"{W}pPr/{W}pStyle")
        sid = (sty.get(W + "val") if sty is not None else "") or ""
        text_now = "".join(t.text or "" for t in p.iter(W + "t") if not any(a.tag == W + "del" for a in t.iterancestors()))
        refs = [c.get(W + "id") for c in p.iter(W + "commentReference") if c.get(W + "id") not in ranged]
        later = []                                       # comment rows that come after a deletion still waiting
        here = text_now.strip() if re.match(r"(?i)heading\s*\d", sid) and text_now.strip() else heading
        pend = None
        for el in p.iter(W + "commentRangeStart", W + "commentRangeEnd", W + "ins", W + "del"):
            cid = el.get(W + "id")
            if el.tag == W + "commentRangeStart":
                open_c.append(cid); continue
            if el.tag == W + "commentRangeEnd":
                if cid in open_c:
                    open_c.remove(cid)
                c = comments.get(cid)
                if c is not None and cid not in used and not c.get("parent"):
                    used.add(cid)
                    (later if pend is not None else out).append({"Number": number_of(here), "Heading": here, "Author": c.get("author") or "",
                                "Date": (c.get("date") or "")[:10], "Comment": c["text"], "Original text": c.get("range") or "",
                                "Our text": "", "Kind": "Comment"})
                continue
            if el.tag == W + "del":
                txt = "".join(x.text or "" for x in el.iter(W + "delText"))
            else:
                txt = "".join(x.text or "" for x in el.iter(W + "t"))
            if not txt.strip():
                continue
            on = [i for i in dict.fromkeys(open_c + refs) if comments.get(i, {}).get("text")]
            used.update(on)
            row = {"Number": number_of(here), "Heading": here, "Author": el.get(W + "author", ""),
                   "Date": (el.get(W + "date", "") or "")[:10], "Comment": "; ".join(comments[i]["text"] for i in on)}
            if el.tag == W + "del":
                if pend is not None:
                    out.append(pend[0]); out.extend(later); later.clear()
                pend = (dict(row, **{"Original text": txt, "Our text": "", "Kind": "Deleted"}), el)
                continue
            nxt = pend[1].getnext() if pend is not None else None
            while nxt is not None and _skip(nxt):
                nxt = nxt.getnext()
            if pend is not None and nxt is el:
                pend[0].update({"Our text": txt, "Kind": "Replaced"})
                if row["Comment"] and row["Comment"] not in pend[0]["Comment"]:
                    pend[0]["Comment"] = "; ".join(x for x in (pend[0]["Comment"], row["Comment"]) if x)
                out.append(pend[0]); out.extend(later); later.clear(); pend = None
            else:
                if pend is not None:
                    out.append(pend[0]); out.extend(later); later.clear(); pend = None
                out.append(dict(row, **{"Original text": "", "Our text": txt, "Kind": "Inserted"}))
        if pend is not None:
            out.append(pend[0])
        out.extend(later)
        if re.match(r"(?i)heading\s*\d", sid) and text_now.strip():
            heading = text_now.strip()
    return out


def to_excel(rws, path):
    import openpyxl
    from openpyxl.styles import Alignment, Font
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Exceptions"
    ws.append(list(COLS))
    for c in ws[1]:
        c.font = Font(bold=True)
    for r in rws:
        ws.append([r.get(c, "") for c in COLS])
    for col, wdt in zip("ABCDEFGH", (12, 50, 50, 11, 18, 12, 40, 30)):
        ws.column_dimensions[col].width = wdt
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    wb.save(path)
    return path


def to_word(rws, path, title="Exceptions"):
    import docxw
    d = docxw.Doc()
    d.landscape = True
    d.heading(title, 1)
    d.table(list(COLS[:7]), [[r.get(c, "") for c in COLS[:7]] for r in rws], [1100, 3300, 3300, 1000, 1400, 1000, 2800])
    d.save(path)
    return path
