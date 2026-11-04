"""3.45.0 Document sections: a section's contents (response elements, Quick Parts, placeholders) at its start in the
template Make templates writes, once (a second run leaves them alone), kept in the setup written on the template
(front matter and appendices are written again); a section's own page setup (a cover with half-inch margins) is
checked and fixed by Fix a Copy; a section design carries its contents. Fictional content (the Kestrel set)."""
import os, re, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("SK_DATA_DIR", tempfile.mkdtemp())
import app_gui as A
import prodrules as PRL, prodtemplate as PT, sectioncontents as SC, partdesigns as PD
from prodengine.engine.pkg import Package
from prodengine.pe import sections as S

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def doc_xml(path):
    return zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")


std = PRL.for_effort(tempfile.mkdtemp())
std["variables"]["marking"] = "Kestrel restriction"
SC.set_items(std, "front", [{"kind": "element", "id": "acr", "title": "Acronyms and Abbreviations"}])
SC.set_items(std, "body", [{"kind": "placeholder", "title": "Executive Summary", "pages": 2},
                           {"kind": "quickpart", "name": "Kestrel Mission Overview"}, {"kind": "bogus"}])
check("the contents are kept clean (an unknown item is dropped)", [r["kind"] for r in SC.items(std, "body")] == ["placeholder", "quickpart"])
check("a kept page holds none", SC.render(std, "cover") == "" and "cover" in SC.NO_CONTENTS)
check("each item reads in plain words", SC.label(SC.items(std, "body")[0]) == "Executive Summary (2 pages for authors)"
      and SC.label(SC.items(std, "body")[1]) == "Kestrel Mission Overview (Quick Part)")
job = PT.make(std, tempfile.mkdtemp(), "")
steps = {s.get("key"): s for s in job.steps}
check("Make templates puts in each section's contents", steps.get("section_contents", {}).get("changed")
      and set(steps["section_contents"]["report"]["placed"]) == {"front", "body"}, steps.get("section_contents"))
x = doc_xml(job.copy)
check("the response starts with the placeholder and the Quick Part, before its first heading",
      x.index("Executive Summary") < x.index('AUTOTEXT "Kestrel Mission Overview"') < x.index("Chapter title"), "")
check("the front matter starts with the acronym list", "Acronyms and Abbreviations" in x and x.count("SK_Section_front") == 1)
check("each section's contents are bookmarked once", x.count('w:name="SK_Section_body"') == 1)
before = x
r = SC.op_section_contents(Package(job.copy), PRL.engine_ready(PT.standard_for_template(std)))
check("a second run finds them and leaves them alone", r["placed"] == [], r)
check("the template's check has no new findings from them", not [f for f in job.check.findings if f.get("rule") in ("RU7", "P1", "P2")],
      [f.get("what") for f in job.check.findings][:5])

# the setup written on the template keeps them
import compliance as C, setupdoc as SD, setuptemplate as ST
RFP = os.path.join(os.path.dirname(HERE), "test_samples", "rfp_walk")
d = tempfile.mkdtemp()
files = sorted(f for f in os.listdir(RFP) if f.lower().endswith((".pdf", ".docx")))
heads = []
M = C.Matrix(os.path.join(d, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = C.extract([(f, A.typed_chunks(os.path.join(RFP, f))) for f in files], heads)
M.headings = heads
M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal Design\n1.2 Risk Management")
for it in M.items:
    it["decision"] = "Keep" if it["suggest"] != "Drop" else "Drop"
SD.place(M, next(it for it in M.items if it["decision"] == "Keep")["id"], "1.1 Thermal Design")
cfg = os.path.join(d, "config"); os.makedirs(cfg)
data = PRL.load(cfg)
SC.set_items(data["company"], "body", [{"kind": "placeholder", "title": "Executive Summary", "pages": 1}])
SC.set_items(data["company"], "front", [{"kind": "element", "id": "lof", "title": "List of Figures"}])
PRL.save(cfg, data)
out = ST.make_all(M, os.path.join(d, "exports"), cfg, effort_name="Kestrel")
sx = doc_xml(out[0]["setup"])
check("the setup on the template keeps the response's contents, before the structure's headings",
      "Executive Summary" in sx and sx.index("Executive Summary") < sx.index("Thermal Design"), sx.count("Executive Summary"))
check("... and the front matter's", "List of Figures" in sx and sx.count('w:name="SK_Section_front"') == 1)
check("for_setup gives the front matter and appendices only", set(SC.for_setup(PRL.load(cfg)["company"])) == {"front"})

# a section's own page setup
std2 = PRL.for_effort(tempfile.mkdtemp())
std2["page_setups"]["cover_half"] = {"name": "Cover, half-inch margins", "w": 8.5, "h": 11, "orient": "portrait",
                                     "top": 0.5, "bottom": 0.5, "left": 0.5, "right": 0.5, "header": 0.3, "footer": 0.3}
PD.part_of(std2, "cover")["setup"] = "cover_half"
job2 = PT.make(std2, tempfile.mkdtemp(), "")
pkg2 = Package(job2.copy)
sm = S.map_sections(pkg2, PRL.engine_ready(PT.standard_for_template(std2)))
cov = next(s for s in sm.sections if s.part == "cover")
body = next(s for s in sm.sections if s.part == "body")
check("the cover follows its own page setup; the response keeps the portrait one", abs(cov.margins["left"] - 0.5) < 0.01
      and abs(body.margins["left"] - 1.0) < 0.01, (cov.margins, body.margins))
check("a section's page setup applies only while its orientation matches", S.setup_key(cov, std2) == "cover_half"
      and S.setup_key(type("X", (), {"part": "cover", "orient": "landscape", "paper": "Letter"})(), std2) == "landscape")

# a section design carries its contents
w = PRL.for_effort(tempfile.mkdtemp())
SC.set_items(w, "body", [{"kind": "placeholder", "title": "Past Performance", "pages": 3}])
des = PD.design_of(w, "body")
w2 = PRL.for_effort(tempfile.mkdtemp())
PD.apply_design(w2, des, "appendix")
check("a section design carries its contents to the section it is used on", SC.items(w2, "appendix") == [{"kind": "placeholder",
      "title": "Past Performance", "pages": 3}] and des.get("contents"))

n = sum(checks)
print(f"SECTION CONTENTS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
