"""4.33.0, step 2b of the Standards board (2026-11-14): a version as one file and the notice of what a version changed.
An update writes the version's file beside its folder; a PC with no link installs it, checked whole first; whenever a
version is put on a PC, each change is kept with who updated and when, until Mark as seen. Three fictional PCs."""
import json, os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "A", "Stationkeeper Data")
import formats as F, globalfile as GX, globalfolder as GF, globalstd as GS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


def put(cfg, rel, text):
    p = os.path.join(cfg, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def get(cfg, rel):
    with open(os.path.join(cfg, rel), encoding="utf-8") as f:
        return f.read()


A, B, C = (os.path.join(tmp, x, "Stationkeeper Data", "config") for x in "ABC")
FOLDER = os.path.join(tmp, "Shared", "Global Standards"); os.makedirs(FOLDER)
for cfg in (A, B, C):
    os.makedirs(cfg)
put(A, "rules.json", json.dumps({"rules": {"RU1": {"on": True}}}))
put(A, "doc_types.json", json.dumps({"types": [{"name": "RFP", "initial": "RFP"}]}))
GF.update(A, FOLDER, by="Ada", note="The first set")
f1 = os.path.join(FOLDER, GX.file_name(1))
check("an update writes the version's file beside its folder", os.path.isfile(f1) and os.path.basename(f1) == "Global Standards version 1.skgs")
with zipfile.ZipFile(f1) as z:
    check("the file holds the manifest and every file of the version", {"manifest.json", "config/rules.json", "config/doc_types.json"} <= set(z.namelist())
          and set(z.namelist()) - {"manifest.json"} == set(json.loads(z.read("manifest.json"))["files"]), z.namelist())

check("a PC with nothing has no notice", GX.notice(B) is None)
got = GX.install(B, f1)
check("Install a file puts the version on a PC with no link", got["version"] == 1 and json.loads(get(B, "rules.json"))["rules"]["RU1"]["on"] is True
      and GS.state(B)["version"] == 1 and GS.state(B)["source"] == GS.INSTALLED, GS.state(B))
nt = GX.notice(B)
check("the first version taken says so, with who and when, and lists no change", nt and nt["version"] == 1 and nt["by"] == "Ada" and nt["rows"] == []
      and "took version 1, updated by Ada" in GX.notice_words(nt), nt)
check("the notice is in its saved format", nt["format"] == F.number("global standards notice") == GX.FORMAT)
GX.mark_seen(B)
check("Mark as seen: the notice is gone", GX.notice(B) is None)

put(A, "rules.json", json.dumps({"rules": {"RU1": {"on": False}}}))
GF.update(A, FOLDER, by="Ada", note="Rule 1 off")
f2 = os.path.join(FOLDER, GX.file_name(2))
try:
    GX.install(B, f1); said = ""
except ValueError as e:
    said = str(e)
check("a file that is not newer is refused in words, and nothing changes", "not newer" in said and GS.state(B)["version"] == 1, said)
got = GX.install(B, f2)
nt = GX.notice(B)
check("a later version: the notice lists each change, what it was and what it is now",
      [(r["what"], r["was"], r["now"]) for r in nt["rows"]] == [("rules.RU1.on", "True", "False")] and nt["note"] == "Rule 1 off", nt)
check("... in words", "Version 2, updated by Ada" in GX.notice_words(nt) and "changed 1 thing on this PC" in GX.notice_words(nt), GX.notice_words(nt))

got = GX.take(C, FOLDER)
check("a linked PC taking from the folder keeps a notice too", got["version"] == 2 and GX.notice(C)["version"] == 2 and GS.state(C)["source"] == GS.LINKED)

bad = os.path.join(tmp, "bad.skgs"); shutil.copyfile(f2, bad)
with zipfile.ZipFile(bad, "a") as z:
    z.writestr("config/extra.json", "{}")
put(B, "rules.json", json.dumps({"rules": {"RU1": {"on": "mine"}}}))


def refused(path):
    try:
        GX.install(B, path)
        return ""
    except ValueError as e:
        return str(e)


GS.take(B, 1, GS.INSTALLED)                                      # as if still on version 1
check("a file holding more than its list says is refused", "does not hold exactly" in refused(bad), refused(bad))
dmg = os.path.join(tmp, "damaged.skgs")
with zipfile.ZipFile(f2) as z, zipfile.ZipFile(dmg, "w") as o:
    for n in z.namelist():
        o.writestr(n, z.read(n) if n == "manifest.json" else b"{\"changed\": 1}")
check("a file whose contents do not match its list is refused", "damaged" in refused(dmg), refused(dmg))
notzip = os.path.join(tmp, "notes.skgs"); open(notzip, "w").write("hello")
check("a file of another kind is refused", "not a Global Standards file" in refused(notzip))
check("after every refusal the PC is as it was", json.loads(get(B, "rules.json"))["rules"]["RU1"]["on"] == "mine" and GS.state(B)["version"] == 1)
got = GX.install(B, f2)
check("installing over the PC's own change keeps it in a dated backup and the notice names it", got["replaced"] == ["Rules"] and os.path.isdir(got["backup"])
      and GX.notice(B)["replaced"] == ["Rules"], got)
check("no temporary folder is left behind", not [n for n in os.listdir(tempfile.gettempdir()) if n.startswith("skgs_")])

n = sum(checks)
print(f"GLOBAL FILE 4330 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
