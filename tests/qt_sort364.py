"""3.64.0 Shred > Sort, offscreen: Unsorted pinned with its count; Start from the RFP's headings, the evaluation factors or
the starter list; file selected requirements under a topic (File, keys 1 to 9, Also under); a sentence's first topic is
its home; rename keeps the old name as another name; subtopics; merge; Back to Unsorted; Split carries the topics to the
parts; Overview counts shall, should and may and L, M and SOW; read topics back from a matrix workbook edited in Excel;
the path strip's Sort step counts what is sorted. The same topics as Review's Sort mode. Fictional content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import compliance as C, effort as E, effortrec as RR, workspace as W, topics as TP, custfocus as F, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
M = C.Matrix(os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"), "Kestrel")
M.items = C.extract([("Kestrel_PWS.docx", [("Page 1", "The contractor shall staff the network operations center at all hours. "
                      "The contractor shall automate pass scheduling. The contractor shall retain security logs for twelve months. "
                      "The contractor shall complete transition within sixty days. The contractor may propose quarterly reviews. "
                      "The contractor shall design and maintain the antenna.")])])
reqs = [it for it in M.items if it.get("type") not in ("Heading", "Context")]
head = {"id": "H1", "type": "Heading", "section": "3.2", "section_title": "Network Operations", "text": "3.2 Network Operations",
        "decision": "Drop", "header": "Yes", "doc": "Kestrel_PWS.docx", "loc": "Page 1"}
M.items.insert(0, head)
M.save(); W.Workspace(W.data_dir_for(LIST), "Kestrel").set("compliance_path", M.path)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
F.add_factor(RR.Record(ws0.root), "Technical Approach", importance="More important")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
check("Sort is in the Shred space, after Review", __import__("skqt.mainwin", fromlist=["x"]).RAIL_OF["sort"] == "assign" and "sort" in w.stepper.views)
w.go("sort"); app.processEvents()
sp = w.sort_page
n = len(TP.sortable(w.review.M.items))
check("Unsorted is pinned on top with every requirement in it at first", sp.tree.topLevelItem(0).text(0) == "Unsorted"
      and sp.tree.topLevelItem(0).text(1) == str(n) and sp.table.rowCount() == n and n >= 5, (n, sp.table.rowCount()))
got = sp.seed("headings")
check("Start from the RFP's headings: a topic per heading, its sentences under it", TP.find(sp.rec(), "Network Operations") is not None and got)
sp.seed("factors"); sp.seed("starter")
names = [t["name"] for t in TP.topics(sp.rec())]
check("Start from the evaluation factors and the starter list", "Technical Approach" in names and "Transition" in names and "Cybersecurity" in names, names)
r = sp.rec()
net, cyber, trans = TP.find(r, "Network Operations")["id"], TP.find(r, "Cybersecurity")["id"], TP.find(r, "Transition")["id"]
sp.showing = "__all__"; sp.refresh(); app.processEvents()
by = {it["id"]: i for i, it in enumerate(sp.rows)}
logs = next(it for it in sp.rows if "security logs" in it.get("text", ""))
sp.table.clearSelection(); sp.table.selectRow(by[logs["id"]]); app.processEvents()
sp.file(cyber)
check("File: the selected requirement's home is the topic", TP.primary(sp.rec(), logs["id"])["id"] == cyber)
sp.file(trans, also=True, rows=[logs])
ids_ = TP.rec_ids = (sp.rec().data.get("topic_tags", {}).get(logs["id"]) or [])
check("Also under: a cross-reference; the home stays", ids_[0] == cyber and trans in ids_, ids_)
tr = next(it for it in sp.rows if "transition" in it.get("text", "").lower())
roots = TP.roots(sp.rec())
k = [t["id"] for t in roots].index(trans)
if k < 9:
    sp.table.clearSelection(); sp.table.selectRow(by[tr["id"]]); app.processEvents()
    sp.file_n(k)
    check("keys 1 to 9 file under the first nine topics", TP.primary(sp.rec(), tr["id"])["id"] == trans)
sp.showing = cyber; sp.refresh(); app.processEvents()
sp.rename("Cyber and Security")
t = TP.get(sp.rec(), cyber)
check("Rename in your own words: the requirements stay, the old name is another name", t["name"] == "Cyber and Security"
      and "Cybersecurity" in t["aliases"] and TP.primary(sp.rec(), logs["id"])["id"] == cyber)
sub = sp.add_topic("Log retention", sub=True)
check("+ Subtopic goes under the topic picked", TP.get(sp.rec(), sub)["parent"] == cyber and sp.tree_items[cyber].childCount() == 1)
qa = TP.find(sp.rec(), "Quality")["id"]
TP.file_under(sp.rec(), [reqs[-1]["id"]], qa)
sp.showing = qa; sp.refresh()
sp.merge(trans)
check("Merge into...: the requirements move and the name is kept as another name", TP.get(sp.rec(), qa) is None
      and TP.primary(sp.rec(), reqs[-1]["id"])["id"] == trans and "Quality" in TP.get(sp.rec(), trans)["aliases"])
sp.unfile([tr])
check("Back to Unsorted", not TP.of(sp.rec(), tr["id"]))
compound = next(it for it in w.review.M.items if "design and maintain" in it.get("text", ""))
TP.file_under(sp.rec(), [compound["id"]], net)
sp.refresh()
at = compound["text"].index(" and maintain")
parts = sp.split(compound, at)
check("Split: parts with the same words (.a, .b), each keeping its topics", len(parts) == 2 and parts[0]["id"].endswith("a")
      and all(TP.primary(sp.rec(), p["id"])["id"] == net for p in parts) and " ".join(p["text"] for p in parts).replace("  ", " ") == compound["text"].strip(),
      [p.get("text") for p in parts])
ov = {o["name"]: o for o in TP.overview(sp.rec(), w.review.M.items)}
check("Overview: each area's requirements by shall, should and may, and by L, M and SOW, then Unsorted",
      ov["Cyber and Security"]["total"] >= 1 and ov["Cyber and Security"]["by_strength"]["Mandatory"] >= 1 and "Unsorted" in ov
      and sp.over.rowCount() == len(ov), ov.get("Cyber and Security"))
# read back from Excel
import openpyxl
wb = openpyxl.Workbook(); sh = wb.active; sh.append(["ID", "Requirement", "Topic"])
sched = next(it for it in w.review.M.items if "pass scheduling" in it.get("text", ""))
sh.append([sched["id"], sched["text"], "Network Operations; Ground Automation"]); sh.append(["ZZ-9", "not ours", "Transition"])
xp = os.path.join(tmp, "edited.xlsx"); wb.save(xp)
got = sp.read_back(xp)
check("Read back from Excel: the Topic column files each row; a new name becomes a topic; unknown IDs are counted",
      got["filed"] == 1 and got["new_topics"] == 1 and got["unknown_ids"] == 1 and TP.primary(sp.rec(), sched["id"])["id"] == net
      and TP.find(sp.rec(), "Ground Automation") is not None, got)
# the path strip
w.go("home"); app.processEvents()
st = {s["key"]: s for s in w.home_page.path.now}
uns = len(TP.unsorted(sp.rec(), w.review.M.items))
check("the path strip's Sort step counts what is sorted", "sort" in st and "sorted" in st["sort"]["count"] and st["sort"]["done"] == (uns == 0), st.get("sort"))
check("Review's Sort mode shows the same topics", any(b.text().endswith("Cyber and Security") for b in w.assign_page.topic_btns) or
      (w.assign_page.fill_topics() or any(b.text().endswith("Cyber and Security") for b in w.assign_page.topic_btns)))

print(f"QT SORT 364 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
