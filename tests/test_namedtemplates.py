"""4.28.2: a template as its own named thing (namedtemplates). New, rename, what goes in, its state, the file made,
and an effort's pick for a volume kept as that volume's template file. Fictional names."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import namedtemplates as NT
import stylelib as SL
import templatelib as TL
import templatereg as TR

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
check("none yet", NT.every(cfg) == [])
a = NT.new(cfg, "Page-limited RFP: Volume I")
check("a new template has the name you gave it (characters a file cannot hold taken out)", a and a["name"] == "Page-limited RFP Volume I", a)
check("the same name twice is refused, whatever its capitals", NT.new(cfg, "page-limited rfp volume i") is None and NT.new(cfg, "  ") is None)
b = NT.new(cfg, "Program plan")
check("two templates, by name", [t["name"] for t in NT.every(cfg)] == ["Page-limited RFP Volume I", "Program plan"])
check("rename: a free name is taken, a used one is not", NT.rename(cfg, b["id"], "Program management plan") and not NT.rename(cfg, b["id"], "Page-limited RFP Volume I")
      and NT.get(cfg, b["id"])["name"] == "Program management plan")
lib = TL.Library(cfg)
it, _st = SL.new_style(lib, "Body Text", "paragraph", {"font": "Arial", "size": 11})
it2, _st = SL.new_style(lib, "Heading 1", "paragraph", {"font": "Arial", "size": 16, "bold": True})
k = SL.new_set(lib, "RFP volume"); SL.add_to_set(lib, k["id"], [it["id"], it2["id"]])
check("nothing picked: it says so", NT.words(cfg, NT.get(cfg, a["id"])).startswith("Nothing picked yet"))
r = NT.set_recipe(cfg, a["id"], {"style_sets": [k["id"]]})
check("what goes in is kept with the template", r["style_sets"] == [k["id"]] and NT.get(cfg, a["id"])["sets"]["style_sets"] == [k["id"]])
check("... and said in a line", NT.words(cfg, NT.get(cfg, a["id"])) == "Styles: RFP volume", NT.words(cfg, NT.get(cfg, a["id"])))
check("not made yet", NT.state(cfg, NT.get(cfg, a["id"]))[0] == NT.NEW)
out = os.path.join(tmp, "Templates")
job = NT.make(cfg, out, a["id"])
t = NT.get(cfg, a["id"])
check("made: a .dotx in Templates\\Named, named for the template", os.path.isfile(job.copy) and job.copy.lower().endswith(".dotx")
      and os.path.dirname(job.copy) == NT.folder(out) and "Page-limited RFP Volume I" in os.path.basename(job.copy), job.copy)
check("... version 1, in the list of templates made", t["made"]["version"] == 1 and (TR.latest(cfg, t["name"]) or {}).get("v") == 1)
check("... Ready", NT.state(cfg, t)[0] == NT.READY, NT.state(cfg, t))
import zipfile
with zipfile.ZipFile(job.copy) as z:
    sx = z.read("word/styles.xml").decode("utf-8", "replace")
check("the picked set's styles are in the file", "Body Text" in sx and "Heading 1" in sx)
it3, _st = SL.new_style(TL.Library(cfg), "Caption", "paragraph", {"font": "Arial", "size": 9})
lib = TL.Library(cfg); SL.add_to_set(lib, k["id"], [it3["id"]])
check("a style added to a picked set: Needs review", NT.state(cfg, NT.get(cfg, a["id"]))[0] == NT.REVIEW, NT.state(cfg, NT.get(cfg, a["id"])))
job2 = NT.make(cfg, out, a["id"])
check("made again: version 2, Ready", NT.get(cfg, a["id"])["made"]["version"] == 2 and NT.state(cfg, NT.get(cfg, a["id"]))[0] == NT.READY)
NT.rename(cfg, a["id"], "Page-limited RFP Volume 1"); j = NT.make(cfg, out, a["id"])
check("renamed and made again: the version goes on counting", NT.get(cfg, a["id"])["made"]["version"] == 3)
NT.rename(cfg, a["id"], "Page-limited RFP Volume I"); job2 = NT.make(cfg, out, a["id"])
os.remove(job2.copy)
check("its file gone: Not made yet, and it says why", NT.state(cfg, NT.get(cfg, a["id"])) == (NT.NEW, "Its file is gone from the folder: make it again"))
job3 = NT.make(cfg, out, a["id"])


# ---- an effort's pick, with a stand-in for the effort's settings and matrix
class WS:
    def __init__(self):
        self.d = {}

    def get(self, k):
        return self.d.get(k)

    def set(self, k, v):
        self.d[k] = v


import compliance as C
import templatesetup as TS
M = C.Matrix(os.path.join(tmp, "m.xlsx")) if hasattr(C, "Matrix") else None
ws = WS()
if M is not None:
    got = NT.pick(M, ws, cfg, "Volume I Technical", a["id"])
    check("an effort picks it for a volume", got == {"id": a["id"], "name": "Page-limited RFP Volume I", "v": 5} and NT.picks(ws)["Volume I Technical"]["v"] == 5, got)
    fv = TS.for_volume(M, "Volume I Technical")
    check("... kept as that volume's template file, so the setup is written on it", fv is not None and os.path.samefile(fv[0], job3.copy), fv)
    check("... another volume has none", TS.for_volume(M, "Volume II Management") is None)
    check("a template not made yet cannot be picked", NT.pick(M, ws, cfg, "Volume II Management", b["id"]) is None)
    NT.make(cfg, out, a["id"])
    check("made again since: the effort is told", NT.newer(cfg, ws) == [("Volume I Technical", "Page-limited RFP Volume I", 5, 6)], NT.newer(cfg, ws))
    check("the volume goes back to the effort's own formatting", NT.unpick(M, ws, "Volume I Technical") and TS.for_volume(M, "Volume I Technical") is None
          and NT.picks(ws) == {})
else:
    check("a matrix to pick on", False)
check("removed: off the list, its file stays", NT.remove(cfg, a["id"]) and NT.get(cfg, a["id"]) is None and os.path.isfile(job3.copy))
n = sum(checks)
print(f"NAMED TEMPLATES {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
