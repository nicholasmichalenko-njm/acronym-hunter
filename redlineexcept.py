"""The exceptions table from a redline's tracked changes (4.8.0; claude/stationkeeper-redline-plan-4.6.md, step 3;
decision 4). Every tracked change becomes a row: the customer's number (the number of the nearest heading above), the
original text, our text, the kind (Inserted, Deleted, Replaced: a deletion followed at once by an insertion), the
author, the date, and the comment anchored on it. It exports to Excel and to Word (a table). Word has no such report.
Rules only (No AI); nothing leaves the PC."""
import re, zipfile

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
COLS = ("Number", "Original text", "Our text", "Kind", "Author", "Date", "Comment", "Heading")
_NUM = re.compile(r"^\s*((?:[A-Z]\.)?\d+(?:\.\d+)*\.?|[A-Z]\.(?:\d+(?:\.\d+)*)?|(?:SECTION|Section|PART|Part)\s+[A-Z0-9]+)")


def number_of(heading):
    m = _NUM.match(heading or "")
    return m.group(1).rstrip(".") if m else ""


def _comments(z):
    try:
        root = etree.fromstring(z.read("word/comments.xml"))
    except KeyError:
        return {}
    return {c.get(W + "id"): "".join(t.text or "" for t in c.iter(W + "t")).strip() for c in root.iter(W + "comment")}


def rows(path):
    """[{column: value}] for every tracked change in the Word file, in document order."""
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"))
        comments = _comments(z)
    out, heading = [], ""
    for p in root.iter(W + "p"):
        sty = p.find(f"{W}pPr/{W}pStyle")
        sid = (sty.get(W + "val") if sty is not None else "") or ""
        text_now = "".join(t.text or "" for t in p.iter(W + "t") if not any(a.tag == W + "del" for a in t.iterancestors()))
        open_c = [c.get(W + "id") for c in p.iter(W + "commentRangeStart")] + [c.get(W + "id") for c in p.iter(W + "commentReference")]
        note = "; ".join(dict.fromkeys(comments.get(i, "") for i in open_c if comments.get(i)))
        pend = None
        for el in p.iter(W + "ins", W + "del"):
            if el.tag == W + "del":
                txt = "".join(x.text or "" for x in el.iter(W + "delText"))
            else:
                txt = "".join(x.text or "" for x in el.iter(W + "t"))
            if not txt.strip():
                continue
            row = {"Number": number_of(heading), "Heading": heading, "Author": el.get(W + "author", ""),
                   "Date": (el.get(W + "date", "") or "")[:10], "Comment": note}
            if el.tag == W + "del":
                if pend is not None:
                    out.append(pend)
                pend = dict(row, **{"Original text": txt, "Our text": "", "Kind": "Deleted"})
            elif pend is not None and pend["Kind"] == "Deleted":
                pend.update({"Our text": txt, "Kind": "Replaced"})
                out.append(pend); pend = None
            else:
                out.append(dict(row, **{"Original text": "", "Our text": txt, "Kind": "Inserted"}))
        if pend is not None:
            out.append(pend)
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
