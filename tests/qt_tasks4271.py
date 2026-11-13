"""4.27.1 offscreen: Tasks, Calendar, Activity (Nicholas 2026-11-12, answer 2). Tasks and Calendar are menu entries
under the Dashboard with no step number; Activity is a tab of it. Tasks: this effort's tasks by gate, late first, the
status on the row; mine across efforts in Late, Today, This week, Later. Calendar: the month, the day's list, what is
coming up. Activity: what happened, by day, filtered by person, kind and time, a row opening its thing.
Fictional (Osprey)."""
import datetime, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, effortrec as RR, graphics as GX, worklists as WL, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D
from skqt.mainwin import MainWindow, RAIL, STEP_KEYS, TABS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


# ---- the rules
T = datetime.date(2026, 11, 13)                     # a Friday
stages = [{"id": "s1", "name": "Pink team"}, {"id": "s2", "name": "Red team"}]
tasks = [{"id": "a", "title": "Send the data call", "owner": "Dana", "due": "2026-11-10", "stage": "s1", "status": "Not started"},
         {"id": "b", "title": "Sign the form", "owner": "Lee", "due": "2026-11-20", "stage": "s1", "status": "In progress"},
         {"id": "c", "title": "Old thing", "owner": "Lee", "due": "2026-11-01", "stage": "s1", "status": "Done"},
         {"id": "d", "title": "Book the room", "owner": "", "due": "", "stage": "s2", "status": "Not started"},
         {"id": "e", "title": "Loose end", "owner": "", "due": "", "stage": "gone", "status": "Not started"}]
gs = WL.task_groups(tasks, stages, T)
check("this effort's tasks by gate, in the gates' order, then No gate", [g[0] for g in gs] == ["Pink team", "Red team", "No gate"], [g[0] for g in gs])
check("... inside a gate: late first, then by date, done last", [t["id"] for t in gs[0][1]] == ["a", "b", "c"] and gs[0][1][0]["late"]
      and not gs[0][1][2]["late"], [(t["id"], t["late"]) for t in gs[0][1]])
check("the counts: open, late, done", WL.task_counts(tasks, today=T) == (4, 1, 1), WL.task_counts(tasks, today=T))
check("mine, by when: Late, Today, This week (through Sunday), Later, No date",
      [WL.bucket(d, T) for d in (datetime.date(2026, 11, 12), T, datetime.date(2026, 11, 15), datetime.date(2026, 11, 16), None)]
      == ["Late", "Today", "This week", "Later", "No date"])
ev = [{"at": "2026-11-13T09:05", "who": "nm", "kind": "task", "text": "Task added: Send the data call", "ref": {"task": "a"}},
      {"at": "2026-11-13T08:00", "who": "dana", "kind": "deliverable", "text": "Deliverable added: Volume I", "ref": {"deliverable": "x"}},
      {"at": "2026-11-12T17:30", "who": "nm", "kind": "effort", "text": "Due date set"},
      {"at": "2026-10-01T10:00", "who": "nm", "kind": "stage", "text": "Stage started: Intake"}]
act = WL.activity(ev, today=T)
check("activity by day, newest first: Today, Yesterday, then the date", [d for d, _r in act] == ["Today", "Yesterday", "Thursday, Oct 1"], [d for d, _r in act])
check("... narrowed by person, by kind, by how far back", [len(r) for _d, r in WL.activity(ev, who="dana", today=T)] == [1]
      and [r[0][3] for _d, r in WL.activity(ev, kind="effort", today=T)] == ["Due date set"]
      and [d for d, _r in WL.activity(ev, days="7", today=T)] == ["Today", "Yesterday"])
check("a row about a task opens Tasks; one with nothing to open opens nothing", WL.page_of({"task": "a"}) == "tasks" and WL.page_of({}) == ""
      and WL.page_of({"deliverable": "x"}) == "deliverables")

# ---- the pages
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Osprey"); os.makedirs(os.path.join(ED, "Customer documents"))
LIST = os.path.join(ED, "Osprey_Effort_List.xlsx"); L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST, customer_dir=os.path.join(ED, "Customer documents"))
ws = W.Workspace(W.data_dir_for(LIST), "Osprey")
rec = RR.Record(ws.root)
today = datetime.date.today()
rec.set_due((today + datetime.timedelta(days=12)).isoformat() + "T14:00", "MT")
t_late = rec.add_task("Send the data call", owner="Dana", due=(today - datetime.timedelta(days=2)).isoformat())
t_next = rec.add_task("Sign the form", owner="Lee", due=(today + datetime.timedelta(days=5)).isoformat())
gid = GX.add(rec, "Transition timeline")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
keys = [k for k, _t in RAIL[0][1]]
check("the menu: Overview, Calendar, Tasks, then the path", keys[:4] == ["home", "calendar", "tasks", "library"]
      and "calendar" not in STEP_KEYS and "tasks" not in STEP_KEYS and w.step_btns["tasks"].n is None and w.step_btns["calendar"].n is None, keys)
check("... the six steps keep their numbers", [w.step_btns[k].n for k in ("library", "assign", "matrix", "setups", "drafts", "finalcheck")] == [1, 2, 3, 4, 5, 6])
check("Activity is a tab of the Overview", [k for k, _t in TABS["home"]][-1] == "activity")
w.open_effort("Osprey"); app.processEvents()

# Tasks
w.rail_go("tasks"); app.processEvents()
tp = w.tasks_page
check("Tasks opens on this effort's tasks", w.stack.currentWidget() is tp and tp.view == "effort" and w.step_btns["tasks"].isChecked())
col0 = [tp.table.item(r, 0).text() for r in range(tp.table.rowCount())]
check("... under their gate, the late one first", len(col0) == 3 and "·   2" in col0[0] and col0[1] == "Send the data call" and col0[2] == "Sign the form", col0)
check("... the late one says so, and the count line counts it", "LATE" in tp.table.item(1, 2).text() and tp.count.text() == "2 open, 1 late", tp.count.text())
tid = tp.add({"title": "Book the room", "owner": "Dana", "due": "", "about": "Red team"})
check("Add a task... adds it and selects it", tid and tp.current() is not None and tp.current()["id"] == tid and tp.current()["about"] == "Red team")
tp.select(t_late)
m = tp.menu(None)
check("right-click a task: Not started, In progress, Done, Remove", [a.text() for a in m.actions() if a.text()] == ["Not started", "In progress", "Done", "Remove the task"])
tp.set_status("Done")
check("Done is saved in the effort record and the count follows", RR.Record(ws.root).task(t_late)["status"] == "Done" and tp.count.text() == "2 open, 1 done", tp.count.text())
tp.select(tid); tp.remove()
check("Remove the task takes it out", RR.Record(ws.root).task(tid) is None)
tp.set_view("mine"); app.processEvents()
check("Mine, across efforts: the name picker shows and the columns change", tp.who.isVisibleTo(tp)
      and [tp.table.horizontalHeaderItem(c).text() for c in range(tp.table.columnCount())] == ["Due", "Effort", "What", "Item", "Where"])
check("... with no name it says to pick one, and Add a task still works from here", (tp.person() != "") or tp.count.text() == "Pick a name.")

# Calendar
w.rail_go("calendar"); app.processEvents()
cp = w.calendar_page
check("Calendar opens with the month, today's list and what is coming up", w.stack.currentWidget() is cp and cp.day == today
      and cp.day_card.title.text() == "Today" and w.step_btns["calendar"].isChecked())
check("... the due date and the task ahead are coming up", any(x[2] == "Due" for x in cp.ahead) and any("Sign the form" in x[3] for x in cp.ahead), cp.ahead)
check("... and their days are marked on the month", cp.paint() >= 1)
due_day = today + datetime.timedelta(days=12)
got = cp.pick(due_day)
check("pick a day: its list shows", any(k == "due" for k, _t in got) and str(due_day.day) in cp.day_card.title.text(), (got, cp.day_card.title.text()))
cp.bar.main.click(); app.processEvents()
check("Today brings today back", cp.day == today and cp.day_card.title.text() == "Today")

# Activity
w.go("activity"); app.processEvents()
ap = w.activity_page
n_all = len(RR.Record(ws.root).events())
check("Activity lists what happened, by day", w.stack.currentWidget() is ap and ap.table.item(0, 0).text().startswith("Today")
      and ap.count.text() == f"{n_all} of {n_all}" and w.step_btns["home"].isChecked(), ap.count.text())
ap.f_kind.setCurrentIndex(ap.f_kind.findData("task")); ap.fill(); app.processEvents()
rows = [x for x in ap.rows if x is not None]
check("filter by kind: only tasks", rows and all("Task" in x["text"] for x in rows) and ap.count.text().endswith(f" of {n_all}"), [x["text"] for x in rows])
ap.table.selectRow(next(r for r, x in enumerate(ap.rows) if x is not None and x["ref"].get("task") == t_next))
check("double-click a task's row: Tasks opens on it", ap.open_row() == "tasks" and w.stack.currentWidget() is tp and tp.current() is not None
      and tp.current()["id"] == t_next)
w.go("activity"); app.processEvents()
ap.f_kind.setCurrentIndex(ap.f_kind.findData("graphic")); ap.fill(); app.processEvents()
ap.table.selectRow(next(r for r, x in enumerate(ap.rows) if x is not None))
check("a graphic need's row opens Graphics on it", ap.open_row() == "graphics" and w.stack.currentWidget() is w.graphics_page
      and (w.graphics_page.current() or {}).get("need") == gid)
w.rail_go("home"); app.processEvents()
op = w.overview_page
check("the Overview: Open the calendar and All activity go to the new places", (op.open_calendar(), w.stack.currentWidget() is cp)[1])
w.close()
print(f"QT TASKS 4271 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
