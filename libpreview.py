"""Previews of library items (3.50.0): Word's own picture where Word can draw the item, the app's sketch otherwise.

Word draws, on this PC and only when a person presses Draw with Word (never by itself):
  covers, title pages and back covers   the kept page itself (wordpreview)
  Quick Parts                           inserted by Word from their kept source, saved as a page (qpmeasure, which
                                        counts their pages in the same pass)
  styles, table styles, headers and footers, header and footer designs, heading numbering, lists, the TOC
                                        a specimen page: a template made from the global standard with the item in
                                        it, its body replaced by sample paragraphs that use the item (specimen())
Everything else (theme, font sets, page setups, pagination, table looks, captions, sections) is drawn by the app.

Pictures are kept in the library's previews folder by the item's content fingerprint, so a picture is drawn once and
shown until the item changes. Offline: Word on this PC, no network."""
import hashlib, os, re, shutil, tempfile, zipfile

import templatelib as TL

VERSION = 1                                             # a new specimen layout draws every picture again
FOLDER = "previews"
WORD_KINDS = ("cover", "backer", "title", "quickpart", "style", "table_style", "hf", "hf_design", "heading_numbering",
              "list_numbering", "toc")
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_DOC_CT = ("application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml",
           "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml")
SAMPLE = ("Our approach meets every requirement of the statement of work. The team has delivered this kind of system "
          "before, on schedule, and the plan below shows how each risk is retired.")


def key(item):
    return f"{item.get('hash') or item['id']}_{VERSION}"


def folder(lib):
    return os.path.join(lib.root, FOLDER)


def cached(lib, item):
    """The picture Word drew for this item as it is now, or ''."""
    if item is None:
        return ""
    p = os.path.join(folder(lib), key(item) + ".png")
    return p if os.path.isfile(p) else ""


def word_can(item):
    return item is not None and item.get("kind") in WORD_KINDS


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _p(text, style=None, runs=None):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    body = runs if runs is not None else f'<w:r><w:t xml:space="preserve">{_esc(text)}</w:t></w:r>'
    return f"<w:p>{ppr}{body}</w:p>"


def style_ids(styles_xml):
    """{style name: style id} of a styles part."""
    out = {}
    for m in re.finditer(r'<w:style\b[^>]*w:styleId="([^"]+)"[^>]*>(.*?)</w:style>', styles_xml, re.S):
        n = re.search(r'<w:name w:val="([^"]+)"', m.group(2))
        if n:
            out[n.group(1)] = m.group(1)
    return out


def body_for(item, values, ids):
    """The specimen paragraphs for an item (WordprocessingML body content), or None when Word has nothing to show."""
    k, name = item["kind"], item.get("base_name") or re.sub(r" \(\d+\)$", "", item["name"])
    sid = ids.get(name, re.sub(r"[^A-Za-z0-9]", "", name))
    if k == "style":
        if values.get("type") == "character":
            return _p("", runs=('<w:r><w:t xml:space="preserve">Body text with </w:t></w:r>'
                                f'<w:r><w:rPr><w:rStyle w:val="{sid}"/></w:rPr><w:t xml:space="preserve">{_esc(name)} in this style</w:t></w:r>'
                                '<w:r><w:t xml:space="preserve"> and more body text after it.</w:t></w:r>'))
        if values.get("type") == "table":
            return _table(sid)
        head = name.lower().startswith(("heading", "title", "toc heading"))
        first = f"{name}: Technical approach" if head else f"{name}. {SAMPLE}"
        return _p(first, sid) + _p(f"{name}, a second paragraph. {SAMPLE}" if not head else SAMPLE, sid if not head else None)
    if k == "table_style":
        return _p(f"{name}:") + _table(sid)
    if k in ("hf", "hf_design"):
        return "".join(_p(SAMPLE) for _i in range(3))
    if k == "heading_numbering":
        return "".join(_p(f"Heading {n} sample", ids.get(f"heading {n}", ids.get(f"Heading {n}", f"Heading{n}"))) + _p(SAMPLE)
                       for n in (1, 2, 3))
    if k == "list_numbering":
        out = [_p(f"{name}:")]
        for lv in (values.get("levels") or [])[:4]:
            st = lv.get("style")
            if st:
                out.append(_p(f"{st}: an item at this level", ids.get(st, re.sub(r'[^A-Za-z0-9]', '', st))))
        return "".join(out) if len(out) > 1 else None
    if k == "toc":
        fld = ('<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> TOC '
               + _esc(" ".join(values.get("switches") or ["\\o \"1-3\" \\h \\z \\u"])) +
               ' </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>Contents</w:t></w:r>'
               '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
        heads = "".join(_p(t, ids.get(s, s.replace(" ", ""))) for s, t in (("Heading 1", "1 Technical approach"),
                        ("Heading 2", "1.1 System design"), ("Heading 2", "1.2 Test and verification"), ("Heading 1", "2 Management")))
        return fld + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' + heads
    return None


def _table(sid):
    rows = [("Item", "Approach", "Result"), ("Design", "Reviewed twice", "Approved"), ("Test", "Three campaigns", "Passed"),
            ("Total", "", "On schedule")]
    out = [f'<w:tbl><w:tblPr><w:tblStyle w:val="{sid}"/><w:tblW w:w="5000" w:type="pct"/>'
           '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="1" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>'
           '<w:tblGrid><w:gridCol w:w="3000"/><w:gridCol w:w="3000"/><w:gridCol w:w="3000"/></w:tblGrid>']
    for r in rows:
        out.append("<w:tr>" + "".join(f'<w:tc><w:tcPr><w:tcW w:w="3000" w:type="dxa"/></w:tcPr>{_p(c)}</w:tc>' for c in r) + "</w:tr>")
    out.append("</w:tbl>")
    return "".join(out) + _p("")


def _with_item(lib, item, values):
    """A global standard (the starting one) with the item in it; headers and footers on every part."""
    import prodrules as PRL
    cfg = tempfile.mkdtemp(prefix="sk_spec_")
    std = PRL.for_effort(cfg)
    k, name = item["kind"], lib.base_of(item)
    if k == "hf":
        for part in list((std.get("hf_layouts") or {}).keys()) or ["body"]:
            TL.use_values(cfg, k, part, values, std)
    elif k == "hf_design":
        for part in list((std.get("hf_layouts") or {}).keys()) or ["body"]:
            TL.use_values(cfg, k, name, values, std, category=part)
    else:
        TL.use_values(cfg, k, name, values, std, file_path=lib.source_path)
    return std, cfg


def specimen(lib, item):
    """A Word document (bytes) that shows the item on its first page, or None (Word has nothing better than the
    sketch, or the item's page is not on this PC). Covers and back covers are their kept page."""
    values = lib.values(item) or {}
    k = item["kind"]
    if k in ("cover", "backer", "title"):
        p = lib.source_path(values.get("file") or "")
        return open(p, "rb").read() if values.get("file") and os.path.isfile(p) else None
    if k not in WORD_KINDS or k == "quickpart":
        return None
    import prodtemplate as PT
    std, cfg = _with_item(lib, item, values)
    out = tempfile.mkdtemp(prefix="sk_spec_out_")
    try:
        job = PT.make(std, out, "")
        with open(job.copy, "rb") as f:
            data = f.read()
    finally:
        shutil.rmtree(out, ignore_errors=True)
        shutil.rmtree(cfg, ignore_errors=True)
    return as_specimen(data, item, values)


def as_specimen(data, item, values):
    """The template as a document whose body is the item's specimen, the last section keeping the headers and footers."""
    zin = zipfile.ZipFile(__import__("io").BytesIO(data))
    parts = {n: zin.read(n) for n in zin.namelist()}
    ids = style_ids(parts.get("word/styles.xml", b"").decode("utf-8"))
    ids.update({n.lower(): i for n, i in list(ids.items())})
    body_xml = body_for(item, values, ids)
    if body_xml is None:
        return None
    doc = parts["word/document.xml"].decode("utf-8")
    b0 = doc.index("<w:body>") + len("<w:body>")
    b1 = doc.rindex("</w:body>")
    body = doc[b0:b1]
    sects = re.findall(r"<w:sectPr\b.*?</w:sectPr>", body, re.S)
    final = sects[-1] if sects else '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/></w:sectPr>'
    refs = ""
    for s in reversed(sects):
        r = "".join(re.findall(r"<w:(?:header|footer)Reference\b[^>]*/>", s))
        if r:
            refs = r
            break
    final = re.sub(r"<w:(?:header|footer)Reference\b[^>]*/>", "", final)
    final = re.sub(r"<w:titlePg/>", "", final)
    final = re.sub(r"(<w:sectPr\b[^>]*>)", lambda m: m.group(1) + refs, final, count=1)
    parts["word/document.xml"] = (doc[:b0] + body_xml + final + doc[b1:]).encode("utf-8")
    ct = parts["[Content_Types].xml"].decode("utf-8").replace(*_DOC_CT)
    parts["[Content_Types].xml"] = ct.encode("utf-8")
    buf = __import__("io").BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in parts.items():
            if n.startswith("word/glossary/"):
                continue                                    # Quick Parts are not part of a specimen
            z.writestr(n, b)
    return _drop_glossary_rel(buf.getvalue())


_R = r'<w:r>(?:<w:rPr>(?:(?!</w:r>).)*?</w:rPr>)?'
_FIELD = re.compile(_R + r'<w:fldChar w:fldCharType="begin"/></w:r>' + _R + r'<w:instrText[^>]*>\s*(STYLEREF|DOCPROPERTY)\s+"([^"]+)"[^<]*</w:instrText></w:r>'
                    + _R + r'<w:fldChar w:fldCharType="separate"/></w:r>(.*?)' + _R + r'<w:fldChar w:fldCharType="end"/></w:r>', re.S)


def plain_fields(xml):
    """A header's or footer's style and document-property fields as their names in brackets ([Volume Name]): a
    specimen has no cover to take the volume's values from, and Word would show an error in their place."""
    def one(m):
        name = re.sub(r"^(PE|AA|SK)\s+", "", m.group(2))
        rpr = re.search(r"<w:rPr>.*?</w:rPr>", m.group(3) or "", re.S)
        return f'<w:r>{rpr.group(0) if rpr else ""}<w:t xml:space="preserve">[{_esc(name)}]</w:t></w:r>'
    return _FIELD.sub(one, xml)


def _drop_glossary_rel(data):
    import io
    zin = zipfile.ZipFile(io.BytesIO(data))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n in zin.namelist():
            b = zin.read(n)
            if n == "word/_rels/document.xml.rels":
                b = re.sub(rb'<Relationship\b[^>]*glossaryDocument[^>]*/>', b"", b)
            if n == "[Content_Types].xml":
                b = re.sub(rb'<Override\b[^>]*PartName="/word/glossary/[^"]*"[^>]*/>', b"", b)
            if re.match(r"word/(header|footer)\d+\.xml$", n):
                b = plain_fields(b.decode("utf-8")).encode("utf-8")
            z.writestr(n, b)
    return buf.getvalue()


def keep_png(lib, item, png):
    """Keeps a picture Word drew as this item's picture. Returns its path."""
    os.makedirs(folder(lib), exist_ok=True)
    dst = os.path.join(folder(lib), key(item) + ".png")
    shutil.copyfile(png, dst + ".tmp")
    os.replace(dst + ".tmp", dst)
    return dst


def draw(lib, ids, runner=None, qp_runner=None, timeout=300):
    """Word draws each item among ids (one Word at a time; Quick Parts in one pass that also counts their pages).
    Returns ({item id: picture path or the reason in words}, {Quick Part id: pages}). Never saves the library."""
    import exactpreview as XP
    import qpmeasure as QM
    import wordpreview as WP
    out, pages = {}, {}
    items = [lib.get(i) for i in ids if lib.get(i) is not None]
    qps = [i["id"] for i in items if i["kind"] == "quickpart"]
    if qps:
        pics = {}
        res = QM.measure(lib, qps, runner=qp_runner, keep=False, pictures=pics)
        for iid, v in res.items():
            if isinstance(v, int):
                pages[iid] = v
            if pics.get(iid):
                out[iid] = keep_png(lib, lib.get(iid), pics[iid])
            elif iid not in out:
                out[iid] = v if isinstance(v, str) else "Word measured it but could not draw it."
        for d in {os.path.dirname(x) for x in pics.values()}:
            shutil.rmtree(d, ignore_errors=True)
    for it in items:
        if it["kind"] == "quickpart":
            continue
        if not word_can(it):
            out[it["id"]] = "The app draws this kind of item."
            continue
        if cached(lib, it):
            out[it["id"]] = cached(lib, it)
            continue
        try:
            data = specimen(lib, it)
        except Exception as e:  # noqa: BLE001  a specimen that cannot be made leaves the sketch
            import diag
            diag.swallowed()
            out[it["id"]] = f"The sample page could not be made ({type(e).__name__})."
            continue
        if data is None:
            out[it["id"]] = "Word has nothing to add to the app's picture for this item."
            continue
        work = tempfile.mkdtemp(prefix="sk_draw_")
        try:
            docx, pdf = os.path.join(work, "item.docx"), os.path.join(work, "item.pdf")
            with open(docx, "wb") as f:
                f.write(data)
            r = XP.lay_out(docx, pdf, runner=runner, timeout=timeout)
            if not r.get("ok"):
                out[it["id"]] = r.get("why") or "Word could not draw it."
                continue
            png = os.path.join(work, "item.png")
            if not WP.pdf_to_png(pdf, png):
                out[it["id"]] = "Word's page could not be turned into a picture."
                continue
            out[it["id"]] = keep_png(lib, it, png)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return out, pages


def fingerprint(data):
    return hashlib.sha256(data or b"").hexdigest()[:16]
