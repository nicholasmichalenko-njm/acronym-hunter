"""4.25.1: the effort's own folder (Nicholas 2026-11-12 16:49, 17:08; answers 8 and 9). The watch finds a file dropped
into the effort's folder, of any kind, and reports it to be added by itself; our volumes, Response Setup, Exports,
Redlines, Deleted and the files beside the effort list are left out; what was there before the first check of an effort
that has documents is left alone; more than 25 at once are offered, not added; a file in the effort's folder is added
where it sits, never copied; the Trash is the visible Deleted folder, and entries an older version kept are still read
and restored. Fictional content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import docversions as DV, docintake as DI, doctrash as T, effortlib as EL, watch as WA, workspace as W

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


def put(path, text="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


tmp = tempfile.mkdtemp()
root = os.path.join(tmp, "Heron")
LIST = put(os.path.join(root, "Heron_Effort_List.xlsx"), "list")
data = W.data_dir_for(LIST); os.makedirs(data)
cust = os.path.join(root, "02_customer documents"); os.makedirs(cust)
skip = [os.path.join(root, n) for n in ("01_proposal", "10_proposal management", "Redlines", "Deleted")]
lib = EL.attach(DV.Library(os.path.join(data, "documents")), LIST)
kw = dict(effort_root=root, skip=skip, not_in=[root])
check("a new effort: nothing found, nothing from before", WA.check(lib, data, cust, **kw) == {"new": [], "changed": [], "missing": [], "auto": []})
a = put(os.path.join(root, "06_cost and pricing", "Rates", "Kestrel rates.xlsx"), "rates")
b = put(os.path.join(root, "05_program management", "Kestrel schedule.mpp"), "schedule")
c = put(os.path.join(cust, "Kestrel_RFP.txt"), "The Offeror shall describe the antenna.")
for p in (os.path.join(root, "01_proposal", "Volume I.docx"), os.path.join(root, "Deleted", "x", "old.pdf"),
          os.path.join(root, "10_proposal management", "Exports", "Heron_Status.docx"), os.path.join(root, "notes beside the list.txt"),
          os.path.join(data, "documents", "kept.txt"), os.path.join(root, "05_program management", "~$lock.docx"),
          os.path.join(root, "05_program management", "desktop.ini")):
    put(p)
f = WA.check(lib, data, cust, **kw)
check("a file dropped into the effort's folder is found to be added by itself, of any kind (.mpp)", sorted(p for p, _c in f["auto"]) == sorted([a, b])
      and all(cat == "ours" for _p, cat in f["auto"]), f["auto"])
check("a file in the customer's folder is offered with its table, as before", f["new"] == [(c, "customer")], f["new"])
check("our volumes, Exports, Deleted, the app's data, the files beside the list, and what programs leave behind are left out",
      not any(n in " ".join(p for p, _c in f["auto"] + f["new"]) for n in ("Volume I", "old.pdf", "Heron_Status", "beside the list", "kept.txt", "~$", "desktop.ini")))
rel = WA.relative_folders([a, b], data, cust, root)
check("its folder is where it sits in the effort's folder", rel == {a: "06_cost and pricing/Rates", b: "05_program management"}, rel)
plan = DI.plan(lib, [a, b], folders=rel, category="ours")
for e in plan:
    e["role"] = "reference"
made = DI.apply(lib, plan, cust)
da = next(d for d, _v in made if d["name"].startswith("Kestrel rates"))
va = da["versions"][-1]
check("added where it sits: no copy in the Library, found again from the effort's folder", len(made) == 2 and lib.path_of(va) == a
      and va.get("erel") == "06_cost and pricing/Rates/Kestrel rates.xlsx" and not os.path.isdir(os.path.join(root, "Library", "Our Documents"))
      and da["category"] == "ours" and da["folder"] == "06_cost and pricing/Rates" and lib.role_of(da) == "reference", (lib.path_of(va), va.get("erel"), da))
check("a kind of file the reader does not open is still a document (no text)", any(d["name"].startswith("Kestrel schedule") for d, _v in made))
lib2 = EL.attach(DV.Library(os.path.join(data, "documents")).load(), LIST)
f = WA.check(lib2, data, cust, **kw)
check("once added, it is not found again", f["auto"] == [] , f["auto"])
moved = os.path.join(tmp, "Moved", "Heron"); os.makedirs(os.path.dirname(moved)); os.rename(root, moved)
LIST2 = os.path.join(moved, "Heron_Effort_List.xlsx")
lib3 = EL.attach(DV.Library(os.path.join(W.data_dir_for(LIST2), "documents")).load(), LIST2)
check("the effort's folder moved: the document is found where the effort is now",
      lib3.path_of(lib3.doc(da["id"])["versions"][-1]) == os.path.join(moved, "06_cost and pricing", "Rates", "Kestrel rates.xlsx"))
os.rename(moved, root)
# an effort from before: what is already there is left alone
root2 = os.path.join(tmp, "Osprey"); L2 = put(os.path.join(root2, "Osprey_Effort_List.xlsx")); d2 = W.data_dir_for(L2); os.makedirs(d2)
c2 = os.path.join(root2, "Customer Documents"); r0 = put(os.path.join(c2, "Kestrel_SOW.txt"), "The Contractor shall deliver the plan.")
libo = EL.attach(DV.Library(os.path.join(d2, "documents")), L2)
DI.apply(libo, DI.plan(libo, [r0]), c2)
old = put(os.path.join(root2, "Old notes", "kickoff.txt"), "kickoff")
k2 = dict(effort_root=root2, skip=[], not_in=[root2])
f = WA.check(libo, d2, c2, **k2)
check("an effort that has documents: what was in its folder before the first check is left alone", f["auto"] == [] and f["new"] == [], f)
new = put(os.path.join(root2, "Old notes", "second.txt"), "second")
f = WA.check(libo, d2, c2, **k2)
check("... and what is dropped in afterwards is added by itself", [p for p, _c in f["auto"]] == [new], f)
many = [put(os.path.join(root2, "Bulk", f"file {i:02d}.txt"), f"bulk {i}") for i in range(WA.AUTO_MOST + 1)]
f = WA.check(libo, d2, c2, **k2)
check("more than 25 new files at once are offered, not added by themselves", f["auto"] == [] and len(f["new"]) == len(many) + 1, (len(f["auto"]), len(f["new"])))
check("the line says what came in", "came into the effort's folder" in WA.summary({"new": [], "changed": [], "missing": [], "auto": [(new, "ours")]}))
# the Trash is the visible Deleted folder
ws = W.Workspace(data, "Heron")
check("the Trash is <effort>\\Deleted", T.folder(ws) == os.path.join(root, "Deleted"), T.folder(ws))
oldeid = "20261101-090000-000000-aaaa"
put(os.path.join(T.old_folder(ws), oldeid, "files", "00-Kestrel old.txt"), "old")
import json
goes_back = os.path.join(root, "04_RFIs and white papers", "Kestrel old.txt")
json.dump({"id": oldeid, "kind": "document", "name": "Kestrel old", "when": "2026-11-01T09:00:00", "who": "x",
           "files": [{"orig": goes_back, "kept": os.path.join("files", "00-Kestrel old.txt")}], "payload": {}},
          open(os.path.join(T.old_folder(ws), oldeid, "entry.json"), "w"))
gone = put(os.path.join(root, "07_tech engineering", "Kestrel draft.txt"), "draft")
eid = T.put(ws, "document", "Kestrel draft", {"x": 1}, [gone])
check("a delete goes into Deleted, with a note that says what the folder is", os.path.isdir(os.path.join(root, "Deleted", eid))
      and not os.path.exists(gone) and os.path.isfile(os.path.join(root, "Deleted", T.NOTE)))
check("entries an older version kept in the app's data are still listed, newest first", [e["id"] for e in T.entries(ws)] == [eid, oldeid])
check("... and restored from where they are", T.take_back(ws, oldeid)["back"] == {goes_back: goes_back} and os.path.isfile(goes_back)
      and T.take_back(ws, eid) and os.path.isfile(gone) and T.entries(ws) == [])
f = WA.check(EL.attach(DV.Library(os.path.join(data, "documents")).load(), LIST), data, cust, **kw)
check("the watch never reads Deleted", not any("Deleted" in p for p, _c in f["auto"] + f["new"]))
n = sum(checks)
print(f"TEST EFFORT FOLDER 4251 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
