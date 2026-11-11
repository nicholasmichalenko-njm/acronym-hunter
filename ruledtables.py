"""Tables read from the borders a page draws (4.13.0; claude/stationkeeper-pdf-fidelity-plan-4.13.html, rung 1).

Word draws a table's borders as lines (or thin filled rectangles). From pdfobjects.drawing:
1. edges are snapped (lines within SNAP points become one), joined (pieces on one line with gaps under SNAP), and short
   ones dropped;
2. edges that cross or touch make one group: a group with two vertical and two horizontal lines or more is a grid; the
   column bounds are its vertical lines, the row bounds its horizontal lines;
3. each box of the grid is a cell, unless a border between two boxes is missing: then they are one cell, spanning
   columns (Word's gridSpan) or rows (vMerge);
4. three horizontal rules or more with the same ends and no vertical lines (a style with rules only) make the rows; the
   columns come from the gaps no word crosses;
5. each word goes in the cell under its middle; a filled rectangle covering most of a cell is its shading; a first row
   all in bold or shaded is the header row.
A group that is one box, holds no text in two cells, or sits inside another table's cell is not a table here (a frame
round a page or a paragraph; a table in a cell stays that cell's text for now). Rules only (No AI); nothing leaves the PC."""

SNAP = 3.0                                   # points: lines this close are one line; pieces this close are joined
MIN_LEN = 4.0                                # points: shorter strokes are not borders
COVER = 0.7                                  # a border covers this much of a box's side to separate two boxes
RULE_GAP = 80.0                              # points: rules farther apart than this are not one table
GUTTER = 5.0                                 # points: a gap no word crosses, this wide, splits columns (rules-only tables)


def _cluster(vals):
    """{value: snapped value} grouping values within SNAP of the previous one."""
    out, group = {}, []
    for v in sorted(set(vals)):
        if group and v - group[-1] > SNAP:
            m = sum(group) / len(group)
            out.update({g: m for g in group})
            group = []
        group.append(v)
    if group:
        m = sum(group) / len(group)
        out.update({g: m for g in group})
    return out


def _join(segs):
    """[(pos, a, b)] on snapped lines: overlapping or near pieces on one line become one."""
    out = []
    for pos, a, b in sorted(segs):
        if out and out[-1][0] == pos and a <= out[-1][2] + SNAP:
            out[-1] = (pos, out[-1][1], max(out[-1][2], b))
        else:
            out.append((pos, a, b))
    return [s for s in out if s[2] - s[1] >= MIN_LEN]


def lines(drawing):
    """(horizontal [(y, x0, x1)], vertical [(x, y0, y1)]) snapped and joined."""
    hs = [(e[1], e[0], e[2]) for e in drawing["edges"] if e[4] == "h"]
    vs = [(e[0], e[1], e[3]) for e in drawing["edges"] if e[4] == "v"]
    hy, vx = _cluster([h[0] for h in hs]), _cluster([v[0] for v in vs])
    return _join([(hy[y], a, b) for y, a, b in hs]), _join([(vx[x], a, b) for x, a, b in vs])


def _groups(hs, vs):
    """Lines that cross or touch, grouped: [(hs, vs)]."""
    items = [("h", h) for h in hs] + [("v", v) for v in vs]
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def touch(a, b):
        (ka, A), (kb, B) = a, b
        if ka == kb:
            return False
        h, v = (A, B) if ka == "h" else (B, A)
        return h[1] - SNAP <= v[0] <= h[2] + SNAP and v[1] - SNAP <= h[0] <= v[2] + SNAP

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if touch(items[i], items[j]):
                parent[find(i)] = find(j)
    out = {}
    for i, it in enumerate(items):
        out.setdefault(find(i), []).append(it)
    return [([x for k, x in g if k == "h"], [x for k, x in g if k == "v"]) for g in out.values()]


def _covers(segs, pos, a, b):
    """How much of a..b the lines at pos cover (0 to 1)."""
    if b <= a:
        return 1.0
    got = 0.0
    for p, s, e in segs:
        if abs(p - pos) <= SNAP:
            got += max(0.0, min(b, e) - max(a, s))
    return min(1.0, got / (b - a))


def _uniq(vals):
    out = []
    for v in sorted(vals):
        if not out or v - out[-1] > SNAP:
            out.append(v)
    return out


def _gutters(ws, l, r):
    """Column bounds inside l..r from the gaps no word crosses (at least GUTTER wide)."""
    spans = sorted((max(l, w["box"][0]), min(r, w["box"][2])) for w in ws)
    bounds, edge = [l], l
    for a, b in spans:
        if a - edge >= GUTTER and edge > l:
            bounds.append((a + edge) / 2)
        edge = max(edge, b)
    bounds.append(r)
    return bounds


def _cell_text(ws):
    """Words in reading order: lines top to bottom (by overlap), each left to right; lines joined with a space. Turned
    text (a rotated header) reads in the PDF's own order."""
    if all(w.get("rot") for w in ws):
        import redlinecopy as RC
        return RC.join_lines([w["text"] for w in sorted(ws, key=lambda w: w["i"])])
    rows = []
    for w in sorted(ws, key=lambda w: (w["box"][1], w["box"][0])):
        if rows and min(w["box"][3], rows[-1][1]) - max(w["box"][1], rows[-1][0]) > 0.4 * (w["box"][3] - w["box"][1]):
            rows[-1][2].append(w)
            rows[-1][1] = max(rows[-1][1], w["box"][3])
        else:
            rows.append([w["box"][1], w["box"][3], [w]])
    import redlinecopy as RC
    return RC.join_lines([" ".join(x["text"] for x in sorted(r[2], key=lambda w: w["box"][0])) for r in rows])


def _grid(xs, ys, hs, vs, need_v=True):
    """Cells of a grid: [(r0, c0, rs, cs)] merging boxes whose shared border is missing."""
    nr, nc = len(ys) - 1, len(xs) - 1
    parent = {(i, j): (i, j) for i in range(nr) for j in range(nc)}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k
    for i in range(nr):
        for j in range(nc):
            if need_v and j + 1 < nc and _covers(vs, xs[j + 1], ys[i], ys[i + 1]) < COVER:
                parent[find((i, j))] = find((i, j + 1))
            if i + 1 < nr and _covers(hs, ys[i + 1], xs[j], xs[j + 1]) < COVER:
                parent[find((i, j))] = find((i + 1, j))
    groups = {}
    for k in parent:
        groups.setdefault(find(k), []).append(k)
    cells = []
    for g in groups.values():
        r0, r1 = min(k[0] for k in g), max(k[0] for k in g)
        c0, c1 = min(k[1] for k in g), max(k[1] for k in g)
        if len(g) == (r1 - r0 + 1) * (c1 - c0 + 1):
            cells.append((r0, c0, r1 - r0 + 1, c1 - c0 + 1))
        else:                                          # not a rectangle: each box its own cell
            cells += [(i, j, 1, 1) for i, j in g]
    return sorted(cells)


def _table(xs, ys, cells, ws, fills, borders):
    """The table: {"box", "widths", "heights", "rows": [[{"text","cs","rs","fill","c"}]], "header", "borders", "words"}."""
    l, t, r, b = xs[0], ys[0], xs[-1], ys[-1]
    inside = [w for w in ws if l <= (w["box"][0] + w["box"][2]) / 2 <= r and t <= (w["box"][1] + w["box"][3]) / 2 <= b]
    rows = [[] for _ in range(len(ys) - 1)]
    filled, placed = 0, []
    for r0, c0, rs, cs in cells:
        cl, cr, ct, cb = xs[c0], xs[c0 + cs], ys[r0], ys[r0 + rs]
        mine = [w for w in inside if cl <= (w["box"][0] + w["box"][2]) / 2 <= cr and ct <= (w["box"][1] + w["box"][3]) / 2 <= cb]
        text = _cell_text(mine) if mine else ""
        placed.append((c0, [w for w in mine if not w.get("rot")]))
        filled += bool(text)
        fill = ""
        for fl, ft, fr, fb, col in fills:
            ov = max(0, min(cr, fr) - max(cl, fl)) * max(0, min(cb, fb) - max(ct, ft))
            if ov >= 0.8 * (cr - cl) * (cb - ct) and col.upper() not in ("FFFFFF",):
                fill = col
        rows[r0].append({"text": text, "cs": cs, "rs": rs, "fill": fill, "c": c0,
                         "bold": bool(mine) and all(w.get("bold") for w in mine)})
    for row in rows:
        row.sort(key=lambda c: c["c"])
    head = 1 if rows and rows[0] and (all(c["bold"] or not c["text"] for c in rows[0]) and any(c["text"] for c in rows[0])
                                      or all(c["fill"] for c in rows[0])) and len(rows) > 1 else 0
    pads = sorted(min(w["box"][0] for w in m) - xs[c0] for c0, m in placed if m)
    pad = pads[len(pads) // 2] if pads else 5.4
    return {"box": (l, t, r, b), "widths": [xs[k + 1] - xs[k] for k in range(len(xs) - 1)], "pad": pad,
            "heights": [ys[k + 1] - ys[k] for k in range(len(ys) - 1)], "rows": rows, "header": head, "borders": borders,
            "words": [w["i"] for w in inside], "filled": filled}


def find(drawing, ws):
    """The ruled tables of one page: [table] top to bottom (see _table). drawing: pdfobjects.drawing; ws: words."""
    hs, vs = lines(drawing)
    out = []
    groups = _groups(hs, vs)
    lone = sorted((h for gh, gv in groups if not gv for h in gh), key=lambda h: h[0])
    groups = [g for g in groups if g[1]]
    run = []                                           # rules only: lines with the same ends, stacked
    for h in lone + [None]:
        if h is not None and run and abs(h[1] - run[-1][1]) <= SNAP and abs(h[2] - run[-1][2]) <= SNAP and h[0] - run[-1][0] <= RULE_GAP:
            run.append(h)
            continue
        if len(run) >= 3:
            groups.append((run, []))
        run = [h] if h is not None else []
    for gh, gv in groups:
        if len(gv) >= 2 and len(gh) >= 2:
            xs, ys = _uniq(v[0] for v in gv), _uniq(h[0] for h in gh)
            l, r = min(min(h[1] for h in gh), xs[0]), max(max(h[2] for h in gh), xs[-1])
            if xs[0] - l > SNAP:                       # no line down the left: the rows' ends are the edge
                xs = [l] + xs
            if r - xs[-1] > SNAP:
                xs = xs + [r]
            if len(xs) < 2 or len(ys) < 2 or (len(xs) - 1) * (len(ys) - 1) < 2:
                continue
            t = _table(xs, ys, _grid(xs, ys, gh, gv), ws, drawing["fills"], "all")
        elif not gv and len(gh) >= 3:
            ends = [(h[1], h[2]) for h in gh]
            if max(e[0] for e in ends) - min(e[0] for e in ends) > SNAP or max(e[1] for e in ends) - min(e[1] for e in ends) > SNAP:
                continue
            ys = _uniq(h[0] for h in gh)
            l, r = min(e[0] for e in ends), max(e[1] for e in ends)
            mid = [w for w in ws if l <= (w["box"][0] + w["box"][2]) / 2 <= r and ys[0] <= (w["box"][1] + w["box"][3]) / 2 <= ys[-1]]
            xs = _gutters(mid, l, r)
            if len(xs) < 3:
                continue
            t = _table(xs, ys, _grid(xs, ys, gh, [], need_v=False), ws, drawing["fills"], "h")
        else:
            continue
        if t["filled"] >= 2:
            out.append(t)
    keep = []
    for t in out:                                      # a table inside another one's cell stays that cell's text
        l, tp, r, b = t["box"]
        if not any(o is not t and o["box"][0] - SNAP <= l and r <= o["box"][2] + SNAP and o["box"][1] - SNAP <= tp
                   and b <= o["box"][3] + SNAP and (o["box"][2] - o["box"][0]) * (o["box"][3] - o["box"][1]) > (r - l) * (b - tp)
                   for o in out):
            keep.append(t)
    return sorted(keep, key=lambda t: (t["box"][1], t["box"][0]))


def truth_rows(t):
    """A table as the fixtures' truth holds it: [[{"text","cs","rs"}]]."""
    return [[{"text": c["text"], "cs": c["cs"], "rs": c["rs"]} for c in row] for row in t["rows"] if row]
