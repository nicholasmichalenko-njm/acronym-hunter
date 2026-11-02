"""3.13.0 roles, Preview tools and the menu, offscreen: the menu is grouped by job and its groups fold away (kept); For
this stage lists the stage's tools in its color; a person's role comes from People and roles in the effort, else their
own choice; tools for another role are greyed and say who they are for (or hide, when asked); Preview tools (Fix a
Copy, Make a template) stay off until the proposal manager turns them on; a team pack carries that choice."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
import app_gui as A
import effort as E, effortrec as RR, roleaccess as RA, teampack as TP, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, modes as MO
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel")
MO.save(my_name="", home_layout={}, hide_other_roles=False, rail_collapsed=[], stage_tools=True)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()

# ---------------------------------------------------------------- the menu
heads = [g for g, _i in RAIL]
check("the menu is grouped by job", heads == ["Home", "Effort", "Customer documents", "Compliance", "Writing", "Quality", "Production",
                                              "Effort files"], heads)
r = RR.Record(w.ws.root)
stage_titles = [b.text() for b in w.stage_btns]
check("For this stage lists the stage's tools, in its color", w.stage_head.isVisibleTo(w) and r.stages[r.index()]["name"] in w.stage_head.text()
      and stage_titles and "color:" in w.stage_head.styleSheet(), (w.stage_head.text(), stage_titles))
w.stage_btns[0].click(); app.processEvents()
check("a stage tool opens its page", w.stack.currentWidget() is not w.notice_page or w.notice_page.why is not None)
w.toggle_group("Writing"); app.processEvents()
check("a group folds away, and stays folded", not w.step_btns["truth"].isVisibleTo(w)
      and "Writing" in json.load(open(A.SETTINGS_FILE))["rail_collapsed"])
w.toggle_group("Writing"); app.processEvents()
check("... and opens again", w.step_btns["truth"].isVisibleTo(w))
MO.save(stage_tools=False); w.refresh_access(); app.processEvents()
check("For this stage can be turned off", not w.stage_head.isVisibleTo(w) and not w.stage_btns)
MO.save(stage_tools=True); w.refresh_access()

# ---------------------------------------------------------------- Preview tools
check("with no role set, the person is the proposal manager: every tool opens", w.profile() == (RA.PM, "own")
      and not any(b.property("offrole") for b in w.step_btns.values()))
w.go("fixcopy"); app.processEvents()
np = w.notice_page
check("Fix a Copy is a Preview tool, off until turned on", w.stack.currentWidget() is np and "Preview" in np.card.title.text()
      and np.act.isVisibleTo(w) and np.act.text() == "Turn it on for this team", np.card.title.text())
np.do_action(); app.processEvents()
check("the proposal manager turns it on, and it opens", RA.preview_on(cfg, "fixcopy") and w.stack.currentWidget() is w.fixcopy_page)
w.go("prodstd"); app.processEvents()
check("Make a template waits until it is turned on", w.prodstd_page.make_template("", wait=True) is None and w.stack.currentWidget() is np
      and "Make a template is in Preview" in np.card.title.text())

# ---------------------------------------------------------------- roles
w.home_page.customize({"role": "Author", "order": __import__("branding").preset("Author")["order"],
                       "hidden": __import__("branding").preset("Author")["hidden"]})
w.refresh_access(); app.processEvents()
check("an author's own choice: production tools are greyed and say who they are for", w.profile() == ("Author", "own")
      and w.step_btns["fixcopy"].property("offrole") and "Production" in w.step_btns["fixcopy"].toolTip()
      and not w.step_btns["truth"].property("offrole"))
w.go("fixcopy"); app.processEvents()
check("opening one explains instead of opening it", w.stack.currentWidget() is np and np.card.title.text() == "Fix a Copy is for Proposal Manager, Production"
      and "Your role here is Author" in np.text.text() and np.act.text() == "Change my role..." and np.act.isVisibleTo(w), np.card.title.text())
np.do_action(answer="Production"); app.processEvents()
check("changing my own role opens it", w.profile()[0] == "Production" and w.stack.currentWidget() is w.fixcopy_page)
r = RR.Record(w.ws.root); r.set_team([("A. Lee", "Volume lead"), ("J. Smith", "Proposal manager")]); r.save()
MO.save(my_name="A. Lee"); w.refresh_access(); app.processEvents()
check("the effort's People and roles decides the role", w.profile() == ("Author", "effort") and w.step_btns["fixcopy"].property("offrole"))
w.go("prodstd"); app.processEvents()
check("... and only the proposal manager changes it: no button to change it here", w.stack.currentWidget() is np
      and not np.act.isVisibleTo(w) and "People and roles" in np.text.text())
MO.save(hide_other_roles=True); w.refresh_access(); app.processEvents()
check("Hide the tools that are not for my role", not w.step_btns["fixcopy"].isVisibleTo(w) and w.step_btns["truth"].isVisibleTo(w)
      and not w.group_heads["Production"].isVisibleTo(w))
MO.save(hide_other_roles=False); w.refresh_access()
w.go("settings"); app.processEvents()
rc = w.settings_page.roles_card
check("Settings says the role and where it comes from; only the proposal manager sets Preview tools",
      "Author" in rc.role_text.text() and "People and roles" in rc.role_text.text() and not rc.prev["fixcopy"].isEnabled())
MO.save(my_name="J. Smith"); w.go("settings"); app.processEvents()
check("the proposal manager can", w.profile()[0] == RA.PM and rc.prev["template"].isEnabled())
rc.prev["template"].setChecked(True)
check("... turning Make a template on", RA.preview_on(cfg, "template"))

# ---------------------------------------------------------------- the team pack carries it
pack = os.path.join(tmp, f"Team{TP.EXT}")
TP.make(cfg, pack, ["access"], lock=("access",), name="Team")
cfgB = os.path.join(tmp, "pcB"); os.makedirs(cfgB)
info, data = TP.read(pack)
TP.install(cfgB, info, data)
check("a team pack carries which Preview tools are on, locked", RA.preview_on(cfgB, "fixcopy") and RA.preview_on(cfgB, "template")
      and TP.locked(cfgB, "access"))
check("role words map to profiles", RA.profile_of("Red team reviewer") == "Reviewer" and RA.profile_of("Desktop publisher") == "Production"
      and RA.profile_of("Capture manager") == "Capture" and RA.profile_of("") == "")

stray = [x for x in app.topLevelWidgets() if x.isVisible() and x is not w and x.isWindow() and type(x).__name__ in ("QPushButton", "QWidget")]
check("the menu's buttons never show as windows of their own", not stray, [type(x).__name__ for x in stray])
MO.save(my_name="", home_layout={}, hide_other_roles=False, rail_collapsed=[])
n = sum(checks)
print(f"QT ROLES {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
