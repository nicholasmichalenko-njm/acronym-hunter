"""4.80.0 (E3): Effort Settings > Stages and reviews. The line of stages across the top (a block per stage with its
planned dates, the current one outlined), the table with Planned start, Planned end and Gate, drag to reorder (stages
still ahead only), remove that asks first, Add stage with a blank stage or the standard reviews, "Gate passed" with a
date, and only the proposal manager changes the plan (anyone when none is named). Fictional (Kestrel)."""
import datetime, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
import app_gui as A
import branding as BR, effort as E, effortrec as RR, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
ASKED = []
ANSWER = [QMessageBox.Yes]
QMessageBox.question = staticmethod(lambda *a, **k: (ASKED.append(a[2] if len(a) > 2 else ""), ANSWER[0])[1])
from skqt import design as theme, modes, stagesplan as SP
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel")
app = QApplication([]); theme.apply(app)
modes.save(my_name="")
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Kestrel"); app.processEvents()
rp = w.record_page
w.go("record"); app.processEvents()
t = rp.stage_table
rec = lambda: RR.Record(w.ws.root)
names = lambda: [s["name"] for s in rec().stages]

check("the table: Stage, Planned start, Planned end, Gate", [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]
      == ["Stage", "Planned start", "Planned end", "Gate"], [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())])
check("... his stages stay the default, every gate None", names() == list(RR.DEFAULT_STAGES)
      and all(t.item(i, 3).text() == "None" for i in range(t.rowCount())), [t.item(i, 3).text() for i in range(t.rowCount())])
line = rp.stages_line.texts()
check("the line: one block per stage in order, the current one first", len(line) == len(names()) and line[0][1] == "current"
      and all(x[1] == "ahead" for x in line[1:]) and line[0][0].startswith("Intake"), line)
check("... a stage with no dates says so", "No dates yet" in line[1][0], line[1])
check("the color is in the panel, not the table", rp.stage_panel.color is not None and t.columnCount() == 4)
check("the panel's gate says the same words as the table", [rp.stage_panel.gate.itemText(i) for i in range(rp.stage_panel.gate.count())][:3]
      == ["None", "Soft", "Hard"], [rp.stage_panel.gate.itemText(i) for i in range(rp.stage_panel.gate.count())])

# planned dates show on the line
rp.set_stage(2, start=("2026-12-01", ""), end=("2026-12-05", "")); rp.flush()
check("planned dates are kept and shown on the line", rec().stages[2]["planned"] == "2026-12-01"
      and "Dec 1 to Dec 5" in rp.stages_line.texts()[2][0], rp.stages_line.texts()[2])

# Add stage
acts = [a.text() for a in rp.add_stage_btn.menu().actions() if a.text()]
check("Add stage offers a blank stage and the six standard reviews, each with its purpose", acts[0] == "Blank stage" and len(acts) == 7
      and "Pink team: storyboards and early draft" in acts and "White glove: final production proofread" in acts, acts)
t.setCurrentCell(0, 0)
next(a for a in rp.add_stage_btn.menu().actions() if a.data() == "Pink team").trigger(); rp.flush()
check("a standard review goes after the selected stage", names()[1] == "Pink team" and len(names()) == len(RR.DEFAULT_STAGES) + 1, names())
check("... with no gate", RR.Record(w.ws.root).gate_id(rec().stages[1]) == "")
t.setCurrentCell(len(names()) - 1, 0)
rp.add_stage_here("New stage", rename=True); rp.flush()
check("a blank stage is added after the selected one, ready to rename", names()[-1] == "New stage" and t.currentRow() == len(names()) - 1)
t.item(t.rowCount() - 1, 0).setText("Cost review"); rp.flush()
check("rename in place: the name typed in the table is kept", names()[-1] == "Cost review", names())

# drag to reorder: stages still ahead only
n = t.rowCount()
t.moved.emit(n - 1, 2); rp.flush()
check("a stage dropped in a new place moves there", names()[2] == "Cost review", names())
check("the current stage keeps its place", not rp.move_row_to(0, 3) and names()[0] == "Intake")
check("a stage ahead cannot go before the current stage", not rp.move_row_to(3, 0) and names()[0] == "Intake")
check("the table takes drags", t.dragEnabled() and t.dragDropMode() == t.DragDropMode.InternalMove)

# a passed gate
r = rec(); r.set_gate(r.stages[0]["id"], "soft"); r.move_to(r.stages[1]["id"])
rp.refresh(); app.processEvents()
today = datetime.date.today()
said = f"Gate passed {today.strftime('%b')} {today.day}, {today.year}"
check("a passed gate reads Gate passed with its date", t.item(0, 3).text() == said, t.item(0, 3).text())
check("... on the line too; nothing reads Done", said.rsplit(",", 1)[0] in rp.stages_line.texts()[0][0] and rp.stages_line.texts()[1][1] == "current"
      and not any("Done" in x[0] for x in rp.stages_line.texts()), rp.stages_line.texts()[:2])
check("a stage already passed keeps its place", not rp.move_row_to(0, 3) and names()[0] == "Intake")

# remove asks first when the stage has dates or a passed gate
ASKED.clear(); ANSWER[0] = QMessageBox.No
t.setCurrentCell(0, 0); rp.remove_stage(); rp.flush()
check("removing a stage with a passed gate asks first; No keeps it", ASKED and "passed gate" in ASKED[-1] and names()[0] == "Intake", ASKED)
i = names().index("Red team"); t.setCurrentCell(i, 0); ANSWER[0] = QMessageBox.Yes; ASKED.clear()
rp.set_stage(i, start=("2026-12-10", "")); rp.flush()
t.setCurrentCell(i, 0); rp.remove_stage(); rp.flush()
check("... a stage with dates asks too; Yes removes it", ASKED and "planned dates" in ASKED[-1] and "Red team" not in names(), names())
ASKED.clear(); i = names().index("Cost review"); t.setCurrentCell(i, 0); rp.remove_stage(); rp.flush()
check("a stage with no dates and no passed gate goes without asking", not ASKED and "Cost review" not in names(), (ASKED, names()))

# only the proposal manager changes the plan
BR.set_identity(rec(), pm="J. Smith"); rp.refresh(); app.processEvents()
check("with a proposal manager named, anyone else sees the plan unavailable", rp._stages_locked and not rp.add_stage_btn.isEnabled()
      and rp.stage_note.text().startswith("Only the proposal manager changes stages") and not rp.stage_panel.name.isEnabled(), rp.stage_note.text())
k = len(names())
check("... and cannot add, move or remove a stage", rp.add_stage("X") == -1 and not rp.move_row_to(k - 1, k - 2)
      and (t.setCurrentCell(k - 1, 0) or True) and not rp.remove_stage() and len(names()) == k)
check("... the Overview's Edit stages does not open either", w.home_page.edit_stages(run=False) is None)
modes.save(my_name="J. Smith"); rp.refresh(); app.processEvents()
check("the proposal manager on this PC can change it", not rp._stages_locked and rp.add_stage_btn.isEnabled() and rp.stage_note.text() == SP.NOTE)
modes.save(my_name="A. Lee"); r = rec(); r.set_role("A. Lee", "Proposal manager"); rp.refresh(); app.processEvents()
check("... so can someone whose role on the effort is Proposal manager", not rp._stages_locked)
modes.save(my_name="")
BR.set_identity(rec(), pm=""); r = rec(); r.set_role("A. Lee", ""); rp.refresh(); app.processEvents()
check("with no proposal manager named, anyone can change it", not rp._stages_locked and rp.add_stage_btn.isEnabled(), BR.proposal_manager(rec()))

# the offscreen picture for the build chat
out = os.environ.get("SK_PICTURE")
if out:
    rp.set_stage(names().index("Gold team"), start=("2026-12-14", ""), end=("2026-12-15", "")); rp.flush()
    rp.refresh()
    for _ in range(3):
        app.processEvents()
    rp.stages_line.parentWidget().grab().save(out)

w.close(); app.processEvents()
print(f"QT STAGES PLAN 4800 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
