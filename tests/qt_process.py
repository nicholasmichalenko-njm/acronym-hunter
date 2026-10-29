"""2.93.0 stages, gates and roles, offscreen: Settings > Stages, gates and roles (default stages for new efforts, the
gate choices with what each does and means, the role list; the built-in gates stay); a new effort starts with the
team's stages and gates; the stage table picks dates from a calendar with optional times and a readable Stage column; a
stage that ends before it starts is refused; gate goals and tasks take a deadline and an owner, accepted only inside the
stage's dates with the reason when not; deadlines show on the calendar and in the readable copy; each person's role on
the effort saves when picked (Effort Record and Effort Home > People and roles...); a team pack carries the settings."""
import datetime, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effortrec as RR, process as PR, teampack as TP, readable as RD, office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
from skqt import stagesedit as SE

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


check("times are read as people write them", [SE.parse_hm(x) for x in ("2:30 PM", "2:30pm", "14:30", "2 pm", "12 am", "Any time", "", "25:00", "noonish")]
      == ["14:30", "14:30", "14:30", "14:00", "00:00", "", "", None, None])
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
sp = w.settings_page
pc = sp.process_card
check("Settings has a Stages, gates and roles card with the built-in ones", pc.st.rowCount() == len(PR.DEFAULT_STAGES)
      and pc.gt.rowCount() == 3 and pc.rl.count() == len(PR.DEFAULT_ROLES))
check("Settings has a Go to row that reaches it", sp.focus_process() is pc and any(
    sp.jump_row.itemAt(i).widget() and sp.jump_row.itemAt(i).widget().text() == "Stages, gates and roles" for i in range(sp.jump_row.count())))
pc.gt.setCurrentCell(0, 0)
check("a built-in gate cannot be removed", not pc.remove_gate() and pc.gt.rowCount() == 3)
pc.gt.item(1, 0).setText("Soft gate: log and move on")
i = pc.add_gate("Color team sign-off", "hard", "The capture lead signs the color team findings")
check("a new gate shows in the stage gate choices at once", pc.st.cellWidget(0, 1).findText("Color team sign-off") >= 0)
pc.st.item(1, 0).setText("Pink team")
pc.st.cellWidget(1, 1).setCurrentIndex(pc.st.cellWidget(1, 1).findText("Color team sign-off"))
pc.add_stage("Blue team")
pc.add_role("Book Boss")
check("Save keeps the stages, gates and roles", pc.save())
P = PR.load(cfg)
gid = next(g["id"] for g in P["gates"] if g["name"] == "Color team sign-off")
check("... the new gate holds and does what it says", next(g for g in P["gates"] if g["id"] == gid)["behavior"] == "hard"
      and RR.GATES[gid] == "Color team sign-off" and RR.GATE_ABOUT[gid].startswith("The capture lead"))
check("... a built-in gate keeps what it does under its new name", RR.GATES["soft"] == "Soft gate: log and move on" and RR.GATE_BEHAVIOR["soft"] == "soft")
check("... the default stages and roles", [n for n, _g in P["stages"]][1] == "Pink team" and P["stages"][1][1] == gid
      and P["stages"][-1][0] == "Blue team" and P["roles"][-1] == "Book Boss")

# a new effort starts with them
L = os.path.join(tmp, "Efforts", "Osprey", "Osprey_Effort_List.xlsx")
sp.new_effort({"name": "Osprey", "path": L})
r = RR.Record(w.ws.root)
check("a new effort starts with the team's stages and gates", [s["name"] for s in r.stages][1] == "Pink team" and r.gate_id(r.stages[1]) == gid
      and r.gate_of(r.stages[1]) == "hard" and r.stages[-1]["name"] == "Blue team")

# the stage table
rp = w.record_page; w.go("record"); app.processEvents()
t = rp.stage_table
check("the stage table: Stage, Starts, Ends, Gate; the Stage column is not stretched", [t.horizontalHeaderItem(c).text() for c in range(4)]
      == ["Stage", "Starts", "Ends", "Gate"] and t.columnWidth(0) < 320, t.columnWidth(0))
c0 = t.cellWidget(0, 1)
check("an empty date says Not set, and its time waits for a date", c0.btn.text() == "Not set" and not c0.time.isEnabled())
m = c0.pick(run=False)
check("clicking a date opens a calendar with Clear", any(a.text() == "Clear the date" for a in m.actions()))
today = datetime.date.today()
c0.set_date(today); c0.time.setCurrentText("8:00 AM")
check("a picked date shows and its time can be set", c0.btn.text().startswith(today.strftime("%b")) and c0.time.isEnabled() and c0.value() == (today.isoformat(), "08:00"))
t.cellWidget(0, 2).set_value((today + datetime.timedelta(days=2)).isoformat(), "17:00")
t.cellWidget(1, 1).set_value((today + datetime.timedelta(days=3)).isoformat(), "")
t.cellWidget(1, 2).set_value((today + datetime.timedelta(days=1)).isoformat(), "")
check("a stage that ends before it starts is refused", not rp.save_stages() and "ends before it starts" in " ".join(rp.stage_problems()))
t.cellWidget(1, 2).set_value((today + datetime.timedelta(days=6)).isoformat(), "12:00")
ok = rp.save_stages()
check("Save stages keeps dates and times", ok)
r = RR.Record(w.ws.root)
s0, s1 = r.stages[0], r.stages[1]
check("... the times are kept", s0["planned"] == today.isoformat() and s0["planned_time"] == "08:00" and s0["planned_end_time"] == "17:00"
      and s1["planned_time"] == "" and s1["planned_end_time"] == "12:00", (s0, s1))
if os.environ.get("SHOT_DIR"):
    rp.refresh(); rp.scroll_to = getattr(rp, "scroll_to", None); rp.stages.parentWidget()
    from PySide6.QtWidgets import QScrollArea
    sa = rp.findChild(QScrollArea)
    if sa: sa.ensureWidgetVisible(rp.stages, 0, 0)
    app.processEvents(); w.grab().save(os.path.join(os.environ["SHOT_DIR"], "stages.png"))
    w.go("settings"); sp.focus_process(); app.processEvents(); w.grab().save(os.path.join(os.environ["SHOT_DIR"], "process.png")); w.go("record")
check("the stage's window reads plainly", r.window_text(s0).endswith("5:00 p.m.") and " to " in r.window_text(s0), r.window_text(s0))

# gate goal deadlines
w.go("home"); app.processEvents()
hp = w.home_page
w.authors.merge([("A. Lee", None), ("K. Park", None)], default=["Osprey"])
out = (today + datetime.timedelta(days=4)).isoformat() + "T09:00"
gid0 = hp.goal_dialog(text="Kickoff held with every lead")
hp.goal_dialog(gid0, due=out, owner="A. Lee")
g = next(x for x in RR.Record(w.ws.root).stage()["goals"] if x["id"] == gid0)
check("a gate goal deadline after the stage ends is refused, with the stage's dates", not g.get("due") and "runs" in hp.goal_problem
      and "pick a time inside it" in hp.goal_problem, hp.goal_problem)
check("... and nothing of that change is kept", not g.get("owner"))
inside = (today + datetime.timedelta(days=1)).isoformat() + "T15:00"
hp.goal_dialog(gid0, due=inside, owner="A. Lee")
g = next(x for x in RR.Record(w.ws.root).stage()["goals"] if x["id"] == gid0)
check("a deadline inside the stage is kept, with its owner", g.get("due") == inside and g.get("owner") == "A. Lee" and not hp.goal_problem)
d = hp._goal_box(g, run=False)
check("the goal dialog shows the owner, the deadline and the stage's dates", d.api["owner"].currentText() == "A. Lee" and d.api["deadline"].has.isChecked()
      and any(" runs " in l.text() for l in d.findChildren(type(d.api["error"]))))
d.api["deadline"].date.setDate(today + datetime.timedelta(days=9))
why = d.api["check"]()
check("... and keeps itself open on a deadline outside them", bool(why) and d.api["error"].isVisibleTo(d) and d.result() == 0, why)
d.deleteLater()
check("the goal shows its owner and deadline on Effort Home", any("A. Lee | due " in l.text() for l in hp.goals.findChildren(type(d.api["error"]))))
cal = RR.Record(w.ws.root).calendar()
check("the goal deadline is on the calendar with its time", any("Gate goal" in txt and "3:00 p.m." in txt for x in cal.values() for _k, txt in x), cal)
# tasks
nt = hp.save_task(None, {"title": "Book the room", "owner": "K. Park", "due": (today + datetime.timedelta(days=5)).isoformat(),
                         "status": "Not started", "stage": r.stages[0]["id"], "notes": ""})
check("a task due after its stage ends is refused", nt is None and r.stages[0]["name"] in hp.task_problem)
nt = hp.save_task(None, {"title": "Book the room", "owner": "K. Park", "due": today.isoformat() + "T16:30",
                         "status": "Not started", "stage": r.stages[0]["id"], "notes": ""})
check("a task due inside its stage, with a time, is kept", nt and RR.Record(w.ws.root).task(nt)["due"].endswith("T16:30"))
# changing the stage's dates afterwards: the deadlines outside are named
t = rp.stage_table; rp.refresh()
t.cellWidget(0, 2).set_value(today.isoformat(), "10:00")
rp.save_stages()
check("stage dates moved past a deadline: it is named, not lost", any(x["text"] == "Book the room" for x in RR.Record(w.ws.root).deadlines_outside()))
files = RD.build(rec=RR.Record(w.ws.root))
head, rows = files["Stages and gate goals.csv"]
check("the readable copy carries the stage's start and end, gate, goal owner and deadline",
      {"Planned start", "Planned end", "Gate", "Goal owner", "Goal deadline"} <= set(head)
      and any(rw[head.index("Goal deadline")] == inside.replace("T", " ") for rw in rows))

# roles
w.go("record"); app.processEvents(); rp.fill_team()
box = rp.team_roles.role_box("A. Lee")
check("each person has a role drop-down with the team's roles", box is not None and box.findText("Book Boss") >= 0 and box.isEditable())
box.setCurrentText("Volume Lead"); box.activated.emit(box.currentIndex())
check("a role saves the moment it is picked", RR.Record(w.ws.root).role_of("A. Lee") == "Volume Lead")
dlg = w.home_page.banner.people_roles(run=False)
b2 = dlg.roles.role_box("K. Park")
b2.setCurrentText("Red team reviewer"); b2.lineEdit().editingFinished.emit()
check("Effort Home > People and roles...: a typed role saves too", RR.Record(w.ws.root).role_of("K. Park") == "Red team reviewer"
      and dlg.roles.role_box("A. Lee").currentText() == "Volume Lead")
dlg.deleteLater()
check("the role change is on the timeline", any("Role: A. Lee is Volume Lead" in e["text"] for e in RR.Record(w.ws.root).events()))

# the team pack
pk = os.path.join(tmp, "team.zip")
TP.make(cfg, pk, ["process"], lock=["process"], name="Proposal Center")
cfgB = os.path.join(tmp, "pcB"); os.makedirs(cfgB)
info, data = TP.read(pk)
said = dict(TP.preview(cfgB, info, data))
check("a team pack carries Stages, gates and roles", "process" in info["parts"] and "process" in said)
TP.install(cfgB, info, data)
PB = PR.load(cfgB)
check("... installed on another PC", any(g["name"] == "Color team sign-off" for g in PB["gates"]) and "Book Boss" in PB["roles"]
      and TP.locked(cfgB, "process"))
PR.apply(cfg)
sp.process_card.fill()
check("Put back the built-in ones resets the card (not saved until Save)", sp.process_card.reset(answer=True) and sp.process_card.gt.rowCount() == 3
      and len(PR.load(cfg)["gates"]) == 4)
n = sum(checks)
print(f"QT PROCESS {'PASS' if all(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
