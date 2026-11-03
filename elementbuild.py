"""What Make templates builds for the Structure Builder (3.30.1): each response element as Word content, divider and
placeholder pages, unnumbered headings, Word sections of their own (portrait or landscape), the library items placed in a
section, and the appendices on heading styles of their own.

  toc            a TOC Heading and a TOC field from the standard's TOC design, the appendix headings in it too
  list_figure    a caption list (TOC \\c "Figure"); list_table the same for tables
  list_appendix  a list of the appendix headings (TOC \\t "Appendix Heading 1,1")
  acronyms       a two-column table: the effort's approved acronyms and their definitions, in order
  units          a units table, header and rows to fill
  matrix         a cross-reference table: each requirement of the volume, its RFP reference and our section
  quickpart      the Quick Part, as an AUTOTEXT field (Word fills it from the template's gallery when fields update)
  divider        a page with its title only; placeholder: its heading and the pages planned for it

Word sections: a marker paragraph where one starts and where it ends; on the template the markers become section breaks
with the template's own page setup (turned for landscape). Fields show "update" text until Word updates them (F9, or
Make templates when Word is on this PC). Rules only; nothing leaves the PC."""
from xml.sax.saxutils import escape

APPENDIX_STYLES = [(f"AppendixHeading{k}", f"Appendix Heading {k}") for k in range(1, 10)]
MARK_STYLE = "SKSectionMark"


def _t(text):
    return f'<w:r><w:t xml:space="preserve">{escape(str(text))}</w:t></w:r>'


def _p(text="", style=None, runs=None, ppr="", bold=False, center=False):
    st = f'<w:pStyle w:val="{style}"/>' if style else ""
    jc = '<w:jc w:val="center"/>' if center else ""
    pp = f"<w:pPr>{st}{ppr}{jc}</w:pPr>" if (st or ppr or jc) else ""
    body = runs if runs is not None else (f'<w:r>{"<w:rPr><w:b/></w:rPr>" if bold else ""}<w:t xml:space="preserve">'
                                          f'{escape(str(text))}</w:t></w:r>' if text else "")
    return f"<w:p>{pp}{body}</w:p>"


def field(instr, shown):
    """A field with its instruction and the text it shows until Word updates it."""
    return (f'<w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r><w:r><w:instrText xml:space="preserve"> {escape(instr)} '
            f'</w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>{_t(shown)}<w:r><w:fldChar w:fldCharType="end"/></w:r>')


def page_break():
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def section_mark(kind, orient):
    """kind: "start" (the section before ends here) or "end" (this section ends here, turned as orient)."""
    return f'<w:p><w:pPr><w:pStyle w:val="{MARK_STYLE}"/></w:pPr>{_t(f"{kind}:{orient}")}</w:p>'


def unnumbered_heading(text, level):
    """A heading with its outline level and the numbering turned off (numId 0): in the TOC, no number."""
    lvl = max(1, min(int(level), 9))
    return f'<w:p><w:pPr><w:pStyle w:val="Heading{lvl}"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr></w:pPr>{_t(text)}</w:p>'


def appendix_heading(text, level):
    lvl = max(1, min(int(level), 9))
    return f'<w:p><w:pPr><w:pStyle w:val="AppendixHeading{lvl}"/></w:pPr>{_t(text)}</w:p>'


def toc_instr(std):
    """The standard's TOC (its styles and switches), with the appendix headings in it."""
    toc = (std or {}).get("toc") or {}
    levels = list(toc.get("levels") or [("Heading 1", 1), ("Heading 2", 2), ("Heading 3", 3)])
    have = {str(s).casefold() for s, _n in levels}
    deep = max([int(n) for _s, n in levels] or [3])
    for k in range(1, min(deep, 9) + 1):
        if f"appendix heading {k}" not in have:
            levels.append((f"Appendix Heading {k}", k))
    sw = " ".join(toc.get("switches") or ["\\h", "\\z"])
    return 'TOC \\t "' + ",".join(f"{s},{n}" for s, n in levels) + '" ' + sw


def caption_ident(std, label):
    for lst in ((std or {}).get("toc") or {}).get("lists", []) or []:
        ids = lst.get("identifiers") or []
        if any(str(i).casefold() == label.casefold() for i in ids):
            return ids[0], lst.get("title") or f"List of {label}s"
    return label, f"List of {label}s"


def table(headers, rows, widths=None, style=None):
    widths = widths or [9360 // max(1, len(headers))] * len(headers)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    st = f'<w:tblStyle w:val="{style}"/>' if style else ""
    borders = "" if style else ('<w:tblBorders>' + "".join(f'<w:{b} w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
                                                           for b in ("top", "left", "bottom", "right", "insideH", "insideV")) + '</w:tblBorders>')

    def tc(text, w, head=False):
        sh = '<w:shd w:val="clear" w:color="auto" w:fill="D9E2F3"/>' if head and not style else ""
        return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{sh}</w:tcPr><w:p>'
                f'{"<w:pPr><w:keepNext/></w:pPr>" if head else ""}<w:r>{"<w:rPr><w:b/></w:rPr>" if head else ""}'
                f'<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r></w:p></w:tc>')
    trs = '<w:tr><w:trPr><w:tblHeader/></w:trPr>' + "".join(tc(h, w, True) for h, w in zip(headers, widths)) + "</w:tr>"
    for r in rows:
        trs += "<w:tr>" + "".join(tc(c, w) for c, w in zip(r, widths)) + "</w:tr>"
    return (f'<w:tbl><w:tblPr>{st}<w:tblW w:w="{sum(widths)}" w:type="dxa"/>{borders}<w:tblLook w:val="04A0" w:firstRow="1"/>'
            f'</w:tblPr><w:tblGrid>{grid}</w:tblGrid>{trs}</w:tbl>')


def element_xml(o, ctx):
    """The Word content for an element section o. ctx: {"std", "acronyms": [(term, definition)], "matrix_rows":
    [(id, reference, section)], "pages": planned pages, "data": the response elements}. Returns XML."""
    import responseelements as RE
    e = RE.get(ctx.get("data") or RE.builtins(), o.get("element") or "") or {}
    src = e.get("source") or "placeholder"
    title = o.get("title") or e.get("name") or ""
    std = ctx.get("std") or {}
    out = []
    if src == "toc":
        out.append(_p(title, "TOCHeading"))
        out.append(_p(runs=field(toc_instr(std), "Update the table of contents in Word (F9).")))
    elif src in ("list_figure", "list_table"):
        ident, _t_ = caption_ident(std, "Figure" if src == "list_figure" else "Table")
        out.append(_p(title, "TOCHeading"))
        out.append(_p(runs=field(f'TOC \\h \\z \\c "{ident}"', "Update the list in Word (F9).")))
    elif src == "list_appendix":
        out.append(_p(title, "TOCHeading"))
        out.append(_p(runs=field('TOC \\h \\z \\t "Appendix Heading 1,1"', "Update the list of appendices in Word (F9).")))
    elif src == "acronyms":
        out.append(_p(title, "TOCHeading"))
        rows = ctx.get("acronyms") or []
        out.append(table(["Acronym", "Definition"], rows or [("", "")], [2000, 7360]))
        out.append(_p(""))
    elif src == "units":
        out.append(_p(title, "TOCHeading"))
        rows = ctx.get("units") or [("", "", "")] * 3
        out.append(table(["Unit", "Meaning", "System"], rows, [1800, 5560, 2000]))
        out.append(_p(""))
    elif src == "matrix":
        out.append(_p(title, "TOCHeading"))
        out.append(table(["Requirement", "RFP reference", "Where we answer it"], ctx.get("matrix_rows") or [("", "", "")], [1800, 3200, 4360]))
        out.append(_p(""))
    elif src == "quickpart":
        out.append(_p(title, "TOCHeading"))
        out.append(quickpart_xml(e.get("lib") or title))
    elif src == "divider":
        out.append(divider_xml(title))
    elif src in ("cover", "backer"):
        return ""                                    # the template's own cover and back cover hold these
    else:                                            # a placeholder element (Title page, Executive Summary)
        out.append(placeholder_xml(title, 1, ctx.get("pages") or e.get("pages") or 1))
    return "".join(out)


def quickpart_xml(name):
    return _p(runs=field(f'AUTOTEXT "{name}"', f"[Quick Part: {name}. Update fields (F9), or Insert > Quick Parts.]"))


def divider_xml(title):
    return page_break() + _p(title, ppr='<w:spacing w:before="4000" w:after="0"/><w:outlineLvl w:val="0"/>', bold=True, center=True) + page_break()


def placeholder_xml(title, level, pages):
    pages = max(1, int(pages or 1))
    out = [unnumbered_heading(title, level),
           _p(f"[Placeholder: {pages} page{'s' if pages != 1 else ''} for authors to fill.]")]
    out += [page_break() for _ in range(pages - 1)]
    return "".join(out)


def lib_xml(x):
    """A library item placed in a section."""
    k = x.get("kind")
    name = x.get("name", "")
    if k == "quickpart":
        return quickpart_xml(name)
    if k in ("table_style", "table_look"):
        import re
        sid = re.sub(r"[^A-Za-z0-9]", "", name) or None
        return table(["Heading", "Heading", "Heading"], [("", "", ""), ("", "", "")], [3120, 3120, 3120],
                     style=sid if k == "table_style" else None) + _p(f"[Table: {name}]")
    return _p(f"[Library: {name}]")


# ------------------------------------------------------------------ on the template (setuptemplate.write uses these)
def ensure_appendix_styles(sroot):
    """The Appendix Heading 1 to 9 styles, each like Heading n (its outline level, so the TOC finds them), without the
    heading numbering (an appendix carries its letter in its text). Added only where missing."""
    import copy
    from lxml import etree
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    q = lambda t: f"{{{W}}}{t}"
    ids = {s.get(q("styleId")): s for s in sroot.findall(q("style"))}
    n = 0
    for k, (sid, name) in enumerate(APPENDIX_STYLES, 1):
        if sid in ids:
            continue
        base = ids.get(f"Heading{k}")
        if base is not None:
            s = copy.deepcopy(base)
            s.set(q("styleId"), sid)
            s.set(q("customStyle"), "1")
            nm = s.find(q("name"))
            if nm is not None:
                nm.set(q("val"), name)
            ppr = s.find(q("pPr"))
            if ppr is not None:
                for np in ppr.findall(q("numPr")):
                    ppr.remove(np)
            for tag in ("link", "aliases"):
                for el in s.findall(q(tag)):
                    s.remove(el)
        else:
            s = etree.fromstring(f'<w:style xmlns:w="{W}" w:type="paragraph" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{name}"/>'
                                 f'<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/>'
                                 f'<w:outlineLvl w:val="{k - 1}"/></w:pPr><w:rPr><w:b/></w:rPr></w:style>')
        sroot.append(s); n += 1
    if MARK_STYLE not in ids:
        sroot.append(etree.fromstring(f'<w:style xmlns:w="{W}" w:type="paragraph" w:customStyle="1" w:styleId="{MARK_STYLE}">'
                                      f'<w:name w:val="SK Section Mark"/><w:basedOn w:val="Normal"/><w:semiHidden/></w:style>'))
    return n


def apply_section_marks(body, final_sect):
    """Each marker paragraph becomes a section break: its sectPr copies the section it sits in (its header, footer,
    margins), turned for landscape when the marker says so. Returns how many breaks were made."""
    import copy
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    q = lambda t: f"{{{W}}}{t}"
    n = 0
    kids = list(body)
    for i, p in enumerate(kids):
        if p.tag != q("p"):
            continue
        ps = p.find(f"{q('pPr')}/{q('pStyle')}")
        if ps is None or ps.get(q("val")) != MARK_STYLE:
            continue
        text = "".join(t.text or "" for t in p.iter(q("t")))
        kind, _c, orient = text.partition(":")
        after = next((k.find(f"{q('pPr')}/{q('sectPr')}") for k in kids[i + 1:] if k.tag == q("p") and
                      k.find(f"{q('pPr')}/{q('sectPr')}") is not None), None)
        base = after if after is not None else final_sect
        if base is None:
            continue
        sp = copy.deepcopy(base)
        _turn(sp, orient if kind == "end" else "portrait", q)
        for r in list(p):
            p.remove(r)
        ppr = p.makeelement(q("pPr"), {})
        ppr.append(sp)
        p.append(ppr)
        n += 1
    return n


def _turn(sp, orient, q):
    sz = sp.find(q("pgSz"))
    if sz is None:
        return
    w, h = sz.get(q("w")), sz.get(q("h"))
    if not (w and h):
        return
    wide = int(w) > int(h)
    if (orient == "landscape") != wide:
        sz.set(q("w"), h); sz.set(q("h"), w)
    if orient == "landscape":
        sz.set(q("orient"), "landscape")
    elif q("orient") in sz.attrib:
        del sz.attrib[q("orient")]
    mar = sp.find(q("pgMar"))
    if mar is not None and (orient == "landscape") != wide:
        t, r, b, l = (mar.get(q(k)) for k in ("top", "right", "bottom", "left"))
        if all(v is not None for v in (t, r, b, l)):
            mar.set(q("top"), l); mar.set(q("right"), t); mar.set(q("bottom"), r); mar.set(q("left"), b)
