"""3.97.0 Make templates picks sets (templatesets): a profile names its style sets in order (the lower one wins where two
hold a style), the Setup style set (hidden), a part set for the gallery and the pages the document starts with. The
standard the template is made from takes the sets' values; the made template carries each style as Word wrote it,
the starting pages before the body, each in its own Word section and also in the Quick Parts gallery, and the part set's
Quick Parts. The checks say what is missing. Fictional files (the Kestrel set)."""
import os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import partlib as PT
import prodrules as PRL
import prodtemplate as PTM
import sectiondesigns as SDZ
import stylelib as SL
import templatelib as TL
import templatesets as TS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def sty(sid, name, extra=""):
    return f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{sid}"><w:name w:val="{name}"/><w:basedOn w:val="Normal"/>{extra}</w:style>'


def make(path, body, styles):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="xml" ContentType="application/xml"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                   '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rIdS" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr("word/document.xml", f'<w:document {WNS}><w:body>{body}<w:sectPr><w:pgSz w:w="12240" w:h="15840"/></w:sectPr></w:body></w:document>')
        z.writestr("word/styles.xml", f'<w:styles {WNS}><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>{styles}</w:styles>')
    return path


def p(t, sid=""):
    return (f'<w:p><w:pPr><w:pStyle w:val="{sid}"/></w:pPr>' if sid else "<w:p>") + f'<w:r><w:t>{t}</w:t></w:r></w:p>'


# the libraries: two style sets, a Setup set, a part set with a cover and a CUI page
lib = TL.Library(cfg)
src1 = make(os.path.join(tmp, "Kestrel RFP Styles.dotx"), p("x"),
            sty("KBody", "Kestrel Body", '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="22"/></w:rPr>')
            + sty("KCallout", "Kestrel Callout", '<w:rPr><w:color w:val="2E74B5"/><w:sz w:val="20"/></w:rPr>'))
src2 = make(os.path.join(tmp, "Kestrel Compact Styles.dotx"), p("x"),
            sty("KBody", "Kestrel Body", '<w:pPr><w:spacing w:after="40"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial Narrow" w:hAnsi="Arial Narrow"/><w:sz w:val="20"/></w:rPr>'))
src3 = make(os.path.join(tmp, "Kestrel Setup Styles.dotx"), p("x"),
            sty("SKGuidance", "SK Guidance", '<w:rPr><w:color w:val="C00000"/></w:rPr>'))
rfp, compact, setup = (SL.new_set(lib, n) for n in ("RFP volume", "Page-limited RFP", "Setup"))
for src, k in ((src1, rfp), (src2, compact), (src3, setup)):
    rows = SL.against(lib, SL.read_styles(src))
    for r in rows:
        r["keep"] = r["name"].startswith(("Kestrel", "SK"))
    SL.bring_in(lib, rows, src, set_of={r["name"]: k["id"] for r in rows})
lib = TL.Library(cfg)
front = make(os.path.join(tmp, "Kestrel Front.docx"), p("Kestrel Ground Segment", "KCover") + '<w:p><w:pPr><w:sectPr/></w:pPr></w:p>'
             + p("CONTROLLED UNCLASSIFIED INFORMATION", "KCover"), sty("KCover", "Kestrel Cover Title"))
plan = PT.look(front, lib, work=os.path.join(tmp, "work"))
designs, _q = PT.keep(cfg, lib, plan)
cover, cui = designs
parts = SL.new_set(lib, "Kestrel parts", kind="part")
PT.add_to_set(cfg, lib, parts["id"], ["d:" + cover["id"], "d:" + cui["id"]])

std = PRL.engine_ready(PRL.resolved_type(PRL.load(cfg), PRL.load(cfg)["default"]))
std["_parts_dir"] = os.path.join(cfg, "production_parts")
check("no sets: the standard is unchanged", TS.apply(std) is std and not TS.used(std))
TS.set_recipe(std, style_sets=[rfp["id"], compact["id"]], setup_set=setup["id"], part_set=parts["id"],
              starts=[{"kind": "cover", "part": cover["id"], "gallery": True}, {"kind": "cui", "part": cui["id"], "gallery": False}])
chosen, wins = TS.styles(lib, TS.recipe(std))
check("style sets in order: the lower one wins", chosen["Kestrel Body"]["id"] != chosen["Kestrel Callout"]["id"]
      and lib.values(chosen["Kestrel Body"]).get("font") == "Arial Narrow" and wins == [("Kestrel Body", "Page-limited RFP", "RFP volume")], wins)
out = TS.apply(std, lib, cfg)
check("the standard takes the sets' values", out["style_defs"]["Kestrel Body"]["font"] == "Arial Narrow"
      and out["style_defs"]["Kestrel Callout"]["color"].upper().endswith("2E74B5"), out["style_defs"].get("Kestrel Callout"))
check("... the Setup styles hidden", out["style_defs"]["SK Guidance"].get("hidden") is True and "<w:vanish/>" in out["_exact_styles"]["SK Guidance"])
check("... Word's own definitions kept for the maker", "Arial Narrow" in out["_exact_styles"]["Kestrel Body"])
check("... the starting pages, in order", [k for k, _p, _g, _n in out["_starts"]] == ["cover", "cui"]
      and all(os.path.isfile(p_) for _k, p_, _g, _n in out["_starts"]))
check("... the profile's own cover is not used with starting pages", "cover" not in (out.get("page_parts") or {}))
check("the checks: styles, starting pages", [st for st, _w, _m in TS.checks(std, lib, cfg)] == ["ok", "ok", "ok", "ok", "ok"]
      or all(st == "ok" for st, _w, _m in TS.checks(std, lib, cfg)), TS.checks(std, lib, cfg))
# make the template
job = PTM.make(std, os.path.join(tmp, "out"), parts_dir=std["_parts_dir"])
with zipfile.ZipFile(job.copy) as z:
    styles_xml = z.read("word/styles.xml").decode("utf-8")
    doc = z.read("word/document.xml").decode("utf-8")
    gloss = z.read("word/glossary/document.xml").decode("utf-8") if "word/glossary/document.xml" in z.namelist() else ""
check("the template carries each style as Word wrote it", "Arial Narrow" in styles_xml and 'w:after="40"' in styles_xml
      and "<w:vanish/>" in styles_xml.split("SK Guidance")[1][:600], [s["step"] for s in job.steps][-6:])
check("the document starts with the cover, then the CUI page, before the body", doc.index("Kestrel Ground Segment")
      < doc.index("CONTROLLED UNCLASSIFIED") < doc.index("Chapter title"))
check("... no Stationkeeper cover or contents before them", "[Volume name]" not in doc and "PEVolumeName" not in doc)
check("... each page in its own Word section", doc[:doc.index("Chapter title")].count("<w:sectPr") >= 2)
check("the cover is also in the Quick Parts gallery; the CUI page is not (its switch is off)", "Kestrel Front cover" in gloss
      and "Kestrel Front marking page" not in gloss, gloss[:300])
check("a step says so in the report", any(s.get("key") == "starts" and s["changed"] for s in job.steps)
      and any(s.get("key") == "exact_styles" and s["changed"] for s in job.steps))
shutil.rmtree(tmp, ignore_errors=True)
print(f"SETS 397 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
