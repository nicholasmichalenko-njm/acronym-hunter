"""3.12.0 the Effort Dashboard, offscreen: Effort Home and the Dashboard are one page (the rail, the title, the old
route); the header is pinned above the scroll, shows the stage with its gate and open goals, and condenses (kept);
Win themes and the Wall of Truth show under it by default and hide (kept for the effort); Submission requirements is one
card with three tabs and Edit; each card holds its own export; the readable copy and page limit left the header; the
Dashboard's numbers and cards are on the page; card widths; Move stage says what is not done and only the proposal
manager overrides a hard gate; carried goals are marked; every overview is kept; the full effort exports to a dated
folder named for its stage; the customer's due date has no switch; All Efforts shows the gate; stage colors."""
import datetime, json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
import app_gui as A
import branding as BR, effort as E, effortrec as RR, effortsummary as ESUM, stagecolors as SC, workspace as W, office_pdf as OP
import themes as TH, walloftruth as WT
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QTabWidget
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
r0 = RR.Record(ws0.root)
TH.add(r0, "Thermal margin you can prove", "Every design point tested at 1.5x")
WT.add(r0, "Mass budget", "412 kg")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
from skqt import modes
modes.save(show_set_aside=True)   # 3.61.0: stages, gate goals, win themes and All overviews are set aside; their code is still tested
w.open_effort("Kestrel")
w.go("home"); app.processEvents()
hp = w.home_page
bn = hp.banner

# ---------------------------------------------------------------- one page
check("the menu has Overview and no Overview", "home" in w.step_btns and "dashboard" not in w.step_btns
      and w.step_btns["home"].text() == "Overview")
check("the page is called Overview (3.96.0)", w.page_title.text() == "Overview")
w.go("dashboard"); app.processEvents()
check("the old Overview route opens Overview", w.stack.currentWidget() is hp)
check("the Overview's numbers and cards are on it for the proposal manager", all(k in hp.shown for k in ("health",
      "pastdue", "acronyms")) and "coverage" not in hp.shown and "people" not in hp.shown and hp.health.isVisibleTo(w)
      and "compliance" not in hp.shown and not w.dash_page.comp.isVisibleTo(w) and w.dash_page.data is not None)     # 4.26.0: the bar is Shred's

# ---------------------------------------------------------------- the pinned header
check("the header is pinned above the scrolling cards", bn.parent() is hp.head and hp.head.isVisibleTo(w)
      and not hp.scroll.widget().isAncestorOf(bn))
check("the stage pill names the gate and the open goals", "No gate" in bn.stage.text() or "gate" in bn.stage.text().lower(), bn.stage.text())
r = RR.Record(w.ws.root)
r.set_gate(r.stages[0]["id"], "hard")
r.stages[0]["goals"].append({"id": "gx", "text": "Kickoff held", "auto": "", "done": False, "by": "", "at": "", "owner": "J. Smith"})
r.save()
hp.refresh(); app.processEvents()
check("a hard gate with open goals shows on the stage pill", "Hard gate" in bn.stage.text() and "goals open" in bn.stage.text(), bn.stage.text())
check("the stage's color is the header's top line and the pill", bn.stage_hex == SC.color_of(RR.Record(w.ws.root).stages[0], 0)
      and bn.stage_hex in bn.styleSheet())
bn.set_condensed(True); app.processEvents()
check("Condense keeps one line: name, due, client, sensitivity, stage", bn.compact.isVisibleTo(w) and not bn.full.isVisibleTo(w)
      and bn.c_name.text() == "Kestrel" and bn.c_stage.text() == bn.stage.text())
hp.refresh(); app.processEvents()
check("the condensed header is kept", bn.condensed and json.load(open(A.SETTINGS_FILE)).get("banner_condensed") is True)
bn.set_condensed(False); app.processEvents()
names = [b.text() for b in bn.findChildren(QPushButton)]
check("the readable copy and the page limit left the header; All overviews is there (in More, 3.75.0)", "Readable copy" not in names
      and hp.bar.action("All overviews...") is not None and not bn.pagelim.isVisible() and not any(lab == "PAGE-LIMITED" for lab, _v in bn.spots), names)

# ---------------------------------------------------------------- the pinned strips
check("Win themes and the Wall of Truth show under the header on the first stage", hp.strips["themes"].isVisibleTo(w)
      and hp.strips["truth"].isVisibleTo(w) and "Thermal margin" in hp.strips["themes"].body.text() and "412 kg" in hp.strips["truth"].body.text())
hp.set_strip("truth", False); hp.refresh(); app.processEvents()
check("hiding the Wall of Truth is kept for this effort", not hp.strips["truth"].isVisibleTo(w) and not bn.toggles["truth"].isChecked()
      and json.load(open(A.SETTINGS_FILE))["pinned_strips"]["Kestrel"]["truth"] is False)
bn.toggles["truth"].setChecked(True); app.processEvents()
check("the header button shows it again", hp.strips["truth"].isVisibleTo(w))

# ---------------------------------------------------------------- submission requirements and card actions
check("Submission requirements: one card, three tabs", hp.sub_card.title.text().startswith("Submission requirements")
      and [hp.sub_tabs.tabText(i).split(" (")[0] for i in range(hp.sub_tabs.count())] == ["How and when", "Formatting", "Page limits"])
key = hp.format_dialog(answer=("Font", "12-point Times New Roman"))
row = next(x["row"] for x in hp.fmt_now["lines"] if x["label"] == "Font")
hp.edit_rule(row, "11-point Arial")
check("Edit changes what a requirement says", next(x["value"] for x in hp.fmt_now["lines"] if x["label"] == "Font") == "11-point Arial",
      [x for x in hp.fmt_now["lines"] if x["label"] == "Font"])
top_buttons = [b.text() for b in hp.scroll.widget().findChildren(QPushButton) if b.parent() is hp.scroll.widget()]
check("one Export menu holds the dashboard's exports (3.75.0, house rule 8)", hp.bar.action("Tasks and questions (Excel)...") is not None
      and not any(b.text() == "Export..." for b in hp.tasks.findChildren(QPushButton)) and "Export tasks and questions..." not in top_buttons)

# ---------------------------------------------------------------- card widths
hp.customize({"role": "Proposal Manager", "order": hp.lay["order"], "hidden": hp.lay["hidden"], "widths": {"tasks": "wide"}})
check("a card's width is the person's choice", BR.width("tasks", hp.lay["widths"]) == "wide" and ["tasks"] in BR.rows(hp.shown, hp.lay["widths"]))

# ---------------------------------------------------------------- Move stage
from skqt import modes as MO
bn.save_details({"pm": "J. Smith"})
MO.save(my_name="A. Lee")
hp.refresh(); app.processEvents()
nxt = RR.Record(w.ws.root).stages[1]["id"]
dlg = hp.move_dialog(run=False)
check("Move stage lists what is not done, with owners", any("Kickoff held" in cb.text() and "J. Smith" in cb.text() for cb, _g in dlg.api["carry"]))
check("someone else cannot override a hard gate: no move button, and why", not dlg.api["action"].isVisibleTo(dlg)
      and "Only the proposal manager, J. Smith" in dlg.api["gate"].text(), dlg.api["gate"].text())
dlg.deleteLater()
check("... and the move is held even with a reason", hp.move_stage(nxt, carry=["gx"], reason="We are ready") is None
      and RR.Record(w.ws.root).index() == 0)
MO.save(my_name="J. Smith")
dlg = hp.move_dialog(run=False)
check("the proposal manager overrides with a reason: Override and move", dlg.api["action"].text() == "Override and move"
      and not dlg.api["action"].isEnabled())
dlg.api["reason"].setText("Customer moved the kickoff")
check("... enabled once the reason is written", dlg.api["action"].isEnabled())
dlg.deleteLater()
check("the move goes through, carrying the open goal", hp.move_stage(nxt, carry=["gx"], reason="Customer moved the kickoff") is True)
r = RR.Record(w.ws.root)
carried = [g for g in r.stage()["goals"] if g.get("from")]
check("the carried goal is marked and counts at the next gate", carried and carried[0]["text"] == "Kickoff held"
      and r.goal_progress()[1] >= 1)
check("the dashboard marks it Carried from", any(p.text().startswith("Carried from") for p in hp.goals.findChildren(type(bn.sens))))
dlg = hp.move_dialog(run=False)
dlg.api["to"].setCurrentIndex(dlg.api["to"].findData(r.stages[0]["id"]))
check("moving back is never held", "never held" in dlg.api["gate"].text() and dlg.api["action"].text() == "Move back")
dlg.deleteLater()

# ---------------------------------------------------------------- overviews and the full export
out = os.path.join(tmp, "status1.docx")
w.record_page.status_export(path=out, summary="On track; pink team Friday")
dlg = w.record_page.overviews_dialog(run=False)
check("every overview is kept with its stage and summary", dlg.api["rows"] and dlg.api["rows"][0]["summary"] == "On track; pink team Friday"
      and dlg.api["rows"][0]["stage"] == r.stage()["name"] and dlg.api["table"].rowCount() == 1)
dlg.deleteLater()
dest = w.export_full_effort(os.path.join(tmp, "exports"), open_it=False)
check("the full effort exports to a dated folder named for its stage", dest and os.path.isdir(dest) and r.stage()["name"] in os.path.basename(dest)
      and "full export" in os.path.basename(dest) and os.listdir(dest), dest)

# ---------------------------------------------------------------- the due date, All Efforts, watched files, colors
from skqt.brandview import DetailsDialog
dd = DetailsDialog(bn, bn.ident, "", "")
dd.due_date.setDate(dd.due_date.date().addDays(0) if False else __import__("PySide6.QtCore", fromlist=["QDate"]).QDate(2030, 3, 4))
check("the customer's due date has no switch: a date sets it", not dd.has_due.isVisible() and dd.values()["due"].startswith("2030-03-04"))
dd.due_date.setDate(dd.due_date.minimumDate())
check("... Clear leaves it Not set yet", dd.values()["due"] == "" and dd.due_date.text() == "Not set yet")
dd.deleteLater()
s = ESUM.summary("Kestrel", {"path": LIST})
check("All Efforts knows each effort's gate", "gate" in s and "goals_open" in s)
check("new files: Add to Documents... or Ignore", w.watch_strip.add_btn.text() == "Add to Documents..." and w.watch_strip.skip_btn.text() == "Ignore")
check("stage colors by name, own color wins", SC.color_of({"name": "Pink team"}) == SC.NAMED["Rose"]
      and SC.color_of({"name": "Pink team", "color": "Teal"}) == SC.NAMED["Teal"] and SC.color_of({"name": "Something"}, 2) == SC.PALETTE[2][1])
r.set_stage_color(r.stages[1]["id"], "Purple")
check("a stage's color is saved", RR.Record(w.ws.root).stages[1].get("color") == "Purple")

n = sum(checks)
print(f"QT DASHBOARD {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
modes.save(show_set_aside=False)   # 3.61.0: the settings file is shared by the tests on the PC
sys.exit(0 if n == len(checks) else 1)
