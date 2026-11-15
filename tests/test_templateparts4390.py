"""4.39.0 (ST27 of 2026-11-14, step 4): a template seen whole. Five rows, one per component: styles, Quick Parts, page
layout, numbering, starting pages; each says where it comes from, what it holds and whether it fits; one line says
whether the template is ready to make. Fictional files."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import namedtemplates as NT, partlib as PT, partstyles as PS, stylelib as SL, templatelib as TL, templateparts as TP, templatesets as TS
from _qpfixture import with_glossary

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
lib = TL.Library(cfg)
t = NT.new(cfg, "Technical Volume")
rows = TP.rows(cfg, t, lib)
check("five components, in order, each with the page that changes it", [(r["key"], r["name"], r["step"]) for r in rows] == list(TP.PARTS), rows)
check("nothing picked: each row says so plainly, and nothing is wrong", rows[0]["from"].startswith("No style set picked") and rows[1]["from"] == "No Quick Part set picked"
      and rows[4]["from"] == "No starting pages picked" and all(r["state"] == "ok" for r in rows), rows)
check("page layout and numbering come from the standards, the same for every template", rows[2]["from"] == TP.SHARED and rows[3]["from"] == TP.SHARED
      and rows[2]["holds"].startswith("Letter, 1 in margins") and "page numbers by part: Cover" in rows[2]["holds"]
      and rows[3]["holds"].startswith("Headings not numbered") and "captions: Table, Figure" in rows[3]["holds"], (rows[2], rows[3]))
check("ready, with nothing wrong", TP.ready(rows) == (True, "Ready to make. The five components fit each other."))
gl = os.path.join(tmp, "Master.docx")
with_glossary(os.path.join(os.path.dirname(HERE), "test_samples", "Kestrel_Technical_Volume.docx"), gl)
plan = PT.look(gl, lib, work=os.path.join(tmp, "w"))
for x in plan["pages"]:
    x["keep"] = False
_d, items = PT.keep(cfg, lib, plan)
h1 = lib.add("style", "Heading 1", {"font": "Arial", "size": 14}, source="test")[0]
rfp = SL.new_set(lib, "RFP", kind="style"); SL.add_to_set(lib, rfp["id"], [h1["id"]])
ps = SL.new_set(lib, "RFP parts", kind="part")
PT.add_to_set(cfg, lib, ps["id"], ["q:" + i["id"] for i in items])
PS.set_goes_with(lib, ps["id"], rfp["id"])
NT.set_recipe(cfg, t["id"], {"style_sets": [rfp["id"]], "part_set": ps["id"]})
t = NT.get(cfg, t["id"])
rows = TP.rows(cfg, t, lib)
check("the styles row names its set and counts its styles", rows[0]["from"] == "Style set: RFP" and rows[0]["holds"] == "1 style" and rows[0]["state"] == "ok", rows[0])
check("the Quick Parts row names its set, the style set it goes with and its count", rows[1]["from"] == "Quick Part set: RFP parts (goes with RFP)"
      and rows[1]["holds"] == "3 Quick Parts", rows[1])
check("... and says which style a Quick Part uses that the template lacks", rows[1]["state"] == "warn" and "QP Callout (CUI header)" in rows[1]["says"], rows[1])
ok, said = TP.ready(rows)
check("not ready: the line names the component and why", not ok and said.startswith("Look before you make it. Quick Parts: 1 style the Quick Parts use is not in the style sets"), said)
qc = lib.add("style", "QP Callout", {"font": "Arial", "size": 10}, source="test")[0]
SL.add_to_set(lib, rfp["id"], [qc["id"]])
rows = TP.rows(cfg, t, lib)
check("with the style in the set the components fit", rows[1]["state"] == "ok" and rows[1]["says"] == "Every style they use is here" and TP.ready(rows)[0], rows[1])
by = TS.checks_by_part(NT.std_of(cfg, t), lib, cfg)
check("the checks by component hold every check once", sum(len(v) for v in by.values()) == len(TS.checks(NT.std_of(cfg, t), lib, cfg)) and by["quick"] and by["styles"], by)
shutil.rmtree(tmp, ignore_errors=True)
print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
