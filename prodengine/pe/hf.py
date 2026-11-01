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
HF_ALLOWED = ("word/header*.xml|*", "word/footer*.xml|*", "parts", "word/header*.xml|fields", "word/footer*.xml|fields")

# volume variables and the cover paragraph style that holds each one (v1.43 Properties table)
SOURCE_STYLES = {"volume_name": "PE Volume Name", "solicitation": "PE Solicitation", "company": "PE Company",
                 "classification": "PE Classification", "project": "PE Project Name"}

DEFAULT_LAYOUTS = {
    "cover": {"header": {}, "footer": {}},
    "front": {"header": {"left": "{volume_name}", "right": "{solicitation}", "rule_below": True},
              "footer": {"marking": True, "center": "{page}"}},
    "body": {"header": {"left": "{volume_name}", "right": "{solicitation}", "rule_below": True},
             "footer": {"marking": True, "center": "{page}"}},
    "appendix": {"header": {"left": "{volume_name}", "right": "{solicitation}", "rule_below": True},
                 "footer": {"marking": True, "center": "{page}"}},
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
        elif k in SOURCE_STYLES and SOURCE_STYLES[k] in sources:
            instr = f'STYLEREF "{SOURCE_STYLES[k]}"'
            runs += _field(instr, str(std["variables"].get(k, ""))); fields.append(instr)
        else:
            runs.append(_r(str(std["variables"].get(k, piece))))
    return runs


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


def _sources(pkg):
    """Cover paragraph styles present in the body (a STYLEREF to a style that has no text shows an error)."""
    names = S._style_names(pkg)
    out = set()
    for p in pkg.tree(pkg.main).iter(q("p")):
        ps = p.find("w:pPr/w:pStyle", NS)
        if ps is not None and names.get(ps.get(q("val"))) in SOURCE_STYLES.values():
            out.add(names[ps.get(q("val"))])
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
    sources = _sources(pkg)
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
                if kind == "header":
                    root.append(_para(hid, spec if spec else None, std, sources, fl, width, spec.get("rule_below")))
                else:
                    if spec.get("marking") and std["variables"].get("marking"):
                        mp = _para(mid, None, std, sources, fl, width)
                        mp.append(_r(std["variables"]["marking"]))
                        root.append(mp)
                    root.append(_para(fid, spec if spec else None, std, sources, fl, width))
                pkg.add_part(name, root, ct)
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
