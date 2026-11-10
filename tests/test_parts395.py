"""3.95.0: the Parts library's rules (partlib): a file read once for its pages (one per Word section, each guessed as a
cover, a CUI page, a title page, contents, acronyms...) and its Quick Parts gallery; the ticked ones kept (pages as whole
Word files on their shelves, Quick Parts in the library); one row per part with its versions; a Word file brought back as
a new version (the first stays; what fills it carries over); a version named; part sets holding one version of each
part. Fictional files (the Kestrel set)."""
import os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import partlib as PT
import sectiondesigns as SDZ
import stylelib as SL
import templatelib as TL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
STY = (f'<w:styles {WNS}><w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
       '<w:style w:type="paragraph" w:styleId="AACoverTitle"><w:name w:val="AA Cover Title"/></w:style></w:styles>')
SECT = '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/></w:sectPr>'


def p(t, sid="", sect=""):
    st = '<w:pStyle w:val="%s"/>' % sid if sid else ""
    ps = f'<w:pPr>{st}{sect}</w:pPr>' if (sid or sect) else ""
    return f'<w:p>{ps}<w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>'


def make(path, body):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", f'<w:document {WNS}><w:body>{body}<w:sectPr/></w:body></w:document>')
        z.writestr("word/styles.xml", STY)
        z.writestr("word/settings.xml", f'<w:settings {WNS}/>')
    return path


front = make(os.path.join(tmp, "Kestrel Front Matter.docx"),
             p("Kestrel Ground Segment", "AACoverTitle") + p("Volume Name Here", "", SECT)
             + p("CONTROLLED UNCLASSIFIED INFORMATION") + p("Handle per the marking on each page.", "", SECT)
             + p("Acronyms and Abbreviations", "AACoverTitle") + p("XXX  Sample meaning"))
lib = TL.Library(cfg)
plan = PT.look(front, lib, work=os.path.join(tmp, "work"))
kinds = [x["kind"] for x in plan["pages"]]
check("a file's pages, one per Word section, each guessed", kinds == ["cover", "cui", "acronyms"], kinds)
check("... named for the file and what it is", plan["pages"][0]["name"] == "Kestrel Front Matter cover", plan["pages"][0]["name"])
check("a file with no gallery: no Quick Parts", plan["gallery"] == [])
check("guessing: contents, units, a title page after the first", PT.guess("Table of Contents 1.1 ...", 2) == "toc"
      and PT.guess("Units and Symbols", 3) == "units" and PT.guess("Volume II Technical", 2) == "title")
plan["pages"][2]["keep"] = False
designs, items = PT.keep(cfg, lib, plan)
check("the ticked pages go onto their shelves as whole Word files", [d["shelf"] for d in designs] == ["cover", "cui"]
      and all(os.path.isfile(SDZ.path_of(cfg, d)) for d in designs))
rows = PT.rows(cfg, "covers")
check("one row per part, by kind", len(rows) == 1 and rows[0]["shown"] == "d:" + designs[0]["id"] and PT.rows(cfg, "marking")
      and PT.count(cfg, "front") == 0)
# a new version
cover2 = make(os.path.join(tmp, "Kestrel Cover v2.docx"), p("Kestrel Ground Segment", "AACoverTitle") + p("CUI") + p("Volume Name Here"))
SDZ.set_map(cfg, designs[0]["id"], {"1": "volume_name"})
v2 = PT.new_version(cfg, designs[0]["id"], cover2, label="CUI")
rows = PT.rows(cfg, "covers")
check("brought back as a new version: still one row, two versions, the newest shown", len(rows) == 1
      and rows[0]["versions"] == ["d:" + designs[0]["id"], "d:" + v2["id"]] and rows[0]["shown"] == "d:" + v2["id"])
check("... the first version stays as it was", SDZ.get(cfg, designs[0]["id"]) is not None and PT.version(SDZ.get(cfg, designs[0]["id"])) == 1
      and PT.version(v2) == 2)
check("... what fills it carries over", v2["map"].get("1") == "volume_name" or v2["map"].get("2") == "volume_name", v2["map"])
check("the shown name says the version and its name", PT.shown_name(cfg, v2) == "Kestrel Front Matter cover v2: CUI", PT.shown_name(cfg, v2))
check("a version can be picked to show", PT.rows(cfg, "covers", shown={rows[0]["family"]: "d:" + designs[0]["id"]})[0]["shown"]
      == "d:" + designs[0]["id"])
check("Name this version", PT.set_label(cfg, designs[0]["id"], "plain") and SDZ.get(cfg, designs[0]["id"])["label"] == "plain")
# Quick Parts from a gallery
from _qpfixture import with_glossary
src = os.path.join(os.path.dirname(HERE), "test_samples", "Kestrel_Technical_Volume.docx")
gl = os.path.join(tmp, "Kestrel Master.docx")
with_glossary(src, gl)
plan2 = PT.look(gl, lib, work=os.path.join(tmp, "work2"))
names = [e["name"] for e in plan2["gallery"]]
check("a file's Quick Parts gallery is read", names == ["Volume cover", "CUI header", "Table caption"], names)
for x in plan2["pages"]:
    x["keep"] = False
_d, items = PT.keep(cfg, lib, plan2)
check("the ticked Quick Parts go into the library", len(items) == 3 and all(i["kind"] == "quickpart" for i in items))
q = PT.rows(cfg, "quick", lib)
check("Quick Parts are a kind too, one row each (3.98.0: the CUI header under Headers and footers)", len(q) == 2
      and all(r["shown"].startswith("q:") for r in q) and len(PT.rows(cfg, "hf", lib)) == 1)
check("met again: Already have it", all(e["state"] == "same" and not e["keep"] for e in PT.look(gl, lib, work=os.path.join(tmp, "w3"))["gallery"]))
# part sets
ps = SL.new_set(lib, "Page-limited RFP", kind="part")
check("a part set is its own kind of set", ps["kind"] == "part" and SL.sets(lib, "part") == [ps] and SL.sets(lib, "style") == [])
PT.add_to_set(cfg, lib, ps["id"], ["d:" + designs[0]["id"], "q:" + items[0]["id"]])
gone = PT.add_to_set(cfg, lib, ps["id"], ["d:" + v2["id"]])
check("a part set holds one version of each part", gone == ["d:" + designs[0]["id"]] and "d:" + v2["id"] in ps["items"]
      and "q:" + items[0]["id"] in ps["items"])
check("the sets a version is in", [k["name"] for k in PT.sets_of(lib, "d:" + v2["id"])] == ["Page-limited RFP"])
shutil.rmtree(tmp, ignore_errors=True)
print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
