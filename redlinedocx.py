"""Word XML for Redline's copy (4.13.0; claude/stationkeeper-pdf-fidelity-plan-4.13.html, step 3): the grid tables and
the page setup, written into a docxw.Doc.

- table(d, grid, room): a Word table from a redlinelayout grid: its columns as wide as on the page (scaled to fit the
  room between the margins when wider), merged cells (gridSpan across, vMerge down), the header row repeated on each page
  (tblHeader), shading, bold where the page had it, borders as the page drew them (all, rules only, or none), each row at
  least as tall as on the page;
- section(g): the break that ends a run of pages with one size (a landscape table page stays landscape);
- final(g): the document's last section.
Rules only (No AI); nothing leaves the PC."""
from docxw import _x

TW = 20                                       # twentieths of a point


def _run(text, bold=False):
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{_x(text)}</w:t></w:r>' if text else ""


def _borders(kind):
    on = {"all": ("top", "left", "bottom", "right", "insideH", "insideV"), "h": ("top", "bottom", "insideH")}.get(kind, ())
    return "<w:tblBorders>" + "".join(
        f'<w:{b} w:val="{"single" if b in on else "nil"}" w:sz="4" w:space="0" w:color="000000"/>'
        for b in ("top", "left", "bottom", "right", "insideH", "insideV")) + "</w:tblBorders>"


def table(d, grid, room=9360):
    """Append the table to d.body. room: twips between the margins."""
    if d.body and d.body[-1].endswith("</w:tbl>"):
        d.body.append("<w:p/>")                       # Word keeps two tables apart with a paragraph
    d.body.append(table_xml(grid, room))


def table_xml(grid, room=9360):
    """The table's XML (a table in a cell is written inside that cell, 4.14.0)."""
    widths = [max(1.0, w) for w in grid["widths"]] or [1.0]
    tw = [int(round(w * TW)) for w in widths]
    if sum(tw) > room:
        tw = [max(144, int(w * room / sum(tw))) for w in tw]
    nc = len(tw)
    rows = grid["rows"]
    # the columns each cell starts at, and the cells a merge down covers in the rows below
    covered = {}                                  # (row, col) -> cs of the merge above
    xml = []
    for ri, row in enumerate(rows):
        cells, col, k = [], 0, 0
        while col < nc:
            if (ri, col) in covered:
                cs = covered[(ri, col)]
                w = sum(tw[col:col + cs])
                span = f'<w:gridSpan w:val="{cs}"/>' if cs > 1 else ""
                cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{span}<w:vMerge/></w:tcPr><w:p/></w:tc>')
                col += cs
                continue
            if k >= len(row):
                cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{tw[col]}" w:type="dxa"/></w:tcPr><w:p/></w:tc>')
                col += 1
                continue
            c = row[k]; k += 1
            cs = max(1, min(int(c.get("cs", 1)), nc - col))
            rs = max(1, int(c.get("rs", 1)))
            w = sum(tw[col:col + cs])
            pr = f'<w:tcW w:w="{w}" w:type="dxa"/>' + (f'<w:gridSpan w:val="{cs}"/>' if cs > 1 else "")
            if rs > 1:
                pr += '<w:vMerge w:val="restart"/>'
                for r2 in range(ri + 1, min(len(rows), ri + rs)):
                    covered[(r2, col)] = cs
            if c.get("fill"):
                pr += f'<w:shd w:val="clear" w:color="auto" w:fill="{_x(c["fill"])}"/>'
            if c.get("rot"):
                pr += '<w:textDirection w:val="btLr"/>'          # 4.14.0: turned text, read bottom to top
            bold = bool(c.get("bold"))
            inner = ""
            if c.get("nested"):                       # a table in the cell, then the paragraph Word ends a cell with
                inner = table_xml(c["nested"], max(720, w - 2 * int(round(grid.get("pad", 5.4) * TW)))) + "<w:p/>"
            own = "".join(f'<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>{_run(t, bold)}</w:p>'
                          for t in (c.get("text") or "").split("\n")) if c.get("text") or not inner else ""   # 4.14.0: each paragraph
            cells.append(f'<w:tc><w:tcPr>{pr}</w:tcPr>{own}{inner}</w:tc>')
            col += cs
        trpr = ""
        if ri < int(grid.get("header") or 0):
            trpr += "<w:tblHeader/>"
        hs = grid.get("heights") or []
        if ri < len(hs) and hs[ri] > 0:
            trpr += f'<w:trHeight w:val="{int(max(1.0, hs[ri] - 0.5) * TW)}" w:hRule="atLeast"/>'   # Word adds the border'
        xml.append("<w:tr>" + (f"<w:trPr>{trpr}</w:trPr>" if trpr else "") + "".join(cells) + "</w:tr>")
    gridx = "".join(f'<w:gridCol w:w="{w}"/>' for w in tw)
    pad = int(round(max(0.0, min(14.0, grid.get("pad", 5.4))) * TW))     # the space before a cell's text, as on the page
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{sum(tw)}" w:type="dxa"/>{_borders(grid.get("borders", "all"))}'
                  f'<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="{pad}" w:type="dxa"/><w:right w:w="{pad}" w:type="dxa"/>'
                  f'</w:tblCellMar></w:tblPr><w:tblGrid>{gridx}</w:tblGrid>' + "".join(xml) + "</w:tbl>")


def _sect(g):
    w, h = int(g["w"] * TW), int(g["h"] * TW)
    t, r, b, l = (int(m * TW) for m in g["margins"])
    orient = ' w:orient="landscape"' if g["landscape"] else ""
    hf = g.get("hf") or {}                          # 4.22.0: the run of pages' own header and footer
    refs = (f'<w:headerReference w:type="default" r:id="{g["hdr"]}"/>' if g.get("hdr") else "") \
        + (f'<w:footerReference w:type="default" r:id="{g["ftr"]}"/>' if g.get("ftr") else "")
    head = int(round(hf["header_at"] * TW)) if hf.get("header_at") is not None else 720
    foot = int(round(hf["footer_at"] * TW)) if hf.get("footer_at") is not None else 720
    num = f'<w:pgNumType w:start="{int(hf["start"])}"/>' if hf.get("start") is not None and hf["start"] >= 0 else ""
    title = "<w:titlePg/>" if hf.get("title_pg") else ""
    return (f'<w:sectPr>{refs}<w:pgSz w:w="{w}" w:h="{h}"{orient}/><w:pgMar w:top="{t}" w:right="{r}" w:bottom="{b}" w:left="{l}" '
            f'w:header="{min(head, max(0, t - 20))}" w:footer="{min(foot, max(0, b - 20))}" w:gutter="0"/>{num}{title}</w:sectPr>')


def section(d, g):
    """End the run of pages g (its size and margins) with a section break."""
    d.body.append(f"<w:p><w:pPr>{_sect(g)}</w:pPr></w:p>")


def final(g):
    return _sect(g)


def room(g):
    """Twips between the margins of g."""
    return int((g["w"] - g["margins"][1] - g["margins"][3]) * TW)


def _ppr(geo, keep_next=False):
    """Paragraph properties from where the paragraph sits: space above, line to line, indents, alignment, a new page."""
    if not geo:
        return ""
    out = "<w:keepNext/>" if keep_next else ""
    if geo.get("break"):
        out += "<w:pageBreakBefore/>"
    line = f' w:line="{int(round(geo["pitch"] * TW))}" w:lineRule="exact"' if geo.get("pitch") else ""
    out += f'<w:spacing w:before="{int(round(geo.get("before", 0) * TW))}" w:after="0"{line}/>'
    left, first = int(round(geo.get("left", 0) * TW)), int(round(geo.get("first", 0) * TW))
    if left or first:
        out += f'<w:ind w:left="{left}"' + (f' w:firstLine="{first}"' if first > 0 else f' w:hanging="{-first}"' if first < 0 else "") + "/>"
    if geo.get("align") in ("center", "right", "both"):
        out += f'<w:jc w:val="{geo["align"]}"/>'
    return out


def _fonts(font):
    f = _x(font)
    return f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}"/>' if font else ""


def rpr(st):
    """Run properties from how the PDF set a paragraph: {"font", "size", "bold", "italic", "color"}; "" for none."""
    if not st:
        return ""
    out = _fonts(st.get("font")) + ("<w:b/>" if st.get("bold") else "") + ("<w:i/>" if st.get("italic") else "") \
        + (f'<w:color w:val="{_x(st["color"])}"/>' if st.get("color") else "") \
        + (f'<w:sz w:val="{int(round(st["size"] * 2))}"/>' if st.get("size") else "")
    return f"<w:rPr>{out}</w:rPr>" if out else ""


def heading(d, text, level, size=None, bold=True, geo=None, color="", font="", italic=False, lead=""):
    """A heading in Word's Heading N style, its run in the font, size, weight and color the PDF set it in, placed as on
    the page. lead: runs that go before its text (a picture behind the page)."""
    level = max(1, min(9, int(level)))
    r = _fonts(font) + ("<w:b/>" if bold else "<w:b w:val=\"0\"/>") + ("<w:i/>" if italic else "") \
        + (f'<w:color w:val="{_x(color)}"/>' if color else "") + (f'<w:sz w:val="{int(round(size * 2))}"/>' if size else "")
    d.body.append(f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/>{_ppr(geo, True)}</w:pPr>{lead}<w:r><w:rPr>{r}</w:rPr>'
                  f'<w:t xml:space="preserve">{_x(text)}</w:t></w:r></w:p>')


def para(d, text, geo, st=None, lead=""):
    d.body.append(f'<w:p><w:pPr>{_ppr(geo)}</w:pPr>{lead}<w:r>{rpr(st)}<w:t xml:space="preserve">{_x(text)}</w:t></w:r></w:p>')


def picture(d, run, geo, lead=""):
    """4.22.0: a picture in the text's flow, in a paragraph of its own: the space above it, its place between the
    margins, a new page where the PDF starts one. The line is as tall as the picture."""
    g = dict(geo or {})
    g["pitch"] = None
    d.body.append(f'<w:p><w:pPr>{_ppr(g)}</w:pPr>{lead}{run}</w:p>')


def holder(d, lead, brk=False):
    """An empty line that holds a picture behind the page (a page with no paragraph of its own to hold it)."""
    b = "<w:pageBreakBefore/>" if brk else ""
    d.body.append(f'<w:p><w:pPr>{b}<w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/></w:pPr>{lead}</w:p>')


def spacer(d, geo):
    """The space above a table (a table holds no space of its own): an empty line exactly that tall; a new PDF page
    starts a new page."""
    if not geo:
        return
    h = geo.get("before", 0)
    brk = "<w:pageBreakBefore/>" if geo.get("break") else ""
    if h >= 2 or brk:
        d.body.append(f'<w:p><w:pPr>{brk}<w:spacing w:before="0" w:after="0" w:line="{max(20, int(round(h * TW)))}" '
                      'w:lineRule="exact"/></w:pPr></w:p>')
