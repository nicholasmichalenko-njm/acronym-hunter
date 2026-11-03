"""The setup written on the effort's template (3.24.0).

For each planned volume, Stationkeeper makes the volume's template from the effort's Production Standards (the volume's
profile, its name on the cover, the solicitation and company, the fill-ins), then writes the Response Setup into a
document made from that template: its styles, cover, pagination, TOC and front matter stay; the template's sample
pages are replaced by the response structure with every placed sentence.

What the customer wrote and the team's notes go in in their own styles, each one hidden text unless you say otherwise,
so an author sees them with Show/Hide on and the response alone with it off:
  rfp       the RFP's requirement text            SK RFP Requirement
  support   RFP support text under a requirement  SK RFP Support
  customer  the customer's own sentences          SK Customer Text
  library   context from library documents        SK Library Context
  pm        proposal manager direction and notes  SK PM Direction
  note      leads, page limits and part rules     SK Setup Note
A style the template already has (your own) is used as it is, with hidden text set as chosen; a missing one is added.
The template is read, never written; the setup is a new dated document. Rules only; nothing leaves the PC."""
import copy, datetime, io, os, re, zipfile
from xml.sax.saxutils import escape

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
TEMPLATE_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"
DOCUMENT_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
KINDS = (("rfp", "RFP requirement text", "SK RFP Requirement", "7030A0", False),
         ("support", "RFP support text", "SK RFP Support", "2E74B5", True),
         ("customer", "The customer's own sentences", "SK Customer Text", "6B21A8", True),
         ("library", "Context from library documents", "SK Library Context", "0F766E", True),
         ("pm", "Proposal manager direction and notes", "SK PM Direction", "00B050", False),
         ("note", "Leads, page limits and part rules", "SK Setup Note", "1E3A8A", False))


def _w(t):
    return f"{{{W}}}{t}"


def sid_of(name):
    return re.sub(r"[^A-Za-z0-9]", "", name) or "SKSetup"


def options(M):
    """{kind: {"style": style name, "hidden": bool}} kept with the matrix's setup; every kind hidden by default."""
    import setupdoc as SD
    S = SD.setup_of(M)
    have = S.get("on_template") or {}
    out = {}
    for k, _label, style, _c, _ind in KINDS:
        o = have.get(k) or {}
        out[k] = {"style": " ".join(str(o.get("style") or style).split())[:60] or style, "hidden": bool(o.get("hidden", True))}
    return out


def set_options(M, opts):
    import setupdoc as SD
    SD.setup_of(M)["on_template"] = {k: {"style": v["style"], "hidden": bool(v["hidden"])} for k, v in opts.items()
                                     if k in dict((x[0], 1) for x in KINDS)}


def _style_xml(sid, name, color, indent, hidden):
    ppr = (f'<w:pPr><w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="{color}"/></w:pBdr><w:ind w:left="720"/></w:pPr>'
           if indent else "")
    return (f'<w:style xmlns:w="{W}" w:type="paragraph" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{escape(name)}"/>'
            f'<w:basedOn w:val="Normal"/><w:qFormat/>{ppr}<w:rPr>{"<w:vanish/>" if hidden else ""}<w:color w:val="{color}"/></w:rPr></w:style>')


def ensure_styles(sroot, opts):
    """The kinds' styles in the document: an existing style by name is used (hidden text set as chosen), a missing one is
    added. Returns {kind: style id}."""
    by_name = {}
    for s in sroot.findall("w:style", NS):
        nm = s.find("w:name", NS)
        if nm is not None:
            by_name[nm.get(_w("val")).casefold()] = s
    ids = {s.get(_w("styleId")) for s in sroot.findall("w:style", NS)}
    out = {}
    for k, _label, default_name, color, indent in KINDS:
        o = opts.get(k) or {"style": default_name, "hidden": True}
        s = by_name.get(o["style"].casefold())
        if s is None:
            sid = sid_of(o["style"])
            n = 2
            while sid in ids:
                sid = f"{sid_of(o['style'])}{n}"; n += 1
            s = etree.fromstring(_style_xml(sid, o["style"], color, indent, o["hidden"]))
            sroot.append(s); ids.add(sid); by_name[o["style"].casefold()] = s
        else:
            rpr = s.find("w:rPr", NS)
            if rpr is None:
                rpr = etree.SubElement(s, _w("rPr"))
            v = rpr.find("w:vanish", NS)
            if o["hidden"] and v is None:
                rpr.insert(0, etree.Element(_w("vanish")))
            elif o["hidden"] and v is not None:
                v.attrib.pop(_w("val"), None)
            elif not o["hidden"] and v is not None:
                rpr.remove(v)
        out[k] = s.get(_w("styleId"))
    return out


def _style_names(sroot):
    out = {}
    for s in sroot.findall("w:style", NS):
        nm = s.find("w:name", NS)
        out[s.get(_w("styleId"))] = (nm.get(_w("val")) if nm is not None else "").casefold()
    return out


def _pstyle(el, names):
    ps = el.find("w:pPr/w:pStyle", NS) if el.tag == _w("p") else None
    return names.get(ps.get(_w("val")), "") if ps is not None else ""


def _set_text(p, text):
    """A paragraph's text replaced, keeping its first run's look."""
    runs = p.findall("w:r", NS)
    rpr = copy.deepcopy(runs[0].find("w:rPr", NS)) if runs and runs[0].find("w:rPr", NS) is not None else None
    for r in list(p):
        if r.tag != _w("pPr"):
            p.remove(r)
    r = etree.SubElement(p, _w("r"))
    if rpr is not None:
        r.append(rpr)
    t = etree.SubElement(r, _w("t")); t.text = text; t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def place_body(droot, names, main_xml, appendix_xml):
    """The template's sample pages (from the first Heading 1 on) replaced by the setup: the main parts before the end of
    the first section that holds them, the appendices before the next one (when the template has one). Paragraphs that
    end a section stay, emptied, so the page scheme stays as the template sets it. Returns how many elements went."""
    body = droot.find("w:body", NS)
    kids = list(body)
    final = kids[-1] if kids and kids[-1].tag == _w("sectPr") else None
    start = next((i for i, el in enumerate(kids) if _pstyle(el, names) == "heading 1"), None)
    frag = lambda xml: list(etree.fromstring(f'<w:body xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">{xml}</w:body>'))
    main, app = frag(main_xml), frag(appendix_xml)
    if start is None:                                  # no sample pages: the setup goes at the end
        anchor = final if final is not None else None
        for el in main + app:
            (anchor.addprevious(el) if anchor is not None else body.append(el))
        return 0
    removed, breaks = 0, []
    for el in kids[start:]:
        if el is final:
            continue
        if el.tag == _w("p") and el.find("w:pPr/w:sectPr", NS) is not None:
            for r in list(el):
                if r.tag != _w("pPr"):
                    el.remove(r)
            breaks.append(el)
            continue
        body.remove(el); removed += 1
    first = breaks[0] if breaks else final
    for el in main:
        first.addprevious(el) if first is not None else body.append(el)
    second = breaks[1] if len(breaks) > 1 else first
    for el in app:
        second.addprevious(el) if second is not None else body.append(el)
    return removed


def write(template_path, out_path, main_doc, appendix_doc, opts, fills=None, props=None):
    """A new document made from the template with the setup in it (see the module text). main_doc, appendix_doc:
    docxw.Doc objects made with styles=style_ids(...). fills: {cover style name: value}. Returns out_path."""
    zin = zipfile.ZipFile(template_path)
    names_in = zin.namelist()
    droot = etree.fromstring(zin.read("word/document.xml"))
    sroot = etree.fromstring(zin.read("word/styles.xml"))
    ids = ensure_styles(sroot, opts)
    names = _style_names(sroot)
    remap = {style_ids(opts)[k]: v for k, v in ids.items() if style_ids(opts)[k] != v}

    def fix(xml):                                       # the template's own style ids where they differ from the guess
        for a, b in remap.items():
            xml = xml.replace(f'w:pStyle w:val="{a}"', f'w:pStyle w:val="{b}"')
        return xml
    for p in droot.iter(_w("p")):                       # the cover: each fill-in's value in its style
        nm = _pstyle(p, names)
        for style, val in (fills or {}).items():
            if val and nm == style.casefold():
                _set_text(p, val)
    place_body(droot, names, fix("".join(main_doc.body)), fix("".join(appendix_doc.body)) if appendix_doc else "")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for i in zin.infolist():
            b = zin.read(i.filename)
            if i.filename == "word/document.xml":
                b = etree.tostring(droot, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif i.filename == "word/styles.xml":
                b = etree.tostring(sroot, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif i.filename == "[Content_Types].xml":
                b = b.replace(TEMPLATE_CT.encode(), DOCUMENT_CT.encode())
            z.writestr(i, b)
    data = out.getvalue()
    if props:
        import prodtemplate as PT
        data = PT.with_properties(data, props)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    tmp = out_path + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, out_path)
    return out_path


def style_ids(opts):
    """{kind: style id} before the template is read (the ids the styles get when they are added)."""
    return {k: sid_of(v["style"]) for k, v in opts.items()}


def make_all(M, folder, config_dir, ws=None, effort_name="", info=None, when=None, context=None, word=None, progress=None):
    """For each planned volume: its template (named "<effort> <volume>", next version) and the setup written on it.
    Returns [{"volume", "template", "setup", "version", "validation"}]."""
    import compliance as C
    import prodrules as PRL
    import prodtemplate as PT
    import setupdoc as SD
    import structparts as SP
    import templatereg as TR
    import fillins as FI
    say = progress or (lambda *a: None)
    when = when or datetime.datetime.now()
    tag = when.strftime("%Y-%m-%d_%H%M")
    stamp = when.strftime("%Y-%m-%d %H:%M")
    opts = options(M)
    P, inh = SD.placed_in(M), SD.inherited_sections(M)
    ctx = PRL.context(config_dir, effort_name, info or {}, rec=None)
    stem = SD._safe(os.path.splitext(os.path.basename(M.path))[0] if getattr(M, "path", "") else M.name)
    tfolder = os.path.join(folder, "Templates")
    out = []
    groups = SD.volume_groups(M)
    for vname, entries in groups:
        say(f"Template for {vname}")
        std = SP.standard_for(config_dir, ws, vname) or PRL.for_effort(config_dir, ws)
        std = PRL.apply_context(PRL.engine_ready(std), ctx, volume_name=vname if len(groups) > 1 or vname else None)
        tname = TR.clean_name(f"{effort_name or stem} {vname}".strip()) or "Effort template"
        ver = TR.next_version(config_dir, tname)
        std["_template_name"], std["_template_version"] = tname, ver
        std["name"] = f"{tname} v{ver}"
        std.setdefault("_parts_dir", os.path.join(config_dir, "production_parts"))
        job = PT.make(std, tfolder, "", word=word, parts_dir=std["_parts_dir"])
        e = TR.record(config_dir, tname, ver, job.copy, "", getattr(job, "validation", None), effort_name)
        TR.note_on_effort(ws, tname, e)
        say(f"Setup for {vname}")
        rules = None
        try:
            rules = SP.summaries(config_dir, ws, M, vname)
        except Exception:                               # noqa: BLE001
            pass
        main_e = [o for o in entries if SP.part_of(o) != "appendix"]
        app_e = [o for o in entries if SP.part_of(o) == "appendix"]
        sids = style_ids(opts)
        dm = SD._doc_for(M, vname, main_e, P, inh, stamp, context, rules, styles=sids)
        da = SD._doc_for(M, vname, app_e, P, inh, stamp, context, rules, styles=sids) if app_e else None
        fills = {FI.styles(std)[k]: FI.value(std, k) for k in FI.styles(std) if FI.value(std, k)}
        part = "" if len(groups) == 1 else "_" + SD._safe(vname)
        path = os.path.join(folder, f"{stem}_Response_Setup{part}_{tag}.docx")
        write(job.copy, path, dm, da, opts, fills, {"StationkeeperMatrix": M.name or "", "StationkeeperSetupExported": stamp,
                                                    "StationkeeperSetupPart": vname, "SK Template": tname, "SK Template Version": str(ver)})
        out.append({"volume": vname, "template": job.copy, "setup": path, "version": ver, "validation": getattr(job, "validation", None),
                    "template_name": tname})
    S = SD.setup_of(M)
    snap = SD.snapshot(M)
    snap.update(time=stamp, files=[os.path.basename(x["setup"]) for x in out])
    S["exports"] = (S["exports"] + [snap])[-10:]
    SD._log(M, "(setup)", f"setup written on templates: {len(out)} file(s)")
    return out


# ------------------------------------------------------------------ ready to make
def ready(M, rec=None):
    """The Ready to make list: [(ok, what, count)] for each thing the matrix, template and setup need."""
    import compliance as C
    import setupdoc as SD
    items = list(getattr(M, "items", []) or [])
    und = [it for it in items if not it.get("decision") and it.get("type") != "Heading"]
    P = SD.placed_in(M)
    placed = {i for ids in P.values() for i in ids}
    keep = [it for it in items if it.get("decision") == "Keep"]
    unplaced = [it for it in keep if it["id"] not in placed]
    out = [(not und, "Every sentence is decided or ignored", len(und)),
           (not unplaced, "Every requirement is in a section of the structure", len(unplaced))]
    if rec is not None:
        import excerpts as EX
        um = EX.objectives_unmapped(rec)
        out.append((not um, "Every customer objective is mapped to a section", len(um)))
        nv = [x for x in EX.excerpts(rec, "submit") if not x.get("value") and not x.get("text_only")]
        out.append((not nv, "Every submission excerpt has its value or is marked text only", len(nv)))
        wr = [x for x in EX.excerpts(rec, "format") if x.get("sub") == "written" and x.get("check") not in ("phrase", "final")]
        out.append((not wr, "Every written formatting rule is a phrase check or a Final Checks item", len(wr)))
    out.append((bool(getattr(M, "outline", None)), "The response structure has sections", len(getattr(M, "outline", []) or [])))
    return out
