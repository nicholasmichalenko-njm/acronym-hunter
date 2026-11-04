"""Quick Parts made here (3.42.0): a small Word file whose glossary holds the Quick Parts given, each with its gallery
(Quick Parts, Headers, Footers, Cover Pages), category, words, fields and pictures. The standards keep it beside their
other Quick Part sources, and Make templates copies the entries into every template the same way as Quick Parts picked
from a file (prodquickparts.op_quick_parts); Word's check of the template (Word on this PC) puts each one in and
confirms it. Written as plain Word XML; nothing leaves the PC."""
import base64, hashlib, os, re, uuid, zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_MAIN = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
CT_GLOSS = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.glossary+xml"
CT_STYLES = "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"
STYLES = (f'<w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr><w:sz w:val="20"/></w:rPr></w:rPrDefault></w:docDefaults>'
          '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>')


def _inner(xml):
    """The body of a header or footer part (its paragraphs and tables), without the hdr/ftr wrapper."""
    m = re.search(r"<w:(?:hdr|ftr)\b[^>]*>(.*)</w:(?:hdr|ftr)>", xml or "", re.S)
    return m.group(1) if m else (xml or "")


def make_source(folder, entries, label="quick part"):
    """Write the Word file holding entries ([{"name", "category", "gallery", "xml", "media"}]) into folder, named by its
    content (the same parts are kept once). Returns its path."""
    os.makedirs(folder, exist_ok=True)
    parts, rels, media_files = [], [f'<Relationship Id="rIdSt" Type="{R}/styles" Target="styles.xml"/>'], []
    n_img = 0
    for e in entries:
        body = _inner(e.get("xml", ""))
        for m in e.get("media") or []:
            n_img += 1
            new_rid = f"rIdQp{n_img}"
            ext = (m.get("name") or "x.png").rsplit(".", 1)[-1].lower()
            mname = f"media/qp{n_img}.{ext}"
            media_files.append((f"word/{mname}", base64.b64decode(m["b64"]), m.get("ct") or f"image/{ext}"))
            rels.append(f'<Relationship Id="{new_rid}" Type="{R}/image" Target="../{mname}"/>')
            body = re.sub(rf'(r:(?:embed|id|link)=")({re.escape(m["rid"])})(")', rf"\g<1>{new_rid}\g<3>", body)
        if not body.rstrip().endswith("</w:p>") and not body.rstrip().endswith("<w:p/>"):
            body += "<w:p/>"
        guid = "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, "sk-qp:" + e["name"] + (e.get("category") or ""))).upper() + "}"
        parts.append(f'<w:docPart><w:docPartPr><w:name w:val="{_esc(e["name"])}"/><w:category><w:name w:val="{_esc(e.get("category") or "General")}"/>'
                     f'<w:gallery w:val="{e.get("gallery") or "docParts"}"/></w:category><w:types><w:type w:val="bbPlcHdr"/></w:types>'
                     f'<w:behaviors><w:behavior w:val="content"/></w:behaviors><w:guid w:val="{guid}"/></w:docPartPr>'
                     f'<w:docPartBody>{body}</w:docPartBody></w:docPart>')
    ns = (f'xmlns:w="{W}" xmlns:r="{R}" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
          'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
    gloss = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:glossaryDocument {ns}><w:docParts>{"".join(parts)}</w:docParts></w:glossaryDocument>'
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body><w:p/></w:body></w:document>'
    exts = sorted({p.rsplit(".", 1)[-1] for p, _b, _c in media_files})
    defaults = "".join(f'<Default Extension="{x}" ContentType="{next(c for p, _b, c in media_files if p.endswith("." + x))}"/>' for x in exts)
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          f'<Default Extension="xml" ContentType="application/xml"/>{defaults}'
          f'<Override PartName="/word/document.xml" ContentType="{CT_MAIN}"/><Override PartName="/word/styles.xml" ContentType="{CT_STYLES}"/>'
          f'<Override PartName="/word/glossary/document.xml" ContentType="{CT_GLOSS}"/>'
          f'<Override PartName="/word/glossary/styles.xml" ContentType="{CT_STYLES}"/></Types>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 f'<Relationship Id="rId1" Type="{R}/officeDocument" Target="word/document.xml"/></Relationships>')
    doc_rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'<Relationship Id="rIdS" Type="{R}/styles" Target="styles.xml"/>'
                f'<Relationship Id="rIdG" Type="{R}/glossaryDocument" Target="glossary/document.xml"/></Relationships>')
    gloss_rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                  + "".join(rels) + "</Relationships>")
    files = [("[Content_Types].xml", ct), ("_rels/.rels", root_rels), ("word/document.xml", doc), ("word/styles.xml", STYLES),
             ("word/_rels/document.xml.rels", doc_rels), ("word/glossary/document.xml", gloss), ("word/glossary/styles.xml", STYLES),
             ("word/glossary/_rels/document.xml.rels", gloss_rels)]
    h = hashlib.sha256("".join(c for _n, c in files).encode("utf-8") + b"".join(b for _p, b, _c in media_files)).hexdigest()[:12]
    safe = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_") or "quick_part"
    path = os.path.join(folder, f"qp_{safe}-{h}.docx")
    if not os.path.exists(path):
        with zipfile.ZipFile(path + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
            for n, c in files:
                z.writestr(n, c)
            for p, b, _c in media_files:
                z.writestr(p, b)
        os.replace(path + ".tmp", path)
    return path


def _esc(s):
    return str(s).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
