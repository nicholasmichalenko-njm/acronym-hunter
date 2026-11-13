"""4.30.3 (Nicholas 2026-11-13 16:34): Documents was adding the app's own published files (Stationkeeper Data: README,
manifest, rules, schema, the effort's template and dictionary). They are never documents: the watch leaves the folder
out, and any already added are taken off the list while the files stay. Fictional effort."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
import docversions as DV, watch as WA, effortdata as ED

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
eff = os.path.join(tmp, "Osprey"); cust = os.path.join(eff, "Customer Documents"); os.makedirs(cust)
data = os.path.join(eff, "Osprey_Effort_List - app data"); os.makedirs(os.path.join(data, "documents"))
lib = DV.Library(os.path.join(data, "documents")).load()
S = lambda *xs: [{"x": x, "l": "1", "s": "", "t": ""} for x in xs]
pub = os.path.join(eff, ED.FOLDER)
check("the watch's name for the folder is the publisher's", WA.APP_DATA == ED.FOLDER)
files = ["README.txt", "manifest.json", os.path.join("rules", "rules.json"), os.path.join("rules", ED.SCHEMA_FILE),
         os.path.join("templates", "effort.dotx"), os.path.join("dictionaries", "effort.dic")]
for rel in files:
    p = os.path.join(pub, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write("app")
notes = os.path.join(eff, "Reference", "Osprey notes.txt"); os.makedirs(os.path.dirname(notes)); open(notes, "w").write("ours")
got = WA.walk(eff, data, any_kind=True)
check("a walk of the effort's folder finds our file and none of the app's published files", [os.path.basename(p) for p in got] == ["Osprey notes.txt"], got)
f = WA.check(lib, data, cust, effort_root=eff, not_in=[eff])
seen = [os.path.basename(p) for k in ("new", "auto") for p, _c in f[k]]
check("a check offers none of them, new or added by itself", not any(os.path.basename(x) in seen for x in files), seen)
# two already added by an earlier version, and one real document
for rel in files[:3]:
    lib.add(os.path.join(pub, rel), S("App text."), doc_name=os.path.basename(rel))
lib.add(notes, S("Our notes."), doc_name="Osprey notes")
check("before: the three app files are on the list", len(WA.app_data_docs(lib)) == 3 and len(lib.all) == 4)
gone = WA.drop_app_data(lib)
check("they are taken off the list; our document stays", sorted(gone) == ["README.txt", "manifest.json", "rules.json"] and [d["name"] for d in lib.all] == ["Osprey notes"], gone)
check("the app's files themselves are untouched", all(os.path.isfile(os.path.join(pub, rel)) for rel in files))
lib2 = DV.Library(os.path.join(data, "documents")).load()
check("it is saved, and a second pass finds nothing to do", [d["name"] for d in lib2.all] == ["Osprey notes"] and WA.drop_app_data(lib2) == [])
n = sum(checks)
print(f"APP FILES 4303 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
