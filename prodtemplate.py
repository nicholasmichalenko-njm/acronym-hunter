"""Make a template from a document type (3.7.0).

Builds a Word template (.dotx) that carries every value of the standard in force: the style library and the format
variables, heading numbering, each table row role's look on a sample table, captions as fields, the TOC and the
lists of tables and figures, the page scheme (cover, front matter, body, appendices) with its page setups, number
formats and restarts, and the headers and footers from the layouts.

The template is written only into the output folder, named "<document type> - TEMPLATE - Stationkeeper <date time>.dotx",
never over another file. It starts either from a small Stationkeeper base (cover, front matter, a chapter, an
appendix) or from a template file the person picks, which is read once and never written. Every value is then put in
by the same guarded fixes Fix a Copy uses, and the result is checked against the standard: a template made from a
standard passes its own check."""
import datetime, io, os, zipfile
from xml.sax.saxutils import escape

import prodcopy as PCY
import prodfix as PF
import prodrules as PRL
from prodengine.pe import fixes as X, fixes2 as X2

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
TEMPLATE_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml"
DOCUMENT_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
MARK = " - TEMPLATE - Stationkeeper "
COVER_STYLES = {"PE Volume Name": {"type": "paragraph", "based_on": "Normal", "size": 20, "bold": True, "jc": "center", "after": 12},
                "PE Solicitation": {"type": "paragraph", "based_on": "Normal", "size": 12, "jc": "center", "after": 6},
                "PE Company": {"type": "paragraph", "based_on": "Normal", "size": 12, "jc": "center", "after": 6}}
# the fixes that put the standard into the template, in Fix a Copy's order
# 3.38.0: rules Make templates cannot meet yet, left out of a template's own check (Audit and Fix a Copy still check them)
RULES_LATER = {}    # 3.42.0: Make templates builds Rule 7's footer, so every rule is checked
TEMPLATE_FIXES = ("styles_apply", "unnumber_inheriting", "heading_numbering", "list_numbering", "table_styles", "tables", "lists", "caption_typed", "caption_fields",
                  "caption_after", "toc_field", "toc_styles", "toc_list_identifiers", "chapter_breaks", "page_numbers",
                  "page_setup", "page_field_clean", "hf_build")


def template_name(type_name, when=None):
    when = when or datetime.datetime.now()
    stem = "".join(c for c in (type_name or "Document type") if c not in '<>:"/\\|?*').strip(" .") or "Document type"
    return f"{stem}{MARK}{when.strftime('%Y-%m-%d %H%M')}.dotx"


# ------------------------------------------------------------------ the base package
def _p(style, text="", runs=None, sect=None):
    ppr = f'<w:pStyle w:val="{style}"/>' if style else ""
    if sect:
        ppr += sect
    body = runs if runs is not None else (f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>' if text else "")
    return f"<w:p>{'<w:pPr>' + ppr + '</w:pPr>' if ppr else ''}{body}</w:p>"


def _fld(instr, result=""):
    return (f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> {escape(instr)} </w:instrText></w:r>'
            f'<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t xml:space="preserve">{escape(result)}</w:t></w:r>'
            f'<w:r><w:fldChar w:fldCharType="end"/></w:r>')


def _t(text):
    return f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _sect(std, final=False):
    v = std.get("variables") or {}
    w, h = PRL.PAGE_SIZES.get(v.get("paper") or "Letter", (8.5, 11))
    m = {k: int(round(float(v.get("margin_" + k) or 1) * 1440)) for k in ("top", "bottom", "left", "right")}
    inner = (f'<w:pgSz w:w="{int(w * 1440)}" w:h="{int(h * 1440)}"/>'
             f'<w:pgMar w:top="{m["top"]}" w:right="{m["right"]}" w:bottom="{m["bottom"]}" w:left="{m["left"]}" w:header="720" w:footer="720" w:gutter="0"/>')
    return f"<w:sectPr>{inner}</w:sectPr>"


def _caption_runs(rule, chap_shown, title):
    chap_i, seq_i = X2.caption_instrs(rule)
    after = {"period_tab": ".", "period_space": ". ", "tab": "", "colon_space": ": "}.get(rule.get("after_number", "period_tab"), ".")
    runs = _t(rule["label"] + " ")
    if chap_i:
        runs += _fld(chap_i, chap_shown) + _t(rule.get("separator", "-"))
    first = {"ROMAN": "I", "roman": "i", "ALPHABETIC": "A", "alphabetic": "a"}.get(X2.seq_format(rule), "1")   # 3.22.1
    runs += _fld(seq_i, first) + _t(after)
    if rule.get("after_number", "period_tab").endswith("tab") or rule.get("after_number") == "tab":
        runs += "<w:r><w:tab/></w:r>"
    return runs + _t(title)


def _tc(text, width):
    return (f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>'
            f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p></w:tc>')


def _sample_table(std, part):
    rule = next((c for c in std["captions"] if c["label"] == "Table" and c["part"] == part), std["captions"][0])
    widths = [3000, 2200, 2200, 2200]
    grid = "".join(f'<w:gridCol w:w="{x}"/>' for x in widths)
    cap = (f'<w:tr><w:tc><w:tcPr><w:tcW w:w="{sum(widths)}" w:type="dxa"/><w:gridSpan w:val="4"/></w:tcPr>'
           f'<w:p><w:pPr><w:pStyle w:val="Caption"/></w:pPr>{_caption_runs(rule, "1" if part == "body" else "A", "Sample data table")}</w:p></w:tc></w:tr>')
    rows = [("Item", "Base year", "Option 1", "Option 2"), ("Labor", "", "", ""), ("Program management", "1,200", "1,250", "1,300"),
            ("Engineering", "3,400", "3,500", "3,600"), ("Total", "4,600", "4,750", "4,900")]
    trs = cap
    for i, r in enumerate(rows):
        hdr = '<w:trPr><w:tblHeader/></w:trPr>' if i == 0 else ""
        trs += f"<w:tr>{hdr}" + "".join(_tc(t, w) for t, w in zip(r, widths)) + "</w:tr>"
    trs += (f'<w:tr><w:tc><w:tcPr><w:tcW w:w="{sum(widths)}" w:type="dxa"/><w:gridSpan w:val="4"/></w:tcPr>'
            f'<w:p><w:r><w:t>Note: values in thousands of dollars.</w:t></w:r></w:p></w:tc></w:tr>')
    return f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>{trs}</w:tbl>'


def _document(std):
    v = std.get("variables") or {}
    sect = _sect(std)
    toc = X.toc_instr(std)
    out = []
    # cover
    out.append(_p("PEVolumeName", v.get("volume_name") or "[Volume name]"))
    out.append(_p("PESolicitation", v.get("solicitation") or "[Solicitation number]"))
    import fillins as FI
    extra = [f for f in FI.custom(std) if f["kind"] == "styleref"]
    out.append(_p("PECompany", v.get("company") or "[Company]", sect=None if extra else sect))
    for i, f in enumerate(extra):                    # 3.23.0: each fill-in once on the cover, in its own style
        out.append(_p(fill_style_id(f["style"]), FI.value(std, f["key"]) or f"[{f['name']}]", sect=sect if i == len(extra) - 1 else None))
    # front matter: the TOC and the lists of tables and figures
    out.append(_p("TOCHeading", "Table of Contents"))
    out.append(_p("", runs=_fld(toc, "Update the table of contents in Word (F9).")))
    for lst in (std.get("toc") or {}).get("lists", []):
        ident = (lst.get("identifiers") or [""])[0]
        if ident:
            out.append(_p("TOCHeading", lst.get("title", "List")))
            out.append(_p("", runs=_fld(f'TOC \\h \\z \\c "{ident}"', "Update the list in Word (F9).")))
    out.append(_p("", sect=sect))
    # body chapter
    out.append(_p("Heading1", "Chapter title"))
    out.append(_p("Heading2", "Section title"))
    out.append(_p("Normal", "Body text in the body style. Every value in this template comes from the document profile."))
    out.append(_p("ListBullet", "A bulleted item"))
    out.append(_p("ListBullet", "Another bulleted item"))
    out.append(_sample_table(std, "body"))
    out.append(_p("Normal", "Text after the table."))
    fig = next((c for c in std["captions"] if c["label"] == "Figure" and c["part"] == "body"), None)
    if fig:
        out.append(_p("Normal", "[Figure]"))
        out.append(_p("Caption", runs=_caption_runs(fig, "1", "Sample figure")))
    out.append(_p("Normal", "", sect=sect))
    # appendix
    out.append(_p("Heading7", "Appendix title"))
    out.append(_p("Normal", "Appendix text."))
    out.append(_sample_table(std, "appendix"))
    out.append(_p("Normal", ""))
    body = "".join(out) + sect
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}">'
            f"<w:body>{body}</w:body></w:document>")


def _styles():
    """Word's built-in styles the template needs, with their outline levels (the TOC reads them); the standard's
    values go in afterwards through the style fix."""
    def ps(sid, name, based="Normal", extra="", ppr="", default=False, ui=None):
        d = ' w:default="1"' if default else ""
        b = f'<w:basedOn w:val="{based}"/>' if based else ""
        return (f'<w:style w:type="paragraph"{d} w:styleId="{sid}"><w:name w:val="{name}"/>{b}<w:next w:val="Normal"/>'
                f'{extra}<w:qFormat/>{"<w:pPr>" + ppr + "</w:pPr>" if ppr else ""}</w:style>')
    s = [ps("Normal", "Normal", based="", default=True)]
    for k in range(1, 10):
        s.append(ps(f"Heading{k}", f"heading {k}", ppr=f'<w:keepNext/><w:keepLines/><w:outlineLvl w:val="{k - 1}"/>'))
    s += [ps("TOCHeading", "TOC Heading"), ps("Caption", "caption"), ps("ListBullet", "List Bullet"), ps("ListNumber", "List Number"),
          ps("TOC1", "toc 1"), ps("TOC2", "toc 2"), ps("TOC3", "toc 3"), ps("TableofFigures", "table of figures"),
          ps("Header", "header"), ps("Footer", "footer")]
    for sid, name in (("PEVolumeName", "PE Volume Name"), ("PESolicitation", "PE Solicitation"), ("PECompany", "PE Company")):
        s.append(ps(sid, name).replace("<w:style ", '<w:style w:customStyle="1" ', 1))
    s.append('<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/>'
             '<w:uiPriority w:val="1"/><w:semiHidden/><w:unhideWhenUsed/></w:style>')
    s.append('<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:semiHidden/>'
             '<w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>'
             '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>')
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:styles xmlns:w="{W_NS}">'
            '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" '
            'w:eastAsia="Times New Roman"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>'
            '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
            + "".join(s) + "</w:styles>")


def base_package(std):
    """A small, valid Word template with the parts the fixes need, as bytes."""
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          f'<Override PartName="/word/document.xml" ContentType="{TEMPLATE_CT}"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
          '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
                '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>'
                '</Relationships>')
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:settings xmlns:w="{W_NS}">'
                '<w:defaultTabStop w:val="720"/><w:characterSpacingControl w:val="doNotCompress"/>'
                '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
                '</w:settings>')
    numbering = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:numbering xmlns:w="{W_NS}"/>'
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(std.get("name", "Document type"))}</dc:title><dc:creator>Stationkeeper</dc:creator>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
            '</cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Stationkeeper</Application></Properties>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in (("[Content_Types].xml", ct), ("_rels/.rels", rels), ("word/document.xml", _document(std)),
                           ("word/_rels/document.xml.rels", doc_rels), ("word/styles.xml", _styles()), ("word/settings.xml", settings),
                           ("word/numbering.xml", numbering), ("docProps/core.xml", core), ("docProps/app.xml", app)):
            z.writestr(name, text.encode("utf-8"))
    return buf.getvalue()


def as_template(data):
    """A .docx's bytes with its main part marked as a template (.dotx); a template's bytes unchanged."""
    zin = zipfile.ZipFile(io.BytesIO(data))
    ct = zin.read("[Content_Types].xml").decode("utf-8")
    if TEMPLATE_CT in ct:
        return data
    ct = ct.replace(DOCUMENT_CT, TEMPLATE_CT).replace(DOCUMENT_CT.replace(".main+xml", ".main+xml"), TEMPLATE_CT)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for it in zin.infolist():
            z.writestr(it, ct.encode("utf-8") if it.filename == "[Content_Types].xml" else zin.read(it.filename))
    return buf.getvalue()


# ------------------------------------------------------------------ making it
class TemplateJob:
    def __init__(self, path, start):
        self.copy = path            # the name the guarded steps use
        self.start = start          # "Stationkeeper base" or the template file read
        self.steps = []
        self.check = None
        self.rules_later = {}       # 3.38.0: {rule id: why the template's own check leaves it out}

    @property
    def report_path(self):
        return os.path.splitext(self.copy)[0] + " - report.xlsx"


def with_theme(data, theme_xml):
    """The package with its theme part replaced (added when it has none)."""
    zin = zipfile.ZipFile(io.BytesIO(data))
    names = zin.namelist()
    part = next((n for n in names if n.startswith("word/theme/") and n.endswith(".xml") and "/_rels/" not in n), None)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for i in zin.infolist():
            b = zin.read(i.filename)
            if i.filename == part:
                b = theme_xml.encode("utf-8")
            elif part is None and i.filename == "[Content_Types].xml":
                b = b.replace(b"</Types>", b'<Override PartName="/word/theme/theme1.xml" ContentType="application/vnd.openxmlformats-'
                              b'officedocument.theme+xml"/></Types>')
            elif part is None and i.filename == "word/_rels/document.xml.rels":
                b = b.replace(b"</Relationships>", b'<Relationship Id="rIdSKth1" Type="http://schemas.openxmlformats.org/officeDocument/'
                              b'2006/relationships/theme" Target="theme/theme1.xml"/></Relationships>')
            z.writestr(i, b)
        if part is None:
            z.writestr("word/theme/theme1.xml", theme_xml.encode("utf-8"))
    return out.getvalue()


def fill_style_id(name):
    import re as _re
    return _re.sub(r"[^A-Za-z0-9]", "", name) or "SKFill"


def standard_for_template(std):
    """The standard with the cover styles the template's headers read (when the standard does not define them), the
    fill-ins' cover styles among them (3.23.0)."""
    import copy as _c
    import fillins as FI
    std = _c.deepcopy(std)
    defs = std.setdefault("style_defs", {})
    for name, d in COVER_STYLES.items():
        defs.setdefault(name, dict(d))
    for f in FI.custom(std):
        if f["kind"] == "styleref":
            defs.setdefault(f["style"], {"type": "paragraph", "based_on": "Normal", "jc": "center", "after": 6})
    return apply_rules(std)


RESPONSE_TOKENS = ("RFP", "RFI", "BAA", "RFQ", "CSO")


def response_renames(std):
    """3.38.0 Rule 4: {old style name: new} for styles named with another response type than the effort's."""
    import re as _re
    rt = (std.get("response_type") or "").upper()
    if rt not in RESPONSE_TOKENS:
        return {}
    out = {}
    for name in (std.get("style_defs") or {}):
        new = name
        for t in RESPONSE_TOKENS:
            if t != rt:
                new = _re.sub(rf"\b{t}\b", rt, new)
        if new != name:
            out[name] = new
    return out


def _rename_values(x, ren):
    if isinstance(x, dict):
        return {(ren.get(k, k) if isinstance(k, str) else k): _rename_values(v, ren) for k, v in x.items()}
    if isinstance(x, list):
        return [_rename_values(v, ren) for v in x]
    if isinstance(x, str) and x in ren:
        return ren[x]
    return x


def apply_rules(std):
    """3.38.0: Rule 4 (style names follow the response type), Rule 5 (no title page, no title page styles) and Rule 6 (every
    heading level's number at 0, one text position), unless the global standards or the effort turned them off."""
    off = set(str(x) for x in (std.get("_rules_off") or []))
    if "5" not in off and not (std.get("page_parts") or {}).get("title"):
        defs = std.get("style_defs") or {}
        fam = [n for n, d in defs.items() if (d or {}).get("used_on") == "Title page"]
        for n in fam:
            defs.pop(n, None)
        st = std.get("styles") or {}
        if fam and st.get("allowed"):
            st["allowed"] = [a for a in st["allowed"] if a not in fam]
    if "6" not in off:
        PRL.rule6(std)
    if "4" not in off:
        ren = response_renames(std)
        if ren:
            keep = {k: std.get(k) for k in ("variables", "_parts_dir", "_rules_off", "response_type", "name")}
            std = _rename_values(std, ren)
            std.update({k: v for k, v in keep.items() if v is not None})
    return std


def with_properties(data, props):
    """3.23.0: the template's document properties: Title and Subject (core), Company and Manager (app), the rest as
    custom properties. props: {name: value}."""
    import re as _re
    from xml.sax.saxutils import escape as _e
    if not props:
        return data
    zin = zipfile.ZipFile(io.BytesIO(data))
    names = zin.namelist()
    custom = {k: v for k, v in props.items() if k not in ("Title", "Subject", "Company", "Manager")}
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for i in zin.infolist():
            b = zin.read(i.filename).decode("utf-8") if i.filename.endswith((".xml", ".rels")) else zin.read(i.filename)
            if i.filename == "docProps/core.xml":
                for k, tag in (("Title", "dc:title"), ("Subject", "dc:subject")):
                    if k in props:
                        b = _re.sub(rf"<{tag}>.*?</{tag}>|<{tag}/>", "", b, flags=_re.S)
                        b = b.replace("</cp:coreProperties>", f"<{tag}>{_e(props[k])}</{tag}></cp:coreProperties>")
            if i.filename == "docProps/app.xml":
                for k in ("Company", "Manager"):
                    if k in props:
                        b = _re.sub(rf"<{k}>.*?</{k}>|<{k}/>", "", b, flags=_re.S)
                        b = b.replace("</Properties>", f"<{k}>{_e(props[k])}</{k}></Properties>")
            if custom and i.filename == "[Content_Types].xml" and "docProps/custom.xml" not in names:
                b = b.replace("</Types>", '<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-'
                              'officedocument.custom-properties+xml"/></Types>')
            if custom and i.filename == "_rels/.rels" and "docProps/custom.xml" not in names:
                b = b.replace("</Relationships>", '<Relationship Id="rIdSKcp1" Type="http://schemas.openxmlformats.org/officeDocument/'
                              '2006/relationships/custom-properties" Target="docProps/custom.xml"/></Relationships>')
            if custom and i.filename == "docProps/custom.xml":
                continue
            z.writestr(i, b.encode("utf-8") if isinstance(b, str) else b)
        if custom:
            CP = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
            VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
            have = ""
            if "docProps/custom.xml" in names:
                old = zin.read("docProps/custom.xml").decode("utf-8")
                have = "".join(p for p in _re.findall(r"<property .*?</property>", old, _re.S)
                               if not any(f'name="{_e(k)}"' in p for k in custom))
            items = "".join(f'<property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="{n}" name="{_e(k)}"><vt:lpwstr>{_e(v)}</vt:lpwstr></property>'
                            for n, (k, v) in enumerate(custom.items(), start=100))
            z.writestr("docProps/custom.xml", (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Properties xmlns="{CP}" '
                                               f'xmlns:vt="{VT}">{have}{items}</Properties>').encode("utf-8"))
    return out.getvalue()


def make(std, folder, start_from="", word=None, when=None, progress=None, parts_dir=None):
    """Write the template into folder and put the standard into it. start_from: a template or document to start
    from (read once, never written), or "" for the Stationkeeper base. Returns a TemplateJob."""
    say = progress or (lambda *a: None)
    std = PRL.engine_ready(standard_for_template(std))
    hn = std.setdefault("heading_numbering", {})
    uses_chapters = any(c.get("chapter_level") for c in std.get("captions") or []) or \
        any((p.get("numbers") or {}).get("chapter_level") for p in (std.get("pagination") or {}).get("parts", []))
    if uses_chapters and not hn.get("on") and hn.get("levels"):
        hn["on"] = True          # chapter numbers in captions and page numbers (2-1, A-1) need numbered headings
    ln = std.setdefault("list_numbering", {})
    if not ln.get("on") and ln.get("lists"):
        ln["on"] = True          # 3.9.0: a template's list styles show their bullets and numbers
    if start_from:
        if os.path.splitext(start_from)[1].lower() not in (".dotx", ".docx"):
            raise PCY.NotAllowed("Start from a Word template or document (.dotx or .docx); macro files are not used.")
        with open(start_from, "rb") as f:                     # read once; never opened for writing
            data = as_template(f.read())
        start = os.path.basename(start_from)
    else:
        data = base_package(std)
        start = "Stationkeeper base"
        pdir = parts_dir or std.get("_parts_dir") or ""
        for where in ("cover", "title", "backer"):     # 3.10.0: the profile's own cover and back cover pages; 3.34.0: title page
            fname = (std.get("page_parts") or {}).get(where)
            if fname and pdir and os.path.isfile(os.path.join(pdir, fname)):
                import prodparts as PP
                with open(os.path.join(pdir, fname), "rb") as f:
                    data = PP.place(data, f.read(), where)
    import fillins as FI
    pr = {f["property"]: (FI.value(std, f["key"]) or f"[{f['name']}]") for f in FI.custom(std) if f["kind"] == "docprop"}
    if std.get("_template_name"):                     # 3.23.0: the template's name and version travel in the file
        pr.update({"SK Template": std["_template_name"], "SK Template Version": str(std.get("_template_version", 1))})
    if pr:                                            # 3.23.0: the document properties the DOCPROPERTY fill-ins read
        data = with_properties(data, pr)
    th = (std.get("theme") or {}).get("xml")
    if th:                                            # 3.22.0: the standard's theme (colors and fonts) replaces the base's
        data = with_theme(data, th)
    folder = os.path.abspath(folder)
    os.makedirs(folder, exist_ok=True)
    PCY.allow_root(folder)
    target = os.path.join(folder, template_name(std.get("name"), when))
    stem, ext = os.path.splitext(target)
    n = 2
    while True:
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
            break
        except FileExistsError:
            target = f"{stem} ({n}){ext}"; n += 1
    with os.fdopen(fd, "wb") as out:
        out.write(data)
    job = TemplateJob(target, start)
    plan = {"on": list(TEMPLATE_FIXES), "table_answers": {}, "table_roles": {}, "table_types": {}, "list_answers": {}, "xref_mapping": {}}
    for fx in PF.FIXES:
        if fx["key"] not in TEMPLATE_FIXES:
            continue
        if fx["key"] == "heading_numbering" and not (std.get("heading_numbering") or {}).get("on"):
            continue
        if fx["key"] == "hf_build":
            from prodengine.engine.pkg import Package
            from prodengine.pe import hf as H
            gone = PRL.missing_values(std, H._sources(Package(job.copy), std))
            if gone:
                job.steps.append({"step": fx["label"], "key": "hf_build", "changed": False, "refused": "Not set and not on the "
                                  "cover: " + ", ".join(PRL.HF_TOKENS[k] for k in gone) + ". Headers and footers were left as they were."})
                continue
        say(fx["label"])
        rec = PCY.run_step(job, fx["label"], fx["op"], fx["allowed"], fx["args"](std, plan))
        rec["key"] = fx["key"]
    qp = std.get("quick_parts") or {}
    if qp.get("entries"):                            # 3.22.0: the standard's Quick Parts, in one gallery under its categories
        import prodquickparts as QP
        say("Putting in the Quick Parts")
        rec = PCY.run_step(job, "Put in the standard's Quick Parts", QP.op_quick_parts, QP.QP_ALLOWED,
                           {"entries": qp["entries"], "parts_dir": parts_dir or std.get("_parts_dir") or "",
                            "one_gallery": qp.get("one_gallery", True)})
        rec["key"] = "quick_parts"
    if (std.get("section_contents") or {}):            # 3.45.0: each document section's components at its start
        import sectioncontents as SC
        say("Putting in each section's contents")
        rec = PCY.run_step(job, "Put in each section's contents", SC.op_section_contents, SC.ALLOWED, {"std": std})
        rec["key"] = "section_contents"
    if word is not None:
        say("Updating fields in Word")
        try:
            r = word(job.copy) or {}
        except Exception as e:  # noqa: BLE001
            r = {"ok": False, "why": type(e).__name__}
        job.steps.append({"step": PF.WORD_STEP["label"], "key": "word_update", "changed": bool(r.get("ok")), "report": r,
                          **({} if r.get("ok") else {"refused": r.get("why", "Word could not update the fields.")})})
    say("Checking the template against the standard")
    later = {k: v for k, v in RULES_LATER.items() if k not in set(str(x) for x in (std.get("_rules_off") or []))}
    job.rules_later = later                           # 3.38.0: rules a template cannot meet yet, said in the report
    job.check = PF.check(job.copy, dict(std, _rules_off=sorted(set(map(str, std.get("_rules_off") or [])) | set(later))))
    try:                                              # 3.23.0: the validation report
        import templatecheck as TC
        job.validation = TC.validate(job.copy, installed_fonts=std.get("_installed_fonts"))
    except Exception:                                 # noqa: BLE001  the report never stops a template
        import diag
        diag.swallowed()
        job.validation = None
    return job
