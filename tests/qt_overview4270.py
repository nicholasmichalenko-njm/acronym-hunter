"""4.27.0 offscreen: the effort's page on one screen (Nicholas's recording 2026-11-12; answer 20). The Dashboard entry
opens the Overview: your next step and the path, up to four counts that open where each is fixed, the deliverables one
row each, the Wall of Truth as a line, the calendar's next dated things, the customer, the last three things that
happened. The cards the Dashboard had are the next tab, All cards. Fictional (Osprey)."""
import datetime, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import deliverables as DL, effort as E, effortrec as RR, overview as OV, walloftruth as WT, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D
from skqt.mainwin import MainWindow, TABS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


# ---- the rules, with no window
T = datetime.date(2026, 11, 13)
f = {"reqs": {"undecided": 28, "reqs": 12, "placed": 8}, "compare": 0, "acronyms": 5}
nums = OV.numbers(f, late_tasks=3, graphics_left=2, questions=9)
check("up to four counts, none that is zero, each with the page that fixes it", nums == [(28, "not shredded", "assign"), (4, "to place", "place"),
                                                                                    (3, "tasks late", "home"), (5, "acros and abs undecided", "acronyms")], nums)
check("nothing waiting: no counts", OV.numbers({"reqs": None}) == [])
cal = {T: [("task", "Call the teammate"), ("event", "Deliverable added")], T + datetime.timedelta(days=1): [("questions", "Questions due 2:00 p.m.")],
       T + datetime.timedelta(days=3): [("done", "Kickoff held")], T + datetime.timedelta(days=12): [("due", "Proposal due")],
       T - datetime.timedelta(days=2): [("task", "Old")]}
ds = OV.dates(cal, T)
check("the next dated things: today first, nothing past, nothing done, nothing that only happened", [(x[1], x[2]) for x in ds] == [("Today", "Task"), ("Tomorrow", "Questions due"),
                                                                                                      ("Nov 25", "Due")], ds)
check("the due date in words", OV.due_words(12) == "Due in 12 days" and OV.due_words(1) == "Due in 1 day" and OV.due_words(0) == "Due today"
      and OV.due_words(-2) == "Due 2 days ago" and OV.due_words(None) == "No due date yet")
rows = OV.deliverables([{"id": "a", "name": "Volume I", "owner": "Dana", "status": "Draft"}, {"id": "b", "name": "Pricing form", "owner": "", "status": "Not started"},
                        {"id": "c", "name": "SOW redline", "owner": "Lee", "status": "Draft"}],
                       [{"changed": [], "over": False}, {"changed": [], "over": False}, {"changed": ["changed in SOW, Amd1"], "over": False}])
check("deliverables: one row each, what changed first, then the ones with no owner", [r[1] for r in rows] == ["SOW redline", "Pricing form", "Volume I"]
      and rows[0][4] == "changed in SOW, Amd1" and rows[1][2] == "No owner", rows)
cu = OV.customer("Osprey Systems Command", "OSC-26-R-0042", [{"name": "Pat Ray", "title": "Contracting Officer", "org": "OSC", "email": [{"label": "Office", "value": "pat.ray@example.test"}]}], [{"id": 1}])
check("the customer: who, the solicitation, a contact with one way to reach them, how much is filed",
      cu[0] == ("Customer", "Osprey Systems Command") and cu[1][1] == "OSC-26-R-0042" and "Pat Ray, Contracting Officer" in cu[2][1]
      and "pat.ray@example.test" in cu[2][1] and cu[3][1].startswith("1 fact"), cu)
check("the last three things that happened", OV.activity([{"at": "2026-11-13T09:05", "who": "nm", "text": "Due date set"}] * 5) ==
      [("2026-11-13 09:05", "nm", "Due date set")] * 3)

# ---- the page
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Osprey"); os.makedirs(os.path.join(ED, "Customer documents"))
LIST = os.path.join(ED, "Osprey_Effort_List.xlsx"); L = E.EffortList(LIST, "Osprey"); L.client = "Osprey Systems Command"
L.solicitation = "OSC-26-R-0042"; L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST, customer_dir=os.path.join(ED, "Customer documents"))
ws = W.Workspace(W.data_dir_for(LIST), "Osprey")
rec = RR.Record(ws.root)
due = (datetime.date.today() + datetime.timedelta(days=12)).isoformat() + "T14:00"
rec.set_due(due, "MT")
DL.add(rec, "Volume I Technical", kind="Volume", owner="Dana")
DL.add(rec, "Pricing form", kind="Customer file")
rec.save_contact({"name": "Pat Ray", "title": "Contracting Officer", "org": "OSC"})
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
check("the Dashboard's tabs: Overview first, then All cards, Deliverables, Effort Record, Meetings",
      [k for k, _t in TABS["home"]] == ["overview", "home", "deliverables", "record", "meetings"] and dict(TABS["home"])["home"] == "All cards")
w.open_effort("Osprey"); app.processEvents()
w.rail_go("home"); app.processEvents()
op = w.overview_page
check("the Dashboard entry opens the Overview, and the entry stays lit", w.stack.currentWidget() is op and w.step_btns["home"].isChecked()
      and w._tab_keys[:2] == ["overview", "home"], w._tab_keys)
d = op.data
check("the head: the effort, its customer and solicitation, how long is left", op.name.text() == "Osprey" and "Osprey Systems Command" in op.sub.text()
      and "OSC-26-R-0042" in op.sub.text() and op.due.text().startswith("Due in 12 days"), (op.sub.text(), op.due.text()))
check("your next step: with no documents, add them", d["next"] is not None and op.next_title.text() == d["next"]["title"]
      and op.next_btn.text() == d["next"]["button"] and "document" in op.next_title.text().lower(), op.next_title.text())
check("the path under it: the six steps, each with what is left", list(op.path_btns) == ["library", "assign", "matrix", "setups", "drafts", "finalcheck"]
      and "Documents" in op.path_btns["library"].text(), [b.text() for b in op.path_btns.values()])
op.path_btns["assign"].click(); app.processEvents()
check("... a step opens its page", w.stack.currentWidget() is w.assign_page)
w.rail_go("home"); app.processEvents()
check("deliverables: one row each", "Deliverables   2" == op.deliv.title.text() and len(d["deliverables"]) == 2 and d["deliverables"][0][1] == "Pricing form",
      d["deliverables"])
check("the calendar has the due date ahead", any(x[2] == "Due" and "Proposal due" in x[3] for x in d["dates"]), d["dates"])
check("the customer card names the customer and folds", op.cust_line.text() == "Osprey Systems Command" and not op.cust_w.isVisibleTo(op)
      and op.fold_customer() and op.cust_w.isVisibleTo(op) and any("Pat Ray" in b for _a, b in d["customer"]))
check("latest activity: three lines at most, newest first", 1 <= len(d["activity"]) <= 3 and d["activity"][0][0] >= d["activity"][-1][0], d["activity"])
check("the Wall of Truth is a line that stays up (none yet)", op.truth.isVisibleTo(op) and "Wall of Truth   0" == op.truth_title.text())
WT.add(RR.Record(ws.root), "Staff on the program", "412")
op.refresh(); app.processEvents()
check("... a fact on the wall shows in it", "412" in op.truth_body.text() and op.truth_title.text() == "Wall of Truth   1",
      op.truth_body.text())
got = op.set_due((datetime.date.today() + datetime.timedelta(days=3)).isoformat() + "T10:00")
check("click the due date: set here", got and op.due.text().startswith("Due in 3 days"), op.due.text())
op.next_btn.click(); app.processEvents()
check("the next step's button opens its page", w.stack.currentWidget() is w.pages[d["next"]["go"]])
w.go("home"); app.processEvents()
check("All cards is the Dashboard as it was", w.stack.currentWidget() is w.home_page and w._tab_keys[:2] == ["overview", "home"])
w.close()
print(f"QT OVERVIEW 4270 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
