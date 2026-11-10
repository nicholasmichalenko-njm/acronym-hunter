"""3.63.0 the effort home, offscreen: the path strip under the header (request type, how and when it is sent, Notes to
sort, the steps with a count each, any order, Steps... on or off); a quick note from any page (Note in the top bar,
Ctrl+Shift+N) sent now or kept in Notes to sort and sent later; Meeting notes up front; Evaluation Criteria (a page in
the Effort space and a card): factors with importance, tied to deliverables; the deliverables list with parts, people
and compliance; All Efforts shows the request type and the factors. Fictional content."""
import datetime, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, effortrec as RR, workspace as W, deliverables as DL, delivmore as DM, meetings as MT, office_pdf as OP
import custfocus as F, effortpath as EP, quicknote as QN, effortsummary as ESUM
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


today = datetime.date.today()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
rec = RR.Record(ws0.root)
rec.set_due((today + datetime.timedelta(days=20)).isoformat() + "T14:00", "Mountain Time")
vol = DL.add(rec, "Volume I Technical", "Volume", owner="A. Lee")
slides = DL.add(rec, "Oral presentation slides", "Presentation")
r2 = RR.Record(ws0.root)
DM.add_part(r2, slides, "Opening", owner="K. Park")
MT.add_meeting(RR.Record(ws0.root), "Kickoff", today.isoformat(), notes="Agreed the outline. Action: confirm the page limit.")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("home"); app.processEvents()
hp = w.home_page
ps = hp.path
check("the path strip sits under the header, not in the scrolling cards", ps.parent() is hp.head and ps.isVisibleTo(w))
check("its steps: Read, Requirements, Structure, Setup, Check, each with a count", [s["key"] for s in ps.now] == ["read", "reqs", "sort", "structure", "setup", "check"]
      and all(s["count"] for s in ps.now), [(s["label"], s["count"]) for s in ps.now])
check("the request type starts as RFP", ps.type.currentText() == "RFP")
check("how and when it is sent is on the strip", "Due " in ps.sub.text(), ps.sub.text())
ps.btns["structure"].click(); app.processEvents()
check("any step opens its page, in any order (Structure opens Setup, 3.74.0)", w.stack.currentWidget() is w.pages["setups"])
w.go("home"); app.processEvents()
hp.path.set_type("RFI")
st = {s["key"]: s for s in hp.path.now}
check("RFI: the words change (Questions) and Setup becomes optional", st["reqs"]["label"] == "Questions" and st["setup"]["state"] == "opt"
      and EP.path_of(RR.Record(ws0.root))["type"] == "RFI")
hp.path.set_type("Draft RFP")
st = {s["key"]: s for s in hp.path.now}
check("Draft RFP: Setup and Check are not needed and count as done", not st["setup"]["on"] and st["setup"]["done"] and not st["check"]["on"])
hp.path.steps_dialog({"check": True})
st = {s["key"]: s for s in hp.path.now}
check("Steps...: switch a step on for this effort", st["check"]["on"])
check("the strip keeps the request type's note; the map above names the next step (3.96.0)", hp.path.note.text() and hp.map.next_title.text())
hp.path.set_type("RFP")
# quick note
check("Note in the top bar and Ctrl+Shift+N", w.note_btn.isVisibleTo(w) and w.note_shortcut.key().toString() == "Ctrl+Shift+N")
w.go("library"); app.processEvents()
got = __import__("skqt.quicknote", fromlist=["open_note"]).open_note(w, "Customer prefers 11 point tables.")
check("a quick note from any page, kept in Notes to sort", got and len(QN.inbox(RR.Record(ws0.root))) == 1)
got2 = __import__("skqt.quicknote", fromlist=["open_note"]).open_note(w, "Slides go to the customer 48 hours early.", f"deliverable:{slides}")
check("... or sent at once to a deliverable's discussion", got2 and any("48 hours" in e["text"] for e in DL.get(RR.Record(ws0.root), slides)["discussion"]))
w.go("home"); app.processEvents()
check("Notes to sort shows how many wait", hp.path.inbox_btn.text() == "Notes to sort (1)")
dlg = hp.path.open_inbox(run=False)
nid = QN.inbox(RR.Record(ws0.root))[0]["id"]
dlg.send(nid, "effort")
check("Notes to sort: send one to the effort's notes; it leaves the inbox", not QN.inbox(RR.Record(ws0.root))
      and any("11 point" in n["text"] for n in RR.Record(ws0.root).data["notes"]))
# meeting notes up front
hp.refresh(); app.processEvents()
check("Meeting notes up front: near the top of the dashboard, with the latest meeting", hp.shown.index("meetings") <= 2
      and hp.meetings_now == ["Kickoff"], (hp.shown[:4], getattr(hp, "meetings_now", None)))
# evaluation criteria
check("Evaluation Criteria is with Matrix & Outline (4.0.0)", __import__("skqt.mainwin", fromlist=["x"]).RAIL_OF["evalcrit"] == "matrix")
w.go("evalcrit"); app.processEvents()
ep = w.evalcrit_page
f1 = ep.add("Technical Approach", "", "Significantly more important")
f2 = ep.add("Network Operations", f1)
ep.add("Past Performance", "", "Less important")
check("add factors and subfactors with their importance", ep.table.rowCount() == 3 and ep.sumlab.text().startswith("2 factor(s), 1 subfactor(s)"))
ep.tie_dialog(f1, [vol, slides])
check("tie a factor to the deliverables it judges", F.factor(RR.Record(ws0.root), f1)["deliverables"] == [vol, slides]
      and "Volume I Technical" in ep.table.item(0, 2).text())
ep.set_importance("More important", f2)
check("set a factor's importance", F.factor(RR.Record(ws0.root), f2)["importance"] == "More important")
check("a deliverable knows the factors that judge it", [f["name"] for f in F.factors_for(RR.Record(ws0.root), vol)] == ["Technical Approach"])
w.go("home"); app.processEvents()
check("the Evaluation criteria card lists the factors", hp.eval_now == ["Technical Approach", "Past Performance"])
# the deliverables list
txt = " ".join(r_["text"] for r_ in getattr(hp, "deliv_rows", []))
check("the deliverables list carries owners, parts and people", "owner A. Lee" in txt and "1 part(s)" in txt and "K. Park" in txt, txt)
# All Efforts
s = ESUM.summarize("Kestrel", {"path": LIST}) if hasattr(ESUM, "summarize") else None
if s is None:
    fn = next(getattr(ESUM, n) for n in dir(ESUM) if n in ("summary", "effort_summary", "card"))
    s = fn("Kestrel", {"path": LIST})
check("All Efforts: the request type and the evaluation factors", s["request"] == "RFP" and s["factors"] == 2, s)

print(f"QT HOME 363 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
