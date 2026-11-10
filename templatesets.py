"""Make templates picks sets (3.97.0; canvas "Libraries and Sets", boards 3, 6 and 9; claude/stationkeeper-libraries-and-
sets.md). A template takes what goes in from the libraries, never edits it:

    style sets, in order (where two sets hold a style, the lower one wins), each style as Word wrote it;
    the Setup style set (its styles hidden in the document);
    a part set for the Quick Parts gallery;
    what the document starts with: pages in order (a cover, a marking page, a title page, contents, acronyms...), each in
    its own Word section before the body, and each also in the Quick Parts gallery unless its switch is off.

The choice is kept with the profile ("sets"); an effort's own changes can override it as any other value. The checks
before it is made say what is missing. Rules only (No AI); nothing leaves the PC."""
import copy
import os

KEY = "sets"
SLOT_KINDS = (("cover", "Cover"), ("cui", "Marking page"), ("title", "Title page"), ("toc", "Table of contents"),
              ("acronyms", "Acronyms table"), ("units", "Units and symbols"))
GALLERY = {"cover": "coverPg", "cui": "coverPg", "title": "coverPg", "toc": "tocs", "acronyms": "docParts", "units": "docParts"}
CATEGORY = {"cover": "01 Covers", "cui": "02 Marking pages", "title": "03 Title pages", "toc": "04 Front matter",
            "acronyms": "04 Front matter", "units": "04 Front matter"}


def recipe(std):
    r = (std or {}).get(KEY) or {}
    return {"style_sets": [x for x in (r.get("style_sets") or []) if x], "setup_set": r.get("setup_set") or "",
            "part_set": r.get("part_set") or "",
            "starts": [dict(kind=s.get("kind", ""), part=s.get("part", ""), gallery=bool(s.get("gallery", True)))
                       for s in (r.get("starts") or []) if s.get("part")]}


def set_recipe(std, **kw):
    """Change what goes in: style_sets, setup_set, part_set, starts. Returns the recipe."""
    r = recipe(std)
    r.update({k: v for k, v in kw.items() if k in r})
    std[KEY] = r
    return r


def used(std):
    r = recipe(std)
    return bool(r["style_sets"] or r["setup_set"] or r["part_set"] or r["starts"])


def _n(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def config_of(std):
    p = (std or {}).get("_parts_dir") or ""
    return os.path.dirname(p) if p else ""


# ------------------------------------------------------------------ styles
def styles(lib, rec):
    """({name: item}, wins: [(name, from set, over set)]). Sets in order; the lower one wins where two hold a style."""
    import stylelib as SL
    out, src, wins = {}, {}, []
    for sid in rec["style_sets"]:
        k = SL.get_set(lib, sid)
        if k is None:
            continue
        for iid in k["items"]:
            it = lib.get(iid)
            if it is None:
                continue
            name = lib.base_of(it)
            if name in out and out[name]["id"] != it["id"]:
                wins.append((name, k["name"], src[name]))
            out[name], src[name] = it, k["name"]
    return out, wins


def setup_styles(lib, rec):
    import stylelib as SL
    k = SL.get_set(lib, rec["setup_set"]) if rec["setup_set"] else None
    return {lib.base_of(it): it for it in (lib.get(i) for i in (k or {}).get("items", [])) if it is not None}


# ------------------------------------------------------------------ parts
def quick_parts(lib, config_dir, rec):
    """The part set's Quick Parts as the template's gallery entries (each from its kept source)."""
    import stylelib as SL
    k = SL.get_set(lib, rec["part_set"]) if rec["part_set"] else None
    out = []
    for pid in (k or {}).get("items", []):
        if not pid.startswith("q:"):
            continue
        it = lib.get(pid[2:])
        if it is None:
            continue
        v = lib.values(it) or {}
        src = v.get("source") or ""
        out.append({"name": v.get("entry") or lib.base_of(it), "category": v.get("category") or "",
                    "gallery": v.get("gallery") or "", "source": lib.source_path(src) if src else "", "id": it["id"]})
    return out


def part_pages(config_dir, lib, rec):
    """The part set's pages (covers, CUI pages...), offered for the starting slots: [(id, name, kind)]."""
    import partlib as PT
    import sectiondesigns as SDZ
    import stylelib as SL
    k = SL.get_set(lib, rec["part_set"]) if rec["part_set"] else None
    out = []
    for pid in (k or {}).get("items", []):
        if pid.startswith("d:"):
            x = SDZ.get(config_dir, pid[2:])
            if x:
                out.append((x["id"], PT.shown_name(config_dir, x), x["shelf"]))
    return out


def start_files(config_dir, rec):
    """[(slot kind, path of the page's Word file, also in the gallery, name)] for the starting pages that exist."""
    import partlib as PT
    import sectiondesigns as SDZ
    out = []
    for s in rec["starts"]:
        x = SDZ.get(config_dir, s["part"])
        if x is None:
            continue
        p = SDZ.path_of(config_dir, x)
        if os.path.isfile(p):
            out.append((s["kind"] or x["shelf"], p, s["gallery"], PT.shown_name(config_dir, x)))
    return out


# ------------------------------------------------------------------ the standard the template is made from
def apply(std, lib=None, config_dir=None):
    """The standard with what the sets hold: style_defs from the style sets (and the Setup set, hidden), the part set's
    Quick Parts added to the gallery, and "_exact_styles" ({name: Word's own definition}) and "_starts" for the maker.
    A standard with no sets comes back unchanged."""
    if not used(std):
        return std
    config_dir = config_dir or config_of(std)
    import templatelib as TL
    lib = lib or TL.Library(config_dir)
    rec = recipe(std)
    std = copy.deepcopy(std)
    defs = std.setdefault("style_defs", {})
    exact = {}
    chosen, _wins = styles(lib, rec)
    for name, it in chosen.items():
        v = dict(lib.values(it) or {})
        xml = v.pop("_xml", "")
        v = {k: x for k, x in v.items() if not str(k).startswith("_")}
        defs[name] = v
        if xml:
            exact[name] = xml
    for name, it in setup_styles(lib, rec).items():
        v = dict(lib.values(it) or {})
        xml = v.pop("_xml", "")
        v = {k: x for k, x in v.items() if not str(k).startswith("_")}
        v["hidden"] = True
        v.setdefault("used_on", "Setup")
        defs[name] = v
        if xml:
            exact[name] = _hidden_xml(xml)
    std["_exact_styles"] = exact
    qp = std.setdefault("quick_parts", {})
    have = {e.get("name") for e in qp.get("entries") or []}
    qp["entries"] = list(qp.get("entries") or []) + [e for e in quick_parts(lib, config_dir, rec) if e["name"] not in have]
    std["_starts"] = start_files(config_dir, rec)
    if std["_starts"]:                      # the starting pages are the template's own: no Stationkeeper cover or title page
        std["page_parts"] = {k: v for k, v in (std.get("page_parts") or {}).items() if k not in ("cover", "title")}
    return std


def _hidden_xml(xml):
    """Word's definition of a style with hidden text (w:vanish in its run properties)."""
    if "<w:vanish" in xml:
        return xml
    if "<w:rPr>" in xml:
        return xml.replace("<w:rPr>", "<w:rPr><w:vanish/>", 1)
    if "<w:rPr/>" in xml:
        return xml.replace("<w:rPr/>", "<w:rPr><w:vanish/></w:rPr>", 1)
    return xml.replace("</w:style>", "<w:rPr><w:vanish/></w:rPr></w:style>", 1)


# ------------------------------------------------------------------ into the made template
def put_exact_styles(path, exact):
    """Each chosen style as Word wrote it: the template's own definition of that style is replaced (its style id kept,
    so every paragraph that uses it follows). Returns the names put in."""
    import re
    import zipfile
    from lxml import etree
    if not exact or not os.path.isfile(path):
        return []
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    q = lambda t: "{%s}%s" % (W, t)
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)
    root = etree.fromstring(data["word/styles.xml"], parser)
    by_name = {}
    for s in root.findall(q("style")):
        n = s.find(q("name"))
        if n is not None:
            by_name[(n.get(q("val")) or "").casefold()] = s
    ids = {s.get(q("styleId")) for s in root.findall(q("style"))}
    done = []
    for name, xml in exact.items():
        try:
            if "xmlns:w=" not in xml:
                xml = re.sub(r"^<w:style\b", f'<w:style xmlns:w="{W}"', xml.strip(), count=1)
            new = etree.fromstring(xml.encode("utf-8"), parser)
        except etree.XMLSyntaxError:
            continue
        old = by_name.get(name.casefold())
        if old is None:
            old = by_name.get(_word_name(name).casefold())
        if old is not None:
            new.set(q("styleId"), old.get(q("styleId")))
            root.replace(old, new)
        else:
            sid = new.get(q("styleId")) or re.sub(r"[^A-Za-z0-9]", "", name)
            while sid in ids:
                sid += "1"
            new.set(q("styleId"), sid); ids.add(sid)
            root.append(new)
        done.append(name)
    data["word/styles.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    tmp = path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, data[n])
    os.replace(tmp, path)
    return done


def _word_name(name):
    return {"Heading 1": "heading 1", "Heading 2": "heading 2", "Heading 3": "heading 3", "Caption": "caption",
            "TOC 1": "toc 1", "TOC 2": "toc 2", "TOC 3": "toc 3"}.get(name, name)


def place_starts(path, starts):
    """The starting pages before the body, in order, each in its own Word section. Returns the kinds placed."""
    import designplace as DP
    items = [(kind, p) for kind, p, _g, _n in starts]
    return DP.place_in_order(path, items)


def starts_gallery(starts, folder):
    """The starting pages whose switch is on, as Quick Parts (one Word file holding them, kept by content):
    [{"name", "category", "gallery", "source", "made_here"}]."""
    import qpmake as QM
    entries = []
    for kind, p, gal, name in starts:
        if not gal:
            continue
        body, media = page_body(p)
        entries.append({"name": name, "category": CATEGORY.get(kind, "04 Front matter"), "gallery": GALLERY.get(kind, "docParts"),
                        "xml": body, "media": media})
    if not entries:
        return []
    src = QM.make_source(folder, entries, "starting pages")
    return [{"name": e["name"], "category": e["category"], "gallery": e["gallery"], "source": src, "made_here": True} for e in entries]


def page_body(path):
    """A page's body as Quick Part content: its paragraphs and tables (the last section's properties apart), with the
    pictures it shows."""
    import base64
    import posixpath
    import re
    import zipfile
    with zipfile.ZipFile(path) as z:
        doc = z.read("word/document.xml").decode("utf-8")
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8") if "word/_rels/document.xml.rels" in z.namelist() else ""
        m = re.search(r"<w:body>(.*)</w:body>", doc, re.S)
        body = m.group(1) if m else ""
        body = re.sub(r"<w:sectPr\b.*?</w:sectPr>\s*$", "", body.strip(), flags=re.S)
        body = re.sub(r"<w:sectPr\b[^>]*/>\s*$", "", body)
        media = []
        for rid, target in re.findall(r'<Relationship[^>]*Id="([^"]+)"[^>]*Type="[^"]*/image"[^>]*Target="([^"]+)"', rels):
            if f'"{rid}"' not in body:
                continue
            part = posixpath.normpath(posixpath.join("word", target))
            if part in z.namelist():
                ext = part.rsplit(".", 1)[-1].lower()
                media.append({"rid": rid, "name": posixpath.basename(part), "b64": base64.b64encode(z.read(part)).decode("ascii"),
                              "ct": {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "emf": "image/x-emf"}.get(ext, f"image/{ext}")})
    if "xmlns:w=" not in body and body:
        pass                                   # the glossary document declares w: and r:
    return body, media


# ------------------------------------------------------------------ before it is made
def checks(std, lib=None, config_dir=None, fonts=None):
    """[(state "ok" or "warn", what, more)] for the chosen sets and starting pages."""
    config_dir = config_dir or config_of(std)
    import templatelib as TL
    lib = lib or TL.Library(config_dir)
    rec = recipe(std)
    out = []
    chosen, wins = styles(lib, rec)
    setup = setup_styles(lib, rec)
    if rec["style_sets"]:
        exact = sum(1 for it in list(chosen.values()) + list(setup.values()) if (lib.values(it) or {}).get("_xml"))
        n = len(chosen) + len(setup)
        out.append(("ok", f"{_n(n, 'style')}, {exact} as Word wrote {'it' if exact == 1 else 'them'}",
                    f"{len(chosen)} from the style sets" + (f", {len(wins)} replaced by a lower set" if wins else "")
                    + (f", {len(setup)} Setup styles hidden" if setup else "")))
        names = set(chosen) | set(setup) | set((std.get("style_defs") or {}).keys())
        missing = sorted({b for it in list(chosen.values()) + list(setup.values())
                          for b in [(lib.values(it) or {}).get("based_on")] if b and b not in names and b not in ("Normal", "Default Paragraph Font")})
        out.append(("warn" if missing else "ok", "Every style they rest on is there" if not missing else
                    f"{len(missing)} style(s) they rest on are not in these sets", ", ".join(missing[:6]) or "Based on, next and linked styles"))
    qps = quick_parts(lib, config_dir, rec)
    if rec["part_set"]:
        gone = [e["name"] for e in qps if not (e["source"] and os.path.isfile(e["source"]))]
        out.append(("warn" if gone else "ok", f"{_n(len(qps), 'Quick Part')} from the part set" + (" open and are whole" if not gone else ""),
                    ("Their kept file is missing: " + ", ".join(gone[:5])) if gone else "Pictures, fields and sections included"))
    starts = start_files(config_dir, rec)
    if rec["starts"]:
        lost = len(rec["starts"]) - len(starts)
        out.append(("warn" if lost else "ok", "Every starting page opens and is whole" if not lost else f"{lost} starting page(s) are gone from Parts",
                    ", ".join(n for _k, _p, _g, n in starts[:6])))
        kinds = [k for k, _p, _g, _n in starts]
        if "cui" in kinds:
            out.append(("ok", "A marking page is in the starting pages", "Use CUI headers and footers in Layout for the body"))
    if fonts is not None:
        want = sorted({(lib.values(it) or {}).get("font") for it in list(chosen.values()) + list(setup.values())} - {None, ""})
        lacking = [f for f in want if f not in fonts]
        out.append(("warn" if lacking else "ok", "Fonts installed on this PC" if not lacking else "Fonts not on this PC",
                    ", ".join(lacking or want[:6])))
    return out
