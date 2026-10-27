"""A deliberately hard Word file for the text check: a text box (with its old-Word copy), a table, a header, a footer,
a footnote and an all-caps instruction line. make(folder) -> path."""
import os, zipfile


def make(OUT):
    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:v="urn:schemas-microsoft-com:vml"'
    def p(t): return f'<w:p><w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>'
    tb = ('<w:p><w:r><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><wp:anchor><a:graphic><a:graphicData><wps:wsp><wps:txbx><w:txbxContent>'
          + p("Text box: the Offeror shall keep the radiator below 40 C.") + '</w:txbxContent></wps:txbx></wps:wsp></a:graphicData></a:graphic></wp:anchor></w:drawing></mc:Choice>'
          '<mc:Fallback><w:pict><v:shape><v:textbox><w:txbxContent>' + p("Text box: the Offeror shall keep the radiator below 40 C.") +
          '</w:txbxContent></v:textbox></v:shape></w:pict></mc:Fallback></mc:AlternateContent></w:r></w:p>')
    table = '<w:tbl><w:tr><w:tc>' + p("CLIN 0001") + '</w:tc><w:tc>' + p("Thermal analysis report, due 30 days after award") + '</w:tc></w:tr></w:tbl>'
    body = (p("L.9 SPECIAL INSTRUCTIONS") + p("The Offeror shall describe its thermal vacuum test plan.") + tb + table +
            p("NOTE TO OFFERORS: SUBMIT QUESTIONS EARLY") + p("See note") + '<w:p><w:r><w:t>Footnoted line.</w:t></w:r><w:r><w:footnoteReference w:id="1"/></w:r></w:p>')
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>{body}<w:sectPr><w:headerReference w:type="default" r:id="rId2"/><w:footerReference w:type="default" r:id="rId3"/></w:sectPr></w:body></w:document>'
    hdr = f'<?xml version="1.0" encoding="UTF-8"?><w:hdr {W}>' + p("CUI: Kestrel source selection information") + '</w:hdr>'
    ftr = f'<?xml version="1.0" encoding="UTF-8"?><w:ftr {W}>' + p("Attachment 4, Revision B") + '</w:ftr>'
    fn = f'<?xml version="1.0" encoding="UTF-8"?><w:footnotes {W}><w:footnote w:id="1">' + p("Footnote: test at 1E-6 torr.") + '</w:footnote></w:footnotes>'
    ct = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/><Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/></Types>'
    rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    drels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/><Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/></Relationships>'
    with zipfile.ZipFile(os.path.join(OUT, "Hard_RFP.docx"), "w") as z:
        for n, d in (("[Content_Types].xml", ct), ("_rels/.rels", rels), ("word/document.xml", doc), ("word/_rels/document.xml.rels", drels),
                     ("word/header1.xml", hdr), ("word/footer1.xml", ftr), ("word/footnotes.xml", fn)):
            z.writestr(n, d)
    return os.path.join(OUT, "Hard_RFP.docx")
