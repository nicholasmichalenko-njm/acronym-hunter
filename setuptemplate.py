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
         ("objective", "Customer objectives mapped to a section", "SK Customer Objective", "B45309", True),    # 3.33.0
         ("topic", "Topics a section answers", "SK Topic", "4338CA", False),                                  # 3.33.0
         ("capture", "Captures placed in a section (every capture, unless set below)", "SK Capture", "00B050", True),   # 3.33.0
         ("library", "Context from library documents", "SK Library Context", "0F766E", True),
         ("pm", "Proposal manager direction and notes", "SK PM Direction", "00B050", False),
         ("note", "Leads, page limits and part rules", "SK Setup Note", "1E3A8A", False))
KIND_OF = {k: (label, style, color, ind) for k, label, style, color, ind in KINDS}


def _w(t):
    return f"{{{W}}}{t}"


def sid_of(name):
    return re.sub(r"[^A-Za-z0-9]", "", name) or "SKSetup"


def _clean(o, style):
    return {"style": " ".join(str(o.get("style") or style).split())[:60] or style, "hidden": bool(o.get("hidden", True)),
            "include": bool(o.get("include", True))}


def options(M, std=None):
    """{kind: {"style", "hidden", "include"}}: the content map (3.33.0). Every kind hidden and included by default; the
    profile's content map (std["content_map"], with this effort's changes on it) over that; a choice an older release kept
    with the matrix over that. A capture kind ("cap:<bin>") is listed only when the map sets it: otherwise a capture takes
    the "capture" row."""
    import setupdoc as SD
    S = SD.setup_of(M) if M is not None else {}
    have = S.get("on_template") or {}
    cmap = (std or {}).get("content_map") or {}
    out = {}
    for k, _label, style, _c, _ind in KINDS:
        o = dict(cmap.get(k) or {}); o.update(have.get(k) or {})
        out[k] = _clean(o, style)
    for k, o in cmap.items():
        if str(k).startswith("cap:") and isinstance(o, dict):
            out[k] = _clean(dict(out["capture"], **o), out["capture"]["style"])
    return out


def set_options(M, opts, ws=None):
    """The content map chosen in Make templates. With the effort's workspace (3.33.0) it is this effort's change to the
    profile's map (Production Standards > This effort shows it); without it, kept with the matrix as before."""
    import setupdoc as SD
    clean = {k: {"style": v["style"], "hidden": bool(v["hidden"]), "include": bool(v.get("include", True))} for k, v in opts.items()
             if k in KIND_OF or str(k).startswith("cap:")}
    if ws is None:
        SD.setup_of(M)["on_template"] = clean
        return
    eff = dict(ws.get("prod_std", {}) or {})
    over = dict(eff.get("over") or {})
    over["content_map"] = dict(over.get("content_map") or {}, **clean)
    eff["over"] = over
    ws.set("prod_std", eff)
    SD.setup_of(M).pop("on_template", None)


def skip_kinds(opts):
    """The kinds left out of the response file."""
    return {k for k, v in opts.items() if not v.get("include", True)}

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
    rows = [(k, KIND_OF[k][1], KIND_OF[k][2], KIND_OF[k][3]) for k in KIND_OF] + \
           [(k, v["style"], KIND_OF["capture"][2], True) for k, v in opts.items() if str(k).startswith("cap:")]
    for k, default_name, color, indent in rows:
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


def element_extras(config_dir, info=None, root=None):
    """3.30.1: what the elements are filled with: the effort's approved acronyms and abbreviations (term, definition), in
    order, and the team's response elements."""
    import responseelements as RE
    out = {"data": RE.load(config_dir) if config_dir else RE.builtins(), "acronyms": [], "units": []}
    try:                                               # 3.31.0: the team's units and the effort's captured ones
        import units as UN
        rec = None
        if root:
            import effortrec as RR
            rec = RR.Record(root)
        out["units"] = UN.for_effort(config_dir, rec)
    except Exception:  # noqa: BLE001
        import diag
        diag.swallowed()
    if config_dir:                                     # 3.32.0: the library's Quick Parts with their pages (measured or typed)
        try:
            import templatelib as TL
            lib = TL.Library(config_dir)
            out["lib_pages"] = {i["id"]: int(i["pages"]) for i in lib.items if i.get("pages")}
            out["lib_pages_by_name"] = {i["name"].casefold(): int(i["pages"]) for i in lib.items
                                        if i.get("pages") and i["kind"] == "quickpart"}
        except Exception:  # noqa: BLE001
            import diag
            diag.swallowed()
    path = (info or {}).get("path") or ""
    if path and os.path.isfile(path):
        try:
            import effort as E
            L = E.EffortList(path, "").load()
            rows = getattr(L, "rows", {}) or {}
            out["acronyms"] = sorted(((t, str((r or {}).get("Definition", "") or "")) for t, r in rows.items()
                                      if (r or {}).get("Status", "") == "Approved"), key=lambda x: x[0].casefold())
        except Exception:  # noqa: BLE001
            import diag
            diag.swallowed()
    return out


def place_front(droot, names, front_xml):
    """3.30.1: the structure's front matter (its elements: TOC, lists, Acronyms...) in place of the template's fixed
    front matter: between the cover's section break and the next one (else just before the first Heading 1)."""
    body = droot.find("w:body", NS)
    kids = list(body)
    start = next((i for i, el in enumerate(kids) if _pstyle(el, names) == "heading 1"), len(kids) - 1)
    brk = [i for i, el in enumerate(kids[:start]) if el.tag == _w("p") and el.find("w:pPr/w:sectPr", NS) is not None]
    els = list(etree.fromstring(f'<w:body xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                                f'{front_xml}</w:body>'))
    if len(brk) >= 2:                                  # cover | front matter | the response
        for el in kids[brk[0] + 1:brk[1]]:
            body.remove(el)
        anchor = kids[brk[1]]
    else:
        anchor = kids[start]
    for el in els:
        anchor.addprevious(el)
    return len(els)


def write(template_path, out_path, main_doc, appendix_doc, opts, fills=None, props=None, front_doc=None):
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
    if front_doc is not None:                          # after the body: the template's own sample pages are gone by then
        place_front(droot, names, fix("".join(front_doc.body)))
    import elementbuild as EB                          # 3.30.1: the appendix styles, and Word sections of their own
    EB.ensure_appendix_styles(sroot)
    body = droot.find("w:body", NS)
    EB.apply_section_marks(body, body.find("w:sectPr", NS))
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


def plan(M, config_dir, ws=None, effort_name="", info=None):
    """3.25.0: what make_all will make, before anything is written: [{"volume", "template_name", "version", "std"}],
    std being the standard in force for that volume with the effort's values on it (for the details view)."""
    import prodrules as PRL
    import setupdoc as SD
    import structparts as SP
    import templatereg as TR
    ctx = PRL.context(config_dir, effort_name, info or {}, rec=None)
    stem = SD._safe(os.path.splitext(os.path.basename(M.path))[0] if getattr(M, "path", "") else M.name)
    groups = SD.volume_groups(M)
    out = []
    for vname, _entries in groups:
        std = SP.standard_for(config_dir, ws, vname) or PRL.for_effort(config_dir, ws)
        std = PRL.apply_context(PRL.engine_ready(std), ctx, volume_name=vname if len(groups) > 1 or vname else None)
        tname = TR.clean_name(f"{effort_name or stem} {vname}".strip()) or "Effort template"
        out.append({"volume": vname, "template_name": tname, "version": TR.next_version(config_dir, tname), "std": std})
    return out


def draft_counts(path):
    """3.27.0: (pages Word counted when the draft was last saved, Heading 1 paragraphs) of a volume's draft; None for a
    value the file does not say. The draft is only read."""
    import re
    import zipfile
    try:
        z = zipfile.ZipFile(path)
        app = z.read("docProps/app.xml").decode("utf-8", "replace") if "docProps/app.xml" in z.namelist() else ""
        doc = z.read("word/document.xml").decode("utf-8", "replace")
    except (OSError, KeyError, zipfile.BadZipFile):
        return None, None
    m = re.search(r"<Pages>(\d+)</Pages>", app)
    return (int(m.group(1)) if m else None), len(re.findall(r'<w:pStyle w:val="Heading1"/>', doc))


def suggest_starts(plans, volumes_dir):
    """3.27.0: where each volume's pages and chapters start when it continues the one before, from the latest draft of
    the volume before in the Volumes folder: [{"volume", "page", "chapter", "why"}]. Pages count the whole draft as Word
    saved it, so check the last page number before making."""
    out, page, chapter = [], 1, 1
    files = []
    if volumes_dir and os.path.isdir(volumes_dir):
        files = [os.path.join(volumes_dir, f) for f in os.listdir(volumes_dir) if f.lower().endswith(".docx") and not f.startswith("~$")]
    for i, p in enumerate(plans):
        why = "starts at 1"
        if i:
            prev = plans[i - 1]["volume"]
            hits = sorted((f for f in files if prev and prev.casefold() in os.path.basename(f).casefold()), key=os.path.getmtime)
            if hits:
                n, ch = draft_counts(hits[-1])
                if n:
                    page += n
                if ch:
                    chapter += ch
                why = f"after {os.path.basename(hits[-1])}: {n or '?'} page(s), {ch} chapter(s)"
            else:
                why = f"no draft of {prev} in the Volumes folder yet: type where it starts"
        out.append({"volume": p["volume"], "page": page, "chapter": chapter, "why": why})
    return out


def with_starts(std, page=None, chapter=None):
    """3.27.0: the standard with the response's pages starting at page (when its pages are not numbered by chapter)
    and its chapters at chapter (when the headings are numbered)."""
    for part in ((std.get("pagination") or {}).get("parts") or []):
        if part.get("key") == "body" and part.get("numbers") and not part["numbers"].get("chapter_level") and page and int(page) > 1:
            part["numbers"]["start_at"] = int(page)
            part["numbers"]["restart"] = "part"
    hn = std.get("heading_numbering") or {}
    if chapter and int(chapter) > 1 and hn.get("levels"):
        hn["levels"][0]["start"] = int(chapter)
    return std


def prepaginate(M):
    """3.32.0: whether Make templates keeps each section's planned pages (a prepaginated setup)."""
    import setupdoc as SD
    return bool(SD.setup_of(M).get("prepaginate"))


def set_prepaginate(M, on):
    import setupdoc as SD
    SD.setup_of(M)["prepaginate"] = bool(on)
    M.pending = True


def make_all(M, folder, config_dir, ws=None, effort_name="", info=None, when=None, context=None, word=None, progress=None,
             starts=None, volumes=None, record=True):
    """For each planned volume: its template (named "<effort> <volume>", next version) and the setup written on it.
    Returns [{"volume", "template", "setup", "version", "validation"}]. 3.32.0: volumes: only these; record False (the
    exact preview) makes the files without recording a template version or an export."""
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
    opts = options(M)                              # 3.33.0: each volume takes its profile's content map below
    P, inh = SD.placed_in(M), SD.inherited_sections(M)
    ctx = PRL.context(config_dir, effort_name, info or {}, rec=None)
    stem = SD._safe(os.path.splitext(os.path.basename(M.path))[0] if getattr(M, "path", "") else M.name)
    tfolder = os.path.join(folder, "Templates")
    out = []
    groups = SD.volume_groups(M)
    planned = {p["volume"]: p for p in plan(M, config_dir, ws, effort_name, info)}
    for vname, entries in groups:
        if volumes is not None and vname not in volumes:
            continue
        say(f"Template for {vname}")
        p = planned[vname]
        std, tname, ver = p["std"], p["template_name"], p["version"]
        st = (starts or {}).get(vname) or {}
        if st:                                         # 3.27.0: this volume continues the one before
            std = with_starts(std, st.get("page"), st.get("chapter"))
        std["_template_name"], std["_template_version"] = tname, ver
        std["name"] = f"{tname} v{ver}"
        std.setdefault("_parts_dir", os.path.join(config_dir, "production_parts"))
        job = PT.make(std, tfolder, "", word=word, parts_dir=std["_parts_dir"])
        if record:
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
        opts = options(M, std)
        sids = style_ids(opts)
        rb = SD.review_bins(ws.root) if ws is not None else None          # 3.29.0: topics, objectives, key points
        extras = element_extras(config_dir, info, ws.root if ws is not None else None)
        extras["matrix_rows"] = SD.matrix_rows(M, entries, P, inh)       # the whole volume, for the front matter's matrix
        extras["prepaginate"] = prepaginate(M)                          # 3.32.0: each section's planned pages kept
        extras["skip_kinds"] = skip_kinds(opts)                          # 3.33.0: kinds the content map leaves out
        front_e = [o for o in main_e if SP.part_of(o) in ("cover", "title", "front")]   # 3.30.1: the structure's front matter
        df = None
        if any(o.get("kind") for o in front_e):          # elements in front matter take the template's fixed TOC block's place
            df = SD._doc_for(M, vname, front_e, P, inh, stamp, context, None, styles=sids, bins=rb, std=std, extras=extras)
            main_e = [o for o in main_e if o not in front_e]
        dm = SD._doc_for(M, vname, main_e, P, inh, stamp, context, rules, styles=sids, bins=rb, std=std, extras=extras)
        da = SD._doc_for(M, vname, app_e, P, inh, stamp, context, rules, styles=sids, bins=rb, std=std, extras=extras,
                         appendix=True) if app_e else None
        fills = {FI.styles(std)[k]: FI.value(std, k) for k in FI.styles(std) if FI.value(std, k)}
        part = "" if len(groups) == 1 else "_" + SD._safe(vname)
        path = os.path.join(folder, f"{stem}_Response_Setup{part}_{tag}.docx")
        write(job.copy, path, dm, da, opts, fills, {"StationkeeperMatrix": M.name or "", "StationkeeperSetupExported": stamp,
                                                    "StationkeeperSetupPart": vname, "SK Template": tname, "SK Template Version": str(ver)},
              front_doc=df)
        out.append({"volume": vname, "template": job.copy, "setup": path, "version": ver, "validation": getattr(job, "validation", None),
                    "template_name": tname})
    if not record:
        return out
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
