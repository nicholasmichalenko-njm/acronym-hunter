"""A small Word file built by hand for the Format Check tests (3.5.0): styles with fonts, a table style, a theme,
typed formatting, a table with and without a caption row, captions typed and with SEQ fields, a TOC field with a
forbidden switch, typed TOC lines, typed bullets, two sections (one with narrow margins and A4), a footer with a PAGE
field and one with a typed page number. Made-up content only."""
import zipfile

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def run(text, font=None, size=None, rstyle=None):
    rpr = ""
    if font or size or rstyle:
        rpr = "<w:rPr>" + (f'<w:rStyle w:val="{rstyle}"/>' if rstyle else "") + (f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>' if font else "") + \
              (f'<w:sz w:val="{int(size * 2)}"/>' if size else "") + "</w:rPr>"
    parts = text.split("\t")
    inner = '<w:tab/>'.join(f'<w:t xml:space="preserve">{p}</w:t>' for p in parts)
    return f"<w:r>{rpr}{inner}</w:r>"


def para(content, style=None, num=False):
    ppr = ""
    if style or num:
        ppr = "<w:pPr>" + (f'<w:pStyle w:val="{style}"/>' if style else "") + ('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>' if num else "") + "</w:pPr>"
    return f"<w:p>{ppr}{content}</w:p>"


def seq_caption(label, num, title):
    return para(run(f"{label} ") + f'<w:fldSimple w:instr=" STYLEREF 1 \\s "><w:r><w:t>{num.split("-")[0]}</w:t></w:r></w:fldSimple>' + run("-") +
                f'<w:fldSimple w:instr=" SEQ {label} \\* ARABIC \\s 1 "><w:r><w:t>{num.split("-")[1]}</w:t></w:r></w:fldSimple>' + run(f".\t{title}"), "Caption")


def table(rows, style="ProposalTable"):
    trs = "".join("<w:tr>" + "".join(f"<w:tc><w:tcPr><w:tcW w:w=\"3000\" w:type=\"dxa\"/></w:tcPr>{para(run(c))}</w:tc>" for c in r) + "</w:tr>" for r in rows)
    return f'<w:tbl><w:tblPr><w:tblStyle w:val="{style}"/></w:tblPr><w:tblGrid><w:gridCol w:w="3000"/><w:gridCol w:w="3000"/></w:tblGrid>{trs}</w:tbl>'


def build(path):
    body = "".join([
        para(run("Volume I Technical"), "Heading1"),
        para('<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r>'
             '<w:r><w:fldChar w:fldCharType="separate"/></w:r>' + run("1 Approach\t1") + '<w:r><w:fldChar w:fldCharType="end"/></w:r>', "TOC1"),
        para(run("2 Risk\t4"), "TOC1"),
        para(run("1.1 Approach"), "Heading2"),
        para(run("Our approach is proven.") + run(" This part is typed in Calibri.", font="Calibri") + run(" And this is small.", size=9)),
        para(run("• A typed bullet that is not a list")),
        para(run("1. A typed number")),
        para(run("A real list item"), num=True),
        table([["Table 1-1.\tMass budget", ""], ["Item", "kg"], ["Radiator", "12"]]),
        seq_caption("Table", "1-2", "Power budget"),
        table([["Item", "W"], ["Heater", "40"]]),
        para(run("Figure 3. A typed caption with a space"), "Caption"),
        '<w:p><w:pPr><w:sectPr><w:footerReference w:type="default" r:id="rIdF1"/><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:pPr></w:p>',
        para(run("Appendix A"), "Heading1"),
        para(run("Appendix text.")),
        '<w:sectPr><w:footerReference w:type="default" r:id="rIdF2"/><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="720" w:bottom="1440" w:left="1440"/></w:sectPr>'])
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>{body}</w:body></w:document>'
    styles = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {W}>
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:asciiTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi"/><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="32"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Heading1"/><w:pPr><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="caption"/><w:basedOn w:val="Normal"/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TOC1"><w:name w:val="toc 1"/><w:basedOn w:val="Normal"/></w:style>
<w:style w:type="table" w:styleId="ProposalTable"><w:name w:val="Proposal Table"/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="20"/></w:rPr></w:style>
</w:styles>'''
    theme = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="T">'
             '<a:themeElements><a:fontScheme name="T"><a:majorFont><a:latin typeface="Calibri Light"/></a:majorFont>'
             '<a:minorFont><a:latin typeface="Calibri"/></a:minorFont></a:fontScheme></a:themeElements></a:theme>')
    f1 = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {W}><w:p><w:fldSimple w:instr=" PAGE "><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>'
    f2 = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {W}><w:p>{run("Page 7")}</w:p></w:ftr>'
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rIdS" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '<Relationship Id="rIdT" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>'
            '<Relationship Id="rIdF1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
            '<Relationship Id="rIdF2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer2.xml"/></Relationships>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
          '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
          '<Override PartName="/word/footer2.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in (("[Content_Types].xml", ct), ("_rels/.rels", root_rels), ("word/document.xml", doc), ("word/styles.xml", styles),
                     ("word/theme/theme1.xml", theme), ("word/_rels/document.xml.rels", rels), ("word/footer1.xml", f1), ("word/footer2.xml", f2)):
            z.writestr(n, d)
    return path
