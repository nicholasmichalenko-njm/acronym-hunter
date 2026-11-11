"""Tables from the PDF's tags (4.14.0; claude/stationkeeper-pdf-fidelity-plan-4.13.html, rung 2).

pdftags gives a tagged table's rows and cells and where each cell's text sits; Word writes no spans. The grid:
- the columns come from the rows with the most cells: column k runs from the left of its cells to the right of them;
  the bounds between columns sit halfway across each gap;
- a cell in a shorter row spans the columns its text crosses (a heading cell over two columns);
- a cell with no text sits in the next free column;
- the words of the page under a cell's place are its text (the tags' own pieces break words at kerning);
- a tagged table inside another table's cell goes in that cell (nested).
Rules only (No AI); nothing leaves the PC."""
import ruledtables as RU


def _overlap(a, b):
    """How much of box a lies inside box b (0 to 1)."""
    if not a or not b:
        return 0.0
    w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    area = max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))
    return w * h / area


def grid(tt, words, pad=5.4):
    """A redlinelayout grid from a tagged table: {"rows", "widths", "heights", "header", "pad", "borders", "source",
    "xs", "ys"} (xs, ys: the bounds on the page, to place words and nested tables)."""
    rows = [r for r in tt["rows"] if r]
    if not rows:
        return None
    full = max(len(r) for r in rows)
    ranges = []
    for k in range(full):
        bx = [r[k]["box"] for r in rows if len(r) == full and r[k]["box"]]
        if not bx:
            return None
        ranges.append((min(b[0] for b in bx), max(b[2] for b in bx)))
    left = min(r[0] for r in ranges) - pad
    right = max(r[1] for r in ranges) + pad
    xs = [left] + [(ranges[k][1] + ranges[k + 1][0]) / 2 for k in range(full - 1)] + [right]
    tops = []
    for r in rows:
        bx = [c["box"] for c in r if c["box"]]
        tops.append((min(b[1] for b in bx), max(b[3] for b in bx)) if bx else None)
    ys = []
    known = [t for t in tops if t]
    if not known:
        return None
    ys.append(known[0][0] - 2)
    for i in range(len(rows) - 1):
        a, b = tops[i], tops[i + 1]
        ys.append((a[1] + b[0]) / 2 if a and b else (a[1] + 2 if a else (b[0] - 2 if b else ys[-1] + 12)))
    ys.append((tops[-1][1] if tops[-1] else ys[-1] + 12) + 2)
    out = []
    for ri, r in enumerate(rows):
        cells, col = [], 0
        for c in r:
            if col >= full:
                break
            cs = 1
            if c["box"] and len(r) < full:
                start = next((k for k in range(full) if xs[k + 1] > c["box"][0] + 0.5), col)
                end = next((k for k in range(full - 1, -1, -1) if xs[k] < c["box"][2] - 0.5), start)
                col = max(col, start)
                cs = max(1, end - col + 1)
            cs = min(cs, full - col)
            l, r_, t, b = xs[col], xs[col + cs], ys[ri], ys[ri + 1]
            mine = [w for w in words if l <= (w["box"][0] + w["box"][2]) / 2 <= r_ and t <= (w["box"][1] + w["box"][3]) / 2 <= b]
            text = RU._cell_text(mine) if mine else ""
            cells.append({"text": text, "cs": cs, "rs": 1, "fill": "", "bold": bool(mine) and all(w.get("bold") for w in mine),
                          "c": col, "place": (l, t, r_, b)})
            col += cs
        out.append(cells)
    head = int(tt.get("head") or 0) or (1 if out and all(c["bold"] or not c["text"] for c in out[0]) and len(out) > 1 else 0)
    return {"rows": out, "widths": [xs[k + 1] - xs[k] for k in range(full)], "heights": [], "header": head, "pad": pad,
            "borders": "none", "source": "tags", "xs": xs, "ys": ys}


def nest(grids):
    """Put each grid that sits inside another's cell into that cell ("nested"); returns the outer grids."""
    outer = []
    for g in grids:
        box = (g["xs"][0], g["ys"][0], g["xs"][-1], g["ys"][-1])
        host = None
        for h in grids:
            if h is g:
                continue
            for row in h["rows"]:
                for c in row:
                    if _overlap(box, c["place"]) > 0.8 and (c["place"][2] - c["place"][0]) * (c["place"][3] - c["place"][1]) > \
                            (box[2] - box[0]) * (box[3] - box[1]):
                        host = c
        if host is None:
            outer.append(g)
        else:
            host["nested"] = g
            host["text"] = _minus(host["text"], g)
    return outer


def _minus(text, g):
    """A cell's own words without those of the table inside it."""
    import redlinelayout as RL
    inner = RL.text_of(g).split()
    words = text.split()
    for w in inner:
        if w in words:
            words.remove(w)
    return " ".join(words)
