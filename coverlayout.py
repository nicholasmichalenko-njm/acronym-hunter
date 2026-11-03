"""The cover layout (3.27.0): what a kept cover or back cover page is built from, where each piece sits, and changes to
it written into a new copy (the kept file and every original stay as they are).

read(data)            the page and its pieces: pictures, text boxes and shapes (floating or in the text), floating
                      and inline tables, and the paragraphs with text (on the page, in a text box, in a table cell),
                      each with its place and size in inches where Word fixes one, and the field it shows
apply(data, changes)  a copy of the cover with pieces moved or resized (floating ones: from the page's top left
                      corner) and paragraphs set to show a field (their style becomes the field's cover style, so
                      every STYLEREF to it in headers, footers and Quick Parts reads it)
Older shapes (VML) are listed and left as they are. Rules only; nothing leaves the PC."""
import io
import re
import zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
V = "urn:schemas-microsoft-com:vml"
NS = {"w": W, "wp": WP, "a": A, "wps": WPS, "v": V}
EMU, TW = 914400.0, 1440.0
BUILTIN = {"volume_name": "PE Volume Name", "solicitation": "PE Solicitation", "company": "PE Company",
           "classification": "PE Classification", "project": "PE Project Name"}
BUILTIN_NAMES = {"volume_name": "Volume name", "solicitation": "Solicitation", "company": "Company",
                 "classification": "Classification", "project": "Project"}


def w(tag):
    return f"{{{W}}}{tag}"


def style_id(name):
    return re.sub(r"[^A-Za-z0-9]", "", name or "") or "SKFill"


def fields(std=None):
    """[(key, label, cover style)]: the built-in volume values and the standard's STYLEREF fields."""
    out = [(k, BUILTIN_NAMES[k], s) for k, s in BUILTIN.items()]
    try:
        import fillins as FI
        out += [(f["key"], f["name"], f["style"]) for f in FI.custom(std or {}) if f["kind"] == "styleref"]
    except ImportError:
        pass
    return out


def _doc(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    return etree.fromstring(z.read("word/document.xml"))


def _page(root):
    sp = root.find(".//w:body/w:sectPr", NS)
    if sp is None:
        sps = root.findall(".//w:sectPr", NS)
        sp = sps[-1] if sps else None
    pw, ph, m = 8.5, 11.0, {"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0}
    if sp is not None:
        sz = sp.find("w:pgSz", NS)
        if sz is not None:
            pw = int(sz.get(w("w"), 12240)) / TW; ph = int(sz.get(w("h"), 15840)) / TW
        mar = sp.find("w:pgMar", NS)
        if mar is not None:
            for k in m:
                try:
                    m[k] = int(mar.get(w(k), int(m[k] * TW))) / TW
                except ValueError:
                    pass
    return {"w": pw, "h": ph, "margins": m}


def _text(el):
    return "".join(t.text or "" for t in el.iter(w("t"))).strip()


def _own_text(p):
    """A paragraph's own words (not those of a text box anchored in it)."""
    out = []
    for t in p.iter(w("t")):
        a = t.getparent()
        while a is not None and a.tag != w("p"):
            a = a.getparent()
        if a is p:
            out.append(t.text or "")
    return "".join(out).strip()


def _paras(body):
    return [(p, _own_text(p)) for p in body.iter(w("p")) if _own_text(p)]


def _pos(anchor, axis, page, size=None):
    """The absolute place (inches from the page's top or left edge) of a floating piece on one axis."""
    ph = anchor.find(f"wp:position{axis}", NS)
    if ph is None:
        return 0.0, "page", None
    rel = ph.get("relativeFrom") or "page"
    off = ph.find("wp:posOffset", NS)
    al = ph.find("wp:align", NS)
    m = page["margins"]
    base = 0.0
    if rel in ("margin", "column", "paragraph", "line", "insideMargin"):
        base = m["left"] if axis == "H" else m["top"]
    if off is not None:
        return base + int(off.text or 0) / EMU, rel, None
    a = (al.text or "").strip() if al is not None else ""
    span = (page["w"] - m["left"] - m["right"]) if axis == "H" else (page["h"] - m["top"] - m["bottom"])
    if rel == "page":
        span = page["w"] if axis == "H" else page["h"]
    if a in ("center", "right", "bottom") and size:
        base += (span - size) / (2 if a == "center" else 1)
    return base, rel, a or None


def _bind(p, by_style):
    ps = p.find("w:pPr/w:pStyle", NS)
    return by_style.get(ps.get(w("val"))) if ps is not None else None


def read(data, std=None):
    """{"page": {"w", "h", "margins"}, "pieces": [...]} for a cover's Word file (bytes)."""
    root = _doc(data)
    page = _page(root)
    by_style = {style_id(s): k for k, _l, s in fields(std)}
    pieces = []
    body = root.find("w:body", NS)
    n = {"picture": 0, "textbox": 0, "shape": 0, "table": 0, "paragraph": 0, "older": 0}

    def add(kind, **kw):
        n[kind] += 1
        d = {"id": f"{kind}{n[kind]}", "kind": kind, "floating": False, "x": None, "y": None, "w": None, "h": None,
             "text": "", "field": None, "where": "page", "movable": False}
        d.update(kw)
        pieces.append(d)
        return d
    for dr in body.iter(f"{{{W}}}drawing"):
        an = dr.find("wp:anchor", NS)
        il = dr.find("wp:inline", NS)
        node = an if an is not None else il
        if node is None:
            continue
        ext = node.find("wp:extent", NS)
        cw = int(ext.get("cx", 0)) / EMU if ext is not None else None
        ch = int(ext.get("cy", 0)) / EMU if ext is not None else None
        tb = node.find(".//wps:txbx", NS)
        kind = "textbox" if tb is not None else ("picture" if node.find(".//a:graphicData/*", NS) is not None and
                                                 etree.QName(node.find(".//a:graphicData/*", NS)).localname == "pic" else "shape")
        name = (node.find("wp:docPr", NS).get("name") if node.find("wp:docPr", NS) is not None else "") or kind
        bl = node.find(".//a:blip", NS)
        d = add(kind, w=cw, h=ch, text=(_text(tb) if tb is not None else name)[:80],
                embed=bl.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed") if bl is not None else None)
        if an is not None:
            x, rx, ax = _pos(an, "H", page, cw)
            y, ry, ay = _pos(an, "V", page, ch)
            d.update(floating=True, x=x, y=y, movable=True, behind=an.get("behindDoc") == "1",
                     align=(ax or ay))
    for _ in body.iter(f"{{{V}}}shape"):
        add("older", text="An older shape (kept as it is)")
    for t in body.iter(w("tbl")):
        if t.getparent() is not None and t.getparent().tag != w("body") and etree.QName(t.getparent()).localname != "txbxContent":
            continue
        tp = t.find("w:tblPr/w:tblpPr", NS)
        tw = t.find("w:tblPr/w:tblW", NS)
        width = int(tw.get(w("w"), 0)) / TW if tw is not None and tw.get(w("type")) == "dxa" else None
        rows = len(t.findall("w:tr", NS))
        d = add("table", w=width, h=round(rows * 0.3, 2), text=_text(t)[:80], rows=rows)
        if tp is not None:
            d.update(floating=True, movable=True, x=int(tp.get(w("tblpX"), 0)) / TW + (page["margins"]["left"] if tp.get(w("horzAnchor")) in (None, "text", "margin") else 0),
                     y=int(tp.get(w("tblpY"), 0)) / TW + (page["margins"]["top"] if tp.get(w("vertAnchor")) in (None, "text", "margin") else 0))
    for p, txt in _paras(body):
        anc = [etree.QName(a).localname for a in p.iterancestors()]
        where = "a text box" if "txbxContent" in anc else ("a table cell" if "tc" in anc else "the page")
        add("paragraph", text=txt[:80], where=where, field=_bind(p, by_style))
    return {"page": page, "pieces": pieces}


def apply(data, changes, std=None):
    """A copy of the cover's bytes with the changes: {piece id: {"x", "y", "w", "h", "field"}} (inches; field: a key
    from fields(), or "" for the paragraph's own style back to Normal text)."""
    z = zipfile.ZipFile(io.BytesIO(data))
    root = etree.fromstring(z.read("word/document.xml"))
    page = _page(root)
    styles = {k: s for k, _l, s in fields(std)}
    body = root.find("w:body", NS)
    n = {"picture": 0, "textbox": 0, "shape": 0, "table": 0, "paragraph": 0}
    for dr in body.iter(f"{{{W}}}drawing"):
        node = dr.find("wp:anchor", NS)
        il = dr.find("wp:inline", NS)
        nd = node if node is not None else il
        if nd is None:
            continue
        tb = nd.find(".//wps:txbx", NS)
        gd = nd.find(".//a:graphicData/*", NS)
        kind = "textbox" if tb is not None else ("picture" if gd is not None and etree.QName(gd).localname == "pic" else "shape")
        n[kind] += 1
        ch = changes.get(f"{kind}{n[kind]}") or {}
        if not ch:
            continue
        if ch.get("w") and ch.get("h"):
            cx, cy = str(int(round(float(ch["w"]) * EMU))), str(int(round(float(ch["h"]) * EMU)))
            ext = nd.find("wp:extent", NS)
            if ext is not None:
                ext.set("cx", cx); ext.set("cy", cy)
            for e in nd.iter(f"{{{A}}}ext"):
                if e.getparent() is not None and etree.QName(e.getparent()).localname == "xfrm":
                    e.set("cx", cx); e.set("cy", cy)
        if node is not None and (ch.get("x") is not None or ch.get("y") is not None):
            for axis, key in (("H", "x"), ("V", "y")):
                if ch.get(key) is None:
                    continue
                ph = node.find(f"wp:position{axis}", NS)
                if ph is None:
                    continue
                for c in list(ph):
                    ph.remove(c)
                ph.set("relativeFrom", "page")
                off = etree.SubElement(ph, f"{{{WP}}}posOffset")
                off.text = str(int(round(float(ch[key]) * EMU)))
    for t in body.iter(w("tbl")):
        if t.getparent() is not None and t.getparent().tag != w("body") and etree.QName(t.getparent()).localname != "txbxContent":
            continue
        n["table"] += 1
        ch = changes.get(f"table{n['table']}") or {}
        tp = t.find("w:tblPr/w:tblpPr", NS)
        if tp is not None and (ch.get("x") is not None or ch.get("y") is not None):
            if ch.get("x") is not None:
                tp.set(w("horzAnchor"), "page"); tp.set(w("tblpX"), str(int(round(float(ch["x"]) * TW))))
                tp.attrib.pop(w("tblpXSpec"), None)
            if ch.get("y") is not None:
                tp.set(w("vertAnchor"), "page"); tp.set(w("tblpY"), str(int(round(float(ch["y"]) * TW))))
                tp.attrib.pop(w("tblpYSpec"), None)
    for p, _txt in _paras(body):
        n["paragraph"] += 1
        ch = changes.get(f"paragraph{n['paragraph']}") or {}
        if "field" not in ch:
            continue
        ppr = p.find("w:pPr", NS)
        if ppr is None:
            ppr = etree.Element(w("pPr")); p.insert(0, ppr)
        ps = ppr.find("w:pStyle", NS)
        if ch["field"]:
            if ps is None:
                ps = etree.Element(w("pStyle")); ppr.insert(0, ps)
            ps.set(w("val"), style_id(styles.get(ch["field"], "")))
        elif ps is not None:
            ppr.remove(ps)
    xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        for i in z.infolist():
            zo.writestr(i, xml if i.filename == "word/document.xml" else z.read(i.filename))
    _ = page
    return out.getvalue()


def missing_styles(data, std=None):
    """The field cover styles the cover's paragraphs use that its own styles part does not define (the template
    carries them, so they are listed, not refused)."""
    z = zipfile.ZipFile(io.BytesIO(data))
    try:
        st = z.read("word/styles.xml").decode("utf-8")
    except KeyError:
        st = ""
    have = set(re.findall(r'w:styleId="([^"]+)"', st))
    used = {style_id(s) for k, _l, s in fields(std)} & set(re.findall(r'w:pStyle w:val="([^"]+)"', z.read("word/document.xml").decode("utf-8")))
    return sorted(used - have)


def picture_bytes(data, rid):
    """The bytes of a picture the cover's document part names by relationship id, or None."""
    import posixpath
    z = zipfile.ZipFile(io.BytesIO(data))
    try:
        rels = etree.fromstring(z.read("word/_rels/document.xml.rels"))
    except KeyError:
        return None
    for r in rels:
        if r.get("Id") == rid and r.get("TargetMode") != "External":
            name = posixpath.normpath(posixpath.join("word", r.get("Target")))
            try:
                return z.read(name)
            except KeyError:
                return None
    return None
