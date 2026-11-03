"""3.22.0 Quick Parts in a standard: a file's Quick Parts are read without writing it (templates, macro templates as
XML, documents); a copy of the source is kept with the standards once; Make a template copies the chosen entries in with
their text, puts every one in the Quick Parts gallery under the standard's category, leaves out the ones not chosen,
reports a source that is gone, and the template still passes its own check."""
import hashlib, io, os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodparts as PP
import prodquickparts as QP
import prodrules as PRL
import prodtemplate as PT

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MASTER = os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx")


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


tmp = tempfile.mkdtemp()
src = os.path.join(tmp, "Team Master.dotx")
with_glossary(MASTER, src)
before = hashlib.sha256(open(src, "rb").read()).hexdigest()
found = QP.read(src)
check("a file's Quick Parts are read: name, category, gallery and text", [(e["name"], e["category"], e["gallery"]) for e in found]
      == [("Volume cover", "Covers", "coverPg"), ("CUI header", "Headers", "hdrs"), ("Table caption", "Captions", "docParts")]
      and found[1]["text"] == "CUI//SP-PROPIN", found)
check("... without writing the file", hashlib.sha256(open(src, "rb").read()).hexdigest() == before)
check("a file with none has none", QP.read(MASTER) == [])
cfg = os.path.join(tmp, "config")
k1 = QP.keep_source(cfg, src)
k2 = QP.keep_source(cfg, src)
check("a copy of the source is kept with the standards, once", k1 == k2 and k1.startswith("qp_Team_Master_") and k1.endswith(".dotx")
      and os.path.isfile(os.path.join(PP.parts_dir(cfg), k1)) and len(os.listdir(PP.parts_dir(cfg))) == 1)
check("the standards carry a Quick Parts list, in one gallery by default", PRL.for_effort(tempfile.mkdtemp())["quick_parts"] == {"one_gallery": True, "entries": []})

std = PRL.for_effort(tempfile.mkdtemp())
std["_parts_dir"] = PP.parts_dir(cfg)
std["quick_parts"] = {"one_gallery": True, "entries": [
    {"name": "Volume cover", "category": "01 Covers", "source": k1}, {"name": "CUI header", "category": "04 Headers", "source": k1},
    {"name": "Gone part", "category": "09 Other", "source": "qp_missing.dotx"}]}
out = os.path.join(tmp, "Production Copies", "Templates")
tj = PT.make(std, out)
step = next((s for s in tj.steps if s.get("key") == "quick_parts"), {})
got = [(e["name"], e["category"], e["gallery"]) for e in QP.read(tj.copy)]
check("Make a template puts the chosen Quick Parts in, each in the Quick Parts gallery under its category",
      sorted(got) == [("CUI header", "04 Headers", "docParts"), ("Volume cover", "01 Covers", "docParts")], (got, step))
check("... with their text, and the one not chosen left out", any(e["text"] == "VOLUME TITLE" for e in QP.read(tj.copy))
      and not any(e["name"] == "Table caption" for e in QP.read(tj.copy)))
check("a source that is gone is reported, not guessed", step.get("report", {}).get("missing") == ["Gone part"], step)
check("the template still passes its own check", tj.check.count() == 0 and not tj.check.error, [f["what"][:80] for f in tj.check.findings])
from prodengine.engine.pkg import Package
from prodengine.engine.ops import word_ops as WO
pk = Package(tj.copy)
mroot = WO.styles_root(pk)
gpart = next(t for (ty, t, m) in pk.rels_of("word/glossary/document.xml").values() if ty.endswith("/styles"))
groot = pk.tree(gpart)
h_main, h_gl = WO.find_style(mroot, "Heading 1"), WO.find_style(groot, "Heading 1")
check("STYLES DRIVE THE QUICK PARTS: a part's style takes the template's own definition, not the one it came with",
      h_gl is not None and WO.effective(groot, h_gl, "size") == WO.effective(mroot, h_main, "size") != 28.0,
      (WO.effective(groot, h_gl, "size"), WO.effective(mroot, h_main, "size")))
check("a style the template lacks comes in with its part and is reported", WO.find_style(mroot, "QP Callout") is not None
      and step["report"].get("styles_added") == ["QP Callout"], step["report"])
std["quick_parts"]["one_gallery"] = False
tj2 = PT.make(std, out)
check("off: each keeps its own gallery", sorted((e["name"], e["gallery"]) for e in QP.read(tj2.copy)) == [("CUI header", "hdrs"), ("Volume cover", "coverPg")])

# ---------------------------------------------------------------- hidden text styles
std3 = PRL.for_effort(tempfile.mkdtemp())
std3["style_defs"]["SK RFP Reference"] = {"type": "paragraph", "based_on": "Normal", "color": "7030A0", "hidden": True}
tj3 = PT.make(std3, out)
r3 = WO.styles_root(Package(tj3.copy)); s3 = WO.find_style(r3, "SK RFP Reference")
import prodlearn as PL
back = PL.learn(tj3.copy, std3).layer(["styles"])["style_defs"]["SK RFP Reference"]
check("a hidden text style (Show/Hide) is written with its color, and learned back", s3 is not None and WO.effective(r3, s3, "hidden") is True
      and WO.effective(r3, s3, "color") == "7030A0" and back.get("hidden") is True and tj3.check.count() == 0)

print(f"QUICK PARTS {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
