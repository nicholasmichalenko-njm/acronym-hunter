"""Sheet view (2.96.0): an Excel workbook in Assign as its rows and cells, instead of a PDF copy that splits a wide sheet
across pages. Each sheet is drawn as a grid (column letters, row numbers, the cells' text wrapped inside them); each
sentence the review read from the workbook is found in its cell, so it can be clicked, combined, split and decided
like a sentence on a page. Standard library plus openpyxl; the drawing is the window's (skqt/assign.py).
"""
import re

WORD = re.compile(r"[A-Za-z0-9]+")
MAX_ROWS, MAX_COLS = 2000, 40


def col_letter(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell_text(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return " ".join(str(v).split())


def read(path, max_rows=MAX_ROWS, max_cols=MAX_COLS):
    """[{"name", "rows": [[text]] (trailing empty rows and columns dropped), "more": rows left out}] per sheet."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    out = []
    try:
        for name in wb.sheetnames:
            rows, more = [], 0
            for k, row in enumerate(wb[name].iter_rows(values_only=True)):
                if k >= max_rows:
                    more += 1
                    continue
                rows.append([_cell_text(v) for v in row[:max_cols]])
            while rows and not any(rows[-1]):
                rows.pop()
            width = max((max((i + 1 for i, v in enumerate(r) if v), default=0) for r in rows), default=0)
            rows = [(r + [""] * width)[:width] for r in rows]
            if rows:
                out.append({"name": name, "rows": rows, "more": more})
    finally:
        wb.close()
    return out


def wrap(text, width):
    """Lines of at most width characters, broken at spaces (a longer word is cut); [(start offset, line)]."""
    out, i, n = [], 0, len(text)
    while i < n:
        if n - i <= width:
            out.append((i, text[i:])); break
        cut = text.rfind(" ", i, i + width + 1)
        if cut <= i:
            cut = i + width
            out.append((i, text[i:cut])); i = cut
        else:
            out.append((i, text[i:cut])); i = cut + 1
    return out or [(0, "")]


def layout(sheets, cw, lh, max_chars=46, pad=4, gap=30):
    """Cells placed as a grid: (cells, labels, height). cells: [{"sheet", "r", "c", "text", "rect": (x, y, w, h), "lines"}];
    labels: [(text, x, y, kind)] for sheet names, column letters and row numbers. cw, lh: a character's width and a
    line's height in the drawing's units (a fixed-width font)."""
    cells, labels, y = [], [], 0.0
    rn_w = 5 * cw + pad
    for s in sheets:
        rows = s["rows"]
        ncol = len(rows[0]) if rows else 0
        widths = [min(max_chars, max([len(r[c]) for r in rows] + [3])) for c in range(ncol)]
        labels.append((f"Sheet: {s['name']}" + (f"  ({s['more']} more rows not shown)" if s.get("more") else ""), 0, y, "sheet"))
        y += lh * 1.6
        x = rn_w
        xs = []
        for c in range(ncol):
            xs.append(x)
            labels.append((col_letter(c), x + pad, y, "col"))
            x += widths[c] * cw + 2 * pad
        y += lh + pad
        for r, row in enumerate(rows):
            wrapped = [wrap(row[c], widths[c]) for c in range(ncol)]
            h = max(len(w) for w in wrapped) * lh + 2 * pad
            labels.append((str(r + 1), 0, y + pad, "row"))
            for c in range(ncol):
                cells.append({"sheet": s["name"], "r": r, "c": c, "text": row[c], "lines": wrapped[c],
                              "rect": (xs[c], y, widths[c] * cw + 2 * pad, h), "width": widths[c]})
            y += h
        y += gap
    return cells, labels, y


def _norm(s):
    return " ".join(WORD.findall((s or "").lower()))


def match(items, cells):
    """{item id: (cell index, start offset in the cell's text or -1)}: each sentence in the cell that holds it."""
    out = {}
    norm_cells = [(_norm(c["text"]), c) for c in cells]
    for it in items:
        t = it.get("text", "")
        nt = _norm(t)
        if not nt:
            continue
        best = None
        for k, (nc, c) in enumerate(norm_cells):
            if nc and (nt in nc or (len(nc) > 12 and nc in nt)):
                best = k
                break
        if best is None:
            continue
        cell = cells[best]["text"]
        first = WORD.search(t)
        start = cell.lower().find(t[:40].lower()) if t else -1
        if start < 0 and first:
            start = cell.lower().find(first.group(0).lower())
        out[it["id"]] = (best, start)
    return out


def word_rects(cell, text, start, cw, lh, pad=4):
    """The rectangles (x, y, w, h) of the sentence's words inside the cell, in order (one per word of the sentence);
    words not found where expected share the cell's last line."""
    x0, y0, _w, _h = cell["rect"]
    lines = cell["lines"]
    ctext = cell["text"]
    low = ctext.lower()
    pos = max(0, start)
    out = []
    for m in WORD.finditer(text):
        k = low.find(m.group(0).lower(), pos)
        if k < 0:
            k = pos
        else:
            pos = k + len(m.group(0))
        li = max(i for i, (s, _l) in enumerate(lines) if s <= k) if lines else 0
        col = k - lines[li][0]
        out.append((x0 + pad + col * cw, y0 + pad + li * lh, max(1, len(m.group(0))) * cw, lh))
    return out


def sentence_rects(words, pad=1.5):
    """One rectangle per line the sentence's words sit on: [(l, t, r, b)]."""
    by = {}
    for x, y, w, h in words:
        l, t, r, b = by.get(y, (x, y, x + w, y + h))
        by[y] = (min(l, x), t, max(r, x + w), b)
    return [(l - pad, t, r + pad, b) for _y, (l, t, r, b) in sorted(by.items())]
