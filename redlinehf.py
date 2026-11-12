"""4.22.0: the headers and footers of a PDF, for Prepare for redline's Word copy (the copy left them out).

The lines pagesent reads as page furniture (the running title, the solicitation's number, the page number) become
Word's own header and footer for the pages that carry them:
- the lines on one baseline are one paragraph, what sits at the left, the middle and the right kept there with tabs;
- the page's number is Word's PAGE field, so it counts on as the text flows, and "of 12" is NUMPAGES when 12 is the
  number of pages;
- a rule drawn under the header or over the footer is the paragraph's border; a picture that repeats in the margin
  (a logo) sits at its place in the header or footer;
- a first page without them (a cover) keeps none.
Rules only (No AI); nothing leaves the PC."""
import re

import redlinedocx as RD

TW = 20
_NUM = re.compile(r"\d+")


def _x(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _pieces(ln, words):
    """A furniture line as the pieces that sit apart on it: [(box, text)]. The reader keeps "Solicitation 7 ... Section
    L" as one line; its words (with their boxes) show the wide gap between what is at the left and what is at the right."""
    b = ln["box"]
    size = ln.get("size") or max(6.0, b[3] - b[1])
    mine = sorted((w for w in words if b[0] - 1 <= (w["box"][0] + w["box"][2]) / 2 <= b[2] + 1
                   and b[1] - 1 <= (w["box"][1] + w["box"][3]) / 2 <= b[3] + 1), key=lambda w: w["box"][0])
    if len(mine) < 2:
        return [(b, ln["text"].strip())]
    out, cur = [], [mine[0]]
    for w in mine[1:]:
        if w["box"][0] - cur[-1]["box"][2] > 3 * size:
            out.append(cur); cur = [w]
        else:
            cur.append(w)
    out.append(cur)
    if len(out) < 2:
        return [(b, ln["text"].strip())]
    return [((g[0]["box"][0], b[1], g[-1]["box"][2], b[3]), " ".join(w["text"] for w in g).strip()) for g in out]


def _rows(page, mine, lo, hi, words=()):
    """[{"top", "bottom", "size", "a", "left", "center", "right"}] for the furniture lines of one page (indices mine)."""
    rows = []
    todo = []
    for li in sorted(mine, key=lambda i: (page["lines"][i]["box"][1], page["lines"][i]["box"][0])):
        for box, text in _pieces(page["lines"][li], words):
            todo.append((dict(page["lines"][li], box=box, text=text)))
    for ln in todo:
        b = ln["box"]
        lh = max(6.0, b[3] - b[1])
        row = next((r for r in rows if abs(r["top"] - b[1]) < 0.6 * lh), None)
        if row is None:
            row = {"top": b[1], "bottom": b[3], "size": ln.get("size") or 0, "a": ln.get("a", 0), "left": "", "center": "", "right": "",
                   "_x": b[0]}
            rows.append(row)
        row["bottom"] = max(row["bottom"], b[3])
        if b[0] < row["_x"]:
            row["_x"], row["a"] = b[0], ln.get("a", 0)
        mid, width = (lo + hi) / 2, max(1.0, hi - lo)
        c = (b[0] + b[2]) / 2
        if abs(c - mid) < 0.06 * width and (b[2] - b[0]) < 0.8 * width:
            where = "center"
        elif b[2] > hi - 0.15 * width and b[0] > mid:
            where = "right"
        else:
            where = "left"
        row[where] = (row[where] + " " + ln["text"].strip()).strip()
    for r in rows:
        r.pop("_x", None)
    return rows


def _fields(text, other, step, total):
    """The parts of a furniture text: [("text", s) | ("page", n) | ("pages", n)]. other: the same place's text on a page
    step pages on (or None); total: the PDF's pages."""
    nums = list(_NUM.finditer(text))
    onum = [int(m.group()) for m in _NUM.finditer(other)] if other is not None else None
    same = other is not None and _NUM.sub("#", other) == _NUM.sub("#", text) and len(onum) == len(nums)
    page_at, pages_at = None, None
    for i, m in enumerate(nums):
        n = int(m.group())
        if same and onum[i] - n == step and page_at is None:
            page_at = i
        elif n == total and re.search(r"\bof\s*$", text[:m.start()], re.I) and (not same or onum[i] == n):
            pages_at = i
    if page_at is None and other is None:
        m = re.match(r"^\s*(?:-\s*)?(?:page\s+)?(\d{1,4})(?:\s*-)?(?:\s+of\s+\d{1,4})?\s*$", text, re.I)
        if m:
            page_at = 0
    out, pos = [], 0
    for i, m in enumerate(nums):
        if i not in (page_at, pages_at):
            continue
        if m.start() > pos:
            out.append(("text", text[pos:m.start()]))
        out.append(("page" if i == page_at else "pages", int(m.group())))
        pos = m.end()
    if pos < len(text):
        out.append(("text", text[pos:]))
    return out


def _run(kind, value, rpr):
    if kind == "text":
        return f'<w:r>{rpr}<w:t xml:space="preserve">{_x(value)}</w:t></w:r>' if value else ""
    code = " PAGE " if kind == "page" else " NUMPAGES "
    return (f'<w:r>{rpr}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{rpr}<w:instrText xml:space="preserve">{code}</w:instrText></w:r>'
            f'<w:r>{rpr}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{rpr}<w:t>{value}</w:t></w:r>'
            f'<w:r>{rpr}<w:fldChar w:fldCharType="end"/></w:r>')


def _para(row, parts, width, st, border="", lead=""):
    rpr = RD.rpr(dict(st or {}, size=row["size"] or None))
    tabs = (f'<w:tabs><w:tab w:val="center" w:pos="{int(width * TW / 2)}"/><w:tab w:val="right" w:pos="{int(width * TW)}"/></w:tabs>')
    runs = ""
    for i, key in enumerate(("left", "center", "right")):
        if i and (parts["center"] or parts["right"]) and (key == "center" or parts["right"]):
            runs += f"<w:r>{rpr}<w:tab/></w:r>"
        runs += "".join(_run(k, v, rpr) for k, v in parts[key])
    bd = f"<w:pBdr>{border}</w:pBdr>" if border else ""
    return f'<w:p><w:pPr>{bd}{tabs}<w:spacing w:before="0" w:after="0"/></w:pPr>{lead}{runs}</w:p>'


def _sign(rows):
    return sorted(_NUM.sub("#", " ".join(r[k] for k in ("left", "center", "right"))).strip().lower() for r in rows)


def plan(doc, running, groups, styles=None, words_of=None):
    """Adds to each group of pages that has furniture: "hf": {"header": [paragraph xml], "footer": [...], "pictures":
    {"header": [box], "footer": [box]}, "page": the page index they were read from, "title_pg", "start", "header_at",
    "footer_at"}. running: {(page index, line index)}; styles: redlinelayout.styles' result for the rows' first letters,
    or a function (page index, character index) -> style."""
    total = len(doc.get("pages") or [])
    for g in groups:
        first, last = g["pages"][0] - 1, g["pages"][1] - 1
        by = {}
        for pi, li in running:
            if first <= pi <= last:
                by.setdefault(pi, []).append(li)
        furn = g.get("furniture") or {}
        pages = sorted(set(by) | set(furn))
        if not pages:
            continue
        later = [p for p in pages if p != first] or pages
        rep = max(later, key=lambda p: (len(by.get(p, ())) + len(furn.get(p, ())), -p))
        lo, hi = g["margins"][3], g["w"] - g["margins"][1]
        h = doc["pages"][rep].get("h") or g["h"]
        wo = words_of or (lambda _pi: ())
        rows = _rows(doc["pages"][rep], by.get(rep, ()), lo, hi, wo(rep))
        step = 1 if rep + 1 <= last and rep + 1 in by else (-1 if rep - 1 >= first and rep - 1 in by else 0)
        orow = _rows(doc["pages"][rep + step], by.get(rep + step, ()), lo, hi, wo(rep + step)) if step else []
        hf = {"header": [], "footer": [], "pictures": {"header": [], "footer": []}, "page": rep, "title_pg": False,
              "start": None, "header_at": None, "footer_at": None}
        rules = (g.get("rules") or {}).get(rep, [])
        for r in rows:
            zone = "header" if (r["top"] + r["bottom"]) / 2 < h / 2 else "footer"
            match = next((o for o in orow if abs(o["top"] - r["top"]) < 3), None)
            parts = {}
            for key in ("left", "center", "right"):
                parts[key] = _fields(r[key], match[key] if match else None, step, total) if r[key] else []
                for kind, val in parts[key]:
                    if kind == "page" and hf["start"] is None:
                        hf["start"] = val - (rep - first)
            st = styles(rep, r["a"]) if callable(styles) else (styles or {}).get((rep, r["a"]))
            border = ""
            for b in rules:
                wide = (b[2] - b[0]) > 0.5 * (hi - lo)
                if zone == "header" and wide and 0 <= b[1] - r["bottom"] < 12:
                    border = '<w:bottom w:val="single" w:sz="4" w:space="1" w:color="auto"/>'
                elif zone == "footer" and wide and 0 <= r["top"] - b[3] < 12:
                    border = '<w:top w:val="single" w:sz="4" w:space="1" w:color="auto"/>'
            hf[zone].append((r, parts, st, border))
            if zone == "header" and hf["header_at"] is None:
                hf["header_at"] = max(0.0, r["top"])
            if zone == "footer":
                hf["footer_at"] = max(0.0, h - r["bottom"])
        for f in furn.get(rep, ()):
            hf["pictures"][f["where"]].append(list(f["box"]))
        # a first page that does not carry them (a cover) keeps none
        hf["title_pg"] = first != rep and _sign(_rows(doc["pages"][first], by.get(first, ()), lo, hi, wo(first))) != _sign(rows)
        if not (hf["header"] or hf["footer"] or hf["pictures"]["header"] or hf["pictures"]["footer"]):
            continue
        hf["width"] = hi - lo
        g["hf"] = hf
    return groups


def parts(g, zone, lead=""):
    """The header's or footer's paragraphs as XML; lead: the runs of its pictures."""
    hf = g.get("hf") or {}
    rows = hf.get(zone) or []
    out = ""
    for i, (r, pts, st, border) in enumerate(rows):
        out += _para(r, pts, hf["width"], st, border, lead if i == 0 else "")
    if not rows and lead:
        out = f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>{lead}</w:p>'
    return out or "<w:p/>"
