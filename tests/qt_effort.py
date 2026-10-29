"""2.62.0 Effort home and the effort dashboard in Qt: the stage track, gate goals (the app ticks what it can check),
tasks, notes and questions, customer information, the calendar and the timeline, all kept in the effort's record
(the same file the classic window reads); the dashboard counts days to the due date and to each stage, gate goals,
requirements placed and owned, coverage by volume, open questions, acronyms and banned words, and what is past due."""
import datetime, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "dark"
import app_gui as A
import compliance as C, effort as E, effortrec as RR, effortstate as ES, setupdoc as SD, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


today = datetime.date.today()
tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel")
for term, d in (("IMS", "Integrated Master Schedule"), ("CDR", "Critical Design Review"), ("TBD", "To Be Determined")):
    L.add_or_update(term, Definition=d)
L.set_status(["IMS"], "Approved", approver="QA")
L.set_status(["TBD"], "Rejected")
L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
ws0.set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Management\nVolume II Past Performance")
ws0.save_session({"volume_report": {"summary": {"volumes": 2, "first_use_problems": 3, "banned_checked": True,
                                                "banned": {"bad": 2, "warn": 1}, "missing": 0, "not_approved": 1},
                                    "pages": [{"level": "bad"}, {"level": "ok"}]}})
rec = RR.Record(ws0.root)
rec.set_due((today + datetime.timedelta(days=20)).isoformat() + "T14:00", "Mountain Time")
rows = [(s["id"], s["name"], s["planned"]) for s in rec.stages]
rows[0] = (rows[0][0], rows[0][1], (today - datetime.timedelta(days=6)).isoformat(), (today - datetime.timedelta(days=2)).isoformat())
rows[1] = (rows[1][0], rows[1][1], (today + datetime.timedelta(days=4)).isoformat(), (today + datetime.timedelta(days=9)).isoformat())
rows[2] = (rows[2][0], rows[2][1], (today - datetime.timedelta(days=1)).isoformat(), "")
rec.edit_stages(rows)
late = rec.add_task("Send the kickoff notes", owner="A. Lee", due=(today - datetime.timedelta(days=2)).isoformat())
rec.add_task("Draft the management volume", owner="K. Park", due=(today + datetime.timedelta(days=5)).isoformat())
q = rec.add_note("Is the oral presentation in scope?", question=True)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
check("the rail starts with Effort home, Deliverables and Dashboard", list(w.step_btns)[1:4] == ["home", "deliverables", "dashboard"])
w.open_effort("Kestrel")
B = os.path.join(A.BASE_DIR, "test_samples", "rfp")
w.read_page.read([os.path.join(B, "Kestrel_RFP_Sections_C_L_M.docx")], os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
t = time.time()
while w.review is None and time.time() - t < 60:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
by = lambda s: next(it for it in M.items if s in it["text"])
R = w.review
a, b = by("thermal design"), by("Integrated Master Schedule")
R.req([a], "1.1 Technical Approach"); R.req([b], "1.2 Management")
SD.set_people(M, "1.1 Technical Approach", lead="A. Lee")
extra = next(it for it in M.items if it["decision"] == "" and it is not a and it is not b and len(it["text"]) > 40)
C.assign_requirement(M.items, [extra], "")
w.changed(); w.save_now()

# Effort home
w.go("home"); app.processEvents()
hp = w.home_page
check("Effort home shows the due date and the countdown", "Due " in hp.due.text() and ("MST" in hp.due.text() or "MDT" in hp.due.text()), hp.due.text())
check("the stage track: one box per stage", hp.track_row.count() == len(rec.stages))
check("the current stage is past its planned end (days past plan)",
      any("2 days past plan" in l.text() for i in range(hp.track_row.count()) for l in hp.track_row.itemAt(i).widget().findChildren(QLabel)))
check("the move button names the next stage", hp.move_btn.text() == f"Move to {rec.stages[1]['name']}...", hp.move_btn.text())
check("gate goals: the app's checks (customer documents not added yet: open)", "gate goals" in hp.goals.title.text())
gid = hp.goal_dialog(text="Kickoff held with every section lead")
r2 = RR.Record(ws0.root)
check("+ Goal is kept in the record", any(g["text"] == "Kickoff held with every section lead" for g in r2.stage()["goals"]))
hp.set_goal(gid, True)
check("ticking a goal records who and when", next(g for g in RR.Record(ws0.root).stage()["goals"] if g["id"] == gid)["done"])
# 2.86.0: click a goal to change it: its wording, remove it, or tick an app-checked goal by hand
from skqt.homepage import ClickLabel
labs = [l for l in hp.goals.findChildren(ClickLabel)]
check("each goal's wording is clickable", any("Kickoff held" in l.text() for l in labs))
hp.goal_dialog(gid, text="Kickoff held with every section lead and the PM")
check("change its wording", any(g["text"].endswith("and the PM") for g in RR.Record(ws0.root).stage()["goals"]))
auto = next(g for g in RR.Record(ws0.root).stage()["goals"] if g.get("auto"))
hp.goal_dialog(auto["id"], action="manual")
check("an app-checked goal can be ticked by hand instead", not next(g for g in RR.Record(ws0.root).stage()["goals"] if g["id"] == auto["id"])["auto"])
n0 = len(RR.Record(ws0.root).stage()["goals"])
hp.goal_dialog(auto["id"], action="remove")
check("and removed", len(RR.Record(ws0.root).stage()["goals"]) == n0 - 1)
keys = hp.save_defaults(answer=True)
import effortrec as ER
check("this stage's goals become the default for new efforts", bool(keys)
      and ER.Record._new_stage(RR.Record(ws0.root).stage()["name"])["goals"][-1]["text"].endswith("and the PM"))
check("tasks: the late one is marked late", "1 open" not in hp.tasks.title.text() and "2 open" in hp.tasks.title.text())
dlg = hp.task_dialog(late, run=False)
check("the task dialog opens on the task", dlg.api["title"].text() == "Send the kickoff notes" and dlg.api["has_due"].isChecked())
dlg.api["status"].setCurrentText("Done"); hp.save_task(late, dlg.api["values"]()); dlg.deleteLater()
check("a task marked done in the dialog is done in the record", RR.Record(ws0.root).task(late)["status"] == "Done")
nt = hp.save_task(None, {"title": "Pink team comments", "owner": "K. Park", "due": (today + datetime.timedelta(days=3)).isoformat(),
                         "status": "In progress", "stage": rec.data["stage"], "notes": ""})
check("+ Task with an owner, a due date and a status", RR.Record(ws0.root).task(nt)["status"] == "In progress")
hp.who.setCurrentText("K. Park"); hp.refresh()
check("Show for one person: only their tasks, with what they own", "2 open" in hp.tasks.title.text())
hp.who.setCurrentText("Everyone"); hp.refresh()
hp.assign_dialog(q, "A. Lee")
check("a question assigned to someone", RR.Record(ws0.root).open_questions(assignee="A. Lee"))
n2 = hp.note_dialog(question=True, text="Do we need a cost volume template?")
check("+ Question", len(RR.Record(ws0.root).open_questions()) == 2 and "2 open" in hp.notes.title.text())
hp.resolve_dialog(n2, "Yes: Attachment J-4")
check("Resolve keeps the answer", next(n for n in RR.Record(ws0.root).notes() if n["id"] == n2).get("answer") == "Yes: Attachment J-4")
added = hp.info_dialog("Contracting officer: J. Smith, j.smith@example.gov, 303-555-0100")
check("customer information is filed by kind", {c["kind"] for c in added} >= {"E-mail", "Phone"}, [c["kind"] for c in added])
days = hp.paint_calendar()
due_d = today + datetime.timedelta(days=20)
hp.cal.setCurrentPage(due_d.year, due_d.month); app.processEvents()
days = hp.paint_calendar()
check("the calendar marks the due date", any(k == "due" for k, _t in days.get(due_d, [])))
check("the day's text format is set (colored, bold)", hp.cal.dateTextFormat(QDate(due_d)).fontWeight() == 700)
items = hp.pick_day(due_d) and hp.show_day()
check("picking a day lists what falls on it", any("Proposal due" in t for _k, t in items), items)
check("the timeline lists the latest first", hp.sections["timeline"].count() >= 5)
ok = hp.move_stage(rec.stages[1]["id"], carry=[])
check("Move stage moves the effort", ok and RR.Record(ws0.root).stage()["name"] == rec.stages[1]["name"])

# the effort dashboard
w.go("dashboard"); app.processEvents()
dp = w.dash_page
d = dp.data
check("dashboard: days to the due date", d["days_to_due"] == 20 and dp.tiles["due"].value.text() == "20")
check("dashboard: requirements placed and owned", d["reqs"]["reqs"] == 3 and d["reqs"]["placed"] == 2 and d["reqs"]["owned"] == 1
      and dp.tiles["placed"].value.text() == "2 of 3", d["reqs"])
vols = {v["volume"]: v for v in d["volumes"]}
check("coverage by volume: Volume I has both, one placed nowhere", vols["Volume I Technical"]["reqs"] == 2
      and vols["Not in a section"]["reqs"] == 1 and dp.vol_table.rowCount() == len(d["volumes"]), d["volumes"])
check("open questions counted", d["questions"] == 1 and dp.tiles["questions"].value.text() == "1")
st = {s["name"]: s for s in d["stages"]}
s2 = rec.stages[2]["name"]
check("a stage that should have started is flagged", st[s2]["late_start"] and any("planned to start" in x[1] for x in d["past_due"]), d["past_due"])
check("days to each stage and days left in the current one", st[rec.stages[1]["name"]]["left"] == 9, st[rec.stages[1]["name"]])
check("acronyms counted by status", d["acronyms"]["Approved"] == 1 and d["acronyms"]["Proposed"] == 1 and d["acronyms"]["Rejected"] == 1)
check("banned words from the last QA/QC check", d["qa"]["banned"] == 2 and d["qa"]["avoid"] == 1 and d["qa"]["pages_over"] == 1)
check("QA/QC tiles shown", dp.qa_row.count() == 4)
check("who has what: A. Lee leads a section and owns requirements", any(p["person"] == "A. Lee" and p["sections"] == 1 and p["reqs"] >= 1
                                                                        for p in d["people"]), d["people"])
dp.tiles["questions"].on_click(); app.processEvents()
check("clicking a number goes where it is worked", w.stack.currentWidget() is hp)
# the same checks drive the classic window's goals
c = ES.checks_of(RR.Record(ws0.root), M)
check("the shared checks: the structure is set, not every requirement placed", c["structure_set"] is True and c["reqs_placed"] is False, c)
check("prove items come from one place", len(ES.prove_items(M, "nosection")) == 1)
# no effort: empty states
w.close_effort(); w.go("dashboard"); app.processEvents()
check("no effort: the dashboard says so", dp.empty.isVisibleTo(dp) and not dp.body.isVisibleTo(dp))
w.close()
n = sum(checks)
print(f"QT EFFORT PASS ({n}/{len(checks)})" if n == len(checks) else f"QT EFFORT FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
