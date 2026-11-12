"""4.22.0: the pictures of a PDF, for Prepare for redline's Word copy (the copy left every picture out and kept the
space it stood in, so a cover lost its pictures and pages had gaps).

A page's pictures and drawings (placed images, and shapes drawn with lines and fills) are found through PDFium, joined
where they touch into regions, and each region is drawn as one picture:
- in the text's flow, between the paragraphs it sat between, when it sits inside the margins ("flow");
- behind the text at its place on the page, when it bleeds into the margins or lies under text ("page"): a cover's
  band, a background;
- in the header or footer, when the same picture sits in the top or bottom margin of two or more pages ("header",
  "footer").
The text of a drawing's labels (a few short lines inside it) stays in the picture and is left out of the copy's text;
a shaded box around sentences is left out and its sentences stay text. A table's borders and shading, the shading
behind a line of text, and a white page fill are not pictures. Text always flows: nothing is put in a text box.
Rules only (No AI); nothing leaves the PC."""
import ctypes, io

import pdfobjects as PO

DPI = 200
NEAR = 6.0                                   # points: drawings this close are one region
SMALL = 8.0                                  # a region smaller than this on a side is not a picture
EMU = 12700
_NS_WP = 'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"'
_NS_A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
_NS_PIC = 'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'


def _bounds(R, obj, h):
    l, b, r, t = (ctypes.c_float() for _ in range(4))
    if not R.FPDFPageObj_GetBounds(obj, ctypes.byref(l), ctypes.byref(b), ctypes.byref(r), ctypes.byref(t)):
        return None
    return (min(l.value, r.value), h - max(b.value, t.value), max(l.value, r.value), h - min(b.value, t.value))


def _has_drawing(R, form):
    for i in range(R.FPDFFormObj_CountObjects(form)):
        o = R.FPDFFormObj_GetObject(form, i)
        t = R.FPDFPageObj_GetType(o)
        if t in (R.FPDF_PAGEOBJ_IMAGE, R.FPDF_PAGEOBJ_PATH, R.FPDF_PAGEOBJ_SHADING):
            return True
        if t == R.FPDF_PAGEOBJ_FORM and _has_drawing(R, o):
            return True
    return False


def objects(page):
    """[{"kind": "image"|"path"|"form", "box" (from the top), "color", "filled"}] of a pypdfium2 page's top objects."""
    import pypdfium2.raw as R
    w, h = page.get_size()
    out = []
    for i in range(R.FPDFPage_CountObjects(page.raw)):
        obj = R.FPDFPage_GetObject(page.raw, i)
        t = R.FPDFPageObj_GetType(obj)
        if t == R.FPDF_PAGEOBJ_TEXT:
            continue
        box = _bounds(R, obj, h)
        if box is None:
            continue
        box = (max(0.0, box[0]), max(0.0, box[1]), min(w, box[2]), min(h, box[3]))
        if box[2] - box[0] <= 0 or box[3] - box[1] <= 0:
            continue
        if t == R.FPDF_PAGEOBJ_IMAGE:
            out.append({"kind": "image", "box": box, "color": "", "filled": True})
        elif t == R.FPDF_PAGEOBJ_FORM:
            if _has_drawing(R, obj):
                out.append({"kind": "form", "box": box, "color": "", "filled": True})
        elif t in (R.FPDF_PAGEOBJ_PATH, R.FPDF_PAGEOBJ_SHADING):
            mode, stroke = ctypes.c_int(), ctypes.c_int()
            filled = True
            if t == R.FPDF_PAGEOBJ_PATH and R.FPDFPath_GetDrawMode(obj, ctypes.byref(mode), ctypes.byref(stroke)):
                filled = mode.value != 0
                if not filled and not stroke.value:
                    continue                                    # a clip or an unpainted path draws nothing
            color, alpha = PO._color(R, obj, fill=filled)
            if alpha == 0:
                continue
            out.append({"kind": "path", "box": box, "color": color, "filled": filled})
    return out


def _inside(inner, outer, pad=0.0):
    return inner[0] >= outer[0] - pad and inner[1] >= outer[1] - pad and inner[2] <= outer[2] + pad and inner[3] <= outer[3] + pad


def _near(a, b, d=NEAR):
    return a[0] <= b[2] + d and b[0] <= a[2] + d and a[1] <= b[3] + d and b[1] <= a[3] + d


def _union(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def _thin(b):
    return (b[2] - b[0]) < PO.THIN + 1 or (b[3] - b[1]) < PO.THIN + 1


def _sentences(texts):
    """Lines that read as running text, not a drawing's labels."""
    words = [len(t.split()) for t in texts]
    return len(texts) >= 2 and sum(words) / max(1, len(words)) >= 6


def page_regions(objs, lines, taken, tables, w, h, margins, body_size):
    """The regions of one page. lines: [(index, box, text)] of the page's text lines not already taken (tables, lines set
    aside); taken: boxes of the running headers and footers; tables: the tables' boxes; margins (top, right, bottom,
    left). Returns ([{"box", "lines": [index], "where", "under_text"}], [rule boxes])."""
    top_m, right_m, bottom_m, left_m = margins
    keep, rules = [], []
    for o in objs:
        b = o["box"]
        if any(_inside(b, t, 3.0) for t in tables):
            continue                                            # a table's borders and shading
        area = (b[2] - b[0]) * (b[3] - b[1])
        if o["kind"] == "path":
            if area > 0.9 * w * h and o["filled"] and o["color"] in ("FFFFFF", ""):
                continue                                        # the page's own white fill
            if o["filled"] and not _thin(b) and (b[3] - b[1]) <= 1.7 * body_size and \
                    any(_inside(lb, b, 2.0) for _i, lb, _t in lines):
                continue                                        # shading behind a line of text
        keep.append(o)
    groups = []                                                 # joined where they touch
    for o in keep:
        hit = [g for g in groups if any(_near(o["box"], x["box"]) for x in g)]
        for g in hit:
            groups.remove(g)
        groups.append([o] + [x for g in hit for x in g])
    out = []
    for g in groups:
        box = _union([o["box"] for o in g])
        bw, bh = box[2] - box[0], box[3] - box[1]
        if all(o["kind"] == "path" and _thin(o["box"]) for o in g) and (min(bw, bh) < 12 or len(g) < 3):
            rules.append(box)                                   # a rule or two, not a drawing
            continue
        if bw < SMALL or bh < SMALL:
            continue
        mine = [(i, lb, t) for i, lb, t in lines if box[0] - 2 <= (lb[0] + lb[2]) / 2 <= box[2] + 2
                and box[1] - 2 <= (lb[1] + lb[3]) / 2 <= box[3] + 2]
        big = bw * bh > 0.5 * w * h or len(mine) > 12
        simple = all(o["kind"] == "path" for o in g) and len(g) <= 4
        if mine and simple and not big and _sentences([t for _i, _b, t in mine]):
            continue                                            # a shaded box around sentences: the sentences stay text
        under = bool(mine) and (big or _sentences([t for _i, _b, t in mine]))
        in_cols = box[0] >= left_m - 3 and box[2] <= w - right_m + 3
        if box[3] <= top_m + 2 or (box[1] < top_m and (box[1] + box[3]) / 2 < top_m):
            where = "header"
        elif box[1] >= h - bottom_m - 2 or (box[3] > h - bottom_m and (box[1] + box[3]) / 2 > h - bottom_m):
            where = "footer"
        elif in_cols and not under:
            where = "flow"
        else:
            where = "page"
        out.append({"box": tuple(round(v, 1) for v in box), "lines": [] if under else [i for i, _b, _t in mine],
                    "where": where, "under_text": under})
    out.sort(key=lambda r: (r["box"][1], r["box"][0]))
    return out, rules


def regions(pdf, doc, skip, tables, groups):
    """{page index: [region]} and {page index: [rule box]} for a PDF. doc: pagesent's; skip: the lines already left out
    (running headers and footers, lines set aside, lines in tables); tables: redlinelayout's; groups: its setup()."""
    import statistics
    import pypdfium2 as pdfium
    sizes = [ln["size"] for p in doc["pages"] for ln in p["lines"] if ln.get("size")]
    body = statistics.median(sizes) if sizes else 11.0
    marg = {}
    for g in groups:
        for n in range(g["pages"][0], g["pages"][1] + 1):
            marg[n - 1] = g["margins"]
    tbox = {}
    for t in tables:
        if t.get("box"):
            tbox.setdefault(t["page"], []).append(t["box"])
    found, rules = {}, {}
    try:
        pp = pdfium.PdfDocument(pdf)
    except Exception:  # noqa: BLE001  a file PDFium cannot open has no pictures to keep
        return found, rules
    try:
        for pi in range(min(len(pp), len(doc.get("pages") or []))):
            page = pp[pi]
            try:
                objs = objects(page)
                w, h = page.get_size()
            finally:
                page.close()
            if not objs:
                continue
            ls = doc["pages"][pi]["lines"]
            lines = [(li, ln["box"], ln["text"]) for li, ln in enumerate(ls) if (pi, li) not in skip]
            taken = [ln["box"] for li, ln in enumerate(ls) if (pi, li) in skip]
            got, rl = page_regions(objs, lines, taken, tbox.get(pi, []), w, h, marg.get(pi, (72, 72, 72, 72)), body)
            if got:
                found[pi] = got
            if rl:
                rules[pi] = rl
    finally:
        pp.close()
    _recurring(found)
    return found, rules


def _recurring(found):
    """A header or footer picture is the page's furniture when the same box holds one on two or more pages; one that
    shows on a single page (a cover's band) belongs to that page."""
    seen = {}
    for pi, regs in found.items():
        for r in regs:
            if r["where"] in ("header", "footer"):
                key = (r["where"],) + tuple(int(round(v / 3.0)) for v in r["box"])
                seen.setdefault(key, []).append((pi, r))
    for spots in seen.values():
        if len({pi for pi, _r in spots}) < 2:
            for _pi, r in spots:
                r["where"] = "page"
        else:
            for _pi, r in spots:
                r["furniture"] = True


def draw(pdf, page_index, boxes, without_text=False, dpi=DPI):
    """PNG bytes of each box (points, from the top) of a page; without_text draws the page with its text taken off."""
    import pypdfium2 as pdfium
    if not boxes:
        return []
    if without_text:
        import redlineslides as SL
        from PIL import Image
        img = Image.open(io.BytesIO(SL.background(pdf, page_index, dpi))).convert("RGB")
    else:
        d = pdfium.PdfDocument(pdf)
        try:
            page = d[page_index]
            try:
                img = page.render(scale=dpi / 72).to_pil().convert("RGB")
            finally:
                page.close()
        finally:
            d.close()
    k = dpi / 72.0
    out = []
    for b in boxes:
        crop = img.crop((max(0, int(b[0] * k)), max(0, int(b[1] * k)), min(img.width, int(round(b[2] * k))),
                         min(img.height, int(round(b[3] * k)))))
        buf = io.BytesIO()
        crop.save(buf, "PNG", optimize=True)
        out.append(buf.getvalue())
    return out


def _pic(rid, n, cx, cy, name):
    return (f'<a:graphic {_NS_A}><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic {_NS_PIC}><pic:nvPicPr><pic:cNvPr id="{n}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill>'
            f'<a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/>'
            f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
            '</a:graphicData></a:graphic>')


def inline(rid, n, w, h):
    """A picture in the text's flow, w by h points: one run."""
    cx, cy = int(w * EMU), int(h * EMU)
    return (f'<w:r><w:drawing><wp:inline {_NS_WP} distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{n}" name="Picture {n}"/><wp:cNvGraphicFramePr/>'
            + _pic(rid, n, cx, cy, f"picture{n}.png") + '</wp:inline></w:drawing></w:r>')


def anchor(rid, n, box):
    """A picture behind the text at its place on the page (box in points from the page's top left): one run. The text
    flows over it; it moves with the paragraph that holds it."""
    cx, cy = int((box[2] - box[0]) * EMU), int((box[3] - box[1]) * EMU)
    return (f'<w:r><w:drawing><wp:anchor {_NS_WP} distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="0" '
            'behindDoc="1" locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/>'
            f'<wp:positionH relativeFrom="page"><wp:posOffset>{int(box[0] * EMU)}</wp:posOffset></wp:positionH>'
            f'<wp:positionV relativeFrom="page"><wp:posOffset>{int(box[1] * EMU)}</wp:posOffset></wp:positionV>'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>'
            f'<wp:docPr id="{n}" name="Picture {n}"/><wp:cNvGraphicFramePr/>' + _pic(rid, n, cx, cy, f"picture{n}.png")
            + '</wp:anchor></w:drawing></w:r>')
