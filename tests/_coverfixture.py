"""Test helper (3.27.0): a cover page built the way the team builds them: a picture behind the text, a floating table
over it holding the volume name and solicitation, a text box with the company, and a plain paragraph."""
import io, os, re, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"


def make(path):
    import docx
    from docx.shared import Inches
    d = docx.Document()
    d.add_picture(os.path.join(HERE, "pefix", "data", "Logo.png"), width=Inches(8.5))
    d.add_paragraph("Prepared for the United States Space Force")
    d.save(path)
    z = zipfile.ZipFile(path)
    files = {i.filename: z.read(i.filename) for i in z.infolist()}
    x = files["word/document.xml"].decode("utf-8")
    m = re.search(r"<wp:inline([^>]*)>(.*?)</wp:inline>", x, re.S)
    nsdecl = " ".join(re.findall(r'xmlns:\w+="[^"]+"', m.group(1)))
    inner = m.group(2)
    anchor = (f'<wp:anchor {nsdecl} distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="1" behindDoc="1" locked="0" '
              'layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="page"><wp:posOffset>0'
              '</wp:posOffset></wp:positionH><wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionV>'
              + inner.replace("<wp:docPr", "<wp:wrapNone/><wp:docPr", 1) + "</wp:anchor>")
    x = x[:m.start()] + anchor + x[m.end():]
    table = ('<w:tbl><w:tblPr><w:tblpPr w:leftFromText="180" w:rightFromText="180" w:vertAnchor="page" w:horzAnchor="page" '
             'w:tblpX="1440" w:tblpY="4320"/><w:tblW w:w="9360" w:type="dxa"/></w:tblPr><w:tblGrid><w:gridCol w:w="9360"/></w:tblGrid>'
             '<w:tr><w:tc><w:tcPr><w:tcW w:w="9360" w:type="dxa"/></w:tcPr><w:p><w:r><w:t>VOLUME I TECHNICAL</w:t></w:r></w:p></w:tc></w:tr>'
             '<w:tr><w:tc><w:tcPr><w:tcW w:w="9360" w:type="dxa"/></w:tcPr><w:p><w:r><w:t>FA8810-26-R-0042</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')
    tbox = ('<w:p><w:r><w:drawing><wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="2" behindDoc="0" '
            'locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="margin"><wp:align>center'
            '</wp:align></wp:positionH><wp:positionV relativeFrom="page"><wp:posOffset>8229600</wp:posOffset></wp:positionV>'
            '<wp:extent cx="2743200" cy="457200"/><wp:wrapNone/><wp:docPr id="5" name="Company box"/><a:graphic xmlns:a="http://'
            'schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/'
            f'wordprocessingShape"><wps:wsp xmlns:wps="{WPS}"><wps:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="2743200" cy="457200"/>'
            '</a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></wps:spPr><wps:txbx><w:txbxContent><w:p><w:r><w:t>Company Name'
            '</w:t></w:r></w:p></w:txbxContent></wps:txbx><wps:bodyPr/></wps:wsp></a:graphicData></a:graphic></wp:anchor></w:drawing>'
            '</w:r></w:p>')
    x = x.replace("<w:sectPr", table + tbox + "<w:sectPr", 1)
    files["word/document.xml"] = x.encode("utf-8")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        for k, v in files.items():
            zo.writestr(k, v)
    with open(path, "wb") as f:
        f.write(out.getvalue())
    return path
