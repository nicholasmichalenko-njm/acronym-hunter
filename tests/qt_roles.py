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
from skqt import modes as _modes
_modes.save(show_set_aside=False)   # 3.61.0: a test before may have left the pages set aside showing
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()

# ---------------------------------------------------------------- the menu
heads = [g for g, _i in RAIL]
check("the menu is the effort's path, then Team and Settings (3.96.0)", heads == ["Effort", "Templates", "Team", "Settings"], heads)
r = RR.Record(w.ws.root)
# 3.15.0: no separate stage group: each tool is in the menu once, the stage's tools marked with a dot in its color
cur_stage = r.stages[r.index()]["name"]
marked = [k for k, b in w.step_btns.items() if b.stage_dot.isVisibleTo(w)]
names = [b.text() for b in w.findChildren(QPushButton) if b.objectName() in ("rail", "railstage") and b.isVisibleTo(w)]
check("3.15.0: every tool is in the menu once (no stage group repeating them)", len(names) == len(set(names)) and not hasattr(w, "stage_btns"),
      [n for n in names if names.count(n) > 1])
check("... the stage's tools carry a dot in the stage's color", marked and set(marked) == set(w.stage_tools_now)
      and all("background:" in w.step_btns[k].stage_dot.styleSheet() for k in marked), (marked, w.stage_tools_now))
check("... and each step says what is left (3.96.0)", [b.badge.isVisibleTo(w) for k, b in w.step_btns.items() if k == "library"] == [True])
check("the open effort and its stage are at the top of the menu", w.rail_effort.isVisibleTo(w) and w.rail_effort.name.text().startswith("Kestrel")
      and w.rail_effort.stage.text() == cur_stage, (w.rail_effort.name.text(), w.rail_effort.stage.text()))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
w.go("efforts"); app.processEvents()
from skqt import frame as FR                                  # 3.75.0: the card opens a menu: the Dashboard, another effort
m = FR.effort_menu(w)
m.actions()[0].trigger(); app.processEvents()
check("... and its menu opens the Dashboard; All Efforts is there too (3.96.0; 4.27.2: Quick tools is in the menu)",
      m.actions()[0].text() == "Dashboard" and w.stack.currentWidget() is w.overview_page
      and [a.text() for a in m.actions()][-1] == "All Efforts")
w.step_btns[marked[0]].click(); app.processEvents()
check("a stage tool opens its page", w.stack.currentWidget() is not w.notice_page or w.notice_page.why is not None)
MO.save(stage_tools=False); w.refresh_access(); app.processEvents()
check("the stage marks can be turned off", not any(b.stage_dot.isVisibleTo(w) for b in w.step_btns.values()))
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
      and "Make a .dotx template is in Preview" in np.card.title.text())

# ---------------------------------------------------------------- roles
w.home_page.customize({"role": "Author", "order": __import__("branding").preset("Author")["order"],
                       "hidden": __import__("branding").preset("Author")["hidden"]})
w.refresh_access(); app.processEvents()
check("an author's own choice: Team shows only the author's tools (3.96.0: tiles by role)", w.profile() == ("Author", "own")
      and "audit" not in w.team_page.refresh()[0:6] and "refs" in w.team_page.shown()[0]
      and not w.step_btns["assign"].property("offrole") and not w.step_btns["team"].property("offrole"))
w.go("fixcopy"); app.processEvents()
check("opening one explains instead of opening it", w.stack.currentWidget() is np and np.card.title.text() == "Fix a Copy is for Proposal Manager, Production"
      and "Your role here is Author" in np.text.text() and np.act.text() == "Change my role..." and np.act.isVisibleTo(w), np.card.title.text())
np.do_action(answer="Production"); app.processEvents()
check("changing my own role opens it", w.profile()[0] == "Production" and w.stack.currentWidget() is w.fixcopy_page)
from PySide6.QtWidgets import QLabel as _QL
check("3.75.0: Fix a Copy is a tab of Check a Draft in the Team group, marked Beta on the page",
      [k for k, _t in __import__("skqt.mainwin", fromlist=["TABS"]).TABS["audit"]] == ["audit", "applyword", "fixcopy"] and w.beta_pill.isVisibleTo(w))
w.go("acrlist"); app.processEvents()
check("3.16.0: a tab's page marks its menu item: the Acro List is Shred's, opened from Acros & Abs (4.1.0), and Production opens it",
      (w.stack.currentWidget() is w.acronym_page and w.acronym_page.tab_stack.currentWidget() is w.acrlist_page) and w.step_btns["assign"].isChecked() and w.page_title.text() == "Shred"
      and "acrlist" not in w.stepper.chips and w.stepper.chips["acronyms"].nm.text() == "Acros & Abs"
      and not w.step_btns["assign"].property("offrole") and not w.beta_pill.isVisibleTo(w))
w.stepper.chips["acronyms"].click(); app.processEvents()
check("... clicking a tab opens its page", w.stack.currentWidget() is w.acronym_page and w.step_btns["assign"].isChecked())
w.go("lists"); app.processEvents()
check("3.37.0: Lists to Submit opens in the Acronym List", (w.stack.currentWidget() is w.acronym_page and w.acronym_page.tab_stack.currentWidget() is w.acrlist_page)
      and w.acrlist_page.views.currentWidget() is w.lists_page)
r = RR.Record(w.ws.root); r.set_team([("A. Lee", "Volume lead"), ("J. Smith", "Proposal manager")]); r.save()
MO.save(my_name="A. Lee"); w.refresh_access(); app.processEvents()
check("the effort's People decides the role", w.profile() == ("Author", "effort") and "audit" not in w.team_page.shown()[0])
w.go("prodstd"); app.processEvents()
check("... and only the proposal manager changes it: no button to change it here", w.stack.currentWidget() is np
      and not np.act.isVisibleTo(w) and "People in this effort" in np.text.text())
MO.save(hide_other_roles=True); w.refresh_access(); app.processEvents()
# 3.57.0: Wall of Truth is set aside (menufocus), so the fold and the role checks use Acronyms
check("Hide the tools that are not for my role", w.step_btns["assign"].isVisibleTo(w) and w.step_btns["team"].isVisibleTo(w)
      and "formatstd" not in w.team_page.shown()[0])
MO.save(hide_other_roles=False); w.refresh_access()
w.go("settings"); app.processEvents()
rc = w.settings_page.roles_card
check("Settings says the role and where it comes from; only the proposal manager sets Preview tools",
      "Author" in rc.role_text.text() and "People in this effort" in rc.role_text.text() and not rc.prev["fixcopy"].isEnabled())
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
