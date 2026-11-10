"""Change a part (3.98.0; canvas "Libraries and Sets", board 5): a Quick Part is changed three ways, each kept as a new
version (the one it came from stays; sets are asked before they move):

    1. The style first. A part follows the styles it names; changing a style in Styles changes every part that uses it,
       with no new version. Typed formatting (a size or font typed into the part) stops the style from deciding:
       Let the styles decide takes it out, as a new version.
    2. Make a variant: cell padding, the table's width, its column widths, its rows' height, its table style, and its
       paragraph styles swapped for others. Saved as a new version under its own name.
    3. Anything else in Word: Open in Word opens the part on its own; Bring back as a new version reads the saved file.

Each version is kept as its own small Word file (the part's source, changed only in that part). The part's kind on
Parts (a table, a callout, a header or footer, a Quick Part) is read from its gallery, its category and its content.
Rules only (No AI); nothing leaves the PC."""
import base64
import copy
import os
import posixpath
import re
import tempfile
import zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"w": W}
TWIP = 1440


def q(t):
    return f"{{{W}}}{t}"


def _parser():
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)


# ------------------------------------------------------------------ reading a part
def source_of(lib, item):
    v = lib.values(item) or {}
    src = v.get("source") or ""
    return (lib.source_path(src) if src else ""), (v.get("entry") or lib.base_of(item))


def _read(path):
    with zipfile.ZipFile(path) as z:
        return z.namelist(), {n: z.read(n) for n in z.namelist()}


def _gloss_name(names, data):
    rels = data.get("word/_rels/document.xml.rels", b"").decode("utf-8", "replace")
    m = re.search(r'Type="[^"]*/glossaryDocument"[^>]*Target="([^"]+)"', rels) or re.search(r'Target="([^"]+)"[^>]*Type="[^"]*/glossaryDocument"', rels)
    if m:
        return posixpath.normpath(posixpath.join("word", m.group(1)))
    return "word/glossary/document.xml" if "word/glossary/document.xml" in names else ""


def load(path, name):
    """(names, data, glossary part name, glossary root, the part's docPart element) or None."""
    if not path or not os.path.isfile(path):
        return None
    names, data = _read(path)
    g = _gloss_name(names, data)
    if not g or g not in data:
        return None
    root = etree.fromstring(data[g], _parser())
    for dp in root.iter(q("docPart")):
        nm = dp.find("w:docPartPr/w:name", NS)
        if nm is not None and nm.get(q("val")) == name:
            return names, data, g, root, dp
    return None


def body(dp):
    return dp.find("w:docPartBody", NS)


def kind_of(values, dp=None):
    """tables, callouts, hf (headers and footers) or quick, from the part's gallery, category and content."""
    gal = (values.get("gallery") or "").lower()
    cat = (values.get("category") or "").lower()
    if gal in ("hdrs", "ftrs") or "header" in cat or "footer" in cat:
        return "hf"
    if gal == "tbls" or "table" in cat:
        return "tables"
    if "callout" in cat or "sidebar" in cat or (gal == "txtbox"):
        return "callouts"
    if dp is not None:
        b = body(dp)
        if b is not None and b.find(".//w:txbxContent", NS) is not None:
            return "callouts"
        if b is not None and b.find("w:tbl", NS) is not None:
            return "tables"
    return "quick"


def style_names(data, g):
    """{style id: (name, type)} from the glossary's styles (else the document's)."""
    out = {}
    for part in (posixpath.join(posixpath.dirname(g), "styles.xml"), "word/styles.xml"):
        if part in data:
            root = etree.fromstring(data[part], _parser())
            for s in root.findall("w:style", NS):
                n = s.find("w:name", NS)
                out.setdefault(s.get(q("styleId")), (n.get(q("val")) if n is not None else s.get(q("styleId")), s.get(q("type"))))
    return out


def styles_used(path, name):
    """[(style name, type)] the part names, in order."""
    got = load(path, name)
    if got is None:
        return []
    _n, data, g, _root, dp = got
    names = style_names(data, g)
    out, seen = [], set()
    for el in body(dp).iter(q("pStyle"), q("rStyle"), q("tblStyle")):
        sid = el.get(q("val"))
        if sid and sid not in seen:
            seen.add(sid)
            nm, typ = names.get(sid, (sid, {"pStyle": "paragraph", "rStyle": "character", "tblStyle": "table"}[etree.QName(el).localname]))
            out.append((nm, typ))
    return out


TYPED = ("sz", "szCs", "rFonts", "color", "b", "i", "u", "highlight")


def typed(path, name):
    """How many runs have formatting typed into them (a size, a font, a color...), which the styles cannot change."""
    got = load(path, name)
    if got is None:
        return 0
    return sum(1 for rpr in body(got[4]).iter(q("rPr")) if any(rpr.find(f"w:{t}", NS) is not None for t in TYPED)
               and rpr.getparent() is not None and etree.QName(rpr.getparent()).localname == "r")


def table_of(path, name):
    """The part's first table as it is: {"padding": {top, bottom, left, right} (in), "width" (in), "columns" [in],
    "row_height" (in or None), "style" (name or "")} or None."""
    got = load(path, name)
    if got is None:
        return None
    _n, data, g, _root, dp = got
    tbl = body(dp).find(".//w:tbl", NS)
    if tbl is None:
        return None
    names = style_names(data, g)

    def tw(el, att="w"):
        try:
            return round(int(el.get(q(att))) / TWIP, 3) if el is not None and el.get(q(att)) not in (None, "") else None
        except ValueError:
            return None
    pr = tbl.find("w:tblPr", NS)
    pad = {}
    for side in ("top", "bottom", "left", "right"):
        el = pr.find(f"w:tblCellMar/w:{side}", NS) if pr is not None else None
        if el is None and side in ("left", "right") and pr is not None:
            el = pr.find(f"w:tblCellMar/w:{'start' if side == 'left' else 'end'}", NS)
        pad[side] = tw(el)
    ts = pr.find("w:tblStyle", NS) if pr is not None else None
    tr = tbl.find("w:tr/w:trPr/w:trHeight", NS)
    return {"padding": pad, "width": tw(pr.find("w:tblW", NS)) if pr is not None and (pr.find("w:tblW", NS) is not None
                                                                                       and pr.find("w:tblW", NS).get(q("type")) == "dxa") else None,
            "columns": [tw(c) for c in tbl.findall("w:tblGrid/w:gridCol", NS)],
            "row_height": tw(tr, "val") if tr is not None else None,
            "style": names.get(ts.get(q("val")), (ts.get(q("val")), ""))[0] if ts is not None else ""}


# ------------------------------------------------------------------ changing a part
def _child(parent, tag, first=False):
    el = parent.find(f"w:{tag}", NS)
    if el is None:
        el = etree.Element(q(tag))
        parent.insert(0, el) if first else parent.append(el)
    return el


def strip_typed(dp):
    n = 0
    for rpr in list(body(dp).iter(q("rPr"))):
        if rpr.getparent() is None or etree.QName(rpr.getparent()).localname != "r":
            continue
        for t in TYPED:
            for el in rpr.findall(f"w:{t}", NS):
                rpr.remove(el); n += 1
    return n


def apply_variant(dp, opts, ids=None):
    """Change the part's tables and styles. opts: {"padding": {side: in}, "width": in, "columns": [in], "row_height": in,
    "table_style": style id, "swap": {old style id: new style id}}. ids: {style name: id} to read names."""
    ids = ids or {}
    sid = lambda x: ids.get(x, x)
    b = body(dp)
    for tbl in b.iter(q("tbl")):
        pr = _child(tbl, "tblPr", first=True)
        if opts.get("table_style"):
            _child(pr, "tblStyle", first=True).set(q("val"), sid(opts["table_style"]))
        if opts.get("width"):
            w = _child(pr, "tblW"); w.set(q("w"), str(int(round(float(opts["width"]) * TWIP)))); w.set(q("type"), "dxa")
        pad = {k: v for k, v in (opts.get("padding") or {}).items() if v not in (None, "")}
        if pad:
            mar = _child(pr, "tblCellMar")
            for side, val in pad.items():
                for tag in ((side,) if side in ("top", "bottom") else (side, "start" if side == "left" else "end")):
                    el = mar.find(f"w:{tag}", NS)
                    if el is None and tag in ("start", "end"):
                        continue
                    el = el if el is not None else etree.SubElement(mar, q(tag))
                    el.set(q("w"), str(int(round(float(val) * TWIP)))); el.set(q("type"), "dxa")
        cols = [c for c in (opts.get("columns") or []) if c not in (None, "")]
        grid = tbl.find("w:tblGrid", NS)
        if cols and grid is not None and len(grid) == len(cols):
            for gc, c in zip(grid.findall("w:gridCol", NS), cols):
                gc.set(q("w"), str(int(round(float(c) * TWIP))))
            for tr in tbl.findall("w:tr", NS):
                for tc, c in zip(tr.findall("w:tc", NS), cols):
                    tcpr = _child(tc, "tcPr", first=True)
                    w = _child(tcpr, "tcW", first=True); w.set(q("w"), str(int(round(float(c) * TWIP)))); w.set(q("type"), "dxa")
        if opts.get("row_height"):
            for tr in tbl.findall("w:tr", NS):
                trpr = _child(tr, "trPr", first=True)
                h = _child(trpr, "trHeight"); h.set(q("val"), str(int(round(float(opts["row_height"]) * TWIP)))); h.set(q("hRule"), "atLeast")
    swap = {sid(k): sid(v) for k, v in (opts.get("swap") or {}).items() if k and v and k != v}
    for el in b.iter(q("pStyle"), q("rStyle")):
        if el.get(q("val")) in swap:
            el.set(q("val"), swap[el.get(q("val"))])
    return dp


def _bring_styles(data, g, want_ids, extra_xml):
    """Styles a swap or a table style names that the source lacks, added to its glossary styles."""
    part = posixpath.join(posixpath.dirname(g), "styles.xml")
    if part not in data or not extra_xml:
        return 0
    root = etree.fromstring(data[part], _parser())
    have = {s.get(q("styleId")) for s in root.findall("w:style", NS)}
    n = 0
    for sid, xml in extra_xml.items():
        if sid in have or sid not in want_ids:
            continue
        try:
            el = etree.fromstring(xml.encode("utf-8") if "xmlns:w" in xml else
                                  re.sub(r"^<w:style\b", f'<w:style xmlns:w="{W}"', xml.strip(), count=1).encode("utf-8"), _parser())
        except etree.XMLSyntaxError:
            continue
        el.set(q("styleId"), sid)
        root.append(el); n += 1
    if n:
        data[part] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    return n


def _write(names, data, out):
    tmp = out + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, data[n])
    os.replace(tmp, out)
    return out


def changed_copy(path, name, change, work=None, styles_xml=None):
    """A copy of the source with only this part changed (change(dp, ids) does it). Returns the copy's path."""
    got = load(path, name)
    if got is None:
        return None
    names, data, g, root, dp = got
    ids = {nm: sid for sid, (nm, _t) in style_names(data, g).items()}
    for nm, xml in (styles_xml or {}).items():
        ids.setdefault(nm, re.sub(r"[^A-Za-z0-9]", "", nm))
    change(dp, ids)
    data[g] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    if styles_xml:
        used = {el.get(q("val")) for el in body(dp).iter(q("pStyle"), q("rStyle"), q("tblStyle"))}
        _bring_styles(data, g, used, {ids[nm]: xml for nm, xml in styles_xml.items()})
    work = work or tempfile.mkdtemp(prefix="sk_part_")
    os.makedirs(work, exist_ok=True)
    return _write(names, data, os.path.join(work, os.path.basename(path)))


def keep_version(lib, item, path, label="", name=None):
    """The changed source kept in the library as a new version of the part (the one it came from stays)."""
    import hashlib
    v = dict(lib.values(item) or {})
    with open(path, "rb") as f:
        raw = f.read()
    v["source"] = lib.keep_file(path, os.path.basename(path))
    v["source_sha"] = hashlib.sha256(raw).hexdigest()[:10]
    if name:
        v["entry"] = name
    new, st = lib.save_version(item["id"], v, label=label)
    return new, st


def let_styles_decide(lib, item, label="styles decide"):
    path, name = source_of(lib, item)
    out = changed_copy(path, name, lambda dp, _ids: strip_typed(dp))
    return keep_version(lib, item, out, label) if out else (None, "missing")


def make_variant(lib, item, opts, label="", styles_xml=None):
    """A variant saved as a new version. styles_xml: {style name: Word's definition} for styles named in opts that the
    part's source does not hold (from the Styles library)."""
    path, name = source_of(lib, item)
    out = changed_copy(path, name, lambda dp, ids: apply_variant(dp, opts, ids), styles_xml=styles_xml)
    return keep_version(lib, item, out, label) if out else (None, "missing")


# ------------------------------------------------------------------ in Word
def export(lib, item, folder):
    """The part on its own in a small Word file to open in Word (its pictures, the styles it uses). Returns its path."""
    path, name = source_of(lib, item)
    got = load(path, name)
    if got is None:
        return None
    names, data, g, _root, dp = got
    b = copy.deepcopy(body(dp))
    inner = "".join(etree.tostring(c, encoding="unicode") for c in b)
    grels = posixpath.join(posixpath.dirname(g), "_rels", posixpath.basename(g) + ".rels")
    rels = data.get(grels, b"").decode("utf-8")
    keep = [(rid, t, typ) for typ, rid, t in re.findall(r'<Relationship[^>]*Type="([^"]+)"[^>]*Id="([^"]+)"[^>]*Target="([^"]+)"', rels)]
    keep += [(rid, t, typ) for rid, typ, t in re.findall(r'<Relationship[^>]*Id="([^"]+)"[^>]*Type="([^"]+)"[^>]*Target="([^"]+)"', rels)]
    files, rel_xml = {}, []
    for rid, t, typ in keep:
        if not typ.endswith("/image") or f'"{rid}"' not in inner:
            continue
        part = posixpath.normpath(posixpath.join(posixpath.dirname(g), t))
        if part in data:
            files["word/media/" + posixpath.basename(part)] = data[part]
            rel_xml.append(f'<Relationship Id="{rid}" Type="{typ}" Target="media/{posixpath.basename(part)}"/>')
    styles = data.get(posixpath.join(posixpath.dirname(g), "styles.xml")) or data.get("word/styles.xml") or \
        f'<w:styles xmlns:w="{W}"/>'.encode()
    os.makedirs(folder, exist_ok=True)
    out = os.path.join(folder, re.sub(r'[<>:"/\\|?*]', "_", name)[:60] + ".docx")
    exts = sorted({p.rsplit(".", 1)[-1].lower() for p in files})
    ctypes = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "emf": "image/x-emf", "wmf": "image/x-wmf"}
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          + "".join(f'<Default Extension="{x}" ContentType="{ctypes.get(x, "image/" + x)}"/>' for x in exts)
          + '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'<Relationship Id="rId1" Type="{R}/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'<Relationship Id="rIdSt" Type="{R}/styles" Target="styles.xml"/>' + "".join(rel_xml) + "</Relationships>")
        z.writestr("word/document.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}" xmlns:r="{R}" '
                   'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
                   'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                   'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
                   f"<w:body>{inner}<w:sectPr/></w:body></w:document>")
        z.writestr("word/styles.xml", styles)
        for n, b_ in files.items():
            z.writestr(n, b_)
    return out


def bring_back(lib, item, path, label=""):
    """The part saved in Word, kept as a new version (a new small Word file holding it as a Quick Part)."""
    import qpmake as QM
    import templatesets as TS
    v = lib.values(item) or {}
    inner, media = TS.page_body(path)
    if not inner.strip():
        return None, "empty"
    src = QM.make_source(tempfile.mkdtemp(prefix="sk_part_"), [{"name": v.get("entry") or lib.base_of(item),
                                                                "category": v.get("category") or "", "gallery": v.get("gallery") or "docParts",
                                                                "xml": inner, "media": media}], "part")
    return keep_version(lib, item, src, label)
