"""3.70.0 without a screen: archiving an effort (a flag; never deleted; restored), and merging another copy of the same
effort: customer documents by content (a changed file a new version), acronyms (new, filled, the stronger status, two
meanings kept for review), volumes and drafts (identical skipped, different kept beside), and the record (by id, then by
name with references rewritten; changed in both kept ours and listed; the timeline joined); from an effort, its folder
or its package; the source never changed. Fictional content (Kestrel)."""
import json, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import docversions as DV, effort as E, effortarchive as EA, effortmerge as EM, effortrec as RR, workspace as W, effortfolders as EF

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
reg = E.Registry(os.path.join(tmp, "efforts.json"))


def effort(name, folder):
    root = os.path.join(tmp, folder); os.makedirs(os.path.join(root, "Customer Documents")); os.makedirs(os.path.join(root, "Volumes"))
    lst = os.path.join(root, "Kestrel_Effort_List.xlsx")
    L = E.EffortList(lst, "Kestrel"); L.save()
    reg.put(name, path=lst, customer_dir=os.path.join(root, "Customer Documents"))
    os.makedirs(W.data_dir_for(lst), exist_ok=True)
    return root, lst


def doc(root, lst, fname, body, name, doc_id=None):
    p = os.path.join(root, "Customer Documents", fname)
    open(p, "w", encoding="utf-8").write(body)
    lib = DV.Library(os.path.join(W.data_dir_for(lst), "documents")).load()
    d, _v = lib.add(p, [{"x": body}], doc_id=doc_id, doc_name=name)
    return d["id"]


A, LA = effort("Kestrel", "Mine")
B, LB = effort("Kestrel (Pat's copy)", "Pats")
doc(A, LA, "Kestrel RFP.txt", "The offeror shall describe the Kestrel Test Vehicle (KTV).", "RFP")
doc(B, LB, "Kestrel RFP.txt", "The offeror shall describe the Kestrel Test Vehicle (KTV).", "RFP")
doc(B, LB, "Kestrel RFP Amendment 1.txt", "The offeror shall also describe the ground station (GS).", "RFP Amendment 1")
la = E.EffortList(LA).load(); la.add_or_update("KTV", Definition="Kestrel Test Vehicle", Status="Proposed"); la.add_or_update("GS", Definition="Ground Station"); la.save()
lb = E.EffortList(LB).load()
lb.add_or_update("KTV", Definition="Kestrel Test Vehicle", Status="Approved", Approver="Pat", **{"Found in": "Kestrel RFP Amendment 1.txt"})
lb.add_or_update("GS", Definition="Ground Segment"); lb.add_or_update("TT&C", Definition="Telemetry, Tracking and Command")
lb.keywords.append({"Keyword": "resilient ground"}); lb.save()
open(os.path.join(A, "Volumes", "Kestrel_Volume_I.docx"), "wb").write(b"mine")
open(os.path.join(B, "Volumes", "Kestrel_Volume_I.docx"), "wb").write(b"pats")
open(os.path.join(B, "Volumes", "Kestrel_Volume_II.docx"), "wb").write(b"pats vol 2")
ra = RR.Record(W.data_dir_for(LA)); ra.data["topics"] = [{"id": "t1", "name": "Ground segment"}]
ra.data["tasks"] = [{"id": "k1", "text": "Draft the approach", "owner": "Nicholas", "done": False}]
ra.log("effort", "Started", at="2026-11-01T09:00"); ra.save()
rb = RR.Record(W.data_dir_for(LB))
rb.data["topics"] = [{"id": "p9", "name": "Ground Segment"}, {"id": "p10", "name": "Launch"}]
rb.data["topic_tags"] = {"s1": ["p9"], "s2": ["p10"]}
rb.data["tasks"] = [{"id": "k1", "text": "Draft the approach", "owner": "Pat", "done": True}, {"id": "k2", "text": "Price the launch", "owner": "Pat", "done": False}]
rb.log("effort", "Pat's notes", at="2026-11-02T10:00"); rb.save()
before_b = {os.path.relpath(os.path.join(dp, f), B): open(os.path.join(dp, f), "rb").read() for dp, _d, fs in os.walk(B) for f in fs}
# ---- merge from another effort on this PC
out = EM.merge(reg, "Kestrel", "Kestrel (Pat's copy)")
check("merged", out["ok"] and out["source"] == "Kestrel (Pat's copy)", out)
check("documents: the amendment is new, the RFP already here", out["documents"]["documents"] == 1 and out["documents"]["same"] == 1)
lib = DV.Library(os.path.join(W.data_dir_for(LA), "documents")).load()
check("... and its file is in this effort's folder", any(d["name"] == "RFP Amendment 1" for d in lib.all)
      and os.path.isfile(os.path.join(A, "Customer Documents", "Kestrel RFP Amendment 1.txt")))
L = E.EffortList(LA).load()
check("acronyms: a new term added", "TT&C" in L.rows and out["acronyms"]["added"] >= 1)
check("the same meaning: in the list, Found in joined (3.76.0: no approval)", L.rows["KTV"]["Status"] == "In the list"
      and "Kestrel RFP Amendment 1.txt" in L.rows["KTV"].get("Found in", ""), L.rows["KTV"])
check("another meaning: ours kept, theirs in Other definitions, listed for review", L.rows["GS"]["Definition"] == "Ground Station"
      and "Ground Segment" in L.rows["GS"]["Other definitions"] and any(r["item"] == "GS" for r in out["review"]))
check("keywords joined", any(k.get("Keyword") == "resilient ground" for k in L.keywords))
check("volumes: a new one copied, a different one kept beside ours", open(os.path.join(A, "Volumes", "Kestrel_Volume_I.docx"), "rb").read() == b"mine"
      and os.path.isfile(os.path.join(A, "Volumes", "Kestrel_Volume_I (from Kestrel (Pat's copy)).docx"))
      and os.path.isfile(os.path.join(A, "Volumes", "Kestrel_Volume_II.docx")))
r = RR.Record(W.data_dir_for(LA))
names = [t["name"] for t in r.data["topics"]]
check("record: a topic matched by name is not doubled; a new one added", names == ["Ground segment", "Launch"], names)
check("... their tags point at our topic", r.data["topic_tags"]["s1"] == ["t1"] and r.data["topic_tags"]["s2"] == ["p10"])
check("a task changed in both copies keeps ours and is listed", next(t for t in r.data["tasks"] if t["id"] == "k1")["owner"] == "Nicholas"
      and any(x["part"] == "Tasks" for x in out["review"]) and any(t["id"] == "k2" for t in r.data["tasks"]))
tl = [e["text"] for e in r.data["timeline"]]
check("the timeline joined in time order, and the merge logged", tl.index("Started") < tl.index("Pat's notes") and tl[-1].startswith("Merged from"))
check("review items kept in the record", len(r.data["merge_review"]) == len(out["review"]) >= 2)
after_b = {os.path.relpath(os.path.join(dp, f), B): open(os.path.join(dp, f), "rb").read() for dp, _d, fs in os.walk(B) for f in fs}
check("the source was only read, every file byte for byte", after_b == before_b, sorted(k for k in after_b if after_b.get(k) != before_b.get(k)))
again = EM.merge(reg, "Kestrel", "Kestrel (Pat's copy)")
check("merging again adds nothing new", again["documents"]["documents"] == 0 and again["acronyms"]["added"] == 0
      and again["files"]["copied"] == 0 and again["files"]["beside"] == 0 and again["record"]["added"] == 0, again)
check("an effort cannot merge into itself", EM.merge(reg, "Kestrel", "Kestrel")["ok"] is False)
# ---- from a folder and a package
C = os.path.join(tmp, "Moved", "Kestrel copy"); shutil.copytree(B, C)
open(os.path.join(C, "Volumes", "Kestrel_Volume_III.docx"), "wb").write(b"vol 3")
fo = EM.merge(reg, "Kestrel", C)
check("from an effort's folder (moved): its new volume copied", fo["ok"] and fo["files"]["copied"] == 1)
import effortpkg as P
pkg = os.path.join(tmp, "Kestrel Pat.skpkg")
P.save(pkg, "Kestrel", LB, W.data_dir_for(LB), customer_dir=os.path.join(B, "Customer Documents"), volumes_dir=os.path.join(B, "Volumes"), customer=True, volumes=True)
po = EM.merge(reg, "Kestrel", pkg)
check("from an effort package: read from a temporary folder, removed after", po["ok"] and not [d for d in os.listdir(tempfile.gettempdir()) if d.startswith("sk_merge_")])
# ---- archive
ar = EA.archive(reg, "Kestrel (Pat's copy)")
check("archive: a flag, the effort's files untouched", ar and reg.get("Kestrel (Pat's copy)")["archived"] and os.path.isfile(LB))
check("archived efforts are listed apart", EA.archived(reg) == ["Kestrel (Pat's copy)"] and "Kestrel (Pat's copy)" not in EA.active(reg))
check("an archived effort can still be merged from", EM.merge(reg, "Kestrel", "Kestrel (Pat's copy)")["ok"])
EA.restore(reg, "Kestrel (Pat's copy)")
check("restore brings it back", not reg.get("Kestrel (Pat's copy)").get("archived") and "Kestrel (Pat's copy)" in EA.active(reg))
check("there is no delete", not any(hasattr(EA, n) for n in ("delete", "remove", "forget")))

print(f"MERGE 370 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
