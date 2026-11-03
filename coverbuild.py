"""Covers, title pages and back covers built and dressed here (3.34.0), on the kept page files coverlayout reads.

blank(std)                     a blank page as a kept page file: the standard's paper and margins, the cover styles of the
                               fields defined, nothing on it yet
set_background(data, image)    a picture behind the text at page size (full bleed, the default) or inside the margins,
                               locked so authors do not move it by mistake; a page that has one gets the new picture in its
                               place, and every text block stays where it is
take_background(data)          the background picture off
add_block(data, block)         a text block: a box at a place and width on the page holding one line that shows a field
                               (Volume name, Solicitation, Company, a Field of yours) in its cover style, or its own text,
                               with its own size, weight, color, font and alignment
remove_block(data, n)          the nth text block off
design_of(data, std)           the page's structure apart from its look: the paper, where the background goes, and each text
                               block (its place, size, field, words and formatting), from the blocks made here, an imported
                               cover's text boxes and its floating tables
from_design(design, std)       a page built from a design, with a background picture when one is given
Pages are small Word files (prodparts keeps and places them). Everything is written as Word writes it; the files given
are read, never changed. Rules only; nothing leaves the PC."""
import copy, io, re, zipfile
from xml.sax.saxutils import escape

from lxml import etree

import coverlayout as CL

W = CL.W
WP = CL.WP
A = CL.A
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
EMU, TW = CL.EMU, CL.TW
BG_NAME = "SK Background"
BLOCK = "SK Text block"
IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "emf": "image/x-emf", "gif": "image/gif",
               "bmp": "image/bmp", "tif": "image/tiff", "tiff": "image/tiff"}
PAPER = {"letter": (8.5, 11.0), "legal": (8.5, 14.0), "a4": (8.27, 11.69), "tabloid": (11.0, 17.0)}
MODES = (("bleed", "Full bleed (to the page edge)"), ("margins", "Inside the margins"))


def w(tag):
    return f"{{{W}}}{tag}"


# ------------------------------------------------------------------ a blank page
def page_of(std):
    """(width, height, {"top", "bottom", "left", "right"}) in inches from the standard's base values."""
    v = (std or {}).get("variables") or {}
    pw, ph = PAPER.get(str(v.get("paper") or "Letter").strip().lower(), (8.5, 11.0))
    m = {k: float(v.get(f"margin_{k}") or 1.0) for k in ("top", "bottom", "left", "right")}
    return pw, ph, m


def _style_xml(sid, name, size=None, bold=False):
    rpr = ("<w:b/>" if bold else "") + (f'<w:sz w:val="{int(size * 2)}"/>' if size else "")
    return (f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{escape(name)}"/>'
            f'<w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>'
            f'{"<w:rPr>" + rpr + "</w:rPr>" if rpr else ""}</w:style>')


def blank(std=None, size=None):
    """A blank page as a kept page file (bytes). size: (width, height, margins) to use instead of the standard's."""
    pw, ph, m = size or page_of(std)
    styles = "".join(_style_xml(CL.style_id(s), s, 28 if k == "volume_name" else 14, k == "volume_name")
                     for k, _l, s in CL.fields(std))
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}" xmlns:r="{R}" '
           f'xmlns:wp="{WP}" xmlns:a="{A}" xmlns:pic="{PIC}"><w:body><w:p/>'
           f'<w:sectPr><w:pgSz w:w="{int(round(pw * TW))}" w:h="{int(round(ph * TW))}"/>'
           f'<w:pgMar w:top="{int(round(m["top"] * TW))}" w:right="{int(round(m["right"] * TW))}" w:bottom="{int(round(m["bottom"] * TW))}" '
           f'w:left="{int(round(m["left"] * TW))}" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    st = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}"><w:style w:type="paragraph" w:default="1" '
          f'w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>{styles}</w:styles>')
    ct = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="{CT}">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    rels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL}">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>')
    drels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{REL}">'
             f'<Relationship Id="rId1" Type="{R}/styles" Target="styles.xml"/></Relationships>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        z.writestr("word/_rels/document.xml.rels", drels)
        z.writestr("word/styles.xml", st)
    return buf.getvalue()


# ------------------------------------------------------------------ reading and writing a page file
def _open(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    files = {n: z.read(n) for n in z.namelist()}
    root = etree.fromstring(files["word/document.xml"])
    rn = "word/_rels/document.xml.rels"
    rels = etree.fromstring(files[rn]) if rn in files else etree.Element(f"{{{REL}}}Relationships")
    return z, files, root, rels


def _close(z, files, root, rels):
    files["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    files["word/_rels/document.xml.rels"] = etree.tostring(rels, xml_declaration=True, encoding="UTF-8", standalone=True)
    buf = io.BytesIO()
    order = [n for n in z.namelist()] + [n for n in files if n not in z.namelist()]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zo:
        for n in order:
            zo.writestr(n, files[n])
    return buf.getvalue()


def _body(root):
    return root.find(w("body"))


def _first_para(body):
    """The body's first paragraph (a new one at the top when the page starts with something else)."""
    first = next(iter(body), None)
    if first is not None and first.tag == w("p") and first.find(w("pPr") + "/" + w("sectPr")) is None:
        return first
    p = etree.Element(w("p"))
    body.insert(0, p)
    return p


def _next_id(root):
    ids = [int(d.get("id")) for d in root.iter(f"{{{WP}}}docPr") if (d.get("id") or "").isdigit()]
    return max(ids + [0]) + 1


def _background(root):
    for an in root.iter(f"{{{WP}}}anchor"):
        dp = an.find(f"{{{WP}}}docPr")
        if dp is not None and dp.get("name") == BG_NAME:
            return an
    return None


def _area(page, mode):
    m = page["margins"]
    if mode == "margins":
        return m["left"], m["top"], page["w"] - m["left"] - m["right"], page["h"] - m["top"] - m["bottom"]
    return 0.0, 0.0, page["w"], page["h"]


def has_background(data):
    return _background(_open(data)[2]) is not None


def background_mode(data):
    """'bleed', 'margins' or '' (no background picture)."""
    root = _open(data)[2]
    an = _background(root)
    if an is None:
        return ""
    off = an.find(f"{{{WP}}}positionH/{{{WP}}}posOffset")
    return "bleed" if off is None or int(off.text or 0) == 0 else "margins"


def set_background(data, image, ext="png", mode="bleed"):
    """A copy of the page with image (bytes) behind the text: full bleed or inside the margins, locked, in front of
    nothing. A page that has a background picture gets this one in its place."""
    ext = ext.lower().lstrip(".")
    if ext not in IMAGE_TYPES:
        raise ValueError("Use a PNG, JPG, EMF, GIF, BMP or TIFF picture.")
    z, files, root, rels = _open(data)
    page = CL._page(root)
    n = 1
    while f"word/media/sk_bg{n}.{ext}" in files:
        n += 1
    media = f"word/media/sk_bg{n}.{ext}"
    files[media] = image
    ct = etree.fromstring(files["[Content_Types].xml"])
    if ext not in {d.get("Extension", "").lower() for d in ct.findall(f"{{{CT}}}Default")}:
        d = etree.SubElement(ct, f"{{{CT}}}Default"); d.set("Extension", ext); d.set("ContentType", IMAGE_TYPES[ext])
        files["[Content_Types].xml"] = etree.tostring(ct, xml_declaration=True, encoding="UTF-8", standalone=True)
    ids = {r.get("Id") for r in rels}
    k = 1
    while f"rIdSKBG{k}" in ids:
        k += 1
    rid = f"rIdSKBG{k}"
    r = etree.SubElement(rels, f"{{{REL}}}Relationship"); r.set("Id", rid); r.set("Type", f"{R}/image"); r.set("Target", media[5:])
    x, y, cw, ch = _area(page, mode)
    an = _background(root)
    if an is not None:                                  # the picture changes; its place follows the mode
        an.find(f".//{{{A}}}blip").set(f"{{{R}}}embed", rid)
        _place(an, x, y, cw, ch)
    else:
        nid = _next_id(root)
        frag = (f'<w:r xmlns:w="{W}"><w:drawing><wp:anchor xmlns:wp="{WP}" distT="0" distB="0" distL="0" distR="0" simplePos="0" '
                f'relativeHeight="0" behindDoc="1" locked="1" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/>'
                f'<wp:positionH relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionH>'
                f'<wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionV>'
                f'<wp:extent cx="0" cy="0"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>'
                f'<wp:docPr id="{nid}" name="{BG_NAME}" descr="Background picture"/>'
                f'<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="{A}" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
                f'<a:graphic xmlns:a="{A}"><a:graphicData uri="{PIC}"><pic:pic xmlns:pic="{PIC}"><pic:nvPicPr>'
                f'<pic:cNvPr id="{nid}" name="{BG_NAME}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill>'
                f'<a:blip xmlns:r="{R}" r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
                f'</pic:spPr></pic:pic></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r>')
        run = etree.fromstring(frag)
        p = _first_para(_body(root))
        ppr = p.find(w("pPr"))
        (ppr.addnext(run) if ppr is not None else p.insert(0, run))
        _place(run.find(f".//{{{WP}}}anchor"), x, y, cw, ch)
    return _close(z, files, root, rels)


def _place(an, x, y, cw, ch):
    for axis, val in (("H", x), ("V", y)):
        ph = an.find(f"{{{WP}}}position{axis}")
        for c in list(ph):
            ph.remove(c)
        ph.set("relativeFrom", "page")
        off = etree.SubElement(ph, f"{{{WP}}}posOffset"); off.text = str(int(round(val * EMU)))
    cx, cy = str(int(round(cw * EMU))), str(int(round(ch * EMU)))
    an.find(f"{{{WP}}}extent").set("cx", cx); an.find(f"{{{WP}}}extent").set("cy", cy)
    e = an.find(f".//{{{A}}}xfrm/{{{A}}}ext")
    if e is not None:
        e.set("cx", cx); e.set("cy", cy)


def take_background(data):
    """A copy of the page with its background picture off."""
    z, files, root, rels = _open(data)
    an = _background(root)
    if an is None:
        return data
    run = an
    while run is not None and run.tag != w("r"):
        run = run.getparent()
    if run is not None:
        run.getparent().remove(run)
    return _close(z, files, root, rels)


# ------------------------------------------------------------------ text blocks
def _block_xml(b, std=None):
    styles = {k: s for k, _l, s in CL.fields(std)}
    labels = {k: lab for k, lab, _s in CL.fields(std)}
    x, y = float(b.get("x") or 1.0), float(b.get("y") or 1.0)
    wd, ht = float(b.get("w") or 6.5), float(b.get("h") or 0.5)
    field = b.get("field") or ""
    text = b.get("text") or (f"[{labels.get(field, field)}]" if field else "Text")
    ps = f'<w:pStyle w:val="{CL.style_id(styles[field])}"/>' if field in styles else ""
    jc = {"left": "left", "center": "center", "right": "right"}.get(b.get("align") or "left", "left")
    rpr = ""
    if b.get("font"):
        f = escape(str(b["font"]), {'"': "&quot;"})
        rpr += f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}"/>'
    if b.get("bold"):
        rpr += "<w:b/>"
    if b.get("color"):
        rpr += f'<w:color w:val="{re.sub(r"[^0-9A-Fa-f]", "", str(b["color"]))[:6] or "000000"}"/>'
    if b.get("size"):
        rpr += f'<w:sz w:val="{int(round(float(b["size"]) * 2))}"/><w:szCs w:val="{int(round(float(b["size"]) * 2))}"/>'
    none = "".join(f'<w:{e} w:val="nil"/>' for e in ("top", "left", "bottom", "right", "insideH", "insideV"))
    tw_ = int(round(wd * TW))
    return (f'<w:tbl xmlns:w="{W}"><w:tblPr><w:tblpPr w:leftFromText="0" w:rightFromText="0" w:vertAnchor="page" w:horzAnchor="page" '
            f'w:tblpX="{int(round(x * TW))}" w:tblpY="{int(round(y * TW))}"/><w:tblOverlap w:val="overlap"/>'
            f'<w:tblW w:w="{tw_}" w:type="dxa"/><w:tblBorders>{none}</w:tblBorders><w:tblLayout w:type="fixed"/>'
            f'<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
            f'<w:tblCaption w:val="{BLOCK}"/></w:tblPr><w:tblGrid><w:gridCol w:w="{tw_}"/></w:tblGrid>'
            f'<w:tr><w:trPr><w:trHeight w:val="{int(round(ht * TW))}"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="{tw_}" w:type="dxa"/></w:tcPr>'
            f'<w:p><w:pPr>{ps}<w:jc w:val="{jc}"/></w:pPr><w:r>{"<w:rPr>" + rpr + "</w:rPr>" if rpr else ""}'
            f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')


def blocks(root):
    """The text blocks made here, in order."""
    out = []
    for t in _body(root).findall(w("tbl")):
        cap = t.find(f"{w('tblPr')}/{w('tblCaption')}")
        if cap is not None and cap.get(w("val")) == BLOCK:
            out.append(t)
    return out


def add_block(data, block, std=None):
    """A copy of the page with a text block added: {"field" or "text", "x", "y", "w", "h" (inches from the page's top
    left corner), "align", "size", "bold", "color", "font"}."""
    z, files, root, rels = _open(data)
    body = _body(root)
    t = etree.fromstring(_block_xml(block, std))
    final = body.find(w("sectPr"))
    holder = etree.Element(w("p"))                      # a paragraph after each table keeps Word from joining them
    if final is not None:
        final.addprevious(t); final.addprevious(holder)
    else:
        body.append(t); body.append(holder)
    return _close(z, files, root, rels)


def remove_block(data, n):
    """A copy of the page with its nth text block (0 first) off."""
    z, files, root, rels = _open(data)
    bs = blocks(root)
    if not 0 <= n < len(bs):
        return data
    t = bs[n]
    nxt = t.getnext()
    if nxt is not None and nxt.tag == w("p") and not "".join(nxt.itertext()).strip() and nxt.find(f"{w('pPr')}/{w('sectPr')}") is None:
        nxt.getparent().remove(nxt)
    t.getparent().remove(t)
    return _close(z, files, root, rels)


# ------------------------------------------------------------------ designs
def _rfmt(p):
    r = p.find(f".//{w('r')}/{w('rPr')}")
    out = {}
    if r is None:
        return out
    f = r.find(w("rFonts"))
    if f is not None and f.get(w("ascii")):
        out["font"] = f.get(w("ascii"))
    if r.find(w("b")) is not None and r.find(w("b")).get(w("val")) not in ("0", "false"):
        out["bold"] = True
    c = r.find(w("color"))
    if c is not None and c.get(w("val")) not in (None, "auto"):
        out["color"] = c.get(w("val"))
    s = r.find(w("sz"))
    if s is not None and (s.get(w("val")) or "").isdigit():
        out["size"] = int(s.get(w("val"))) / 2
    return out


def design_of(data, std=None):
    """{"page": {"w", "h", "margins"}, "background": "bleed"|"margins"|"", "blocks": [...], "left_out": n}: the page's
    structure apart from its look. Blocks come from the text blocks made here, an imported cover's text boxes and its
    floating tables (each with its first line's field, words and formatting); text in the page's flow is counted in
    left_out, as it has no place of its own."""
    root = _open(data)[2]
    page = CL._page(root)
    by_style = {CL.style_id(s): k for k, _l, s in CL.fields(std)}
    out = []

    def para_block(p, x, y, wd, ht):
        ps = p.find(f"{w('pPr')}/{w('pStyle')}") if p is not None else None
        jc = p.find(f"{w('pPr')}/{w('jc')}") if p is not None else None
        field = by_style.get(ps.get(w("val"))) if ps is not None else None
        b = {"x": round(x, 3), "y": round(y, 3), "w": round(wd, 3), "h": round(ht, 3), "field": field or "",
             "text": "" if field else (CL._own_text(p) if p is not None else ""), "align": (jc.get(w("val")) if jc is not None else "left")}
        b.update(_rfmt(p) if p is not None else {})
        out.append(b)
    for t in _body(root).iter(w("tbl")):
        tp = t.find(f"{w('tblPr')}/{w('tblpPr')}")
        if tp is None:
            continue
        m = page["margins"]
        x = int(tp.get(w("tblpX"), 0)) / TW + (0 if tp.get(w("horzAnchor")) == "page" else m["left"])
        y = int(tp.get(w("tblpY"), 0)) / TW + (0 if tp.get(w("vertAnchor")) == "page" else m["top"])
        tw_ = t.find(f"{w('tblPr')}/{w('tblW')}")
        wd = int(tw_.get(w("w"), 0)) / TW if tw_ is not None and tw_.get(w("type")) == "dxa" else 6.5
        th = t.find(f".//{w('trHeight')}")
        ht = int(th.get(w("val"), 0)) / TW if th is not None else 0.4 * len(t.findall(w("tr")))
        p = next((pp for pp in t.iter(w("p")) if CL._own_text(pp)), t.find(f".//{w('p')}"))
        para_block(p, x, y, wd, ht)
    for an in _body(root).iter(f"{{{WP}}}anchor"):
        tb = an.find(f".//{{{CL.WPS}}}txbx")
        if tb is None:
            continue
        ext = an.find(f"{{{WP}}}extent")
        wd, ht = (int(ext.get("cx", 0)) / EMU, int(ext.get("cy", 0)) / EMU) if ext is not None else (2.0, 0.5)
        x, _r, _a = CL._pos(an, "H", page, wd)
        y, _r, _a = CL._pos(an, "V", page, ht)
        p = next((pp for pp in tb.iter(w("p")) if CL._own_text(pp)), tb.find(f".//{w('p')}"))
        para_block(p, x, y, wd, ht)
    flow = [p for p in _body(root).findall(w("p")) if CL._own_text(p)]
    out.sort(key=lambda b: (b["y"], b["x"]))
    return {"page": page, "background": background_mode(data), "blocks": out, "left_out": len(flow)}


def from_design(design, std=None, image=None, ext="png"):
    """A page built from a design: its paper and margins, its text blocks, and the background picture when given."""
    pg = (design or {}).get("page") or {}
    size = (float(pg.get("w") or 8.5), float(pg.get("h") or 11.0), dict(pg.get("margins") or {"top": 1, "bottom": 1, "left": 1, "right": 1}))
    data = blank(std, size)
    for b in (design or {}).get("blocks") or []:
        data = add_block(data, b, std)
    if image is not None:
        data = set_background(data, image, ext, (design or {}).get("background") or "bleed")
    return data
