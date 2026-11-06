"""The setup made from a Word template the team brings (3.72.0, claude/stationkeeper-template-setup-decisions-2026-11-06.md).

write(template, out, main, appendix, front, opts, picks) makes a new document from the template: its styles, theme,
page setup, numbering, headers and footers stay. It starts blank in the template's look: the body section only, its
sample pages gone. picks say what else comes in: "keep" (the template's own cover, title page, front matter or back
matter sections, by index), "quick_parts" (by name: a cover page Quick Part goes first, the rest just before the body),
"no_hf" (sections whose header and footer are blank). The structure goes on the template's Heading 1 to 9, numbered
by the template's own list (templatefile.number_headings); each kind of setup text goes in its setup style, a style of
the same name in the template used as it is. A .dotm's macros are left out: the setup is a plain .docx.

check(path, plan) reads the made file back before it is handed over and lists what is wrong, with where: the headings
on the template's styles and numbering; no style outside the template's and the setup styles; each section's header
and footer as picked; every placed requirement in once; only the picked pages and Quick Parts in, the sample pages
gone. make(...) does both for every volume. The template is only read. Rules only; nothing leaves the PC."""
import copy, datetime, io, os, posixpath, re, zipfile

from lxml import etree

import templatefile as TF

W, R, NS = TF.W, TF.R, TF.NS
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
DOC_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
HDR_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"
FTR_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"
REL_HDR = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header"
REL_FTR = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer"
VBA = ("vbaProject.bin", "vbaData.xml")
_w = TF._w


def _frag(xml):
    return list(etree.fromstring(f'<w:body xmlns:w="{W}" xmlns:r="{R}">{xml}</w:body>'))


class Out:
    """The new document's parts as they are being made (the template's zip, read once)."""

    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.names = self.z.namelist()
        self.trees, self.added = {}, {}
        self.drop = {n for n in self.names if posixpath.basename(n) in VBA or n.endswith("vbaProject.bin.rels")}

    def tree(self, name):
        if name not in self.trees:
            self.trees[name] = TF.xml_of(self.z, name)
        return self.trees[name]

    def rels(self, part):
        d, f = posixpath.split(part)
        name = posixpath.join(d, "_rels", f + ".rels")
        t = self.tree(name)
        if t is None:
            t = etree.Element(f"{{{PR}}}Relationships", nsmap={None: PR})
            self.trees[name] = t; self.added[name] = None
        return t

    def rel_targets(self, part):
        base = posixpath.dirname(part)
        out = {}
        for r in self.rels(part).findall(f"{{{PR}}}Relationship"):
            t = r.get("Target") or ""
            out[r.get("Id")] = (r.get("Type"), t if r.get("TargetMode") == "External" else
                                (t.lstrip("/") if t.startswith("/") else posixpath.normpath(posixpath.join(base, t))), r.get("TargetMode"))
        return out

    def add_rel(self, part, typ, target_part):
        rels = self.rels(part)
        ids = {r.get("Id") for r in rels}
        k = 1
        while f"rIdSK{k}" in ids:
            k += 1
        r = etree.SubElement(rels, f"{{{PR}}}Relationship")
        r.set("Id", f"rIdSK{k}"); r.set("Type", typ); r.set("Target", posixpath.relpath(target_part, posixpath.dirname(part)))
        return f"rIdSK{k}"

    def add_part(self, name, root, ct):
        self.trees[name] = root; self.added[name] = ct

    def save(self, path, props=None):
        ct = self.tree("[Content_Types].xml")
        for o in ct.findall(f"{{{CT}}}Override"):
            pn = o.get("PartName").lstrip("/")
            if pn == "word/document.xml":
                o.set("ContentType", DOC_CT)
            if pn in self.drop:
                ct.remove(o)
        for d in ct.findall(f"{{{CT}}}Default"):
            if d.get("Extension", "").lower() == "bin" and not any(n.endswith(".bin") and n not in self.drop for n in self.names):
                ct.remove(d)
        for name, typ in self.added.items():
            if typ:
                o = etree.SubElement(ct, f"{{{CT}}}Override"); o.set("PartName", "/" + name); o.set("ContentType", typ)
        drels = self.rels("word/document.xml")
        for r in list(drels):
            if (r.get("Type") or "").endswith("/vbaProject"):
                drels.remove(r)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zo:
            for n in self.names:
                if n in self.drop:
                    continue
                b = etree.tostring(self.trees[n], xml_declaration=True, encoding="UTF-8", standalone=True) \
                    if self.trees.get(n) is not None else self.z.read(n)
                zo.writestr(n, b)
            for n in self.added:
                if n not in self.names:
                    zo.writestr(n, etree.tostring(self.trees[n], xml_declaration=True, encoding="UTF-8", standalone=True))
        data = buf.getvalue()
        if props:
            import prodtemplate as PT
            data = PT.with_properties(data, props)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        tmp = path + ".part"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        return path


def _blank_story(out, kind):
    """One empty header or footer part (made once), for a section the person wants without one."""
    name = f"word/{'header' if kind == 'header' else 'footer'}SKblank.xml"
    if name not in out.trees:
        root = etree.Element(_w("hdr" if kind == "header" else "ftr"), nsmap={"w": W, "r": R})
        etree.SubElement(root, _w("p"))
        out.add_part(name, root, HDR_CT if kind == "header" else FTR_CT)
        out._blank = getattr(out, "_blank", {})
        out._blank[kind] = out.add_rel("word/document.xml", REL_HDR if kind == "header" else REL_FTR, name)
    return out._blank[kind]


def _blank_hf(out, sp):
    for r in [r for r in sp if etree.QName(r).localname in ("headerReference", "footerReference")]:
        sp.remove(r)
    for i, kind in enumerate(("header", "footer")):
        rid = _blank_story(out, kind)
        for typ in ("default", "first", "even"):
            el = etree.Element(_w(f"{kind}Reference")); el.set(_w("type"), typ); el.set(f"{{{R}}}id", rid)
            sp.insert(0, el)


def _quick_part(out, name):
    """A Quick Part's content (its section breaks left out), its pictures and links carried into the document."""
    g = next((t for (typ, t, mode) in out.rel_targets("word/document.xml").values() if (typ or "").endswith("/glossaryDocument")), None)
    groot = out.tree(g) if g else None
    if groot is None:
        return None, None
    dp = next((d for d in groot.iter(_w("docPart")) if (d.find("w:docPartPr/w:name", NS) is not None
                                                        and d.find("w:docPartPr/w:name", NS).get(_w("val")) == name)), None)
    if dp is None:
        return None, None
    gal = dp.find("w:docPartPr/w:category/w:gallery", NS)
    els = [copy.deepcopy(ch) for ch in dp.find("w:docPartBody", NS) if etree.QName(ch).localname != "sectPr"]
    grels = out.rel_targets(g)
    remap = {}
    for el in els:
        for node in el.iter():
            for att in list(node.attrib):
                if att in (f"{{{R}}}embed", f"{{{R}}}id", f"{{{R}}}link"):
                    rid = node.get(att)
                    if rid in grels and rid not in remap:
                        typ, tgt, mode = grels[rid]
                        if mode == "External":
                            rels = out.rels("word/document.xml")
                            k = len(rels) + 1
                            r = etree.SubElement(rels, f"{{{PR}}}Relationship")
                            r.set("Id", f"rIdSKx{k}"); r.set("Type", typ); r.set("Target", tgt); r.set("TargetMode", "External")
                            remap[rid] = f"rIdSKx{k}"
                        else:
                            remap[rid] = out.add_rel("word/document.xml", typ, tgt)
                    if rid in remap:
                        node.set(att, remap[rid])
    return els, (gal.get(_w("val")) if gal is not None else "")


def styleref_styles(out_or_z):
    """The style names the headers and footers print with STYLEREF fields (the volume's name on the cover, say)."""
    names = out_or_z.names if isinstance(out_or_z, Out) else out_or_z.namelist()
    got = set()
    for n in names:
        if re.match(r"word/(header|footer)[^/]*\.xml$", n):
            root = out_or_z.tree(n) if isinstance(out_or_z, Out) else TF.xml_of(out_or_z, n)
            if root is None:
                continue
            instr = " ".join([x.text or "" for x in root.iter(_w("instrText"))] + [x.get(_w("instr")) or "" for x in root.iter(_w("fldSimple"))])
            got |= {m.strip('"').casefold() for m in re.findall(r'STYLEREF\s+("[^"]+"|\S+)', instr)}
    return got


def _keep_styleref_text(out, body, removed, names):
    """A header field that prints text from a page the setup leaves out (the cover's volume name) would print an error.
    That text comes along as hidden text at the top of the body, so the field still finds it. Returns the style names."""
    want = styleref_styles(out)
    have = {names.get(p.find("w:pPr/w:pStyle", NS).get(_w("val")), "") for p in body.iter(_w("p")) if p.find("w:pPr/w:pStyle", NS) is not None}
    got = []
    for st in sorted(want - have):
        src = next((p for e in removed for p in e.iter(_w("p")) if p.find("w:pPr/w:pStyle", NS) is not None
                    and names.get(p.find("w:pPr/w:pStyle", NS).get(_w("val")), "") == st and TF.text_of(p).strip()), None)
        if src is None:
            continue
        p = copy.deepcopy(src)
        for r in p.iter(_w("r")):
            rpr = r.find("w:rPr", NS)
            if rpr is None:
                rpr = etree.Element(_w("rPr")); r.insert(0, rpr)
            if rpr.find("w:vanish", NS) is None:
                rpr.append(etree.Element(_w("vanish")))
        sp = p.find("w:pPr/w:sectPr", NS)
        if sp is not None:
            sp.getparent().remove(sp)
        body.insert(0, p)
        got.append((st, TF.text_of(p).strip()))
    return got


def write(template_path, out_path, main_doc, appendix_doc, front_doc, opts, picks, props=None):
    """See the module text. Returns {"path", "plan"}: plan is what check() holds the file to."""
    import setuptemplate as ST
    import elementbuild as EB
    picks = picks or TF.default_picks(None)
    out = Out(template_path)
    droot, sroot, nroot = out.tree("word/document.xml"), out.tree("word/styles.xml"), out.tree("word/numbering.xml")
    tmpl_ids = {s.get(_w("styleId")) for s in sroot.findall("w:style", NS)}
    ids = ST.ensure_styles(sroot, opts)
    hid = TF.heading_ids(sroot)
    remap = {ST.style_ids(opts)[k]: v for k, v in ids.items() if ST.style_ids(opts)[k] != v}
    remap.update({f"Heading{n}": sid for n, sid in hid.items() if sid != f"Heading{n}"})

    def fix(xml):
        for a, b in remap.items():
            xml = xml.replace(f'w:pStyle w:val="{a}"', f'w:pStyle w:val="{b}"')
        return xml
    body = droot.find("w:body", NS)
    names = TF.style_names(sroot)
    secs = TF.split_sections(body)
    kinds = TF.kinds(secs, names)
    keep = set(picks.get("keep") or [])
    body_i = kinds.index("body")
    app_i = next((i for i, k in enumerate(kinds) if k == "appendix"), None) if appendix_doc is not None else None
    gone_text = []
    kept_secs = []
    removed = []                                                # the template's paragraphs left out, for the header fields below
    for i, els in enumerate(secs):
        take = i == body_i or i == app_i or (i in keep and kinds[i] not in ("body", "appendix"))
        last = els[-1]
        if not take:
            gone_text += [t for t in (TF.text_of(e).strip() for e in els) if len(t) > 6][:3]
            for e in els:
                if e.tag == _w("sectPr"):
                    continue
                removed.append(e)
                body.remove(e)
            if last.tag == _w("sectPr") and kept_secs and kept_secs[-1][-1].tag == _w("p"):
                pr = kept_secs[-1][-1]                          # the last section went: the one before ends the document
                sp = pr.find("w:pPr/w:sectPr", NS)
                body.replace(last, sp)                          # its section properties move to the body's end
                if not TF.text_of(pr).strip():
                    body.remove(pr)
                kept_secs[-1] = kept_secs[-1][:-1] + [sp]
            continue
        if i in (body_i, app_i):                                # the template's sample pages go; its section break stays
            gone_text += [t for t in (TF.text_of(e).strip() for e in els[:-1]) if len(t) > 6][:3]
            for e in els[:-1]:
                removed.append(e)
                body.remove(e)
            if last.tag == _w("p"):
                for r in [r for r in last if r.tag != _w("pPr")]:
                    last.remove(r)
            anchor = last
            doc = main_doc if i == body_i else appendix_doc
            for e in _frag(fix("".join(doc.body))):
                anchor.addprevious(e)
        kept_secs.append(els)
    if appendix_doc is not None and app_i is None:              # no appendix section in the template: after the body
        body_secs = TF.split_sections(body)
        end = body_secs[-1][-1]
        for e in _frag(fix("".join(appendix_doc.body))):
            end.addprevious(e)
    ours = set()
    for e in body:
        for p in e.iter(_w("p")):
            ours.add(p)
    template_paras = set()                                      # the template's own kept paragraphs are not ours
    for i in sorted(keep):
        if i < len(secs) and i not in (body_i, app_i):
            for e in secs[i]:
                template_paras.update(e.iter(_w("p")))
    ours -= template_paras
    if front_doc is not None:                                   # the structure's front matter, before the body
        first_body = next((e for e in body if e in ours), None)
        for e in _frag(fix("".join(front_doc.body))):
            (first_body.addprevious(e) if first_body is not None else body.insert(0, e))
            ours.update(e.iter(_w("p")))
    qp_in = []
    for name in picks.get("quick_parts") or []:
        els, gallery = _quick_part(out, name)
        if not els:
            continue
        qp_in.append((name, " ".join(TF.text_of(e) for e in els).strip()[:40]))
        if gallery == "coverPg":                                 # a cover is a page of its own
            if not any(b.get(_w("type")) == "page" for b in els[-1].iter(_w("br"))) and els[-1].find(".//w:sectPr", NS) is None:
                els.append(_frag('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')[0])
            for e in reversed(els):
                body.insert(0, e)
        else:
            first_body = next((e for e in body if any(p in ours for p in e.iter(_w("p")))), None)
            for e in els:
                (first_body.addprevious(e) if first_body is not None else body.insert(0, e))
    no_hf = set(picks.get("no_hf") or [])
    for i, els in enumerate(secs):
        if i in no_hf and (i in (body_i, app_i) or i in keep):
            sp = TF.sect_of(els)
            if sp is not None:
                _blank_hf(out, sp)
    anchors = _keep_styleref_text(out, body, removed, names)
    EB.ensure_appendix_styles(sroot)
    EB.apply_section_marks(body, body.find("w:sectPr", NS))
    notes = TF.number_headings(body, sroot, nroot, only=ours)
    plan = {"template_styles": tmpl_ids, "setup_styles": set(ids.values()) | {s.get(_w("styleId")) for s in sroot.findall("w:style", NS)
                                                                           if (s.get(_w("styleId")) or "").startswith("Appendix")},
            "headings": hid, "numbered": {h["level"] for h in TF.heading_numbering(sroot, nroot) if h["numbered"]},
            "gone": [t for t in gone_text if t and t not in {a[1] for a in anchors}], "quick_parts": qp_in, "kept": sorted(keep), "no_hf": sorted(no_hf),
            "kinds": kinds, "notes": notes, "anchors": anchors}
    out.save(out_path, props)
    return {"path": out_path, "plan": plan}


# ------------------------------------------------------------------ the check before it is handed over
def check(path, plan, required=()):
    """[{"what", "ok", "where"}] for the made file (see the module text). required: [(label, text)] the placed
    requirements that must each be in once."""
    rows = []
    add = lambda what, ok, where="": rows.append({"what": what, "ok": bool(ok), "where": where})
    with zipfile.ZipFile(path) as z:
        doc, sroot = TF.xml_of(z, "word/document.xml"), TF.xml_of(z, "word/styles.xml")
        hdr_parts = {n: TF.xml_of(z, n) for n in z.namelist() if re.match(r"word/(header|footer)SKblank\.xml$", n)}
        has_vba = any(n.endswith("vbaProject.bin") for n in z.namelist())
        ct = z.read("[Content_Types].xml").decode("utf-8", "replace")
    body = doc.find("w:body", NS)
    names = TF.style_names(sroot)
    allowed = set(plan["template_styles"]) | set(plan["setup_styles"])
    used = {}
    for el in body.iter():
        if etree.QName(el).localname in ("pStyle", "rStyle", "tblStyle"):
            used.setdefault(el.get(_w("val")), 0)
            used[el.get(_w("val"))] += 1
    foreign = sorted(s for s in used if s not in allowed)
    add("No style outside the template's and the setup styles", not foreign, ", ".join(foreign[:6]))
    heads, typed = 0, []
    hlev = {sid: lev for lev, sid in plan["headings"].items()}
    for p in body.iter(_w("p")):
        ps = p.find("w:pPr/w:pStyle", NS)
        sid = ps.get(_w("val")) if ps is not None else None
        if sid in hlev:
            heads += 1
            off = p.find("w:pPr/w:numPr/w:numId", NS)
            if hlev[sid] in plan["numbered"] and TF.TYPED.match(TF.text_of(p)) and not (off is not None and off.get(_w("val")) == "0"):
                typed.append(TF.text_of(p)[:50])
    add("Every heading is on the template's heading styles, numbered by its own list (no number typed twice)",
        heads and not typed, "; ".join(typed[:4]) if typed else ("no headings" if not heads else ""))
    for n in plan.get("notes") or []:
        add("A heading keeps its typed number", True, n)
    text = TF.text_of(body)
    left = [t for t in plan.get("gone") or [] if t in text]
    add("The template's sample pages are gone", not left, "; ".join(left[:3]))
    for name, snippet in plan.get("quick_parts") or []:
        add(f"Quick Part in: {name}", snippet[:20] in text if snippet else True, "")
    with zipfile.ZipFile(path) as z:
        refs = styleref_styles(z)
    present = {names.get(p.find("w:pPr/w:pStyle", NS).get(_w("val")), "") for p in body.iter(_w("p"))
               if p.find("w:pPr/w:pStyle", NS) is not None and TF.text_of(p).strip()}
    lost = sorted(refs - present)
    add("Every header and footer field finds its text", not lost, ", ".join(f"STYLEREF {x}" for x in lost))
    secs = TF.split_sections(body)
    add("Each kept part is a section of its own, as the template has it", len(secs) >= 1, f"{len(secs)} section(s)")
    blanks = sum(1 for sp in body.iter(_w("sectPr")) for r in sp if etree.QName(r).localname == "headerReference"
                 and "SK" in (r.get(f"{{{R}}}id") or ""))
    add("Headers and footers as picked", (blanks > 0) == bool(plan.get("no_hf")) and (not plan.get("no_hf") or hdr_parts),
        f"{len(plan.get('no_hf') or [])} part(s) without")
    missing, twice = [], []
    flat = re.sub(r"\s+", " ", text)
    for lab, t in required or ():
        key = re.sub(r"\s+", " ", t).strip()[:60]
        c = flat.count(key) if key else 1
        (missing if c == 0 else twice if c > 1 else []).append(f"{lab}: {key[:40]}")
    add("Every placed requirement is in once", not missing and not twice,
        "; ".join(([f"missing {x}" for x in missing] + [f"twice {x}" for x in twice])[:4]))
    add("A plain Word document (no macros, not a template)", not has_vba and "template.main+xml" not in ct and "macroEnabled" not in ct)
    return rows


def problems(rows):
    return [r for r in rows if not r["ok"]]


# ------------------------------------------------------------------ the effort's choice, and making every volume
KEY = "template_file"                                           # in the setup record: {"*" or volume: {"file", "picks"}}


def keep_with_effort(effort_path, path):
    """A copy of the template in the effort's Templates folder (once per distinct file). Returns the copy's path."""
    import hashlib, shutil
    import effortfolders as EF
    root = EF.root(effort_path) if effort_path else ""
    if not root:
        return path
    folder = os.path.join(root, "Templates")
    os.makedirs(folder, exist_ok=True)
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    dst = os.path.join(folder, os.path.basename(path))
    if os.path.isfile(dst):
        with open(dst, "rb") as f:
            if hashlib.sha256(f.read()).hexdigest() == digest:
                return dst
        stem, ext = os.path.splitext(os.path.basename(path))
        dst = os.path.join(folder, f"{stem} {digest[:6]}{ext}")
    if not os.path.isfile(dst):
        shutil.copyfile(path, dst)
    return dst


def choice(M):
    import setupdoc as SD
    return dict(SD.setup_of(M).get(KEY) or {})


def set_choice(M, volume, path, picks, effort_path=""):
    """volume "*": every volume (a volume of its own keeps its own). The file is kept with the effort; the record holds
    its name relative to the effort's folder when it is inside it."""
    import setupdoc as SD
    import effortfolders as EF
    kept = keep_with_effort(effort_path, path) if effort_path else path
    root = EF.root(effort_path) if effort_path else ""
    rel = os.path.relpath(kept, root) if root and os.path.abspath(kept).startswith(os.path.abspath(root) + os.sep) else kept
    S = SD.setup_of(M)
    c = dict(S.get(KEY) or {})
    c[volume or "*"] = {"file": rel.replace(os.sep, "/"), "picks": {k: list(v) for k, v in (picks or {}).items()}}
    S[KEY] = c
    SD._log(M, "(setup)", "template file chosen" + (f" for {volume}" if volume and volume != "*" else ""))
    return c


def clear_choice(M, volume=None):
    import setupdoc as SD
    S = SD.setup_of(M)
    if volume in (None, "*"):
        S.pop(KEY, None)
    else:
        (S.get(KEY) or {}).pop(volume, None)


def for_volume(M, vname, effort_path=""):
    """(the template's path, picks) for a volume, or None when it has no template file."""
    import effortfolders as EF
    c = choice(M)
    e = c.get(vname) or c.get("*")
    if not e:
        return None
    p = e["file"]
    if not os.path.isabs(p) and effort_path:
        p = os.path.join(EF.root(effort_path), *p.split("/"))
    return p, e.get("picks") or TF.default_picks(None)


def make(M, folder, config_dir, ws=None, effort_name="", info=None, when=None, context=None, effort_path="", volumes=None):
    """Every volume with a template file: the setup made on it and checked. Returns [{"volume", "setup", "template",
    "check", "plan"}]; a volume without a template file is left out (Make the setup makes it as before)."""
    import setupdoc as SD
    import setuptemplate as ST
    when = when or datetime.datetime.now()
    tag, stamp = when.strftime("%Y-%m-%d_%H%M"), when.strftime("%Y-%m-%d %H:%M")
    P, inh, B = SD.placed_in(M), SD.inherited_sections(M), SD.by_id(M)
    stem = SD._safe(os.path.splitext(os.path.basename(M.path))[0] if getattr(M, "path", "") else M.name)
    groups = SD.volume_groups(M)
    planned = {p["volume"]: p for p in ST.plan(M, config_dir, ws, effort_name, info)}
    out = []
    for vname, entries in groups:
        if volumes is not None and vname not in volumes:
            continue
        got = for_volume(M, vname, effort_path)
        if not got or not os.path.isfile(got[0]):
            continue
        tpath, picks = got
        info_t = TF.read(tpath)
        kinds = [s["kind"] for s in info_t["sections"]]
        title_kept = any(kinds[i] == "title" for i in picks.get("keep") or [] if i < len(kinds))
        std = planned[vname]["std"]
        opts, df, dm, da = ST.volume_docs(M, vname, entries, std, config_dir, ws, info, context, stamp, P, inh, title_in_template=title_kept)
        part = "" if len(groups) == 1 else "_" + SD._safe(vname)
        path = os.path.join(folder, f"{stem}_Response_Setup{part}_{tag}.docx")
        res = write(tpath, path, dm, da, df, opts, picks, {"StationkeeperMatrix": M.name or "", "StationkeeperSetupExported": stamp,
                                                          "StationkeeperSetupPart": vname, "SK Template": os.path.basename(tpath)})
        req = []
        skip = ST.skip_kinds(opts)
        if "rfp" not in skip:
            for o in entries:
                lab = __import__("compliance").outline_label(o)
                for iid in P.get(lab) or []:
                    it = B.get(iid)
                    if it is not None and it.get("decision") == "Keep" and SD.kind_of(it) == "Requirement":
                        req.append((lab, it.get("text", "")))
        rows = check(path, res["plan"], req)
        out.append({"volume": vname, "setup": path, "template": tpath, "check": rows, "plan": res["plan"]})
    if out:
        S = SD.setup_of(M)
        snap = SD.snapshot(M)
        snap.update(time=stamp, files=[os.path.basename(x["setup"]) for x in out])
        S["exports"] = (S["exports"] + [snap])[-10:]
        SD._log(M, "(setup)", f"setup made on the team's template: {len(out)} file(s)")
    return out
