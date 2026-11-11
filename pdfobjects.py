"""What a PDF page draws, read through PDFium (4.13.0; claude/stationkeeper-pdf-fidelity-plan-4.13.html, step 2).

For Redline's copy, tables are read from the borders a page draws, not guessed from where text lines up:
- edges: straight horizontal and vertical strokes, and filled rectangles thinner than THIN points (Word draws many
  borders that way), as (x0, y0, x1, y1) with y measured from the top of the page, like pagesent's boxes;
- fills: filled rectangles larger than that (cell shading), with their color;
- words: each word's text and box, from the page's characters, split at spaces and at gaps wider than a space.
Form objects (drawings inside drawings) are read too, their placement applied. Rules only (No AI); nothing leaves the PC."""
import ctypes, math

THIN = 2.5                                  # points: a filled rectangle this thin is a line, not shading
BULLETS = {"\uf0b7": "\u2022", "\uf0a7": "\u25aa", "\uf076": "\u2756", "\uf0d8": "\u27a2", "\uf0fc": "\u2713", "\uf0a8": "\u25e6"}   # Symbol and
                                             # Wingdings bullets Word writes in the private area, as the characters they show
AXIS = 0.6                                  # points a stroke may lean and still count as horizontal or vertical


def _mul(m, n):
    """m then n, as PDF matrices (a, b, c, d, e, f)."""
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F)


def _apply(m, x, y):
    a, b, c, d, e, f = m
    return a * x + c * y + e, b * x + d * y + f


def _matrix(R, obj):
    fm = R.FS_MATRIX()
    if R.FPDFPageObj_GetMatrix(obj, ctypes.byref(fm)):
        return (fm.a, fm.b, fm.c, fm.d, fm.e, fm.f)
    return (1, 0, 0, 1, 0, 0)


def _color(R, obj, fill=True):
    r, g, b, a = (ctypes.c_uint() for _ in range(4))
    fn = R.FPDFPageObj_GetFillColor if fill else R.FPDFPageObj_GetStrokeColor
    if fn(obj, ctypes.byref(r), ctypes.byref(g), ctypes.byref(b), ctypes.byref(a)):
        return "%02X%02X%02X" % (r.value, g.value, b.value), a.value
    return "000000", 255


def _path(R, obj, m, h, out):
    """A path's straight axis-aligned pieces as edges, its filled rectangles as edges (thin) or fills."""
    fill, stroke = ctypes.c_int(), ctypes.c_int()
    R.FPDFPath_GetDrawMode(obj, ctypes.byref(fill), ctypes.byref(stroke))
    width = ctypes.c_float(1.0)
    R.FPDFPageObj_GetStrokeWidth(obj, ctypes.byref(width))
    pts, start = [], None
    n = R.FPDFPath_CountSegments(obj)
    polys = []
    for i in range(n):
        seg = R.FPDFPath_GetPathSegment(obj, i)
        x, y = ctypes.c_float(), ctypes.c_float()
        R.FPDFPathSegment_GetPoint(seg, ctypes.byref(x), ctypes.byref(y))
        X, Y = _apply(m, x.value, y.value)
        p = (X, h - Y)
        t = R.FPDFPathSegment_GetType(seg)
        if t == R.FPDF_SEGMENT_MOVETO or not pts:
            if pts:
                polys.append(pts)
            pts, start = [p], p
        else:
            pts.append(p)
        if R.FPDFPathSegment_GetClose(seg) and start is not None:
            pts.append(start)
    if pts:
        polys.append(pts)
    for poly in polys:
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        l, r, t_, b = min(xs), max(xs), min(ys), max(ys)
        rect = len(poly) >= 4 and all(abs(p[0] - l) < AXIS or abs(p[0] - r) < AXIS for p in poly) \
            and all(abs(p[1] - t_) < AXIS or abs(p[1] - b) < AXIS for p in poly)
        if fill.value and rect:
            if r - l <= THIN and b - t_ > THIN:
                out["edges"].append(((l + r) / 2, t_, (l + r) / 2, b, "v", r - l))
                continue
            if b - t_ <= THIN and r - l > THIN:
                out["edges"].append((l, (t_ + b) / 2, r, (t_ + b) / 2, "h", b - t_))
                continue
            if r - l > THIN and b - t_ > THIN:
                col, alpha = _color(R, obj, True)
                if alpha:
                    out["fills"].append((l, t_, r, b, col))
        if stroke.value:
            for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
                if abs(y0 - y1) < AXIS and abs(x1 - x0) > AXIS:
                    out["edges"].append((min(x0, x1), y0, max(x0, x1), y0, "h", width.value))
                elif abs(x0 - x1) < AXIS and abs(y1 - y0) > AXIS:
                    out["edges"].append((x0, min(y0, y1), x0, max(y0, y1), "v", width.value))


def _walk(R, objs, m, h, out, depth=0):
    for obj in objs:
        t = R.FPDFPageObj_GetType(obj)
        om = _mul(_matrix(R, obj), m) if t == R.FPDF_PAGEOBJ_FORM else m
        if t == R.FPDF_PAGEOBJ_PATH:
            _path(R, obj, _mul(_matrix(R, obj), m), h, out)
        elif t == R.FPDF_PAGEOBJ_FORM and depth < 8:
            kids = [R.FPDFFormObj_GetObject(obj, i) for i in range(R.FPDFFormObj_CountObjects(obj))]
            _walk(R, kids, om, h, out, depth + 1)
        elif t == R.FPDF_PAGEOBJ_IMAGE:
            l, b, r, tp = (ctypes.c_float() for _ in range(4))
            if R.FPDFPageObj_GetBounds(obj, ctypes.byref(l), ctypes.byref(b), ctypes.byref(r), ctypes.byref(tp)):
                out["images"].append((l.value, h - tp.value, r.value, h - b.value))


def drawing(page):
    """{"w", "h", "edges": [(x0, y0, x1, y1, "h"|"v", width)], "fills": [(l, t, r, b, color)], "images": [box]} of a
    pypdfium2 page; y from the top."""
    import pypdfium2.raw as R
    w, h = page.get_size()
    out = {"w": w, "h": h, "edges": [], "fills": [], "images": []}
    objs = [R.FPDFPage_GetObject(page.raw, i) for i in range(R.FPDFPage_CountObjects(page.raw))]
    _walk(R, objs, (1, 0, 0, 1, 0, 0), h, out)
    return out


def words(page):
    """The page's words: [{"text", "box": (l, t, r, b) from the top, "size", "bold", "i": first char index}], in the
    text's own order. A gap wider than a space splits a word too (text set with tabs or in table cells)."""
    import pypdfium2.raw as R
    w, h = page.get_size()
    tp = page.get_textpage()
    try:
        n = tp.count_chars()
        t = (tp.get_text_range(0, n) if n else "").replace("￾", "-")
        out, cur, last = [], None, None
        for k in range(min(n, len(t))):
            ch = t[k]
            if ch.isspace():
                cur = None
                continue
            try:
                l, bo, r, tt = tp.get_charbox(k)
            except Exception:
                continue
            box = (l, h - tt, r, h - bo)
            size = R.FPDFText_GetFontSize(tp.raw, k)
            ch = BULLETS.get(ch, ch)
            ang = R.FPDFText_GetCharAngle(tp.raw, k)
            rot = 0.3 < (ang % math.pi) < math.pi - 0.3             # turned a quarter: read down or up the page
            if cur is not None and (rot or cur.get("rot")):
                near = cur.get("rot") == rot and min(box[2], cur["box"][2]) - max(box[0], cur["box"][0]) > -1.0 and \
                    min(abs(box[1] - cur["box"][3]), abs(cur["box"][1] - box[3])) < max(3.0, 0.75 * (size or 10))
                if not near:
                    cur = None
            elif cur is not None:
                gap = box[0] - cur["box"][2]
                same_line = min(box[3], cur["box"][3]) - max(box[1], cur["box"][1]) > -1.0     # the boxes overlap up and down
                lig = last is not None and abs(box[0] - last[0]) < 0.1 and abs(box[2] - last[2]) < 0.1   # a ligature: one box
                if not same_line or gap > max(3.0, 0.75 * (size or 10)) or (gap < -0.6 * (size or 10) and not lig):
                    cur = None
            if cur is None:
                cur = {"text": "", "box": box, "size": size, "bold": R.FPDFText_GetFontWeight(tp.raw, k) >= 600, "i": k, "rot": rot}
                out.append(cur)
            cur["text"] += ch
            last = box
            b0 = cur["box"]
            cur["box"] = (min(b0[0], box[0]), min(b0[1], box[1]), max(b0[2], box[2]), max(b0[3], box[3]))
        return out
    finally:
        tp.close()
