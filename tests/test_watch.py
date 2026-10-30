"""2.94.0 watched folders, no window: the Customer Documents folder and added folders are checked, subfolders included;
a file no document has is new (and "Not these" sets it aside until its contents change); the file a document was read
from holding other contents is changed; a document's file gone is missing until the person finds it, keeps the record
without it, or marks the document withdrawn; the app's own folders are left out; a file already in the customer folder
(or a subfolder) is not copied again when added."""
import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import docversions as DV, docintake as DI, watch as WA, effortrec as RR

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
eff = os.path.join(tmp, "Kestrel"); cust = os.path.join(eff, "Customer Documents"); os.makedirs(cust)
data = os.path.join(eff, "Kestrel_Effort_List - app data"); os.makedirs(os.path.join(data, "documents"))
lib = DV.Library(os.path.join(data, "documents")).load()
rec = RR.Record(data)
S = lambda *xs: [{"x": x, "l": "1", "s": "", "t": ""} for x in xs]


def put(rel, body):
    p = os.path.join(cust, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(body)
    return p


rfp = put("RFP.pdf", "the rfp v1")
d1, v1 = lib.add(rfp, S("The Offeror shall."), doc_name="RFP", initial="R", dtype="RFP")
put("Amendments/Amendment 01.pdf", "amendment one")
put("~$lock.docx", "temp")
os.makedirs(os.path.join(data, "x")); open(os.path.join(data, "x", "inner.pdf"), "w").write("app")
inner_app = os.path.join(cust, "Kestrel_Effort_List - app data"); os.makedirs(inner_app); open(os.path.join(inner_app, "a.pdf"), "w").write("app2")
f = WA.check(lib, data, cust)
check("a new file in a subfolder is new; temp files and the app's folders are not", [os.path.basename(p) for p, _c in f["new"]] == ["Amendment 01.pdf"]
      and not f["changed"] and not f["missing"], f)
check("its category is the folder's", f["new"][0][1] == "customer")
WA.set_aside(data, [f["new"][0][0]])
check("Not these: set aside", not WA.check(lib, data, cust)["new"])
time.sleep(1.1); put("Amendments/Amendment 01.pdf", "amendment one, corrected")
check("... until its contents change", [os.path.basename(p) for p, _c in WA.check(lib, data, cust)["new"]] == ["Amendment 01.pdf"])
# added from its subfolder: stays where it is
plan = DI.plan(lib, [os.path.join(cust, "Amendments", "Amendment 01.pdf")], reader=lambda p: S("Amendment text."))
plan[0]["choice"] = "new"; plan[0]["initial"] = "A1"; plan[0]["type"] = "Amendment"
DI.apply(lib, plan, cust)
check("a file added from a subfolder of Customer Documents is not copied again", not os.path.exists(os.path.join(cust, "Amendment 01.pdf"))
      and lib.has_original(lib.all[-1]["versions"][-1]))
check("once added it is no longer new", not WA.check(lib, data, cust)["new"])
# changed
time.sleep(1.1); put("RFP.pdf", "the rfp, quietly replaced")
f = WA.check(lib, data, cust)
check("the file a document was read from holds other contents: changed", [(os.path.basename(p), d["name"]) for p, d, _v in f["changed"]] == [("RFP.pdf", "RFP")], f)
WA.set_aside(data, [f["changed"][0][0]])
check("Not these works for a change too", not WA.check(lib, data, cust)["changed"])
# missing
os.remove(rfp)
f = WA.check(lib, data, cust)
check("a document's file gone: missing", [d["name"] for d, _v, _p in f["missing"]] == ["RFP"], f)
moved = os.path.join(tmp, "elsewhere.pdf"); open(moved, "w").write("the rfp, quietly replaced")
check("Find it: a file with other contents is not taken as the same", not WA.found_at(lib, rec, d1["id"], moved))
open(moved, "w").write("the rfp v1")
check("Find it: the same contents, at a new place", WA.found_at(lib, rec, d1["id"], moved) and lib.has_original(d1["versions"][-1]))
check("... and it is no longer missing", not WA.check(lib, data, cust)["missing"])
os.remove(moved)
WA.add_folder(data, tmp + os.sep + "nothing")
check("a found file gone again, outside the watched folders, is not reported by the watch (the library still flags it)",
      not WA.check(lib, data, cust)["missing"])
d1["versions"][-1]["path"] = rfp; d1["versions"][-1].pop("rel", None); lib.save()
check("back in a watched folder: missing again", [d["name"] for d, _v, _p in WA.check(lib, data, cust)["missing"]] == ["RFP"])
WA.keep_without_original(lib, rec, d1["id"])
check("Keep the record without the original: it stops asking, and it is on the timeline", not WA.check(lib, data, cust)["missing"]
      and any("record kept without it" in e["text"] for e in RR.Record(data).events()))
d1["versions"][-1].pop("missing_kept"); lib.save()
WA.mark_withdrawn(lib, rec, d1["id"])
check("Mark withdrawn: it stops asking, stops building the matrix, and it is on the timeline", not WA.check(lib, data, cust)["missing"]
      and lib.doc(d1["id"])["withdrawn"] and lib.doc(d1["id"])["role"] != "matrix"
      and any("marked withdrawn" in e["text"] for e in RR.Record(data).events()))
# added folders
extra = os.path.join(tmp, "Bidders Library"); os.makedirs(os.path.join(extra, "Standards"))
open(os.path.join(extra, "Standards", "MIL-STD-1540.pdf"), "w").write("std")
check("an added folder is watched with its category", WA.add_folder(data, extra, "bidders") and not WA.add_folder(data, extra, "bidders"))
f = WA.check(lib, data, cust)
check("... its files and subfolders too", [(os.path.basename(p), c) for p, c in f["new"]] == [("MIL-STD-1540.pdf", "bidders")], f)
check("the folders listed: Customer Documents first", [b for _p, _c, b in WA.folders(data, cust)][0] is True and len(WA.folders(data, cust)) == 3)
check("a folder can stop being watched", WA.remove_folder(data, extra) and len(WA.folders(data, cust)) == 2)
check("the summary reads plainly", WA.summary({"new": [1, 2], "changed": [], "missing": [1]}) == "2 new file(s), 1 document file(s) missing")
n = sum(checks)
print(f"WATCH {'PASS' if all(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
