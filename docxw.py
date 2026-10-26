"""Minimal Word (.docx) writer: headings 1-6, paragraphs and tables, written as Office XML directly.
No add-in, no macros, no third-party library. Used for the compliance outline (2.8.0)."""
import zipfile

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _x(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _run(text, bold=False, color=None):
    props = ("<w:b/>" if bold else "") + (f'<w:color w:val="{color}"/>' if color else "")
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    lines = str(text).split("\n")
    out = []
    for i, ln in enumerate(lines):
        if i:
            out.append("<w:r><w:br/></w:r>")
        out.append(f'<w:r>{rpr}<w:t xml:space="preserve">{_x(ln)}</w:t></w:r>')
    return "".join(out)


class Doc:
    def __init__(self):
        self.body = []
        self.props = {}          # custom document properties (File > Info > Properties > Advanced > Custom)

    def heading(self, text, level=1):
        level = max(1, min(int(level), 6))
        self.body.append(f'<w:p><w:pPr><w:pStyle w:val="Heading{level}"/></w:pPr>{_run(text)}</w:p>')

    def para(self, text, bold=False, color=None):
        self.body.append(f"<w:p>{_run(text, bold, color)}</w:p>")

    def rich(self, parts):
        """One paragraph of several runs: parts = [(text, {"bold", "color", "fill", "size", "italic"})] (2.29.0).
        fill shades the run's background (a highlighter in any color); size is in half-points."""
        runs = []
        for text, f in parts:
            f = f or {}
            props = (("<w:b/>" if f.get("bold") else "") + ("<w:i/>" if f.get("italic") else "")
                     + (f'<w:color w:val="{f["color"]}"/>' if f.get("color") else "")
                     + (f'<w:sz w:val="{int(f["size"])}"/>' if f.get("size") else "")
                     + (f'<w:shd w:val="clear" w:color="auto" w:fill="{f["fill"]}"/>' if f.get("fill") else ""))
            rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
            runs.append(f'<w:r>{rpr}<w:t xml:space="preserve">{_x(text)}</w:t></w:r>')
        self.body.append("<w:p>" + "".join(runs) + "</w:p>")

    def table(self, header, rows, widths):
        def cell(text, w, bold=False, shade=None):
            sh = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else ""
            return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{sh}</w:tcPr>'
                    f'<w:p><w:pPr><w:spacing w:before="20" w:after="20"/></w:pPr>{_run(text, bold)}</w:p></w:tc>')
        border = "".join(f'<w:{b} w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
                         for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
        trs = ['<w:tr><w:trPr><w:tblHeader/></w:trPr>' + "".join(cell(h, w, True, "D9E2F3") for h, w in zip(header, widths)) + "</w:tr>"]
        trs += ["<w:tr><w:trPr><w:cantSplit/></w:trPr>" + "".join(cell(v, w) for v, w in zip(r, widths)) + "</w:tr>" for r in rows]
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
        self.body.append(f'<w:tbl><w:tblPr><w:tblW w:w="{sum(widths)}" w:type="dxa"/><w:tblBorders>{border}</w:tblBorders>'
                         f'<w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>' + "".join(trs) + "</w:tbl><w:p/>")

    def save(self, path):
        sect = ('<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" '
                'w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>')
        doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>{"".join(self.body)}{sect}</w:body></w:document>'
        heads = "".join(
            f'<w:style w:type="paragraph" w:styleId="Heading{i}"><w:name w:val="heading {i}"/><w:basedOn w:val="Normal"/>'
            f'<w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="{240 - 20 * i}" w:after="80"/>'
            f'<w:outlineLvl w:val="{i - 1}"/></w:pPr><w:rPr><w:b/><w:sz w:val="{max(22, 34 - 2 * i)}"/></w:rPr></w:style>'
            for i in range(1, 7))
        styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {W}>'
                  '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>'
                  '<w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>'
                  '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
                  + heads + "</w:styles>")
        ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
              '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
              + ('<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/>'
                 if self.props else "") + '</Types>')
        rel = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{t}" Target="{g}"/></Relationships>')
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ct)
            if self.props:
                z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                           '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                           '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties" Target="docProps/custom.xml"/>'
                           '</Relationships>')
                items = "".join(f'<property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="{i}" name="{_x(k)}"><vt:lpwstr>{_x(v)}</vt:lpwstr></property>'
                                for i, (k, v) in enumerate(self.props.items(), start=2))
                z.writestr("docProps/custom.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
                           'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">' + items + '</Properties>')
            else:
                z.writestr("_rels/.rels", rel.format(t="officeDocument", g="word/document.xml"))
            z.writestr("word/document.xml", doc)
            z.writestr("word/styles.xml", styles)
            z.writestr("word/_rels/document.xml.rels", rel.format(t="styles", g="styles.xml"))
