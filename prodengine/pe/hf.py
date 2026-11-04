"""Header and footer builder: writes each part's header and footer from its layout, and links the sections that
follow so every page of a part shows the same thing. For templates (closed file); in live mode the same layout is
written through Word.

Layout of a part (std["hf_layouts"][part key]):
  header: {"left": text, "center": text, "right": text, "rule_below": bool}
  footer: {"marking": bool, "left": text, "center": text, "right": text}
  Text may hold tokens: {volume_name} {solicitation} {company} {classification} (volume variables; a STYLEREF to
  the source paragraph on the cover when the document has one, else the typed value), {page} (PAGE field),
  {pages} (SECTIONPAGES field), {chapter} (3.7.0: the Heading 1 the page is in, STYLEREF). An empty layout (cover) gives empty header and footer parts.

op_hf_build(pkg, std)  new header and footer parts for the first section of each part, references removed from
                       the sections after it (linked), "Different first page" off unless the layout asks for it,
                       old parts no longer referenced removed. Fields declared exactly.
"""
import posixpath
import re

from lxml import etree
from prodengine.engine.pkg import NS, W, R, PR
from prodengine.engine.ordered import q, local, ensure, remove, insert_ordered
from prodengine.engine.ops.word_ops import find_style, new_style
from prodengine.pe import sections as S

HDR_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"
FTR_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"
HDR_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header"
FTR_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
HF_ALLOWED = ("word/header*.xml|*", "word/footer*.xml|*", "parts", "word/header*.xml|fields", "word/footer*.xml|fields",
              "package|media")   # 3.42.0: the pictures (logos) the headers and footers carry

# volume variables and the cover paragraph style that holds each one (v1.43 Properties table)
SOURCE_STYLES = {"volume_name": "PE Volume Name", "solicitation": "PE Solicitation", "company": "PE Company",
                 "classification": "PE Classification", "project": "PE Project Name"}

from prodengine.pe.rules import r7_footer as _r7    # 3.42.0: Rule 7's footer is the default
DEFAULT_LAYOUTS = {
    "cover": {"header": {}, "footer": {}},
    "front": {"header": {"left": "{volume_name}", "right": "{solicitation}", "rule_below": True}, "footer": _r7()},
    "body": {"header": {"left": "{volume_name}", "right": "{solicitation}", "rule_below": True}, "footer": _r7()},
    "appendix": {"header": {"left": "{volume_name}", "right": "{solicitation}", "rule_below": True}, "footer": _r7()},
}


def _r(text=None, child=None, rpr=None):
    r = etree.Element(q("r"))
    if rpr is not None:
        r.append(rpr)
    if text is not None:
        t = etree.SubElement(r, q("t")); t.text = text
        if text != text.strip():
            t.set(XML_SPACE, "preserve")
    if child is not None:
        r.append(child)
    return r


def _field(instr, result):
    out = []
    for kind in ("begin", "instr", "separate", "result", "end"):
        if kind in ("begin", "separate", "end"):
            fc = etree.Element(q("fldChar")); fc.set(q("fldCharType"), kind); out.append(_r(child=fc))
        elif kind == "instr":
            it = etree.Element(q("instrText")); it.text = f" {instr} "; it.set(XML_SPACE, "preserve"); out.append(_r(child=it))
        else:
            out.append(_r(result))
    return out


def _slot_runs(text, std, sources, fields):
    """Runs for one slot's text with its tokens, and the field instructions it adds."""
    runs = []
    for piece in re.split(r"(\{\w+\})", text or ""):
        if not piece:
            continue
        m = re.fullmatch(r"\{(\w+)\}", piece)
        if not m:
            runs.append(_r(piece)); continue
        k = m.group(1)
        if k == "page":
            runs += _field("PAGE", "1"); fields.append("PAGE")
        elif k == "pages":
            runs += _field("SECTIONPAGES", "1"); fields.append("SECTIONPAGES")
        elif k == "chapter":                      # 3.7.0: the chapter title the page is in (Heading 1)
            runs += _field('STYLEREF "Heading 1"', ""); fields.append('STYLEREF "Heading 1"')
        elif k == "a_number" and ((std.get("style_roles") or {}).get("a_number")):    # 3.42.0 Rule 7: the A number's style
            instr = f'STYLEREF "{std["style_roles"]["a_number"]}"'
            runs += _field(instr, str((std.get("variables") or {}).get("a_number") or "A-number")); fields.append(instr)
        elif k == "a_number":                     # no style chosen for the A number yet: the cell stays blank
            continue
        elif k == "marking":                      # 3.42.0: the marking's words; blank when the standard has none
            if (std.get("variables") or {}).get("marking"):
                runs.append(_r(str(std["variables"]["marking"])))
        elif k == "team_line":                    # 3.48.0: Rule 7's team line; blank until the team gives the words
            words = _team_line(std)
            if words:
                runs.append(_r(words))
        elif k in _styles_of(std) and _styles_of(std)[k] in sources:    # 3.23.0: the standard's fill-ins too
            instr = f'STYLEREF "{_styles_of(std)[k]}"'
            runs += _field(instr, _value_of(std, k)); fields.append(instr)
        elif k in _props_of(std):                                    # 3.23.0: a document property
            instr = f'DOCPROPERTY "{_props_of(std)[k]}"'
            runs += _field(instr, _value_of(std, k)); fields.append(instr)
        else:
            runs.append(_r(str(std["variables"].get(k) or _value_of(std, k) or piece)))
    return runs


def _team_line(std):
    v = str((std.get("variables") or {}).get("team_line") or "").strip()
    return v or str((std.get("hf_r7") or {}).get("line2") or "").strip()


def _r7_filled(spec):
    """3.48.0: a Rule 7 footer saved before the team line was a token (its second middle line blank) takes {team_line}."""
    cells = ((spec or {}).get("table") or {}).get("cells") or []
    if len(cells) != 3:
        return spec
    left = " ".join(str(l.get("text") or "") for l in cells[0].get("lines") or [])
    right = " ".join(str(l.get("text") or "") for l in cells[2].get("lines") or [])
    mid = cells[1].get("lines") or []
    if "{a_number}" not in left or "{page}" not in right or len(mid) < 2 or "{marking}" not in str(mid[0].get("text") or "") \
            or str(mid[1].get("text") or "").strip():
        return spec
    import copy as _copy
    spec = _copy.deepcopy(spec)
    spec["table"]["cells"][1]["lines"][1]["text"] = "{team_line}"
    return spec


def _styles_of(std):
    try:
        import fillins as FI
        return FI.styles(std)
    except ImportError:                                # the engine used on its own
        return dict(SOURCE_STYLES)


def _props_of(std):
    try:
        import fillins as FI
        return FI.props(std)
    except ImportError:
        return {}


def _value_of(std, k):
    try:
        import fillins as FI
        return FI.value(std, k)
    except ImportError:
        return str((std.get("variables") or {}).get(k, ""))


def _para(style_id, slots, std, sources, fields, width_tw, rule_below=False, align=None):
    p = etree.Element(q("p"))
    ppr = etree.SubElement(p, q("pPr"))
    etree.SubElement(ppr, q("pStyle")).set(q("val"), style_id)
    if rule_below:
        bdr = ensure(ppr, "pBdr")
        b = etree.SubElement(bdr, q("bottom"))
        b.set(q("val"), "single"); b.set(q("sz"), "6"); b.set(q("space"), "1"); b.set(q("color"), "auto")
    if slots is not None:
        tabs = ensure(ppr, "tabs")
        for val, pos in (("center", width_tw // 2), ("right", width_tw)):
            t = etree.SubElement(tabs, q("tab")); t.set(q("val"), val); t.set(q("pos"), str(pos))
        for k, name in enumerate(("left", "center", "right")):
            if k:
                p.append(_r(child=etree.Element(q("tab"))))
            for r in _slot_runs(slots.get(name, ""), std, sources, fields):
                p.append(r)
    if align:
        ensure(ppr, "jc").set(q("val"), align)
    return p


IMG_NS = {"wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
          "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
          "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture"}


def _picture_run(rid, w_in, h_in, n=1, name="Logo"):
    """3.42.0: a run holding a picture in line with the text (a logo), w_in by h_in inches."""
    cx, cy = int(float(w_in) * 914400), int(float(h_in) * 914400)
    xml = (f'<w:r xmlns:w="{W}" xmlns:r="{R}" xmlns:wp="{IMG_NS["wp"]}" xmlns:a="{IMG_NS["a"]}" xmlns:pic="{IMG_NS["pic"]}">'
           f'<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
           f'<wp:docPr id="{900 + n}" name="{name} {n}"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
           f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
           f'<pic:nvPicPr><pic:cNvPr id="{n}" name="{name} {n}"/><pic:cNvPicPr/></pic:nvPicPr>'
           f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
           f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
           f'</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')
    return etree.fromstring(xml)


def _line_runs(line, std, sources, fields):
    """3.42.0: one line of a cell: its words and fields, with its own size and bold."""
    runs = _slot_runs(line.get("text", ""), std, sources, fields)
    size, bold = line.get("size"), line.get("bold")
    if size or bold:
        for r in runs:
            if r.find(q("t")) is None:
                continue
            rpr = etree.Element(q("rPr"))
            if bold:
                etree.SubElement(rpr, q("b"))
            if size:
                v = str(int(round(float(size) * 2)))
                etree.SubElement(rpr, q("sz")).set(q("val"), v); etree.SubElement(rpr, q("szCs")).set(q("val"), v)
            r.insert(0, rpr)
    return runs


def _cells_table(style_id, spec, std, sources, fields, width_tw, add_picture=None):
    """3.42.0: a header or footer built as a one-row table of cells, each with its width, its lines (each its own words or
    fields, alignment, size and bold) and a logo (a picture, left or right); a rule above or below, or a grid."""
    t = spec.get("table") or {}
    cells = [c for c in (t.get("cells") or []) if isinstance(c, dict)]
    widths = [float(c.get("width_in") or 0) for c in cells]
    free = max(0, width_tw - sum(int(w * 1440) for w in widths if w))
    blanks = sum(1 for w in widths if not w)
    tws = [int(w * 1440) if w else (free // blanks if blanks else 0) for w in widths]
    tbl = etree.Element(q("tbl"))
    pr = etree.SubElement(tbl, q("tblPr"))
    w = etree.SubElement(pr, q("tblW")); w.set(q("w"), str(sum(tws))); w.set(q("type"), "dxa")
    b = etree.SubElement(pr, q("tblBorders"))
    kind = t.get("borders") or "none"
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = etree.SubElement(b, q(edge))
        on = kind == "grid" or (kind == edge) or (kind == "above" and edge == "top") or (kind == "below" and edge == "bottom")
        e.set(q("val"), "single" if on else "nil")
        if on:
            e.set(q("sz"), "6"); e.set(q("space"), "0"); e.set(q("color"), "auto")
    etree.SubElement(pr, q("tblLayout")).set(q("type"), "fixed")
    mar = etree.SubElement(pr, q("tblCellMar"))
    for side in ("left", "right"):
        m = etree.SubElement(mar, q(side)); m.set(q("w"), "0"); m.set(q("type"), "dxa")
    grid = etree.SubElement(tbl, q("tblGrid"))
    for tw in tws:
        etree.SubElement(grid, q("gridCol")).set(q("w"), str(tw))
    tr = etree.SubElement(tbl, q("tr"))
    for k, (c, tw) in enumerate(zip(cells, tws)):
        tc = etree.SubElement(tr, q("tc"))
        tcw = etree.SubElement(etree.SubElement(tc, q("tcPr")), q("tcW")); tcw.set(q("w"), str(tw)); tcw.set(q("type"), "dxa")
        logo = c.get("logo") or {}
        if logo.get("b64") and add_picture is not None:
            p = _para(style_id, None, std, sources, fields, width_tw, align=logo.get("align") or "left")
            rid = add_picture(logo)
            p.append(_picture_run(rid, logo.get("w_in") or 1.0, logo.get("h_in") or 0.5, n=k + 1))
            tc.append(p)
        lines = [ln for ln in (c.get("lines") or []) if isinstance(ln, dict)]
        for ln in lines:
            p = _para(style_id, None, std, sources, fields, width_tw, align=ln.get("align") or "left")
            for r in _line_runs(ln, std, sources, fields):
                p.append(r)
            tc.append(p)
        if tc.find(q("p")) is None:
            tc.append(_para(style_id, None, std, sources, fields, width_tw))
    return tbl


def _hf_table(style_id, spec, std, sources, fields, width_tw, add_picture=None):
    """3.25.0: a header or footer built as a one-row table, the way the team builds them: columns at their inch widths
    (blank: the text width shared out), the left, center and right text in its cells, borders none, a line under, or a
    grid. One width: the center text; two: the left and the right; three: all three. 3.42.0: cells with lines and logos."""
    t = spec.get("table") or {}
    if t.get("cells"):
        return _cells_table(style_id, spec, std, sources, fields, width_tw, add_picture)
    widths = [float(x) for x in (t.get("widths_in") or []) if x not in (None, "")]
    n = len(widths) or 3
    slots = {1: ["center"], 2: ["left", "right"]}.get(n, ["left", "center", "right"] + [""] * max(0, n - 3))
    tws = [int(round(w * 1440)) for w in widths] or [width_tw // 3] * 3
    tbl = etree.Element(q("tbl"))
    pr = etree.SubElement(tbl, q("tblPr"))
    w = etree.SubElement(pr, q("tblW")); w.set(q("w"), str(sum(tws))); w.set(q("type"), "dxa")
    b = etree.SubElement(pr, q("tblBorders"))          # schema order: tblW, tblBorders, tblLayout, tblCellMar
    kind = t.get("borders") or "none"
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = etree.SubElement(b, q(edge))
        on = kind == "grid" or (kind == "bottom" and edge == "bottom")
        e.set(q("val"), "single" if on else "nil")
        if on:
            e.set(q("sz"), "6"); e.set(q("space"), "0"); e.set(q("color"), "auto")
    etree.SubElement(pr, q("tblLayout")).set(q("type"), "fixed")
    mar = etree.SubElement(pr, q("tblCellMar"))
    for side in ("left", "right"):
        m = etree.SubElement(mar, q(side)); m.set(q("w"), "0"); m.set(q("type"), "dxa")
    grid = etree.SubElement(tbl, q("tblGrid"))
    for tw in tws:
        etree.SubElement(grid, q("gridCol")).set(q("w"), str(tw))
    tr = etree.SubElement(tbl, q("tr"))
    for k, tw in enumerate(tws):
        tc = etree.SubElement(tr, q("tc"))
        tcw = etree.SubElement(etree.SubElement(tc, q("tcPr")), q("tcW")); tcw.set(q("w"), str(tw)); tcw.set(q("type"), "dxa")
        name = slots[k] if k < len(slots) else ""
        p = _para(style_id, None, std, sources, fields, width_tw, align={"left": "left", "center": "center", "right": "right"}.get(name))
        for r in _slot_runs(spec.get(name, "") if name else "", std, sources, fields):
            p.append(r)
        tc.append(p)
    return tbl


def _style_id(pkg, name, size=None, center=False):
    sp = pkg.word_part("/styles")
    root = pkg.tree(sp)
    st = find_style(root, name)
    if st is None:
        pkg.touch(sp)
        st = new_style(root, name, based_on="Normal")
        pkg.mark(st)
        if size:
            rpr = ensure(st, "rPr")
            v = str(int(size * 2))
            ensure(rpr, "sz").set(q("val"), v); ensure(rpr, "szCs").set(q("val"), v)
        if center:
            ensure(ensure(st, "pPr"), "jc").set(q("val"), "center")
    return st.get(q("styleId"))


def _sources(pkg, std=None):
    """Cover paragraph styles present in the body (a STYLEREF to a style that has no text shows an error)."""
    names = S._style_names(pkg)
    want = set(_styles_of(std).values()) if std else set(SOURCE_STYLES.values())
    out = set()
    for p in pkg.tree(pkg.main).iter(q("p")):
        ps = p.find("w:pPr/w:pStyle", NS)
        if ps is not None and names.get(ps.get(q("val"))) in want:
            out.add(names[ps.get(q("val"))])
    return out


def _design_media(pkg, part, media):
    """The pictures a kept header or footer design uses, back under the relationship ids its XML names."""
    import base64
    if not media:
        return
    rn = pkg.rels_name(part)
    root = etree.Element(f"{{{PR}}}Relationships", nsmap={None: PR})
    pkg.add_part(rn, root, "application/vnd.openxmlformats-package.relationships+xml")
    for m in media:
        ext = (m.get("name") or "x.png").rsplit(".", 1)[-1]
        k = 1
        while pkg.has(f"word/media/pe_hf{k}.{ext}"):
            k += 1
        mname = f"word/media/pe_hf{k}.{ext}"
        pkg.add_part(mname, base64.b64decode(m["b64"]), m.get("ct") or f"image/{ext}")
        r = etree.SubElement(root, f"{{{PR}}}Relationship")
        r.set("Id", m["rid"]); r.set("Type", m.get("type") or "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
        r.set("Target", posixpath.relpath(mname, posixpath.dirname(part)))


def designs_of(pkg, std):
    """3.24.0: each part's header and footer as kept whole: {part: {"header", "footer", "header_media", "footer_media"}}
    from the first section of each part (its default header and footer), with the pictures they use."""
    import base64
    sm = S.map_sections(pkg, std)
    rels = pkg.rels_of(pkg.main)
    out = {}
    for s in sm.sections:
        if s.part in out:
            continue
        d = {}
        for kind in ("header", "footer"):
            ref = next((r for r in s.el.findall(f"w:{kind}Reference", NS) if r.get(q("type")) in (None, "default")), None)
            if ref is None or ref.get(f"{{{R}}}id") not in rels:
                continue
            tgt = rels[ref.get(f"{{{R}}}id")][1]
            d[kind] = etree.tostring(pkg.tree(tgt), encoding="unicode")
            media = []
            for rid, (typ, t, mode) in pkg.rels_of(tgt).items():
                if mode != "External" and typ.endswith("/image") and t in pkg.raw:
                    media.append({"rid": rid, "name": posixpath.basename(t), "type": typ, "ct": pkg.content_type("/" + t),
                                  "b64": base64.b64encode(pkg.raw[t]).decode("ascii")})
            d[kind + "_media"] = media
        if d.get("header") or d.get("footer"):
            out[s.part] = d
    return out


def _new_name(pkg, kind):
    i = 1
    while pkg.has(f"word/{kind}{i}.xml"):
        i += 1
    return f"word/{kind}{i}.xml"


def _rels_tree(pkg):
    rn = pkg.rels_name(pkg.main)
    pkg.touch(rn)
    pkg.mark_part(rn)
    return pkg.tree(rn)


def _new_rid(rels):
    ids = {r.get("Id") for r in rels}
    i = 1
    while f"rIdPEhf{i}" in ids:
        i += 1
    return f"rIdPEhf{i}"


def _style_tabs(sroot, sid):
    """The tab stops a paragraph style gives (through its base styles)."""
    if sroot is None or not sid:
        return set()
    by_id = {x.get(q("styleId")): x for x in sroot.findall("w:style", NS)}
    out, chain, cur, seen = {}, [], by_id.get(sid), set()
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur)); chain.append(cur)
        b = cur.find("w:basedOn", NS)
        cur = by_id.get(b.get(q("val"))) if b is not None else None
    for st in reversed(chain):
        for t in st.findall("w:pPr/w:tabs/w:tab", NS):
            if t.get(q("val")) == "clear":
                out.pop(t.get(q("pos")), None)
            else:
                out[t.get(q("pos"))] = t.get(q("val"))
    return {(v, k) for k, v in out.items()}


def _hf_semantic(root, sroot=None):
    """What a header or footer part shows and how: per paragraph its style, alignment, rule below, tab stops, text and
    field codes. Word's own bookkeeping (rsids, paragraph ids, attribute order) is left out (3.6.0)."""
    from prodengine.engine.fingerprint import visible_text, fields as _fields
    out = []
    for p in root.iter(q("p")):
        ppr = p.find("w:pPr", NS)
        st = ppr.find("w:pStyle", NS) if ppr is not None else None
        jc = ppr.find("w:jc", NS) if ppr is not None else None
        bdr = ppr.find("w:pBdr/w:bottom", NS) if ppr is not None else None
        eff = _style_tabs(sroot, st.get(q("val")) if st is not None else "Normal")
        for t in (ppr.findall("w:tabs/w:tab", NS) if ppr is not None else []):
            if t.get(q("val")) == "clear":
                eff = {x for x in eff if x[1] != t.get(q("pos"))}
            else:
                eff = {x for x in eff if x[1] != t.get(q("pos"))} | {(t.get(q("val")), t.get(q("pos")))}
        tabs = tuple(sorted(eff))
        out.append((st.get(q("val")) if st is not None else "", jc.get(q("val")) if jc is not None else "",
                    (bdr.get(q("val")), bdr.get(q("sz")), bdr.get(q("color"))) if bdr is not None else None, tabs,
                    visible_text(p), tuple(_fields(p))))
    return tuple(out)


def _hf_signature(pkg):
    """What every section's headers and footers read, by section and type, ignoring part names and ids (3.6.0).
    Only the types that show count: a first-page header only with Different first page on, even-page headers only
    with Different odd and even on (Word writes blank ones it never shows)."""
    rels = pkg.rels_of(pkg.main)
    sp_ = pkg.word_part("/styles")
    sroot = pkg.tree(sp_) if sp_ else None
    st = pkg.word_part("/settings")
    even_on = st is not None and pkg.tree(st).find("w:evenAndOddHeaders", NS) is not None and \
        pkg.tree(st).find("w:evenAndOddHeaders", NS).get(q("val")) not in ("0", "false")
    out = []
    for sp in pkg.tree(pkg.main).iter(q("sectPr")):
        refs = []
        title = sp.find("w:titlePg", NS) is not None and sp.find("w:titlePg", NS).get(q("val")) not in ("0", "false")
        for r in list(sp.findall("w:headerReference", NS)) + list(sp.findall("w:footerReference", NS)):
            if (r.get(q("type")) == "first" and not title) or (r.get(q("type")) == "even" and not even_on):
                continue
            tgt = rels.get(r.get(f"{{{R}}}id"), (None, None, None))[1]
            refs.append((etree.QName(r).localname, r.get(q("type")), _hf_semantic(pkg.tree(tgt), sroot) if tgt and pkg.has(tgt) else None))
        out.append((tuple(sorted(refs, key=lambda x: (x[0], x[1] or ""))), sp.find("w:titlePg", NS) is not None))
    return out


def op_hf_build(pkg, std):
    """Headers and footers from the layouts. 3.6.0: when every section already reads exactly what the build would
    write, nothing changes (a second run is a no-op instead of the same content under new part names)."""
    from prodengine.engine.pkg import Package as _Pkg
    trial = _Pkg.from_bytes(pkg.to_bytes())
    rep = _hf_build(trial, std)
    if _hf_signature(trial) == _hf_signature(pkg):
        return {"made": [], "removed": [], "field_changes": [], "checks": [], "unchanged": True}
    return _hf_build(pkg, std)


def _hf_build(pkg, std):
    layouts = std.get("hf_layouts") or DEFAULT_LAYOUTS
    sm = S.map_sections(pkg, std)
    pkg.touch(pkg.main)
    rels = _rels_tree(pkg)
    sources = _sources(pkg, std)
    hid = _style_id(pkg, "Header")
    fid = _style_id(pkg, "Footer")
    mid = _style_id(pkg, "PE Marking", size=7, center=True)
    even = sm.even_odd
    fields_declared, made = [], []
    first_of_part, prev_layout = {}, None
    for s in sm.sections:
        first_of_part.setdefault(s.part, s.i)
    old_targets = {rid: tgt for rid, (typ, tgt, mode) in pkg.rels_of(pkg.main).items() if typ in (HDR_REL, FTR_REL)}
    for s in sm.sections:
        sp = s.el
        pkg.mark(s.owner if s.owner is not None else sp)
        lay = layouts.get(s.part, DEFAULT_LAYOUTS.get(s.part, DEFAULT_LAYOUTS["body"]))
        part_def = next(p for p in sm.scheme["parts"] if p["key"] == s.part)
        first = s.i == first_of_part[s.part]
        for r in sp.findall("w:headerReference", NS) + sp.findall("w:footerReference", NS):
            sp.remove(r)
        remove(sp, "titlePg")
        own = first and not (part_def.get("linked") and prev_layout == lay and s.i > 0)
        if not own:
            continue                                     # linked to the section before: the same header and footer
        prev_layout = lay
        width = int(((s.margins and (_page_w(sp) - (s.margins["left"] + s.margins["right"]) * 1440)) or 9360))
        width = int(width)
        for kind, rel, ct, root_tag in (("header", HDR_REL, HDR_CT, "hdr"), ("footer", FTR_REL, FTR_CT, "ftr")):
            for typ in (("default", "even") if even else ("default",)):
                name = _new_name(pkg, kind)
                root = etree.Element(q(root_tag), nsmap={"w": W, "r": R})
                fl = []
                spec = lay.get(kind) or {}
                if kind == "footer":
                    spec = _r7_filled(spec)
                design = ((std.get("hf_designs") or {}).get(s.part) or {}).get(kind)
                if design:                                   # 3.24.0: a design kept whole (its tables, tabs, pictures, fields)
                    root = etree.fromstring(design.encode("utf-8") if isinstance(design, str) else design)
                    fl = [" ".join(i.split()) for i in re.findall(r"<w:instrText[^>]*>([^<]*)</w:instrText>", design)
                          if i.strip()] + re.findall(r'w:instr="([^"]+)"', design)
                    pkg.add_part(name, root, ct)
                    _design_media(pkg, name, ((std.get("hf_designs") or {}).get(s.part) or {}).get(kind + "_media") or [])
                    rid = _new_rid(rels)
                    rr = etree.SubElement(rels, f"{{{PR}}}Relationship")
                    rr.set("Id", rid); rr.set("Type", rel); rr.set("Target", posixpath.relpath(name, "word"))
                    ref = etree.Element(q(f"{kind}Reference"))
                    ref.set(q("type"), typ); ref.set(f"{{{R}}}id", rid)
                    insert_ordered(sp, ref)
                    fields_declared += [(name, None, f) for f in fl]
                    made.append(name)
                    continue
                as_table = bool((spec.get("table") or {}).get("widths_in")) or (spec.get("table") or {}).get("on") \
                    or bool((spec.get("table") or {}).get("cells"))
                media = []                                   # 3.42.0: logos in the table's cells

                def add_picture(logo, media=media):
                    rid = f"rIdPeLogo{len(media) + 1}"
                    media.append({"rid": rid, "name": logo.get("name") or "logo.png", "ct": logo.get("ct") or "image/png",
                                  "b64": logo["b64"]})
                    return rid
                if kind == "header":
                    if as_table:                             # 3.25.0: built as a table, the team's way
                        root.append(_hf_table(hid, spec, std, sources, fl, width, add_picture))
                        root.append(_para(hid, None, std, sources, fl, width, spec.get("rule_below")))
                    else:
                        root.append(_para(hid, spec if spec else None, std, sources, fl, width, spec.get("rule_below")))
                else:
                    if as_table:
                        root.append(_hf_table(fid, spec, std, sources, fl, width, add_picture))
                    if spec.get("marking") and std["variables"].get("marking"):
                        mp = _para(mid, None, std, sources, fl, width)
                        mp.append(_r(std["variables"]["marking"]))
                        root.append(mp)
                    if not as_table:
                        root.append(_para(fid, spec if spec else None, std, sources, fl, width))
                    elif not (spec.get("marking") and std["variables"].get("marking")):
                        root.append(_para(fid, None, std, sources, fl, width))
                pkg.add_part(name, root, ct)
                if media:
                    _design_media(pkg, name, media)
                rid = _new_rid(rels)
                rr = etree.SubElement(rels, f"{{{PR}}}Relationship")
                rr.set("Id", rid); rr.set("Type", rel); rr.set("Target", posixpath.relpath(name, "word"))
                ref = etree.Element(q(f"{kind}Reference"))
                ref.set(q("type"), typ); ref.set(f"{{{R}}}id", rid)
                insert_ordered(sp, ref)
                fields_declared += [(name, None, f) for f in fl]
                made.append(name)
    # old header and footer parts that no section uses any more go, with their relationships
    used = {r.get(f"{{{R}}}id") for r in pkg.tree(pkg.main).iter(q("headerReference"), q("footerReference"))}
    removed = []
    for rel_el in list(rels):
        rid = rel_el.get("Id")
        if rid in old_targets and rid not in used:
            tgt = old_targets[rid]
            rels.remove(rel_el)
            if pkg.has(tgt):
                from prodengine.engine.fingerprint import fields as _fields
                fields_declared += [(tgt, f, None) for f in _fields(pkg.tree(tgt))]
            if pkg.has(tgt) and pkg.rels_name(tgt) in pkg.raw:
                pkg.remove_part(pkg.rels_name(tgt))
            if pkg.has(tgt):
                pkg.remove_part(tgt)
                removed.append(tgt)
    return {"made": made, "removed": removed, "field_changes": fields_declared, "checks": []}


def _page_w(sp):
    pg = sp.find("w:pgSz", NS)
    return int(pg.get(q("w"), 12240)) if pg is not None else 12240
