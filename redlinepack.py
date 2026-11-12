"""4.22.0: the parts Prepare for redline's Word copy needs beyond its text: the pictures (word/media), the headers and
footers, and the relationships and content types that name them. The copy is written by docxw first; add() opens it
and puts these in. Rules only (No AI)."""
import re, zipfile

REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
R = f'xmlns:r="{REL}"'


def _rels(items):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(f'<Relationship Id="{rid}" Type="{REL}/{kind}" Target="{target}"/>' for rid, kind, target in items)
            + "</Relationships>")


def add(path, media=(), parts=()):
    """media: [(rid, "pictureN.png", bytes, owner)] where owner is "document" or a part's file name ("header1.xml");
    parts: [(rid, "header"|"footer", "header1.xml", body xml)]. Rewrites the .docx at path."""
    if not media and not parts:
        return
    with zipfile.ZipFile(path) as z:
        data = {n: z.read(n) for n in z.namelist()}
    ct = data["[Content_Types].xml"].decode("utf-8")
    if media and 'Extension="png"' not in ct:
        ct = ct.replace("<Default ", '<Default Extension="png" ContentType="image/png"/><Default ', 1)
    rels = data["word/_rels/document.xml.rels"].decode("utf-8")
    new = [(rid, "image", f"media/{name}") for rid, name, _b, owner in media if owner == "document"]
    for rid, kind, name, xml in parts:
        tag = "hdr" if kind == "header" else "ftr"
        data[f"word/{name}"] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:{tag} {W} {R}>{xml}</w:{tag}>').encode("utf-8")
        new.append((rid, kind, name))
        ct = ct.replace("</Types>", f'<Override PartName="/word/{name}" ContentType="application/vnd.openxmlformats-officedocument.'
                                    f'wordprocessingml.{kind}+xml"/></Types>')
        own = [(r2, "image", f"media/{n2}") for r2, n2, _b, owner in media if owner == name]
        if own:
            data[f"word/_rels/{name}.rels"] = _rels(own).encode("utf-8")
    rels = rels.replace("</Relationships>", "".join(
        f'<Relationship Id="{rid}" Type="{REL}/{kind}" Target="{target}"/>' for rid, kind, target in new) + "</Relationships>")
    data["word/_rels/document.xml.rels"] = rels.encode("utf-8")
    data["[Content_Types].xml"] = ct.encode("utf-8")
    for _rid, name, blob, _owner in media:
        data[f"word/media/{name}"] = blob
    order = ["[Content_Types].xml"] + [n for n in data if n != "[Content_Types].xml"]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n in order:
            z.writestr(n, data[n])


def pictures(path):
    """How many pictures a .docx holds (word/media)."""
    try:
        with zipfile.ZipFile(path) as z:
            return sum(1 for n in z.namelist() if re.match(r"word/media/.+\.(png|jpe?g|gif|emf|wmf|bmp|tiff?)$", n, re.I))
    except (OSError, zipfile.BadZipFile):
        return 0
