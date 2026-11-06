"""3.72.0 test fixture: a fictional team template: the app's own template with a glossary added (a cover page Quick
Part and a front matter Quick Part with a picture). Fictional content (Kestrel)."""
import io, zipfile

import templatefile as TF

W = TF.W
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000" "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


def add_glossary(src, dst):
    """The app's template with a glossary: a cover page Quick Part and a front matter Quick Part with a picture."""
    zin = zipfile.ZipFile(src)
    out = io.BytesIO()
    pic = ('<w:r><w:drawing><wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
           '<wp:extent cx="9525" cy="9525"/><wp:docPr id="1" name="Seal"/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
           '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
           '<pic:nvPicPr><pic:cNvPr id="1" name="seal.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdG1"/></pic:blipFill>'
           '<pic:spPr/></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')
    gloss = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:glossaryDocument xmlns:w="{W}" xmlns:r="{TF.R}"><w:docParts>'
             '<w:docPart><w:docPartPr><w:name w:val="Kestrel Cover"/><w:category><w:name w:val="General"/><w:gallery w:val="coverPg"/></w:category>'
             '<w:guid w:val="{00000000-0000-0000-0000-000000000001}"/></w:docPartPr><w:docPartBody><w:p><w:r><w:t>KESTREL GROUND SEGMENT PROPOSAL</w:t></w:r></w:p>'
             '<w:sectPr/></w:docPartBody></w:docPart>'
             '<w:docPart><w:docPartPr><w:name w:val="Kestrel Front Matter"/><w:category><w:name w:val="General"/><w:gallery w:val="docParts"/></w:category>'
             '<w:guid w:val="{00000000-0000-0000-0000-000000000002}"/></w:docPartPr><w:docPartBody><w:p><w:r><w:t>Proprietary notice for Kestrel</w:t></w:r>'
             f'{pic}</w:p></w:docPartBody></w:docPart></w:docParts></w:glossaryDocument>')
    grels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rIdG1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/sk_seal.png"/></Relationships>')
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for i in zin.infolist():
            b = zin.read(i)
            if i.filename == "[Content_Types].xml":
                b = b.decode().replace("</Types>", '<Override PartName="/word/glossary/document.xml" ContentType="application/vnd.openxmlformats-'
                                       'officedocument.wordprocessingml.document.glossary+xml"/>'
                                       + ('<Default Extension="png" ContentType="image/png"/>' if 'Extension="png"' not in b.decode() else "")
                                       + "</Types>").encode()
            if i.filename == "word/_rels/document.xml.rels":
                b = b.decode().replace("</Relationships>", '<Relationship Id="rIdGloss" Type="http://schemas.openxmlformats.org/officeDocument/'
                                       '2006/relationships/glossaryDocument" Target="glossary/document.xml"/></Relationships>').encode()
            z.writestr(i, b)
        z.writestr("word/glossary/document.xml", gloss)
        z.writestr("word/glossary/_rels/document.xml.rels", grels)
        z.writestr("word/media/sk_seal.png", PNG)
    with open(dst, "wb") as f:
        f.write(out.getvalue())
    return dst


def team_template(M, folder, cfg, dst):
    """The app's own template for M's first volume, with the glossary: the path of the copy."""
    import setuptemplate as ST
    made = ST.make_all(M, folder, cfg, effort_name="Kestrel", record=False)
    return add_glossary(made[0]["template"], dst)
