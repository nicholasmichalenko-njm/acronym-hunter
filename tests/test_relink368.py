"""3.68.0 without a screen: an effort found again after its folder moves. The Effort List is found from the folder, the
list itself or the marker file; a moved effort is told apart from a new one; its customer document versions, matrix and
deliverable files are pointed at the new place (by where they sat in the old folder, then by name); the marker file is
written once and names the list relative to the folder. Fictional content (Kestrel)."""
import json, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import effort as E, effortrelink as ER, workspace as W

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
root = os.path.join(tmp, "Old place", "Kestrel")
for sub in ("Customer Documents", "Volumes"):
    os.makedirs(os.path.join(root, sub))
LIST = os.path.join(root, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
data = W.data_dir_for(LIST); os.makedirs(os.path.join(data, "documents"))
rfp = os.path.join(root, "Customer Documents", "Kestrel RFP.pdf"); open(rfp, "wb").write(b"%PDF-1.4 fictional")
sow = os.path.join(root, "Customer Documents", "Section C", "Kestrel SOW.docx"); os.makedirs(os.path.dirname(sow)); open(sow, "wb").write(b"x")
mat = os.path.join(root, "Kestrel_Compliance_Matrix.xlsx"); open(mat, "wb").write(b"x")
vol = os.path.join(root, "Volumes", "Kestrel_Volume_I.docx"); open(vol, "wb").write(b"x")
W.write_json(os.path.join(data, "documents", "index.json"),
             {"docs": [{"name": "RFP", "versions": [{"file": "Kestrel RFP.pdf", "path": rfp}]},
                       {"name": "SOW", "versions": [{"file": "Kestrel SOW.docx", "path": sow}]}]})
W.write_json(os.path.join(data, "settings.json"), {"compliance_path": mat})
W.write_json(os.path.join(data, "record.json"), {"deliverables": [{"name": "Volume I", "file": vol}]})
info = {"path": LIST}
check("an effort in its place is not missing", not ER.missing(info))
NEWL = os.path.join(tmp, "New", "X_Effort_List.xlsx"); os.makedirs(os.path.dirname(NEWL)); E.EffortList(NEWL, "X").save()
check("a new effort whose app data folder is not made yet is not missing", not ER.missing({"path": NEWL}))
mk = ER.write_marker(LIST, "Kestrel")
body = json.load(open(mk, encoding="utf-8"))
check("the marker names the effort and its list relative to the folder", os.path.basename(mk) == ER.MARKER
      and body["effort"] == "Kestrel" and body["list"] == "Kestrel_Effort_List.xlsx")
t = os.path.getmtime(mk)
check("the marker is written once (not again while it is right)", ER.write_marker(LIST, "Kestrel") == mk and os.path.getmtime(mk) == t)
# ---- the folder moves
new_root = os.path.join(tmp, "New place", "Kestrel moved")
os.makedirs(os.path.dirname(new_root))
shutil.move(root, new_root)
check("after the move the effort is missing", ER.missing(info))
NEW = os.path.join(new_root, "Kestrel_Effort_List.xlsx")
check("found from its folder, its list, or its marker", ER.find_list(new_root) == NEW and ER.find_list(NEW) == NEW
      and ER.find_list(os.path.join(new_root, ER.MARKER)) == NEW)
check("found from a folder above it", ER.find_list(os.path.join(tmp, "New place")) == NEW)
check("a folder with no effort finds nothing", ER.find_list(os.path.join(tmp, "Old place")) == "" if os.path.isdir(os.path.join(tmp, "Old place")) else True)
got = ER.relink(NEW, LIST)
d2 = W.data_dir_for(NEW)
idx = W.read_json(os.path.join(d2, "documents", "index.json"))
paths = [v["path"] for doc in idx["docs"] for v in doc["versions"]]
check("customer document versions point at the new place (subfolders kept)", paths == [os.path.join(new_root, "Customer Documents", "Kestrel RFP.pdf"),
      os.path.join(new_root, "Customer Documents", "Section C", "Kestrel SOW.docx")], paths)
check("the matrix and the deliverable's file too", W.read_json(os.path.join(d2, "settings.json"))["compliance_path"] == os.path.join(new_root, "Kestrel_Compliance_Matrix.xlsx")
      and W.read_json(os.path.join(d2, "record.json"))["deliverables"][0]["file"] == os.path.join(new_root, "Volumes", "Kestrel_Volume_I.docx"))
check("what it did is said", got["name"] == "Kestrel" and got["repointed"] == 3 and got["new_root"] == new_root, got)
check("nothing was made at the old place", not os.path.exists(root))
# ---- moved again with no record of the old place: the paths' shared folder, then names
third = os.path.join(tmp, "Third", "K"); shutil.move(new_root, third)
got3 = ER.relink(os.path.join(third, "Kestrel_Effort_List.xlsx"))
idx3 = W.read_json(os.path.join(W.data_dir_for(os.path.join(third, "Kestrel_Effort_List.xlsx")), "documents", "index.json"))
check("without the old list's path: found by the folder the saved paths share", all(v["path"].startswith(third) and os.path.isfile(v["path"])
      for doc in idx3["docs"] for v in doc["versions"]) and got3["repointed"] == 3, idx3)
# a file renamed into another folder: found by its name
os.makedirs(os.path.join(third, "Customer Documents", "Moved here"))
shutil.move(os.path.join(third, "Customer Documents", "Kestrel RFP.pdf"), os.path.join(third, "Customer Documents", "Moved here", "Kestrel RFP.pdf"))
ER.relink(os.path.join(third, "Kestrel_Effort_List.xlsx"))
idx4 = W.read_json(os.path.join(W.data_dir_for(os.path.join(third, "Kestrel_Effort_List.xlsx")), "documents", "index.json"))
check("a file moved inside the folder is found by its name", idx4["docs"][0]["versions"][0]["path"].endswith(os.path.join("Moved here", "Kestrel RFP.pdf")))

print(f"RELINK 368 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
