"""2.80.0 where your data lives: run from source, the data stays in the source folder; packaged, it goes in
"Stationkeeper Data" beside the program folder (or where data_location.txt points), and when that cannot be made it
stays in the program folder; the first start copies config, the database, training data, feedback and settings across
(nothing deleted, a note left), and a second start copies nothing; moving the data folder needs an empty folder; a save
waits out a file held for a moment; the effort check finds damaged, missing, moved, synced and conflict-copy problems
and puts back the newest good copy."""
import os, shutil, sys, tempfile, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import datahome as DH

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
APP = os.path.join(tmp, "Desktop", "Stationkeeper"); os.makedirs(os.path.join(APP, "config", "models"))
open(os.path.join(APP, "config", "efforts.json"), "w").write('{"Heron": {}}')
open(os.path.join(APP, "acronym_database.csv"), "w").write("Term\nMY ROW\n")
os.makedirs(os.path.join(APP, "_local_sandbox")); open(os.path.join(APP, "_local_sandbox", "settings.json"), "w").write('{"backup_dir": "X"}')
os.makedirs(os.path.join(APP, "training_data")); open(os.path.join(APP, "training_data", "samples.csv"), "w").write("a")
os.environ.pop("SK_DATA_DIR", None)
check("run from source: the data stays in the source folder", DH.resolve(APP) == (APP, "source"))
sys.frozen = True
try:
    d, why = DH.resolve(APP)
    check("packaged: Stationkeeper Data beside the program folder", d == os.path.join(tmp, "Desktop", "Stationkeeper Data") and why == "beside")
    got = DH.ensure(d, APP)
    check("first start: config, database, training data and settings copied across", sorted(got) ==
          sorted(["config", "acronym_database.csv", "training_data", "settings.json"]) and
          open(os.path.join(d, "acronym_database.csv")).read() == "Term\nMY ROW\n" and open(os.path.join(d, "settings.json")).read() == '{"backup_dir": "X"}')
    check("nothing deleted; a note in the old config folder; an Efforts folder and a READ ME", os.path.isfile(os.path.join(APP, "acronym_database.csv"))
          and os.path.isfile(os.path.join(APP, "config", "MOVED TO Stationkeeper Data.txt")) and os.path.isdir(os.path.join(d, "Efforts"))
          and os.path.isfile(os.path.join(d, "READ ME.txt")))
    open(os.path.join(d, "acronym_database.csv"), "w").write("Term\nNEWER\n")
    check("a second start copies nothing (your newer data is kept)", DH.ensure(d, APP) == [] and "NEWER" in open(os.path.join(d, "acronym_database.csv")).read())
    APP2 = os.path.join(tmp, "Desktop", "Stationkeeper 2.81"); os.makedirs(os.path.join(APP2, "config"))
    d2, _w = DH.resolve(APP2)
    check("a new download unzipped beside it picks up the same data", d2 == d and DH.ensure(d2, APP2) == [])
    fresh = os.path.join(tmp, "Fresh", "Stationkeeper"); os.makedirs(os.path.join(fresh, "config"))
    open(os.path.join(fresh, "config", "app_settings.json"), "w").write("{}")
    DH.ensure(os.path.join(tmp, "Fresh", DH.NAME), fresh)
    check("a fresh download (only the shipped defaults): no note is written into the program folder", os.listdir(os.path.join(fresh, "config")) == ["app_settings.json"])
    other = os.path.join(tmp, "Work data")
    os.makedirs(other); open(os.path.join(other, "x.txt"), "w").write("x")
    try:
        DH.set_location(APP, other, d); ok = False
    except OSError as e:
        ok = "empty folder" in str(e)
    check("moving the data folder needs an empty folder", ok)
    new = DH.set_location(APP, os.path.join(tmp, "Work data 2"), d)
    check("moved: copied, and the program points at it", DH.resolve(APP) == (new, "pointer") and os.path.isfile(os.path.join(new, "acronym_database.csv")))
    ro = os.path.join(tmp, "ro", "Stationkeeper"); os.makedirs(ro)
    real = os.makedirs
    def deny(p, *a, **k):
        if "ro" in p and p.endswith(DH.NAME):
            raise PermissionError(p)
        return real(p, *a, **k)
    DH.os.makedirs = deny
    try:
        check("the folder beside cannot be made: the data stays in the program folder", DH.resolve(ro) == (ro, "program folder"))
    finally:
        DH.os.makedirs = real
finally:
    del sys.frozen
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "envdata")
check("SK_DATA_DIR wins (tests)", DH.resolve(APP) == (os.path.join(tmp, "envdata"), "env"))
os.environ.pop("SK_DATA_DIR")

# a save waits out a file held for a moment
import workspace as W
src, dst = os.path.join(tmp, "a.tmp"), os.path.join(tmp, "a.xlsx")
open(src, "w").write("new"); open(dst, "w").write("old")
real_replace = os.replace
calls = {"n": 0}
def flaky(a, b):
    calls["n"] += 1
    if calls["n"] < 3:
        raise PermissionError(b)
    return real_replace(a, b)
W.os.replace = flaky
try:
    W.replace_retry(src, dst, wait=0.01)
finally:
    W.os.replace = real_replace
check("a save waits out a file held for a moment (OneDrive, a scanner)", open(dst).read() == "new" and calls["n"] == 3)

# effort check
import effort as E, compliance as C, effortcheck as EC
ED = os.path.join(tmp, "Heron"); os.makedirs(ED)
LP = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LP, "Heron"); L.pending = True; L.save()
ws = W.Workspace(W.data_dir_for(LP), "Heron")
M = C.Matrix(os.path.join(ED, "Heron_Compliance_Matrix.xlsx"), "Heron")
M.items = C.extract([("L.docx", [("Page 1", "The Offeror shall describe the design.")])]); M.save()
ws.backup(M.path, "matrix", force=True); ws.backup(LP, "effort", force=True)
check("a healthy effort: nothing to report", EC.check(ws, LP, M.path) == [], EC.check(ws, LP, M.path))
open(M.path, "wb").write(b"not a workbook")
iss = EC.check(ws, LP, M.path, customer_dir=os.path.join(ED, "gone"))
kinds = {i["kind"]: i for i in iss}
check("a damaged matrix is an error with a fix; a moved folder a warning", kinds["matrix_damaged"]["severity"] == "error"
      and kinds["matrix_damaged"]["fix"] == "restore_matrix" and kinds["customer_moved"]["fix"] == "find_customer")
used = EC.restore_copy(ws, "matrix", M.path)
check("the newest good copy goes back; the damaged file is kept beside it", used and C.Matrix(M.path).load().items
      and any("(damaged" in f for f in os.listdir(ED)))
open(os.path.join(ws.root, "record.json"), "w").write("{broken")
open(os.path.join(ED, "Heron_Compliance_Matrix-NICK-LAPTOP.xlsx"), "w").write("x")
kinds = {i["kind"] for i in EC.check(ws, LP, M.path)}
check("a damaged record file and a sync conflict copy are found", {"json_damaged", "conflict_copy"} <= kinds, kinds)
os.environ["OneDriveCommercial"] = tmp
check("a live effort in a folder OneDrive uploads: move it to this PC", any(i["kind"] == "live_synced" and i["fix"] == "move_local"
                                                                          for i in EC.check(ws, LP, M.path)))
os.environ.pop("OneDriveCommercial")
check("the summary", EC.summary([]) == "Effort health: everything checks out." and "1 problem(s) to fix" in EC.summary([{"severity": "error"}]))
shutil.rmtree(tmp, ignore_errors=True)
n = sum(checks)
print(f"DATA HOME PASS ({n}/{len(checks)})" if n == len(checks) else f"DATA HOME FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
