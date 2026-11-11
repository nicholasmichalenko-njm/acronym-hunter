"""Redline's copy of a slide deck saved as PDF (4.15.0; claude/stationkeeper-pdf-fidelity-plan-4.13.html, 4.15.0).

A slide is not a page of running text: its text sits in boxes placed anywhere, over pictures, charts and shapes. The
copy keeps each slide as one Word page the slide's size:
- the slide drawn without its text (PDFium takes the text objects off a copy of the page and draws the rest: pictures,
  charts, shapes, a table's shading) is a picture behind the page;
- each box of text is a Word frame at its place on the slide, its paragraphs at their size, weight and color, bullets
  and their levels as written. Frames keep their text in the document's own text, so Track Changes, comments, Check and
  Exceptions read it as they read any paragraph (text boxes would not);
- the boxes read title first, then top to bottom, left to right.
is_slides(pdf): a deck saved by PowerPoint or Impress, or wide pages with little, large text.
Rules only (No AI); nothing leaves the PC."""
import base64, ctypes, datetime, io, json, os, re, statistics, zipfile

import pagesent as PS

EMU = 12700                                   # per point
TW = 20
DPI = 150
MARK = re.compile(r"^(•|▪|◦|–|—|-|❖|➢|✓|o|\d{1,2}[.)]|[a-z][.)])\s")


def _meta(pdf):
    import pypdfium2 as pdfium
    try:
        d = pdfium.PdfDocument(pdf)
    except Exception:  # noqa: BLE001
        return {}, []
    try:
        return d.get_metadata_dict(), [d[i].get_size() for i in range(len(d))]
    finally:
        d.close()


def is_slides(pdf, doc=None):
    meta, sizes = _meta(pdf)
    made = (meta.get("Creator", "") + " " + meta.get("Producer", "")).lower()
    if "powerpoint" in made or "impress" in made:
        return True
    if not sizes or not all(w > h * 1.2 for w, h in sizes):
        return False
    doc = doc or PS.doc_of(pdf)
    lines = [ln for p in doc["pages"] for ln in p["lines"]]
    if not lines:
        return False
    per_page = len(lines) / max(1, len(doc["pages"]))
    return per_page <= 25 and statistics.median(ln.get("size") or 0 for ln in lines) >= 16


def _pieces(page, skip_page=()):
    """The page's pieces of text: a line split at its wide gaps (cells of a row, two columns)."""
    out = []
    for li, ln in enumerate(page["lines"]):
        if li in skip_page:
            continue
        segs = ln.get("segs") or [(ln["box"][0], ln["box"][2], ln["text"])]
        for a, b, t in segs:
            if t.strip():
                out.append({"box": (a, ln["box"][1], b, ln["box"][3]), "text": " ".join(t.split()), "size": ln.get("size") or 12,
                            "bold": ln.get("bold", False), "line": li, "a": ln.get("a", 0)})
    return out


def blocks(page, skip_page=()):
    """The page's boxes of text: [{"box", "paras": [{"text", "size", "bold", "x"}]}] in reading order."""
    pieces = sorted(_pieces(page, skip_page), key=lambda p: (p["box"][1], p["box"][0]))
    bl = []
    for p in pieces:
        h = p["box"][3] - p["box"][1]
        home = None
        for b in bl:
            last = b["items"][-1]
            gap = p["box"][1] - last["box"][3]
            over = min(p["box"][2], b["box"][2]) - max(p["box"][0], b["box"][0])
            if -0.5 * h < gap < 0.9 * h and over > 0 and 0.6 < p["size"] / max(1, last["size"]) < 1.6:
                home = b
        if home is None:
            bl.append({"items": [p], "box": p["box"]})
        else:
            home["items"].append(p)
            bx = home["box"]
            home["box"] = (min(bx[0], p["box"][0]), min(bx[1], p["box"][1]), max(bx[2], p["box"][2]), max(bx[3], p["box"][3]))
    out = []
    for b in bl:
        paras = []
        for p in b["items"]:
            if paras and not MARK.match(p["text"]) and p["box"][0] >= paras[-1]["x"] - 2 and abs(p["size"] - paras[-1]["size"]) < 1:
                import redlinecopy as RC
                paras[-1]["text"] = RC.join_lines([paras[-1]["text"], p["text"]])
                paras[-1]["tops"].append(p["box"][1])
            else:
                paras.append({"text": p["text"], "size": p["size"], "bold": p["bold"], "x": p["box"][0], "tops": [p["box"][1]],
                              "a": p["a"]})
        for q in paras:                            # line to line, and the space above each paragraph
            d = [b2 - b1 for b1, b2 in zip(q["tops"], q["tops"][1:])]
            q["pitch"] = round(sorted(d)[len(d) // 2], 2) if d else round(1.2 * q["size"], 2)
        for q0, q1 in zip(paras, paras[1:]):
            q1["before"] = round(max(0.0, q1["tops"][0] - q0["tops"][-1] - q0["pitch"]), 2)
        out.append({"box": b["box"], "paras": paras})
    if out:                                        # the title first: the largest text in the top third
        top = [b for b in out if b["box"][1] < 0.34 * (page.get("h") or 540)]
        title = max(top, key=lambda b: b["paras"][0]["size"], default=None)
    else:
        title = None
    rest = sorted((b for b in out if b is not title), key=lambda b: (round(b["box"][1] / 12), b["box"][0]))
    return ([title] if title else []) + rest


def plan(pdf, name=None):
    """{"slides": [{"w", "h", "blocks"}], "paragraphs": [{"kind", "text", "page"}] (the words in reading order)}."""
    name = name or os.path.basename(pdf)
    doc = PS.doc_of(pdf)
    extra, _force = PS.decided(pdf, name)
    slides, paras = [], []
    import redlinelayout as RL
    for pi, page in enumerate(doc["pages"]):
        skip = {li for (p, li) in extra if p == pi}
        bl = blocks(page, skip)
        for b in bl:                                   # the weight and color each paragraph was set in
            for p in b["paras"]:
                bold, color = RL.line_style(pdf, pi, p.pop("a", 0))
                p["bold"], p["color"] = p["bold"] or bold, color
        slides.append({"w": page["w"], "h": page["h"], "blocks": bl})
        for k, b in enumerate(bl):
            for p in b["paras"]:
                paras.append({"kind": "heading" if k == 0 and b is bl[0] and p is b["paras"][0] else "text", "level": 1,
                              "text": p["text"], "page": pi + 1})
    aside = [(pi + 1, doc["pages"][pi]["lines"][li]["text"].strip()) for pi, li in sorted(extra)
             if pi < len(doc["pages"]) and li < len(doc["pages"][pi]["lines"])]
    return slides, paras, aside


def background(pdf, index, dpi=DPI):
    """PNG bytes of the slide drawn without its text."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as R
    d = pdfium.PdfDocument(pdf)
    try:
        page = d[index]

        def strip(container, form=False):
            n = R.FPDFFormObj_CountObjects(container) if form else R.FPDFPage_CountObjects(page.raw)
            for i in range(n - 1, -1, -1):
                obj = R.FPDFFormObj_GetObject(container, i) if form else R.FPDFPage_GetObject(page.raw, i)
                t = R.FPDFPageObj_GetType(obj)
                if t == R.FPDF_PAGEOBJ_TEXT:
                    if (R.FPDFFormObj_RemoveObject(container, obj) if form else R.FPDFPage_RemoveObject(page.raw, obj)):
                        R.FPDFPageObj_Destroy(obj)
                elif t == R.FPDF_PAGEOBJ_FORM:
                    strip(obj, True)
        strip(page.raw)
        R.FPDFPage_GenerateContent(page.raw)
        img = page.render(scale=dpi / 72).to_pil().convert("RGB")
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        return buf.getvalue()
    finally:
        d.close()


def _x(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _picture(rid, n, w, h):
    cx, cy = int(w * EMU), int(h * EMU)
    return ('<w:r><w:drawing><wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="0" behindDoc="1" '
            'locked="1" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="page"><wp:posOffset>0'
            '</wp:posOffset></wp:positionH><wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionV>'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>'
            f'<wp:docPr id="{n}" name="Slide {n}"/><wp:cNvGraphicFramePr/><a:graphic><a:graphicData '
            'uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr>'
            f'<pic:cNvPr id="{n}" name="slide{n}.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="{rid}"/>'
            '<a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/>'
            f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
            '</a:graphicData></a:graphic></wp:anchor></w:drawing></w:r>')


def _frame(b, p, k, slide_w):
    """One paragraph of a box. Every paragraph of a box carries the same frame, so Word keeps them in one frame, one
    under the other, each with the space above it and its line to line spacing as on the slide."""
    l, t, r, bt = b["box"]
    pad = 2.0
    first = b["paras"][0]
    w = min(slide_w - l + pad, (r - l) + 2 * pad + 0.06 * (r - l))      # room for a font a little wider than the PDF's
    lead = max(0.0, first["pitch"] - first["size"]) / 2 + 0.2 * first["size"]
    fp = (f'<w:framePr w:w="{int(w * TW)}" w:h="{int((bt - t) * TW)}" w:hRule="atLeast" w:wrap="around" '
          f'w:vAnchor="page" w:hAnchor="page" w:x="{int((l - pad) * TW)}" w:y="{int((t - lead) * TW)}"/>')
    ind = int(max(0.0, p["x"] - l) * TW)
    rpr = ("<w:b/>" if p.get("bold") else "") + (f'<w:color w:val="{_x(p["color"])}"/>' if p.get("color") else "") \
        + f'<w:sz w:val="{int(round(p["size"] * 2))}"/>'
    sp = f'<w:spacing w:before="{int(p.get("before", 0) * TW)}" w:after="0" w:line="{int(p["pitch"] * TW)}" w:lineRule="exact"/>'
    return (f'<w:p><w:pPr>{fp}{sp}' + (f'<w:ind w:left="{ind}"/>' if ind else "")
            + f'</w:pPr><w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{_x(p["text"])}</w:t></w:r></w:p>')


NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')


def build(pdf, out, name=None, sidecar_format=1):
    """Write the slide copy to out and its sidecar (as redlinecopy.build does). Returns the same summary."""
    import redlinecopy as RC
    import redlinelayout as RL
    slides, paras, aside = plan(pdf, name)
    if not paras:
        raise ValueError("The PDF has no typed text the copy could be made from.")
    font = RL.body_font(pdf)
    body, rels, media = [], [], []
    for n, s in enumerate(slides, 1):
        rid = f"rIdS{n}"
        media.append((f"media/slide{n}.png", background(pdf, n - 1)))
        rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                    f'Target="media/slide{n}.png"/>')
        for k, b in enumerate(s["blocks"]):
            for p in b["paras"]:
                body.append(_frame(b, p, k, s["w"]))
        brk = '<w:pageBreakBefore/>' if n > 1 else ""
        body.append(f'<w:p><w:pPr>{brk}<w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/></w:pPr>'
                    f'{_picture(rid, n, s["w"], s["h"])}</w:p>')
    w0, h0 = slides[0]["w"], slides[0]["h"]
    sect = (f'<w:sectPr><w:pgSz w:w="{int(w0 * TW)}" w:h="{int(h0 * TW)}" w:orient="landscape"/>'
            '<w:pgMar w:top="0" w:right="0" w:bottom="0" w:left="0" w:header="0" w:footer="0" w:gutter="0"/></w:sectPr>')
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>{"".join(body)}{sect}</w:body></w:document>'
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{_x(font)}" w:hAnsi="{_x(font)}" w:cs="{_x(font)}"/><w:sz w:val="24"/>'
              '</w:rPr></w:rPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
              '<w:qFormat/></w:style></w:styles>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships '
                   'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" '
                   'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                   '</Relationships>')
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships '
                   'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" '
                   'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                   + "".join(rels) + "</Relationships>")
        for path, data in media:
            z.writestr("word/" + path, data)
    side = {"format": sidecar_format, "layout": "slides", "source": os.path.basename(pdf), "source_sha256": RC._sha(pdf),
            "made": datetime.datetime.now().isoformat(timespec="seconds"), "paragraphs": paras,
            "set_aside": [list(x) for x in aside]}
    with open(out + RC.SIDE, "w", encoding="utf-8") as f:
        json.dump(side, f, indent=1, ensure_ascii=False)
    return {"path": out, "paragraphs": len(paras), "headings": sum(1 for p in paras if p["kind"] == "heading"), "tables": 0,
            "set_aside": len(aside), "slides": len(slides)}
