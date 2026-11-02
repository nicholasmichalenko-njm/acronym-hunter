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
# 3.15.1: an outside watched folder: where each file came from, the same words not added twice, a file leaving it
out = os.path.join(tmp, "SharePoint sync"); os.makedirs(out)
src1 = os.path.join(out, "Section L.txt"); open(src1, "w").write("one")
check("an outside folder is watched", WA.add_folder(data, out, "customer"))
rd = lambda p: S("The Offeror shall submit three volumes.", "Each volume has a page limit.") if "Section L" in p else S("other words")
pl = DI.plan(lib, [src1], rd)
made = DI.apply(lib, pl, cust, None)
v1 = made[0][1]
check("the effort keeps a copy and remembers where the file came from", DV.same_path(v1.get("source"), src1)
      and lib.has_original(v1) and not DV.same_path(lib.path_of(v1), src1), v1)
check("its words are fingerprinted", bool(v1.get("text_sha")) and v1["text_sha"] == DV.text_print(rd(src1)))
open(src1, "w").write("one, saved again by sync")                      # other bytes, the same words
f = WA.check(lib, data, cust)
check("a re-saved file comes up as changed, not new", [os.path.basename(p) for p, _d, _v in f["changed"]] == ["Section L.txt"]
      and not f["new"], f)
pl = DI.plan(lib, [src1], rd)
check("... and the intake knows it: the same text, skipped", pl[0].get("dup") and pl[0].get("dup_how") == "same text"
      and pl[0]["choice"] == "skip", pl[0].get("dup_how"))
n0 = len(lib.all)
DI.apply(lib, pl, cust, None)
check("... nothing is added twice", len(lib.all) == n0 and len(lib.doc(made[0][0]["id"])["versions"]) == 1)
WA.set_aside(data, [src1])
check("... and once set aside the watch stops offering it", not WA.check(lib, data, cust)["changed"])
rd2 = lambda p: S("The Offeror shall submit four volumes.", "Each volume has a page limit.")
open(src1, "w").write("two")
pl = DI.plan(lib, [src1], rd2)
check("new words from the same file: a new version of its document", pl[0]["choice"] == "version"
      and pl[0]["doc"] == made[0][0]["id"] and "added before from this file" in pl[0]["cands"][0][2], pl[0]["cands"][:1])
twin = os.path.join(out, "Section L copy.txt"); open(twin, "w").write("three")
pl = DI.plan(lib, [src1, twin], lambda p: S("Brand new words here.", "And more."))
check("two files in one batch with the same words: the second is skipped", not pl[0].get("dup") and pl[1].get("dup_how") == "same text"
      and pl[1]["choice"] == "skip")
os.remove(twin)
os.remove(src1)
f = WA.check(lib, data, cust)
check("a file that leaves the outside watched folder is missing", [p for _d, _v, p in f["missing"]] == [src1], f["missing"])
check("Keep without it: the effort's copy stays and the check stops asking",
      WA.keep_without_original(lib, rec, made[0][0]["id"], path=src1) and not WA.check(lib, data, cust)["missing"]
      and lib.has_original(lib.doc(made[0][0]["id"])["versions"][-1])
      and not lib.doc(made[0][0]["id"])["versions"][-1].get("missing_kept"))
n = sum(checks)
print(f"WATCH {'PASS' if all(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
