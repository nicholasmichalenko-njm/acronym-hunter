"""The tags a PDF carries (4.14.0; claude/stationkeeper-pdf-fidelity-plan-4.13.html, rung 2).

Word's Save as PDF, with "Document structure tags for accessibility" on, writes a tree: Document > H1, P, Table > THead /
TBody > TR > TH / TD > P, each leaf pointing at the text it marks (marked-content ids, one numbering per page). Print to
PDF, flattening and most government tooling drop the tags, and Word writes no row or column spans, so the tags are a
second source: they give a table's rows and cells where no borders do (a table with no borders), and they are checked
against the borders where both exist.

tables(page): [{"rows": [[{"text", "box": (l, t, r, b) from the top or None}]], "box"}] for every Table element whose
text sits on this page. PDFium's tag functions are new in its interface; each is looked up before use and a PDF whose
tags cannot be read has none. Rules only (No AI); nothing leaves the PC."""
import ctypes

NEED = ("FPDF_StructTree_GetForPage", "FPDF_StructTree_CountChildren", "FPDF_StructTree_GetChildAtIndex",
        "FPDF_StructTree_Close", "FPDF_StructElement_GetType", "FPDF_StructElement_CountChildren",
        "FPDF_StructElement_GetChildAtIndex", "FPDF_StructElement_GetMarkedContentIdCount",
        "FPDF_StructElement_GetMarkedContentIdAtIndex", "FPDFPageObj_GetMarkedContentID", "FPDFTextObj_GetText")


def available():
    import pypdfium2.raw as R
    return all(hasattr(R, f) for f in NEED)


def _type(R, el):
    n = R.FPDF_StructElement_GetType(el, None, 0)
    if n <= 0:
        return ""
    buf = ctypes.create_string_buffer(n)
    R.FPDF_StructElement_GetType(el, buf, n)
    return buf.raw.decode("utf-16-le", "replace").rstrip("\x00")


def _kids(R, el):
    out = []
    for i in range(R.FPDF_StructElement_CountChildren(el)):
        c = R.FPDF_StructElement_GetChildAtIndex(el, i)
        if c:
            out.append(c)
    return out


def _mcids(R, el):
    """Every marked-content id under el (itself and its children)."""
    ids = [R.FPDF_StructElement_GetMarkedContentIdAtIndex(el, i) for i in range(R.FPDF_StructElement_GetMarkedContentIdCount(el))]
    ids = [i for i in ids if i >= 0]
    for c in _kids(R, el):
        ids += _mcids(R, c)
    return ids


def marked_text(page):
    """{mcid: [(text, box from the top)]} of the page's text objects, form objects included."""
    import pypdfium2.raw as R
    w, h = page.get_size()
    tp = page.get_textpage()
    out = {}

    def walk(objs, depth=0):
        for obj in objs:
            t = R.FPDFPageObj_GetType(obj)
            if t == R.FPDF_PAGEOBJ_FORM and depth < 8:
                walk([R.FPDFFormObj_GetObject(obj, i) for i in range(R.FPDFFormObj_CountObjects(obj))], depth + 1)
                continue
            if t != R.FPDF_PAGEOBJ_TEXT:
                continue
            mc = R.FPDFPageObj_GetMarkedContentID(obj)
            if mc < 0:
                continue
            n = R.FPDFTextObj_GetText(obj, tp.raw, None, 0)
            buf = (ctypes.c_ushort * max(1, n // 2))()
            R.FPDFTextObj_GetText(obj, tp.raw, buf, n)
            text = bytes(buf).decode("utf-16-le", "replace").rstrip("\x00")
            l, b, r, tt = (ctypes.c_float() for _ in range(4))
            box = None
            if R.FPDFPageObj_GetBounds(obj, ctypes.byref(l), ctypes.byref(b), ctypes.byref(r), ctypes.byref(tt)):
                box = (l.value, h - tt.value, r.value, h - b.value)
            out.setdefault(mc, []).append((text, box))

    try:
        walk([R.FPDFPage_GetObject(page.raw, i) for i in range(R.FPDFPage_CountObjects(page.raw))])
    finally:
        tp.close()
    return out


def _union(boxes):
    bx = [b for b in boxes if b]
    return (min(b[0] for b in bx), min(b[1] for b in bx), max(b[2] for b in bx), max(b[3] for b in bx)) if bx else None


def tables(page):
    """The page's tagged tables (see the module's note); [] for a page with no tags or tags PDFium cannot read."""
    import pypdfium2.raw as R
    if not available():
        return []
    tree = R.FPDF_StructTree_GetForPage(page.raw)
    if not tree:
        return []
    try:
        text = marked_text(page)
        found = []

        def cell(el):
            ids = _mcids(R, el)
            parts = [x for i in ids for x in text.get(i, [])]
            words = " ".join(" ".join(t.split()) for t, _b in parts if t.strip())
            return {"text": " ".join(words.split()), "box": _union([b for _t, b in parts])}

        def table(el):
            rows = []

            head = [0]

            def rows_of(e, in_head=False):
                for c in _kids(R, e):
                    k = _type(R, c)
                    if k == "TR":
                        rows.append([cell(x) for x in _kids(R, c) if _type(R, x) in ("TH", "TD")])
                        head[0] += 1 if in_head else 0
                    elif k in ("THead", "TBody", "TFoot"):
                        rows_of(c, k == "THead")
            rows_of(el)
            rows = [r for r in rows if r]
            if rows and any(c["box"] for r in rows for c in r):
                found.append({"rows": rows, "box": _union([c["box"] for r in rows for c in r]), "head": head[0],
                              "nested": any(_type(R, d) == "Table" for r in _kids(R, el) for d in _kids(R, r))})

        def walk(el, depth=0):
            if depth > 40:
                return
            if _type(R, el) == "Table":
                table(el)
            for c in _kids(R, el):
                walk(c, depth + 1)

        for i in range(R.FPDF_StructTree_CountChildren(tree)):
            c = R.FPDF_StructTree_GetChildAtIndex(tree, i)
            if c:
                walk(c)
        return found
    finally:
        R.FPDF_StructTree_Close(tree)
