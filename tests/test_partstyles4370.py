"""4.37.0 (ST27 of 2026-11-14, step 1): the styles a Quick Part uses. Read from the part's kept file by name, as Word
shows them; a part with no style of its own; the library's names; a template's check names the styles its Quick Parts
use that its style sets lack, and passes once they are there. Fictional files."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import partlib as PT, partstyles as PS, stylelib as SL, templatelib as TL, templatesets as TS
from _qpfixture import with_glossary

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
src = os.path.join(os.path.dirname(HERE), "test_samples", "Kestrel_Technical_Volume.docx")
gl = os.path.join(tmp, "Master.docx")
with_glossary(src, gl, table_hdr=True)
by = PS.of_file(gl)
check("a file's Quick Parts, each with the styles it uses, by name as Word shows it", by.get(PS.key("Volume cover", "Covers")) == ["Heading 1"]
      and by.get(PS.key("CUI header", "Headers")) == ["QP Callout"], by)
check("a part written in no style of its own uses none", by.get(PS.key("Table caption", "Captions")) == [] and by.get(PS.key("Table header", "Headers")) == [])
check("a file with no gallery, or none at all: nothing", PS.of_file(src) == {} and PS.of_file(os.path.join(tmp, "no.docx")) == {})
check("the read is remembered", PS.of_file(gl) is by)
lib = TL.Library(cfg)
plan = PT.look(gl, lib, work=os.path.join(tmp, "w"))
for x in plan["pages"]:
    x["keep"] = False
_d, items = PT.keep(cfg, lib, plan)
it = {lib.base_of(i): i for i in items}
check("one Quick Part of the library", PS.of_item(lib, it["Volume cover"]) == ["Heading 1"] and PS.of_item(lib, it["CUI header"]) == ["QP Callout"]
      and PS.of_item(lib, it["Table caption"]) == [], [PS.of_item(lib, i) for i in items])
check("none of them is among this PC's styles yet", PS.state(lib, it["CUI header"], PS.library_names(lib)) == [("QP Callout", False)])
h1 = lib.add("style", "Heading 1", {"font": "Arial", "size": 14}, source="test")[0]
check("a style the library holds is found whatever its case", PS.state(lib, it["Volume cover"], PS.library_names(lib)) == [("Heading 1", True)])
# a template: a style set and a part set
ss = SL.new_set(lib, "RFP", kind="style"); SL.add_to_set(lib, ss["id"], [h1["id"]])
ps = SL.new_set(lib, "RFP parts", kind="part")
PT.add_to_set(cfg, lib, ps["id"], ["q:" + i["id"] for i in items])
std = {}
TS.set_recipe(std, style_sets=[ss["id"]], part_set=ps["id"])
rows = TS.checks(std, lib, cfg)
row = next((r for r in rows if "Quick Parts use" in r[1]), None)
check("the template's check names the style its Quick Parts use that the style sets lack", row is not None and row[0] == "warn"
      and row[1] == "1 style the Quick Parts use is not in the style sets" and "QP Callout (CUI header)" in row[2]
      and "from the Quick Parts' own file" in row[2], row)
qc = lib.add("style", "QP Callout", {"font": "Arial", "size": 10}, source="test")[0]
SL.add_to_set(lib, ss["id"], [qc["id"]])
row = next((r for r in TS.checks(std, lib, cfg) if "Quick Parts use" in r[1]), None)
check("with the style in the set the check passes", row == ("ok", "Every style the Quick Parts use is in the style sets", "Paragraph, character and table styles"), row)
check("the words for several", PS.words([("A", ["x", "y"]), ("B", ["z"])], limit=2) == "x (A), y (A) and 1 more")
shutil.rmtree(tmp, ignore_errors=True)
print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
