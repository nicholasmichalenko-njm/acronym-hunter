"""3.96.0 offscreen: the menu as the effort's path (canvas "Navigation", boards 1 to 3). The effort switcher at the top;
Dashboard and the five steps, each with what is left; Team and Settings; Ctrl+K. Review's tabs as a stepper with counts
and See it as; the bar at the bottom with the next step; the Dashboard as the map; Team as tiles. Fictional (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt import mainwin as MW
from skqt import navrail as NR

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); D.apply(app)
from skqt import modes as _modes
_modes.save(show_set_aside=False, hide_other_roles=False)
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1440, 900); w.show(); app.processEvents()
check("eight entries: the Dashboard, five steps, Team, Settings", [b.text() for b in w.step_btns.values()] ==
      ["Dashboard", "Customer files", "Review", "Setup", "Write", "Submit", "Team", "Settings"])
check("the steps are numbered 1 to 5", [b.circle.text() for k, b in w.step_btns.items()][1:6] == ["1", "2", "3", "4", "5"])
check("the effort switcher is there with nothing open", w.rail_effort.isVisibleTo(w) and w.rail_effort.name.text().startswith("No effort open"))
check("Ctrl+K is named at the foot of the menu", "Ctrl+K" in w.rail_hint.text())
w.open_effort("Kestrel"); app.processEvents()
NR.refresh_steps(w, force=True)
check("each step says what is left: add files, next", w.step_btns["library"].badge.text() == "add files"
      and w.step_btns["assign"].badge.text() == "next")
check("the switcher names the effort", w.rail_effort.name.text().startswith("Kestrel"))
from skqt import frame as FR
acts = [a.text() for a in FR.effort_menu(w).actions() if a.text()]
check("the switcher holds the Dashboard, All Efforts and Your Tools", acts[0] == "Dashboard" and acts[-2:] == ["All Efforts", "Your Tools"], acts)
# Review
w.rail_go("assign"); app.processEvents()
check("Review: the stepper, not tabs", w.stepper.isVisibleTo(w) and not w.page_tabs.isVisibleTo(w) and w.page_title.text() == "Review"
      and w.page_crumb.text() == "Step 2 of 5")
check("... Verify, Read, Compare, Place with counts; Place current", [w.stepper.chips[k].nm.text() for k in ("verify", "read", "compare", "assign")]
      == ["Verify", "Read", "Compare", "Place"] and w.stepper.chips["read"].ct.text() == "not read yet")
check("... See it as: Our structure first", [b.text() for b in w.stepper.views.values()] ==
      ["Our structure", "Requirements", "Sort", "Matrix", "L to M", "Coverage"] and w.stepper.views["assign"].isChecked())
w.stepper.chips["verify"].click(); app.processEvents()
check("a step chip opens its tab", w.stack.currentWidget() is w.verify_page and w.step_btns["assign"].isChecked())
w.stepper.see("crosswalk"); app.processEvents()
check("L to M shows beside Review's page", w.stack.currentWidget() is w.assign_page and w.assign_page.views.key == "lm"
      and w.stepper.views["crosswalk"].isChecked())
w.stepper.see("sort"); app.processEvents()
check("Sort is a way to see Review: the menu stays on Review", w.stack.currentWidget() is w.sort_page and w.step_btns["assign"].isChecked()
      and w.stepper.views["sort"].isChecked() and w.page_title.text() == "Review")
w.go("shredacc"); app.processEvents()
check("Accuracy sits with Requirements", w.stepper.views["shredreq"].isChecked() and w.step_btns["assign"].isChecked())
# the bar
w.rail_go("assign"); app.processEvents()
check("the bar at the bottom: what is left and the next step", w.next_bar.isVisibleTo(w) and w.next_bar.left.text().startswith("On this step:")
      and w.next_bar.btn.text().startswith("Next: Setup"))
w.next_bar.go(); app.processEvents()
check("... its button opens the next step", w.stack.currentWidget() is w.setups_page and w.step_btns["setups"].isChecked())
w.rail_go("finalcheck"); app.processEvents()
check("Submit, the last step: no next button", w.next_bar.isVisibleTo(w) and not w.next_bar.btn.isVisibleTo(w)
      and w._tab_keys == ["finalcheck", "qa", "checks", "postsub", "keywords"])
w.rail_go("acronyms"); app.processEvents()
check("Write: Acronyms, the Acronym List and Technical Edit (Draft Status set aside)", w._tab_keys == ["acronyms", "acrlist", "techedit"]
      and w.page_title.text() == "Write")
w.rail_go("library"); app.processEvents()
check("Customer files: the files, Customer Q&A", w._tab_keys[:2] == ["library", "custqa"] and w.page_title.text() == "Customer files")
# the Dashboard
w.rail_go("home"); app.processEvents()
hp = w.home_page
check("the Dashboard: five step cards", [c.name.text() for c in hp.map.cards.values()] == ["Customer files", "Review", "Setup", "Write", "Submit"]
      and hp.map.cards["library"].cap.text() == "1  NOW" and hp.map.isVisibleTo(w))
check("... Your next step with one button", hp.map.next_title.text() == "Add the customer's files" and "Open Customer files" in hp.map.next_btn.text())
check("... This week", hp.map.week.isVisibleTo(w))
check("... Deliverables, the Effort Record and Meetings are its tabs", w._tab_keys[:4] == ["home", "deliverables", "record", "meetings"])
check("... no bar at the bottom of the Dashboard", not w.next_bar.isVisibleTo(w))
hp.map.cards["assign"].click(); app.processEvents()
check("a card opens its step", w.step_btns["assign"].isChecked())
hp.map.go_next(); app.processEvents()
check("Your next step's button opens it", w.stack.currentWidget() is w.library_page)
# Team
w.rail_go("team"); app.processEvents()
check("Team: one page of tiles", w.stack.currentWidget() is w.team_page and set(w.team_page.shown()[0]) == set(MW.TEAM)
      and not w.next_bar.isVisibleTo(w))
w.team_page.tiles["formatstd"].click(); app.processEvents()
check("a tile opens its tool; the menu stays on Team", w.stack.currentWidget() is w.formatstd_page and w.step_btns["team"].isChecked()
      and w.page_crumb.text() == "Team")
check("Ctrl+K finds Team", any(r[1] == "Team" for r in __import__("skqt.helpcenter", fromlist=["x"]).open_finder(w, run=False).entries))
print(f"QT NAV 396 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
