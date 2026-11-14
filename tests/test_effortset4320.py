"""4.32.0, Standards step 3 (decisions ST3 and ST4 of 2026-11-14): an effort's own set of standards. Taken from the
Global Standards on the PC once, independent after; a change with the effort open changes the effort's set only; a
later Global change is offered with what it would change, and taken by choice. One fictional PC, two efforts."""
import json, os, sys, tempfile, threading
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import effortset as ES, formats as F, globalstd as GS, prodrules as PRL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "Stationkeeper Data", "config"); os.makedirs(cfg)
A, B = os.path.join(tmp, "Effort A", "work"), os.path.join(tmp, "Effort B", "work")


def font(where=None):
    return PRL.load(where or cfg)["company"]["variables"]["body_font"]


def set_font(name):
    d = PRL.load(cfg); d["company"]["variables"]["body_font"] = name; PRL.save(cfg, d)


set_font("Global One")
with open(os.path.join(cfg, "acronym_note.txt"), "w") as f:
    f.write("the PC's own")
check("with no effort open the config folder is in use", ES.base(cfg) == cfg and ES.active() == "")

d = ES.enter(cfg, A)
check("the effort is given its set the first time it opens", ES.has(A) and os.path.isfile(os.path.join(ES.set_dir(A), "production_standards.json")), d)
check("its info is in the saved format", d["format"] == F.number("effort standards") == ES.FORMAT and "production_standards.json" in d["files"])
check("the set is the one in use", ES.base(cfg) == ES.set_dir(A) and font() == "Global One")
set_font("Effort A Font")
check("a change with the effort open changes the effort's set", font() == "Effort A Font")
with ES.as_global():
    check("and not the Global Standards", font() == "Global One" and ES.base(cfg) == cfg)
check("the file in the config folder is untouched", "Effort A Font" not in open(os.path.join(cfg, "production_standards.json")).read())
fp = GS.fingerprint(cfg)
seen = []
t = threading.Thread(target=lambda: seen.append(ES.base(cfg))); 
with ES.as_global():
    t.start(); t.join()
check("as_global holds for its own thread only", seen == [ES.set_dir(A)], seen)
check("another config folder is never redirected", ES.base(os.path.join(tmp, "other")) == os.path.join(tmp, "other"))
check("the effort's change is named", ES.changed(cfg, A) == ["production_standards.json"], ES.changed(cfg, A))
check("the line says so", "its own set" in ES.line(cfg, A) and "changed 1 file" in ES.line(cfg, A), ES.line(cfg, A))

ES.leave()
check("closed: the config folder again, with the Global value", ES.base(cfg) == cfg and font() == "Global One")
ES.enter(cfg, B)
check("a second effort takes the Global value, not the first effort's", font() == "Global One")
ES.leave(); ES.enter(cfg, A)
check("the first effort opens with its own value again", font() == "Effort A Font")
ES.leave()

check("nothing is offered while the Global Standards are as the set took them", ES.offer(cfg, B)["rows"] == [])
set_font("Global Two")
of = ES.offer(cfg, B)
check("a Global change is offered to the effort with what it would change",
      [(r["what"], r["old"], r["new"]) for r in of["rows"]] == [("company.variables.body_font", "Global One", "Global Two")], of["rows"])
check("the row names its part", of["rows"][0]["part"].startswith("Production Standards"), of["rows"])
check("an effort that did not change the file is not warned", of["also_here"] == [])
ofa = ES.offer(cfg, A)
check("an effort that changed it too is told", ofa["also_here"] == ["production_standards.json"] and ofa["rows"][0]["old"] == "Effort A Font", ofa)
ES.enter(cfg, B)
check("offered is not taken", font() == "Global One")
check("taking is by choice", ES.take(cfg, B) == 1 and font() == "Global Two")
check("then nothing more is offered", ES.offer(cfg, B)["rows"] == [] and ES.changed(cfg, B) == [])
ES.leave()
check("the other effort keeps its own until it takes it", ES.enter(cfg, A) and font() == "Effort A Font")
check("naming no offered file takes nothing", ES.take(cfg, A, files=["rules.json"]) == 0 and font() == "Effort A Font")
ES.leave()

check("the effort's change did not move the Global Standards' fingerprint", GS.fingerprint(cfg) != fp)   # Global Two since
with open(os.path.join(cfg, "outline_layouts.json"), "w") as f:
    f.write("{}")
rows = ES.offer(cfg, A)["rows"]
check("a file the Global Standards gained later is offered as added",
      any(r["file"] == "outline_layouts.json" and r["new"] == "added" for r in rows), rows)
ES.enter(cfg, A)
check("the effort's change is given to the Global Standards only when asked", ES.give(cfg, A, files=["production_standards.json"]) == 1)
with ES.as_global():
    check("it is in the config folder, as a change waiting", font() == "Effort A Font")
check("the effort is then as the Global Standards: nothing changed, nothing offered for that file",
      "production_standards.json" not in ES.changed(cfg, A) and "production_standards.json" not in ES.offer(cfg, A)["files"])
ES.leave()
check("and the other effort is offered it", any(r["new"] == "Effort A Font" for r in ES.offer(cfg, B)["rows"]), ES.offer(cfg, B)["rows"])
check("a set folder that cannot be made leaves the config folder in use",
      ES.enter(cfg, os.path.join(cfg, "production_standards.json", "x")) == {} and ES.base(cfg) == cfg)
check("the PC's other files never enter a set", not os.path.exists(os.path.join(ES.set_dir(A), "acronym_note.txt")))

print(f"TEST EFFORTSET4320 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
