"""Test helper (3.22.0): a template with Quick Parts in three galleries and a styles part of its own."""
import io, zipfile
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def part(name, cat, gallery, text, guid, style=""):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return (f'<w:docPart><w:docPartPr><w:name w:val="{name}"/><w:category><w:name w:val="{cat}"/><w:gallery w:val="{gallery}"/>'
            f'</w:category><w:behaviors><w:behavior w:val="content"/></w:behaviors><w:guid w:val="{{{guid}}}"/></w:docPartPr>'
            f'<w:docPartBody><w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p></w:docPartBody></w:docPart>')


GSTYLES = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}">'
           '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:rPr><w:sz w:val="56"/></w:rPr></w:style>'
           '<w:style w:type="paragraph" w:customStyle="1" w:styleId="QPCallout"><w:name w:val="QP Callout"/><w:basedOn w:val="Normal"/>'
           '<w:rPr><w:color w:val="1F5FAD"/></w:rPr></w:style></w:styles>')


def with_glossary(src, dst):
    """A template with three Quick Parts in three galleries (what a team template holds)."""
    zin = zipfile.ZipFile(src)
    out = io.BytesIO()
    zout = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
    gloss = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:glossaryDocument xmlns:w="{W}" '
             f'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:docParts>'
             + part("Volume cover", "Covers", "coverPg", "VOLUME TITLE", "11111111-1111-1111-1111-111111111111", "Heading1")
             + part("CUI header", "Headers", "hdrs", "CUI//SP-PROPIN", "22222222-2222-2222-2222-222222222222", "QPCallout")
             + part("Table caption", "Captions", "docParts", "Table 1. Caption", "33333333-3333-3333-3333-333333333333")
             + "</w:docParts></w:glossaryDocument>")
    for i in zin.infolist():
        b = zin.read(i.filename)
        if i.filename == "[Content_Types].xml":
            b = b.replace(b"</Types>", b'<Override PartName="/word/glossary/document.xml" ContentType="application/vnd.openxmlformats-'
                          b'officedocument.wordprocessingml.document.glossary+xml"/></Types>')
        if i.filename == "word/_rels/document.xml.rels":
            b = b.replace(b"</Relationships>", b'<Relationship Id="rIdGL1" Type="http://schemas.openxmlformats.org/officeDocument/'
                          b'2006/relationships/glossaryDocument" Target="glossary/document.xml"/></Relationships>')
        if i.filename == "[Content_Types].xml":
            b = b.replace(b"</Types>", b'<Override PartName="/word/glossary/styles.xml" ContentType="application/vnd.openxmlformats-'
                          b'officedocument.wordprocessingml.styles+xml"/></Types>')
        zout.writestr(i, b)
    zout.writestr("word/glossary/document.xml", gloss)
    zout.writestr("word/glossary/styles.xml", GSTYLES)
    zout.writestr("word/glossary/_rels/document.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships '
                  'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://'
                  'schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    zout.close()
    open(dst, "wb").write(out.getvalue())


