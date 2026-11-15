"""4.42.0 (ST29 of 2026-11-14, way A): page layouts and numbering as named components a template picks. One is taken
from standards that exist; a page layout's paper and margins change; a template's pick is written over its standard and
changes what it is made from; a volume's standards and its template's pick are compared in words. Fictional names."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import pagelayouts as PGL, namedtemplates as NT, prodrules as PRL, templateparts as TP, templatesets as TS, formats as F

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
data = PRL.load(cfg)
check("none to begin with", PGL.every(cfg, "layout") == [] and PGL.every(cfg, "numbering") == [])
srcs = PGL.sources(cfg)
check("sources: the Global Standards first, then each profile", srcs[0][0] == "Global Standards"
      and all(any(s == f"Effort Profile: {t['name']}" for s, _ in srcs) for t in data["types"]), [s for s, _ in srcs])
lay = PGL.new(cfg, "layout", "  Letter,  1 in ", data["company"])
check("a page layout taken from the Global Standards", lay and lay["name"] == "Letter, 1 in"
      and lay["values"]["variables"] == {"paper": "Letter", "margin_top": 1.0, "margin_bottom": 1.0, "margin_left": 1.0, "margin_right": 1.0}
      and "page_setups" in lay["values"] and "body_font" not in lay["values"]["variables"], lay)
check("... said in words", PGL.words("layout", lay["values"]) == "Letter, 1 in margins; header and footer at 0.5 in", PGL.words("layout", lay["values"]))
check("a name is used once in its kind, and may be used in the other", PGL.new(cfg, "layout", "letter, 1 IN", data["company"]) is None
      and PGL.new(cfg, "layout", " ", data["company"]) is None and PGL.new(cfg, "numbering", "Letter, 1 in", data["company"]) is not None)
num = PGL.every(cfg, "numbering")[0]
check("a numbering holds heading numbering, page numbers and captions, and no margins", set(num["values"]) == {"heading_numbering", "pagination", "captions"})
check("... said in words", PGL.words("numbering", num["values"]).startswith("Headings not numbered; page numbers by part: ")
      and "captions: Table, Figure" in PGL.words("numbering", num["values"]), PGL.words("numbering", num["values"]))
tight = PGL.new(cfg, "layout", "Letter, 0.75 in", data["company"])
got = PGL.set_page(cfg, tight["id"], "Letter", [0.75, 0.75, 0.75, 0.75])
check("a page layout's margins change", got and PGL.get(cfg, "layout", tight["id"])["values"]["variables"]["margin_left"] == 0.75
      and PGL.words("layout", got["values"]).startswith("Letter, 0.75 in margins"))
check("a margin out of range or an unknown paper is refused", PGL.set_page(cfg, tight["id"], None, [0.75, 0.75, 9, 0.75]) is None
      and PGL.set_page(cfg, tight["id"], "Postcard") is None and PGL.set_page(cfg, tight["id"], None, [1, 1]) is None
      and PGL.get(cfg, "layout", tight["id"])["values"]["variables"]["margin_left"] == 0.75)
check("rename: a free name only", PGL.rename(cfg, "layout", tight["id"], "Letter, tight") and not PGL.rename(cfg, "layout", tight["id"], "Letter, 1 in")
      and PGL.get(cfg, "layout", tight["id"])["name"] == "Letter, tight")
import json
check("the file carries its format number", json.load(open(os.path.join(cfg, PGL.FILE), encoding="utf-8"))["format"] == F.number("named layouts") == PGL.FORMAT)

# ---------------------------------------------------------------- a template picks them
t = NT.new(cfg, "Page-limited RFP, Technical")
fp0 = NT.fingerprint(cfg, NT.get(cfg, t["id"]))
check("no pick: the standards', as before", NT.std_of(cfg, NT.get(cfg, t["id"]))["variables"]["margin_left"] == 1.0
      and TS.recipe({})["layout"] == "" and TS.recipe({})["numbering"] == "")
rows = TP.rows(cfg, NT.get(cfg, t["id"]))
check("... and its rows say so", rows[2]["from"] == TP.SHARED == PGL.SHARED and rows[3]["from"] == TP.SHARED and rows[2]["holds"].startswith("Letter, 1 in margins")
      and rows[2]["step"] == rows[3]["step"] == "layouts", rows[2:4])
NT.set_recipe(cfg, t["id"], {"layout": tight["id"], "numbering": num["id"]})
tt = NT.get(cfg, t["id"])
std = NT.std_of(cfg, tt)
check("a pick is kept and written over the template's standard", tt["sets"]["layout"] == tight["id"] and std["variables"]["margin_left"] == 0.75
      and std["variables"]["body_font"] == data["company"]["variables"]["body_font"])
check("... and it changes what the template is made from", NT.fingerprint(cfg, tt) != fp0)
rows = TP.rows(cfg, tt)
check("the rows name the picks", rows[2]["from"] == "Page layout: Letter, tight" and rows[2]["holds"].startswith("Letter, 0.75 in margins")
      and rows[3]["from"] == "Numbering: Letter, 1 in" and rows[2]["state"] == rows[3]["state"] == "ok" and TP.ready(rows)[0], rows[2:4])
check("picked by: the template's name", PGL.used_by(cfg, "layout", tight["id"]) == ["Page-limited RFP, Technical"] and PGL.used_by(cfg, "layout", lay["id"]) == [])
check("a picked one is not removed; a free one is", not PGL.remove(cfg, "layout", tight["id"]) and PGL.remove(cfg, "layout", lay["id"])
      and [x["name"] for x in PGL.every(cfg, "layout")] == ["Letter, tight"])
fp1 = NT.fingerprint(cfg, tt)
PGL.set_page(cfg, tight["id"], None, [0.5, 0.5, 0.75, 0.75])
check("changing a picked layout changes what the template is made from", NT.fingerprint(cfg, NT.get(cfg, t["id"])) != fp1)

# ---------------------------------------------------------------- one answer per volume
ws = {"prod_std": {"effort_type": "rfp_limited"}}
vstd = PGL.volume_std(cfg, ws, "Technical Volume")
check("a volume's standards: its profile as its effort type sees it", vstd["variables"]["margin_left"] == 1.0)
what = PGL.disagree(cfg, ws, "Technical Volume", NT.get(cfg, t["id"]))
check("the template and the volume differ on margins, and on nothing else", len(what) == 1 and what[0].startswith("margins (margins 0.5 in top, 0.5 in bottom, 0.75 in left, 0.75 in right in the template, 1 in margins in the volume's standards)"), what)
said = PGL.disagree_words("Technical Volume", "Page-limited RFP, Technical", what)
check("... said in a sentence", said.startswith("Technical Volume: Page-limited RFP, Technical and this volume's standards differ on margins") and "The checks read the volume's standards" in said)
ws2 = {"prod_std": {"effort_type": "rfp_limited", "over": {"variables": {"margin_top": 0.5, "margin_bottom": 0.5, "margin_left": 0.75, "margin_right": 0.75}}}}
check("the effort's own values count: now they agree", PGL.disagree(cfg, ws2, "Technical Volume", NT.get(cfg, t["id"])) == [] and PGL.disagree_words("V", "T", []) == "")
t2 = NT.new(cfg, "Plain")
check("a template with no pick is never said to differ", PGL.disagree(cfg, ws, "Technical Volume", NT.get(cfg, t2["id"])) == [])
d = PGL.load(cfg); del d["layout"][tight["id"]]; PGL.save(cfg, d)
rows = TP.rows(cfg, NT.get(cfg, t["id"]))
check("a pick that is gone: the standards' values, and the row says to pick another", NT.std_of(cfg, NT.get(cfg, t["id"]))["variables"]["margin_left"] == 1.0
      and rows[2]["state"] == "warn" and "gone" in rows[2]["says"] and not TP.ready(rows)[0], rows[2])
shutil.rmtree(tmp, ignore_errors=True)
print(f"PAGELAYOUTS 4420 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
