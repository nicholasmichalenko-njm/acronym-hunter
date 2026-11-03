"""Covers and back covers (3.10.0): a profile keeps its cover and back cover pages as small Word files of their own,
learned from a template or a finished volume, and Make a template puts them in.

  std["page_parts"] = {"cover": "<file name>", "title": "<file name>" (3.34.0), "backer": "<file name>"}   files in <config>\\production_parts

extract(raw, part, std)          the cover (first section) or back cover (last section, recognised by the page
                                 scheme) of a Word file as a Word file of its own (bytes), or None
save_part(parts_dir, data, label) keeps it under a name made from its content (the same page is kept once)
place(base, part_bytes, where)   a copy of the template bytes with the part in place of the base cover, or added
                                 as the last section (back cover); its pictures, links and styles come with it
signature(raw, part, std)        what a cover looks like without its words (paragraph styles, tables, pictures),
                                 for Check: a draft whose cover is built differently is reported, never changed
Only pictures and hyperlinks travel with a part; a part holding charts, diagrams or embedded objects is refused."""
import hashlib, io, os, posixpath, re, zipfile

from lxml import etree
from prodengine.engine.pkg import Package, NS
from prodengine.engine.ordered import q, local

W = NS["w"]
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
IMAGE = R_NS + "/image"
HYPERLINK = R_NS + "/hyperlink"
TRAVELS = (IMAGE, HYPERLINK)
FOLDER = "production_parts"


class PartError(Exception):
    """A cover or back cover that cannot be kept or placed."""


def parts_dir(config_dir):
    return os.path.join(config_dir, FOLDER)


def _blocks(root):
    """[(sectPr, [elements])] for each section of the body, in order (the last one's sectPr is the body's)."""
    body = root.find("w:body", NS)
    out, cur = [], []
    for el in body:
        if local(el) == "sectPr":
            out.append((el, cur)); cur = []
            continue
        cur.append(el)
        sp = el.find("w:pPr/w:sectPr", NS) if local(el) == "p" else None
        if sp is not None:
            out.append((sp, cur)); cur = []
    if cur:
        out.append((None, cur))
    return out


def _which(raw, part, std):
    from prodengine.pe import sections as S
    pkg = Package.from_bytes(raw)
    sm = S.map_sections(pkg, std)
    if part == "cover":            # the first section of a volume with more than one, whatever the page scheme calls it
        return pkg, (0 if len(sm.sections) >= 2 else None)
    idx = [s.i for s in sm.sections if s.part == part]
    return pkg, (idx[0] if idx else None)


def extract(raw, part, std):
    """The section of the given part (cover or backer) as a Word file of its own, or None when the file has none."""
    pkg, i = _which(raw, part, std)
    if i is None:
        return None
    root = pkg.tree(pkg.main)
    blocks = _blocks(root)
    if i >= len(blocks):
        return None
    sp, els = blocks[i]
    rels = _rels(pkg)
    for el in els:
        for rid in _rids(el):
            t = rels.get(rid)
            if t is None or t[0] not in TRAVELS:
                raise PartError("The " + ("cover" if part == "cover" else "back cover") + " holds a chart, a diagram or an "
                                "embedded object; only pictures and links travel with a page.")
    new_root = etree.fromstring(etree.tostring(root))
    body = new_root.find("w:body", NS)
    for c in list(body):
        body.remove(c)
    for el in els:
        e = etree.fromstring(etree.tostring(el))
        psp = e.find("w:pPr/w:sectPr", NS) if local(e) == "p" else None
        if psp is not None:
            psp.getparent().remove(psp)
        body.append(e)
    final = etree.fromstring(etree.tostring(sp)) if sp is not None else etree.SubElement(body, q("sectPr"))
    for ref in final.findall("w:headerReference", NS) + final.findall("w:footerReference", NS):
        final.remove(ref)                                   # headers and footers come from the layouts
    body.append(final)
    data = etree.tostring(new_root, xml_declaration=True, encoding="UTF-8", standalone=True)
    zin = zipfile.ZipFile(io.BytesIO(raw))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for it in zin.infolist():
            z.writestr(it, data if it.filename == pkg.main else zin.read(it.filename))
    return buf.getvalue()


def save_part(pdir, data, label):
    os.makedirs(pdir, exist_ok=True)
    h = hashlib.sha256(data).hexdigest()[:12]
    name = f"{re.sub(r'[^A-Za-z0-9]+', '_', label).strip('_') or 'part'}-{h}.docx"
    p = os.path.join(pdir, name)
    if not os.path.exists(p):
        with open(p + ".tmp", "wb") as f:
            f.write(data)
        os.replace(p + ".tmp", p)
    return name


def _rels(pkg):
    out = {}
    rn = Package.rels_name(pkg.main)
    if pkg.has(rn):
        for r in pkg.tree(rn):
            out[r.get("Id")] = (r.get("Type"), r.get("Target"), r.get("TargetMode") == "External")
    return out


def _rids(el):
    for x in el.iter():
        if local(x) == "sectPr" or any(local(a) == "sectPr" for a in x.iterancestors()):
            continue                                        # a section's header and footer links stay behind
        for a, v in x.attrib.items():
            if a.startswith("{" + R_NS + "}"):
                yield v


def _styles_used(el):
    for tag in ("pStyle", "rStyle", "tblStyle"):
        for x in el.iter(q(tag)):
            yield x.get(q("val"))


def signature(raw, part, std):
    """(paragraph styles, tables, pictures) of the part's section, words left out; None when the file has none."""
    pkg, i = _which(raw, part, std)
    if i is None:
        return None
    blocks = _blocks(pkg.tree(pkg.main))
    if i >= len(blocks):
        return None
    return _signature(pkg, blocks[i][1])


def part_signature(part_bytes):
    """The signature of a kept page (a Word file holding just that page)."""
    pkg = Package.from_bytes(part_bytes)
    blocks = _blocks(pkg.tree(pkg.main))
    return _signature(pkg, blocks[0][1]) if blocks else None


def _signature(pkg, els):
    from prodengine.pe.tables import style_name_map
    from prodengine.pe.hf import SOURCE_STYLES
    from prodengine.engine.fingerprint import visible_text
    names = style_name_map(pkg.tree(pkg.word_part("/styles")))
    styles, tables, pics = [], 0, 0
    for el in els:
        if local(el) == "p":
            ps = el.find("w:pPr/w:pStyle", NS)
            nm = names.get(ps.get(q("val")), ps.get(q("val"))) if ps is not None else "Normal"
            if visible_text(el).replace("\u00b6", "").strip() and nm not in SOURCE_STYLES.values():   # words-bearing paragraphs, not the volume values
                styles.append(nm)
        elif local(el) == "tbl":
            tables += 1
        pics += sum(1 for _ in el.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip")) + \
            sum(1 for _ in el.iter("{urn:schemas-microsoft-com:vml}imagedata"))
    return (tuple(styles), tables, pics)


def place(base, part_bytes, where):
    """The template bytes with the part as its cover (replacing the first section's content) or as a new last section
    (back cover). Pictures, links and the styles the part uses are copied in."""
    bz = zipfile.ZipFile(io.BytesIO(base))
    pz = zipfile.ZipFile(io.BytesIO(part_bytes))
    files = {n: bz.read(n) for n in bz.namelist()}
    bpkg, ppkg = Package.from_bytes(base), Package.from_bytes(part_bytes)
    broot = etree.fromstring(files[bpkg.main])
    proot = ppkg.tree(ppkg.main)
    pblocks = _blocks(proot)
    if not pblocks:
        raise PartError("The page is empty.")
    els = [etree.fromstring(etree.tostring(e)) for e in pblocks[0][1]]
    part_sect = pblocks[0][0]
    # relationships: pictures and links, renamed into the template
    brn = Package.rels_name(bpkg.main)
    brels = etree.fromstring(files[brn]) if brn in files else etree.Element(f"{{{REL_NS}}}Relationships")
    used_ids = {r.get("Id") for r in brels}
    prels = _rels(ppkg)
    ct = etree.fromstring(files["[Content_Types].xml"])
    defaults = {d.get("Extension").lower() for d in ct.findall(f"{{{CT_NS}}}Default")}
    pct = etree.fromstring(pz.read("[Content_Types].xml"))
    pdefaults = {d.get("Extension").lower(): d.get("ContentType") for d in pct.findall(f"{{{CT_NS}}}Default")}
    remap = {}
    for el in els:
        for rid in set(_rids(el)):
            if rid in remap:
                continue
            t = prels.get(rid)
            if t is None or t[0] not in TRAVELS:
                raise PartError("The page holds something other than pictures and links.")
            k = 1
            while f"rIdSK{k}" in used_ids:
                k += 1
            nid = f"rIdSK{k}"; used_ids.add(nid)
            r = etree.SubElement(brels, f"{{{REL_NS}}}Relationship"); r.set("Id", nid); r.set("Type", t[0])
            if t[2]:
                r.set("Target", t[1]); r.set("TargetMode", "External")
            else:
                src = posixpath.normpath(posixpath.join(posixpath.dirname(ppkg.main), t[1]))
                ext = posixpath.splitext(src)[1]
                m = 1
                while f"word/media/sk_part{m}{ext}" in files:
                    m += 1
                dst = f"word/media/sk_part{m}{ext}"
                files[dst] = pz.read(src)
                r.set("Target", posixpath.relpath(dst, posixpath.dirname(bpkg.main)))
                e = ext.lstrip(".").lower()
                if e not in defaults and e in pdefaults:
                    d = etree.SubElement(ct, f"{{{CT_NS}}}Default"); d.set("Extension", e); d.set("ContentType", pdefaults[e])
                    defaults.add(e)
            remap[rid] = nid
    for el in els:
        for x in el.iter():
            for a, v in list(x.attrib.items()):
                if a.startswith("{" + R_NS + "}") and v in remap:
                    x.set(a, remap[v])
        for npr in list(el.iter(q("numPr"))):
            npr.getparent().remove(npr)                     # a cover's list numbering would point at nothing here
    # styles the part uses and the template lacks
    sname = bpkg.word_part("/styles")
    sroot = etree.fromstring(files[sname])
    have = {s.get(q("styleId")) for s in sroot.findall("w:style", NS)}
    psroot = ppkg.tree(ppkg.word_part("/styles"))
    pstyles = {s.get(q("styleId")): s for s in psroot.findall("w:style", NS)}
    need = set()
    for el in els:
        need.update(x for x in _styles_used(el) if x and x not in have)
    while need:
        sid = need.pop()
        s = pstyles.get(sid)
        if s is None:
            for el in els:
                for x in el.iter(q("pStyle"), q("rStyle"), q("tblStyle")):
                    if x.get(q("val")) == sid:
                        x.getparent().remove(x)
            continue
        c = etree.fromstring(etree.tostring(s))
        for npr in list(c.iter(q("numPr"))):
            npr.getparent().remove(npr)
        sroot.append(c); have.add(sid)
        b = c.find("w:basedOn", NS)
        if b is not None and b.get(q("val")) not in have:
            need.add(b.get(q("val")))
    # put the part in
    body = broot.find("w:body", NS)
    blocks = _blocks(broot)
    if where == "cover":
        sp, old = blocks[0]
        anchor = old[0] if old else None
        for e in els:
            (anchor.addprevious(e) if anchor is not None else body.insert(0, e))
        holder = next((o for o in old if local(o) == "p" and o.find("w:pPr/w:sectPr", NS) is not None), None)
        # the volume values the headers read (PE Volume Name, PE Solicitation, PE Company) stay on the cover when the
        # part has none of its own, so headers can still show them
        from prodengine.pe.hf import SOURCE_STYLES
        id_name = {s_.get(q("styleId")): (s_.find("w:name", NS).get(q("val")) if s_.find("w:name", NS) is not None else "")
                   for s_ in sroot.findall("w:style", NS)}
        part_has = {id_name.get(x) for e in els for x in _styles_used(e)}
        keep = [o for o in old if o is not holder and local(o) == "p" and o.find("w:pPr/w:pStyle", NS) is not None
                and id_name.get(o.find("w:pPr/w:pStyle", NS).get(q("val"))) in SOURCE_STYLES.values()
                and id_name.get(o.find("w:pPr/w:pStyle", NS).get(q("val"))) not in part_has]
        for o in old:
            if o is not holder and o not in keep:
                body.remove(o)
        if holder is not None and keep:                     # the kept values sit after the part, before the break
            for o in keep:
                holder.addprevious(o)
        if holder is not None:                             # keep the section break, empty
            for c in list(holder):
                if local(c) != "pPr":
                    holder.remove(c)
            ppr = holder.find("w:pPr", NS)
            for c in list(ppr):
                if local(c) not in ("sectPr",):
                    ppr.remove(c)
    elif where == "title":                                   # 3.34.0: the title page, a section of its own after the cover
        sp, old = blocks[0]
        holder = next((o for o in old if local(o) == "p" and o.find("w:pPr/w:sectPr", NS) is not None), None)
        if holder is None or len(blocks) < 2:
            raise PartError("The template has no cover section to put the title page after.")
        anchor = holder
        for e in els:
            anchor.addnext(e); anchor = e
        brk = etree.Element(q("p")); ppr = etree.SubElement(brk, q("pPr"))
        sect = etree.fromstring(etree.tostring(holder.find("w:pPr/w:sectPr", NS)))
        for x in list(sect):
            if local(x) in ("headerReference", "footerReference", "pgNumType"):
                sect.remove(x)
        if part_sect is not None:
            for tag in ("pgSz", "pgMar"):
                src = part_sect.find(f"w:{tag}", NS)
                dst = sect.find(f"w:{tag}", NS)
                if src is not None and dst is not None:
                    dst.getparent().replace(dst, etree.fromstring(etree.tostring(src)))
        ppr.append(sect)
        anchor.addnext(brk)
    else:
        final = body.find("w:sectPr", NS)
        brk = etree.SubElement(body, q("p"))
        ppr = etree.SubElement(brk, q("pPr"))
        ppr.append(etree.fromstring(etree.tostring(final)))
        final.addprevious(brk)
        for e in els:
            final.addprevious(e)
        if part_sect is not None:
            for tag in ("pgSz", "pgMar"):
                src = part_sect.find(f"w:{tag}", NS)
                dst = final.find(f"w:{tag}", NS)
                if src is not None and dst is not None:
                    dst.getparent().replace(dst, etree.fromstring(etree.tostring(src)))
        pn = final.find("w:pgNumType", NS)
        if pn is not None:
            final.remove(pn)
    files[bpkg.main] = etree.tostring(broot, xml_declaration=True, encoding="UTF-8", standalone=True)
    files[brn] = etree.tostring(brels, xml_declaration=True, encoding="UTF-8", standalone=True)
    files[sname] = etree.tostring(sroot, xml_declaration=True, encoding="UTF-8", standalone=True)
    files["[Content_Types].xml"] = etree.tostring(ct, xml_declaration=True, encoding="UTF-8", standalone=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n in bz.namelist():
            z.writestr(n, files[n])
        for n in files:
            if n not in bz.namelist():
                z.writestr(n, files[n])
    return buf.getvalue()
