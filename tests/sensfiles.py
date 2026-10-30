"""Word files written by hand for the 2.97.0 sensitivity tests: a body, a page header, a Purview label."""
import zipfile

W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def docx(path, body, header=None, label=None):
    """A small Word file written by hand: the body, a page header, a Purview sensitivity label."""
    ct = ('<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          + ('<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>' if header else "")
          + ('<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/>' if label else "")
          + '</Types>')
    rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             + ('<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>' if header else "")
             + '</Relationships>')
    doc = (f'<?xml version="1.0"?><w:document {W_NS}><w:body><w:p><w:r><w:t>{body}</w:t></w:r></w:p>'
           + ('<w:sectPr><w:headerReference w:type="default" r:id="rId9"/></w:sectPr>' if header else "") + '</w:body></w:document>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc); z.writestr("word/_rels/document.xml.rels", drels)
        if header:
            z.writestr("word/header1.xml", f'<?xml version="1.0"?><w:hdr {W_NS}><w:p><w:r><w:t>{header}</w:t></w:r></w:p></w:hdr>')
        if label:
            z.writestr("docProps/custom.xml", '<?xml version="1.0"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
                       'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" '
                       f'name="MSIP_Label_3f1c2a4e-1111-2222-3333-444455556666_Name"><vt:lpwstr>{label}</vt:lpwstr></property></Properties>')
    return path
