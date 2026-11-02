"""Graphics standards (3.17.0): every picture, chart, drawing and text box in a Word document or PowerPoint deck read
against the profile's graphics rules. Check only: Stationkeeper never re-encodes, resizes or moves a picture.

The rules (std["graphics"]); blank or None means not checked:
  types           picture formats allowed, e.g. ["png", "jpeg", "emf", "svg"]
  min_ppi         the smallest resolution at the size the picture is placed (pixels / placed inches)
  max_width       "margins" (the text width of its section) or "set" (max_width_in inches) or ""
  max_width_in    the set width, in inches
  fonts           fonts allowed for text in drawings, charts, SmartArt and text boxes (blank: the profile's fonts)
  min_text_pt     the smallest text in a drawing, chart or text box (pt)
  ocr_text        estimate the text size inside pictures with the OCR reader (an estimate, flagged as such)
  caption         every figure has a caption next to it
  alt_text        every picture has alt text (a description)
  rgb_only        no CMYK pictures
  max_file_mb     the largest picture file inside the document (MB)

Rules only (No AI); the OCR estimate uses the OCR reader (AI and ML) on this PC. Nothing leaves the PC."""
import io, os, posixpath, re, zipfile
import xml.etree.ElementTree as ET

EMU = 914400.0
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
      "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
      "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
      "rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
W = "{%s}" % NS["w"]
R_EMBED = "{%s}embed" % NS["r"]
R_ID = "{%s}id" % NS["r"]

DEFAULT = {"types": ["png", "jpeg", "emf", "wmf", "svg"], "min_ppi": 150, "max_width": "margins", "max_width_in": None,
           "fonts": [], "min_text_pt": 8, "ocr_text": False, "caption": True, "alt_text": True, "rgb_only": True,
           "max_file_mb": 10}
TYPE_NAMES = {"png": "PNG", "jpeg": "JPEG", "gif": "GIF", "bmp": "BMP", "tiff": "TIFF", "emf": "EMF", "wmf": "WMF", "svg": "SVG",
              "webp": "WebP"}
RULES = {"G1": "Picture type not allowed", "G2": "Resolution below the minimum at its placed size",
         "G3": "Wider than allowed", "G4": "Text in a drawing, chart or text box in a font not allowed",
         "G5": "Text in a drawing, chart or text box smaller than allowed", "G6": "Figure with no caption",
         "G7": "Picture with no alt text", "G8": "CMYK picture", "G9": "Picture file larger than allowed",
         "G10": "Text inside a picture looks smaller than allowed (estimate)"}
_EXT_TYPE = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".jpe": "jpeg", ".gif": "gif", ".bmp": "bmp", ".tif": "tiff",
             ".tiff": "tiff", ".emf": "emf", ".wmf": "wmf", ".svg": "svg", ".webp": "webp"}
VECTOR = {"emf", "wmf", "svg"}


def rules_of(std):
    g = dict(DEFAULT)
    g.update({k: v for k, v in ((std or {}).get("graphics") or {}).items()})
    fr = ((std or {}).get("fonts") or {}).get("graphic") or {}   # the font rules' Graphic row fills what is blank here
    if not g.get("fonts") and fr.get("fonts"):
        g["fonts"] = list(fr["fonts"]) if isinstance(fr["fonts"], list) else [x.strip() for x in str(fr["fonts"]).split(",") if x.strip()]
    if fr.get("min_size") and not ((std or {}).get("graphics") or {}).get("min_text_pt"):
        g["min_text_pt"] = fr["min_size"]
    if not g.get("fonts"):                                   # blank: the profile's body, table and caption fonts
        v = (std or {}).get("variables") or {}
        g["fonts"] = [f for f in dict.fromkeys(v.get(k) for k in ("body_font", "table_font", "caption_font")) if f]
    g["types"] = [str(t).lower().replace("jpg", "jpeg") for t in (g.get("types") or [])]
    return g


def _type_of(name, data):
    t = _EXT_TYPE.get(os.path.splitext(name)[1].lower(), "")
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        t = "png"
    elif data[:3] == b"\xff\xd8\xff":
        t = "jpeg"
    return t


def image_info(data):
    """(width px, height px, mode) of a raster picture, from its header only; (0, 0, "") for vector or unreadable."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        return im.size[0], im.size[1], im.mode
    except Exception:  # noqa: BLE001
        return 0, 0, ""


def _rels(z, part):
    d, b = posixpath.split(part)
    rp = posixpath.join(d, "_rels", b + ".rels")
    out = {}
    if rp not in z.namelist():
        return out
    for r in ET.fromstring(z.read(rp)).findall("rel:Relationship", NS):
        t = r.get("Target", "")
        out[r.get("Id")] = t if r.get("TargetMode") == "External" else posixpath.normpath(posixpath.join(d, t))
    return out


def _text_width(body):
    """Inches of text width for each section, in document order, from w:sectPr (page width less margins)."""
    out = []
    for sp in body.iter(W + "sectPr"):
        pg, mar = sp.find(W + "pgSz"), sp.find(W + "pgMar")
        try:
            wd = int(pg.get(W + "w")) - int(mar.get(W + "left")) - int(mar.get(W + "right"))
            out.append(wd / 1440.0)
        except Exception:  # noqa: BLE001
            out.append(None)
    return out


def _para_text(p):
    return "".join(t.text or "" for t in p.iter(W + "t")).strip()


def _para_style(p):
    ps = p.find(W + "pPr/" + W + "pStyle")
    return ps.get(W + "val", "") if ps is not None else ""


def _is_caption(p, labels=("Figure", "Exhibit", "Graphic", "Table")):
    st = _para_style(p).lower()
    if "caption" in st:
        return True
    t = _para_text(p)
    if any(t.startswith(l + " ") for l in labels):
        return True
    return any(i.text and "SEQ " in i.text for i in p.iter(W + "instrText")) or any("SEQ " in (f.get(W + "instr") or "")
                                                                                     for f in p.iter(W + "fldSimple"))


def _run_fonts(root, ns_text):
    """[(font, size pt)] of the runs inside a drawing part (DrawingML a:rPr) or a text box (w:rPr)."""
    out = []
    for rpr in root.iter("{%s}rPr" % NS["a"]):
        lat = rpr.find("a:latin", NS)
        sz = rpr.get("sz")
        out.append(((lat.get("typeface") if lat is not None else ""), (int(sz) / 100.0) if sz else None))
    for rpr in root.iter(W + "rPr"):
        f = rpr.find(W + "rFonts")
        sz = rpr.find(W + "sz")
        out.append(((f.get(W + "ascii") or f.get(W + "hAnsi") or "") if f is not None else "",
                    (int(sz.get(W + "val")) / 2.0) if sz is not None and sz.get(W + "val", "").isdigit() else None))
    return [(f, s) for f, s in out if not f.startswith("+")]        # +mn-lt / +mj-lt: the theme's font


def _font_findings(fonts, g, where, add):
    allowed = {f.casefold() for f in g.get("fonts") or []}
    bad = sorted({f for f, _s in fonts if f and allowed and f.casefold() not in allowed})
    if bad:
        add("G4", f"Text in {', '.join(bad)}; allowed: {', '.join(g['fonts'])}", where)
    small = [s for _f, s in fonts if s and g.get("min_text_pt") and s < float(g["min_text_pt"]) - 0.01]
    if small:
        add("G5", f"Text at {min(small):g} pt; the smallest allowed is {float(g['min_text_pt']):g} pt", where)


def _picture(z, name, data, cx, cy, descr, label, g, add, width_in):
    t = _type_of(name, data)
    w_in, h_in = cx / EMU, cy / EMU
    if g.get("types") and t and t not in g["types"]:
        add("G1", f"{TYPE_NAMES.get(t, t.upper())}; allowed: {', '.join(TYPE_NAMES.get(x, x.upper()) for x in g['types'])}", label)
    px, py, mode = (0, 0, "") if t in VECTOR else image_info(data)
    ppi = round(min(px / w_in, py / h_in)) if px and w_in > 0 and h_in > 0 else None
    if ppi is not None and g.get("min_ppi") and ppi < float(g["min_ppi"]):
        add("G2", f"{ppi} ppi at {w_in:.2f} x {h_in:.2f} in ({px} x {py} px); the minimum is {float(g['min_ppi']):g} ppi", label)
    lim = (width_in if g.get("max_width") == "margins" else g.get("max_width_in") if g.get("max_width") == "set" else None)
    if lim and w_in > float(lim) + 0.02:
        add("G3", f"{w_in:.2f} in wide; the most is {float(lim):.2f} in", label)
    if g.get("alt_text") and not (descr or "").strip():
        add("G7", "No alt text (description)", label)
    if g.get("rgb_only") and mode == "CMYK":
        add("G8", "The picture is CMYK; use RGB", label)
    if g.get("max_file_mb") and len(data) > float(g["max_file_mb"]) * 1048576:
        add("G9", f"{len(data) / 1048576:.1f} MB; the most is {float(g['max_file_mb']):g} MB", label)
    return {"type": t, "ppi": ppi, "w_in": w_in, "h_in": h_in, "px": (px, py), "data": data}


def check_word(raw, std, add, ocr=None):
    """Every picture, chart and text box of a .docx. add(rule, what, where). Returns the pictures seen."""
    g = rules_of(std)
    z = zipfile.ZipFile(io.BytesIO(raw))
    if "word/document.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    rels = _rels(z, "word/document.xml")
    widths = _text_width(body)
    paras = [p for p in body.iter(W + "p")]
    pos = {id(p): i for i, p in enumerate(paras)}
    # which section each paragraph is in: a paragraph's own sectPr ends a section
    sec_of, s = {}, 0
    for p in paras:
        sec_of[id(p)] = s
        if p.find(W + "pPr/" + W + "sectPr") is not None:
            s += 1
    seen, n = [], 0
    for p in paras:
        for dr in list(p.iter("{%s}inline" % NS["wp"])) + list(p.iter("{%s}anchor" % NS["wp"])):
            n += 1
            seen += _drawing(z, dr, p, paras, pos, rels, g, add, widths, sec_of, ocr, n)
    for tb in root.iter(W + "txbxContent"):                 # text boxes (also inside shapes)
        _font_findings(_run_fonts(tb, True), g, "Text box", add)
    return seen


def _drawing(z, dr, p, paras, pos, rels, g, add, widths, sec_of, ocr, n):
    ext = dr.find("wp:extent", NS)
    cx, cy = (int(ext.get("cx", 0)), int(ext.get("cy", 0))) if ext is not None else (0, 0)
    dp = dr.find("wp:docPr", NS)
    descr = (dp.get("descr") or dp.get("title") or "") if dp is not None else ""
    name = (dp.get("name") if dp is not None else "") or f"Picture {n}"
    near = _para_text(p)[:60]
    label = f"{name}" + (f" (near \"{near}\")" if near else "")
    i = pos[id(p)]
    sec = sec_of.get(id(p), 0)
    width_in = widths[min(sec, len(widths) - 1)] if widths else None
    out = []
    blip = dr.find(".//a:blip", NS)
    chart = dr.find(".//c:chart", NS)
    if blip is not None and rels.get(blip.get(R_EMBED)) in z.namelist():
        part = rels[blip.get(R_EMBED)]
        info = _picture(z, part, z.read(part), cx, cy, descr, label, g, add, width_in)
        info["label"] = label
        out.append(info)
        if g.get("ocr_text") and ocr is not None and info["ppi"]:
            est = ocr(info["data"], info["ppi"])
            if est and g.get("min_text_pt") and est < float(g["min_text_pt"]) - 0.25:
                add("G10", f"Text looks about {est:.0f} pt at its placed size; the smallest allowed is {float(g['min_text_pt']):g} pt", label)
    elif chart is not None and rels.get(chart.get(R_ID)) in z.namelist():
        croot = ET.fromstring(z.read(rels[chart.get(R_ID)]))
        _font_findings(_run_fonts(croot, False), g, label.replace(name, name + " (chart)"), add)
        lim = width_in if g.get("max_width") == "margins" else g.get("max_width_in") if g.get("max_width") == "set" else None
        if lim and cx / EMU > float(lim) + 0.02:
            add("G3", f"{cx / EMU:.2f} in wide; the most is {float(lim):.2f} in", label)
    else:
        _font_findings(_run_fonts(dr, False), g, label, add)       # shapes, SmartArt and groups drawn in place
    if g.get("caption") and (blip is not None or chart is not None):
        near_ps = [paras[k] for k in (i - 1, i + 1, i + 2) if 0 <= k < len(paras)] + [p]
        if not any(_is_caption(x) for x in near_ps):
            add("G6", "No caption next to it", label)
    return out


def check_powerpoint(raw, std, add, ocr=None):
    """Every picture and chart on every slide of a .pptx (placed size against the slide)."""
    g = rules_of(std)
    z = zipfile.ZipFile(io.BytesIO(raw))
    slides = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                    key=lambda n: int(re.findall(r"\d+", n)[-1]))
    seen = []
    pres = ET.fromstring(z.read("ppt/presentation.xml")) if "ppt/presentation.xml" in z.namelist() else None
    sw = None
    if pres is not None and pres.find("p:sldSz", NS) is not None:
        sw = int(pres.find("p:sldSz", NS).get("cx")) / EMU
    for k, sl in enumerate(slides, 1):
        root = ET.fromstring(z.read(sl))
        rels = _rels(z, sl)
        for pic in root.iter("{%s}pic" % NS["p"]):
            blip = pic.find(".//a:blip", NS)
            ext = pic.find(".//a:xfrm/a:ext", NS)
            nv = pic.find(".//p:cNvPr", NS)
            if blip is None or ext is None or rels.get(blip.get(R_EMBED)) not in z.namelist():
                continue
            name = (nv.get("name") if nv is not None else "") or "Picture"
            descr = (nv.get("descr") or nv.get("title") or "") if nv is not None else ""
            label = f"Slide {k}: {name}"
            part = rels[blip.get(R_EMBED)]
            info = _picture(z, part, z.read(part), int(ext.get("cx")), int(ext.get("cy")), descr, label,
                            dict(g, caption=False, max_width="set" if g.get("max_width") else "", max_width_in=g.get("max_width_in") or sw),
                            add, sw)
            info["label"] = label
            seen.append(info)
        for gf in root.iter("{%s}graphicFrame" % NS["p"]):
            ch = gf.find(".//c:chart", NS)
            if ch is not None and rels.get(ch.get(R_ID)) in z.namelist():
                _font_findings(_run_fonts(ET.fromstring(z.read(rels[ch.get(R_ID)])), False), g, f"Slide {k}: chart", add)
    return seen


def ocr_estimate(data, ppi):
    """3.17.0: the typical text size inside a picture, in points at its placed size, from the OCR reader's line boxes
    (the median line height; a line box is about nine tenths of the font size). None when no text is found. An
    estimate, always shown as one."""
    try:
        import numpy as np
        from PIL import Image
        import app_gui as eng
        im = np.array(Image.open(io.BytesIO(data)).convert("RGB"))[:, :, ::-1].copy()
        lines = eng._ocr_lines(im)
    except Exception:  # noqa: BLE001
        return None
    hs = sorted(y1 - y0 for (_x0, y0, _x1, y1, txt, _c) in lines if len(str(txt).strip()) >= 2 and y1 - y0 > 3)
    if not hs or not ppi:
        return None
    return hs[len(hs) // 2] / float(ppi) * 72.0 / 0.9
