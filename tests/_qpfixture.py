"""Test helper (3.22.0): a template with Quick Parts in three galleries and a styles part of its own."""
import io, zipfile
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def part(name, cat, gallery, text, guid, style=""):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return (f'<w:docPart><w:docPartPr><w:name w:val="{name}"/><w:category><w:name w:val="{cat}"/><w:gallery w:val="{gallery}"/>'
            f'</w:category><w:behaviors><w:behavior w:val="content"/></w:behaviors><w:guid w:val="{{{guid}}}"/></w:docPartPr>'
            f'<w:docPartBody><w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p></w:docPartBody></w:docPart>')


FOLDOUT = ('<w:docPart><w:docPartPr><w:name w:val="Tabloid foldout"/><w:category><w:name w:val="Pages"/><w:gallery w:val="docParts"/>'
           '</w:category><w:behaviors><w:behavior w:val="pg"/></w:behaviors><w:guid w:val="{44444444-4444-4444-4444-444444444444}"/>'
           '</w:docPartPr><w:docPartBody><w:p><w:r><w:t>Foldout</w:t></w:r></w:p><w:p><w:pPr><w:sectPr>'
           '<w:headerReference w:type="default" r:id="rIdH9"/><w:pgSz w:w="24480" w:h="15840" w:orient="landscape"/>'
           '<w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720" w:header="360" w:footer="360" w:gutter="0"/>'
           '</w:sectPr></w:pPr></w:p></w:docPartBody></w:docPart>')


NUMBERED = ('<w:docPart><w:docPartPr><w:name w:val="Numbered steps"/><w:category><w:name w:val="Lists"/><w:gallery w:val="docParts"/>'
            '</w:category><w:behaviors><w:behavior w:val="p"/></w:behaviors><w:guid w:val="{55555555-5555-5555-5555-555555555555}"/>'
            '</w:docPartPr><w:docPartBody><w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="5"/></w:numPr></w:pPr>'
            '<w:r><w:t>First step</w:t></w:r></w:p></w:docPartBody></w:docPart>')


GSTYLES = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}">'
           '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:rPr><w:sz w:val="56"/></w:rPr></w:style>'
           '<w:style w:type="paragraph" w:customStyle="1" w:styleId="QPCallout"><w:name w:val="QP Callout"/><w:basedOn w:val="Normal"/>'
           '<w:rPr><w:color w:val="1F5FAD"/></w:rPr></w:style></w:styles>')


def with_glossary(src, dst, foldout=False, numbered=False):
    """A template with three Quick Parts in three galleries (what a team template holds)."""
    zin = zipfile.ZipFile(src)
    out = io.BytesIO()
    zout = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
    gloss = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:glossaryDocument xmlns:w="{W}" '
             f'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:docParts>'
             + part("Volume cover", "Covers", "coverPg", "VOLUME TITLE", "11111111-1111-1111-1111-111111111111", "Heading1")
             + part("CUI header", "Headers", "hdrs", "CUI//SP-PROPIN", "22222222-2222-2222-2222-222222222222", "QPCallout")
             + part("Table caption", "Captions", "docParts", "Table 1. Caption", "33333333-3333-3333-3333-333333333333")
             + (FOLDOUT if foldout else "") + (NUMBERED if numbered else "") + "</w:docParts></w:glossaryDocument>")
    for i in zin.infolist():
        b = zin.read(i.filename)
        if i.filename == "[Content_Types].xml":
            b = b.replace(b"</Types>", b'<Override PartName="/word/glossary/document.xml" ContentType="application/vnd.openxmlformats-'
                          b'officedocument.wordprocessingml.document.glossary+xml"/></Types>')
        if i.filename == "word/_rels/document.xml.rels":
            b = b.replace(b"</Relationships>", b'<Relationship Id="rIdGL1" Type="http://schemas.openxmlformats.org/officeDocument/'
                          b'2006/relationships/glossaryDocument" Target="glossary/document.xml"/></Relationships>')
        if i.filename == "[Content_Types].xml" and numbered:
            b = b.replace(b"</Types>", b'<Override PartName="/word/glossary/numbering.xml" ContentType="application/vnd.openxmlformats-'
                          b'officedocument.wordprocessingml.numbering+xml"/></Types>')
        if i.filename == "[Content_Types].xml" and foldout:
            b = b.replace(b"</Types>", b'<Override PartName="/word/glossary/header9.xml" ContentType="application/vnd.openxmlformats-'
                          b'officedocument.wordprocessingml.header+xml"/></Types>')
        if i.filename == "[Content_Types].xml":
            b = b.replace(b"</Types>", b'<Override PartName="/word/glossary/styles.xml" ContentType="application/vnd.openxmlformats-'
                          b'officedocument.wordprocessingml.styles+xml"/></Types>')
        zout.writestr(i, b)
    zout.writestr("word/glossary/document.xml", gloss)
    zout.writestr("word/glossary/styles.xml", GSTYLES)
    if numbered:
        zout.writestr("word/glossary/numbering.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering xmlns:w="{W}">'
                      '<w:abstractNum w:abstractNumId="3"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
                      '<w:lvlText w:val="Step %1."/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>'
                      '<w:num w:numId="5"><w:abstractNumId w:val="3"/></w:num></w:numbering>')
    if foldout:
        zout.writestr("word/glossary/header9.xml", f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="{W}">'
                      '<w:p><w:r><w:t>FOLDOUT HEADER</w:t></w:r></w:p></w:hdr>')
    zout.writestr("word/glossary/_rels/document.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships '
                  'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://'
                  'schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                  + ('<Relationship Id="rIdH9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" '
                     'Target="header9.xml"/>' if foldout else "")
                  + ('<Relationship Id="rIdN5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" '
                     'Target="numbering.xml"/>' if numbered else "") + '</Relationships>')
    zout.close()
    open(dst, "wb").write(out.getvalue())


