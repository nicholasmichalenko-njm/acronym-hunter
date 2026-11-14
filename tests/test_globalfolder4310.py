"""4.31.0, step 2a of the Standards board (2026-11-14): the Global Standards folder. A few people update it, every PC
reads it: numbered versions written whole and never edited, taken only when every file matches, with the changes
waiting on a PC listed against the version in use. Two fictional PCs and one folder."""
import json, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "A", "Stationkeeper Data")
import globalfolder as GF, globalstd as GS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


def put(cfg, rel, text):
    p = os.path.join(cfg, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def get(cfg, rel):
    with open(os.path.join(cfg, rel), encoding="utf-8") as f:
        return f.read()


A = os.path.join(tmp, "A", "Stationkeeper Data", "config"); os.makedirs(A)
B = os.path.join(tmp, "B", "Stationkeeper Data", "config"); os.makedirs(B)
F = os.path.join(tmp, "Shared", "Global Standards")
check("a folder that is not there cannot be updated, and holds no version", not GF.can_update(F) and GF.current(F) is None and GF.versions(F) == [])
os.makedirs(F)
check("a folder this PC can write to can be updated; the test leaves nothing behind", GF.can_update(F) and os.listdir(F) == [])
put(A, "production_standards.json", json.dumps({"fonts": {"body": {"size": 11}}, "levels": [{"name": "Heading 1", "size": 14}]}))
put(A, "banned_words.csv", "word\nsynergy\n")
put(A, os.path.join("production_parts", "cover.docx"), "cover one")
rows = GF.waiting(A, F)
check("with no version yet, everything this PC holds is waiting as added", rows and all(r["new"] == "added" for r in rows), rows)
man = GF.update(A, F, by="Avery", note="First version")
check("the first update writes version 1 and names it the one in use", man["version"] == 1 and GF.versions(F) == [1]
      and GF.current(F)["version"] == 1 and json.load(open(os.path.join(F, "current.json")))["by"] == "Avery")
check("the version holds every file under its member name, with a manifest", os.path.isfile(os.path.join(F, "v0001", "config", "production_standards.json"))
      and os.path.isfile(os.path.join(F, "v0001", "config", "production_parts", "cover.docx")) and "config/banned_words.csv" in man["files"])
check("the PC that updated is on that version, with nothing waiting", GS.state(A)["version"] == 1 and GS.state(A)["source"] == GS.PUBLISHED
      and GF.waiting(A, F) == [] and "updated from this PC" in GS.line(A), GS.line(A))
check("no writing folder is left behind", not [n for n in os.listdir(F) if n.endswith(".writing")], os.listdir(F))

# another PC, with its own changes, takes the version
put(B, "production_standards.json", json.dumps({"fonts": {"body": {"size": 10}}}))
put(B, "banned_words.csv", "word\nsynergy\n")
put(B, os.path.join("production_parts", "old.docx"), "an old cover")
r = GF.ready(B, F)
check("a PC on no version is told version 1 is ready", r and r["version"] == 1 and r["note"] == "First version")
got = GF.take(B, F)
check("taking it puts every file of the version on the PC", json.loads(get(B, "production_standards.json"))["fonts"]["body"]["size"] == 11
      and get(B, os.path.join("production_parts", "cover.docx")) == "cover one")
check("what the PC had that differed is replaced, named, and kept in a dated backup", got["version"] == 1 and any("Production Standards" in x for x in got["replaced"])
      and os.path.isfile(os.path.join(got["backup"], "config", "production_standards.json"))
      and json.load(open(os.path.join(got["backup"], "config", "production_standards.json")))["fonts"]["body"]["size"] == 10, got)
check("a file the version does not have leaves the PC and is in the backup", not os.path.exists(os.path.join(B, "production_parts", "old.docx"))
      and os.path.isfile(os.path.join(got["backup"], "config", "production_parts", "old.docx")))
check("a file that was already the same is not backed up", not os.path.exists(os.path.join(got["backup"], "config", "banned_words.csv")))
check("that PC is on version 1 from the linked folder, nothing waiting, nothing ready", GS.state(B)["version"] == 1 and GS.state(B)["source"] == GS.LINKED
      and GF.waiting(B, F) == [] and GF.ready(B, F) is None)

# changes waiting, value by value
put(A, "production_standards.json", json.dumps({"fonts": {"body": {"size": 12}}, "levels": [{"name": "Heading 1", "size": 16}]}))
put(A, "banned_words.csv", "word\nsynergy\nleverage\n")
os.remove(os.path.join(A, "production_parts", "cover.docx"))
put(A, os.path.join("production_parts", "title.docx"), "title")
rows = GF.waiting(A, F)
by = {r["what"]: r for r in rows}
check("a changed value is one row: what, the version's value, this PC's value", by.get("fonts.body.size", {}).get("old") == "11"
      and by["fonts.body.size"]["new"] == "12" and by.get("levels.Heading 1.size", {}).get("new") == "16", rows)
check("a file that is not values is one row: changed, added or removed", by["banned_words.csv"]["new"] == "changed"
      and by["production_parts/title.docx"]["new"] == "added" and by["production_parts/cover.docx"]["new"] == "removed", rows)
check("the other PC has nothing waiting: the changes are on the PC that made them", GF.waiting(B, F) == [])
check("the status line names the parts with changes waiting", "Changes waiting on this PC" in GS.line(A), GS.line(A))
man2 = GF.update(A, F, by="Avery", note="Body 12 pt")
check("the next update is version 2; version 1 stays beside it, untouched", man2["version"] == 2 and GF.versions(F) == [1, 2]
      and GF.read(F, 1) is not None and json.load(open(os.path.join(F, "v0001", "config", "production_standards.json")))["fonts"]["body"]["size"] == 11)
check("the other PC is told version 2 is ready, with its note and who", (GF.ready(B, F) or {}).get("note") == "Body 12 pt" and GF.ready(B, F)["by"] == "Avery")

# a half-synced version is never read
v3 = os.path.join(F, "v0003"); shutil.copytree(os.path.join(F, "v0002"), v3)
m3 = json.load(open(os.path.join(v3, "manifest.json"))); m3["version"] = 3
json.dump(m3, open(os.path.join(v3, "manifest.json"), "w"))
os.remove(os.path.join(v3, "config", "banned_words.csv"))
json.dump({"format": 1, "version": 3}, open(os.path.join(F, "current.json"), "w"))
check("a version with a file missing is not sound", GF.read(F, 3) is None and GF.versions(F) == [1, 2, 3])
check("the folder's version in use falls back to the newest sound one", GF.current(F)["version"] == 2 and GF.ready(B, F)["version"] == 2)
try:
    GF.take(B, F, 3); refused = False
except ValueError:
    refused = True
check("taking the unsound version is refused and the PC stays as it is", refused and GS.state(B)["version"] == 1
      and json.loads(get(B, "production_standards.json"))["fonts"]["body"]["size"] == 11)
with open(os.path.join(v3, "config", "banned_words.csv"), "w") as f:
    f.write("tampered")
check("a version with a file that does not match its checksum is not sound", GF.read(F, 3) is None)
got = GF.take(B, F)
check("the PC takes version 2; with no changes of its own nothing is replaced and no backup is made", got == {"version": 2, "replaced": [], "backup": ""}
      and json.loads(get(B, "production_standards.json"))["fonts"]["body"]["size"] == 12 and not os.path.exists(os.path.join(B, "production_parts", "cover.docx")), got)
put(B, "banned_words.csv", "word\nmine\n")
json.dump({"format": 1, "version": 1}, open(os.path.join(F, "current.json"), "w"))
got = GF.take(B, F, 1)
check("going to another version backs up only what the PC itself changed", got["replaced"] == ["Banned and avoided phrases"]
      and os.listdir(os.path.join(got["backup"], "config")) == ["banned_words.csv"], (got, os.listdir(os.path.join(got["backup"], "config"))))
man4 = GF.update(A, F, by="Avery", note="again")
check("an update never reuses a number, even one an unsound version holds", man4["version"] == 4)
n = sum(checks)
print(f"GLOBAL FOLDER 4310 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
