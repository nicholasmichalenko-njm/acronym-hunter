"""The page layout Redline's copy follows (4.13.0; claude/stationkeeper-pdf-fidelity-plan-4.13.html, steps 2 and 3).

- tables(pdf, doc, skip): every table of the PDF, read first from the borders each page draws (ruledtables) and then,
  among the lines left, from text that lines up (redlinetables, 4.11.0). Each table: {"page", "lines", "grid"}, the grid
  {"rows": [[{"text", "cs", "rs", "fill", "bold"}]], "widths" (points), "header" (rows), "borders" ("all", "h" or
  "none"), "source" ("ruled" or "aligned")}.
- setup(doc, keep): each run of pages with one size: its size, orientation and margins (from where the text sits).
Both the copy (redlinecopy) and its check (redlinecheck) use these, so the check reads tables the way the copy holds
them. Rules only (No AI); nothing leaves the PC."""
import pdfobjects as PO
import redlinetables as RT
import ruledtables as RU


def _inside(box, ln):
    l, t, r, b = box
    x = (ln["box"][0] + ln["box"][2]) / 2
    y = (ln["box"][1] + ln["box"][3]) / 2
    return l - 1 <= x <= r + 1 and t - 1 <= y <= b + 1


def ruled(pdf, doc, skip):
    """The tables drawn with borders: [{"page", "lines", "grid", "box"}]."""
    import pypdfium2 as pdfium
    out = []
    try:
        pp = pdfium.PdfDocument(pdf)
    except Exception:  # noqa: BLE001  a file PDFium cannot open has no drawing to read
        return out
    try:
        for pi in range(min(len(pp), len(doc.get("pages") or []))):
            page = pp[pi]
            try:
                found = RU.find(PO.drawing(page), PO.words(page))
            finally:
                page.close()
            lines = doc["pages"][pi]["lines"]
            for t in found:
                mine = [(pi, li) for li, ln in enumerate(lines) if (pi, li) not in skip and _inside(t["box"], ln)]
                if not mine:
                    continue
                rows = [[{k: c[k] for k in ("text", "cs", "rs", "fill", "bold")} for c in row] for row in t["rows"] if row]
                out.append({"page": pi, "lines": mine, "box": t["box"],
                            "grid": {"rows": rows, "widths": t["widths"], "heights": t["heights"], "header": t["header"],
                                     "borders": t["borders"], "source": "ruled"}})
    finally:
        pp.close()
    return out


def tables(pdf, doc, skip):
    """Ruled tables first; then aligned text among the lines left."""
    got = ruled(pdf, doc, skip)
    taken = {x for t in got for x in t["lines"]}
    for t in RT.find(doc, skip | taken):
        n = max(len(r) for r in t["rows"])
        rows = [[{"text": c, "cs": 1, "rs": 1, "fill": "", "bold": False} for c in list(r) + [""] * (n - len(r))] for r in t["rows"]]
        got.append({"page": t["page"], "lines": t["lines"],
                    "grid": {"rows": rows, "widths": t["widths"], "heights": [], "header": 1, "borders": "all", "source": "aligned"}})
    return sorted(got, key=lambda t: tuple(t["lines"][0]))


def text_of(grid):
    """A table's words, row by row and cell by cell (how Word reads the copy's table)."""
    return " ".join(c["text"] for row in grid["rows"] for c in row if c["text"])


def setup(doc, keep=None, found=()):
    """[{"pages": [first, last] (1-based), "w", "h", "landscape", "margins": (top, right, bottom, left)}] in points.
    found: the tables (their boxes count: a table's borders reach past its text)."""
    extra = {}
    for t in found:
        if t.get("box"):
            extra.setdefault(t["page"], []).append(t["box"])
    out = []
    for pi, p in enumerate(doc.get("pages") or []):
        w, h = round(p.get("w") or 612), round(p.get("h") or 792)
        boxes = [ln["box"] for li, ln in enumerate(p["lines"]) if keep is None or (pi, li) in keep] + extra.get(pi, [])
        if out and (out[-1]["w"], out[-1]["h"]) == (w, h):
            g = out[-1]
            g["pages"][1] = pi + 1
        else:
            g = {"pages": [pi + 1, pi + 1], "w": w, "h": h, "landscape": w > h, "_boxes": []}
            out.append(g)
        g["_boxes"] += boxes
    for g in out:
        bx = g.pop("_boxes")
        if bx:
            top, left = min(b[1] for b in bx), min(b[0] for b in bx)
            right, bottom = g["w"] - max(b[2] for b in bx), g["h"] - max(b[3] for b in bx)
        else:
            top = right = bottom = left = 72
        clamp = lambda v: max(18, min(144, round(v / 9) * 9))         # noqa: E731  to the nearest eighth of an inch
        g["margins"] = (clamp(top), clamp(right), clamp(bottom), clamp(left))
    return out


FAMILIES = {"timesnewroman": "Times New Roman", "times": "Times New Roman", "liberationserif": "Times New Roman",
            "arial": "Arial", "helvetica": "Arial", "liberationsans": "Arial", "arialnarrow": "Arial Narrow",
            "calibri": "Calibri", "carlito": "Calibri", "cambria": "Cambria", "caladea": "Cambria", "aptos": "Aptos",
            "garamond": "Garamond", "georgia": "Georgia", "verdana": "Verdana", "tahoma": "Tahoma", "segoeui": "Segoe UI",
            "couriernew": "Courier New", "courier": "Courier New", "bookantiqua": "Book Antiqua", "centurygothic": "Century Gothic"}


def family(name):
    """A PDF font's name as Word's family: the subset tag (ABCDEF+), the style (,Bold -BoldMT PSMT) taken off."""
    import re
    n = (name or "").split("+", 1)[-1]
    n = re.split(r"[,-]", n)[0]
    n = re.sub(r"(PSMT|MT|PS)$", "", n)
    key = re.sub(r"[^a-z]", "", n.lower())
    for k, v in FAMILIES.items():
        if key == k or (key.startswith(k) and len(k) >= 5):
            return v
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n) or "Calibri"


def body_font(pdf, sample=4000):
    """The font most of the PDF's text is set in, as a Word family (from up to sample characters)."""
    import ctypes
    from collections import Counter
    import pypdfium2 as pdfium
    import pypdfium2.raw as R
    seen = Counter()
    try:
        doc = pdfium.PdfDocument(pdf)
    except Exception:  # noqa: BLE001
        return "Calibri"
    try:
        buf = ctypes.create_string_buffer(256)
        flags = ctypes.c_int()
        for i in range(len(doc)):
            page = doc[i]
            tp = page.get_textpage()
            n = tp.count_chars()
            for k in range(0, n, max(1, n // 400)):
                if R.FPDFText_GetFontInfo(tp.raw, k, buf, 256, ctypes.byref(flags)):
                    seen[family(buf.value.decode("utf-8", "replace"))] += 1
            tp.close(); page.close()
            if sum(seen.values()) >= sample:
                break
    finally:
        doc.close()
    return seen.most_common(1)[0][0] if seen else "Calibri"
