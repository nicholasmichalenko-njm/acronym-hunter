"""4.0.0 offscreen: the six steps (3.96.0's menu as the effort's path; claude/stationkeeper-six-steps-plan-4.0.md). The
effort switcher at the top; Dashboard and Documents, Shred, Matrix & Outline, Setup, Drafts, Submit, each with what is
left; Team and Settings; Ctrl+K. Shred's tabs as a stepper with counts and See it as; Changes and Text check are
Documents' tabs; the bar at the bottom with the next step; the Dashboard as the map; Team as tiles. Fictional (Kestrel)."""
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
check("4.27.2: thirteen entries: the Dashboard with Calendar and Tasks, six steps, Graphics under Documents, Quick tools, Team, Settings", [b.text() for b in w.step_btns.values()] ==
      ["Dashboard", "Calendar", "Tasks", "Documents", "Graphics", "Shred", "Matrix && Outline", "Setup", "Drafts", "Submit", "Quick tools", "Team", "Settings"],
      [b.text() for b in w.step_btns.values()])
check("the steps are numbered 1 to 6", [b.circle.text() for k, b in w.step_btns.items() if k not in ("redline", "graphics", "calendar", "tasks")][1:7] == ["1", "2", "3", "4", "5", "6"])
check("the effort switcher is there with nothing open", w.rail_effort.isVisibleTo(w) and w.rail_effort.name.text().startswith("No effort open"))
check("Ctrl+K is named at the foot of the menu", "Ctrl+K" in w.rail_hint.text())
w.open_effort("Kestrel"); app.processEvents()
NR.refresh_steps(w, force=True)
check("each step says what is left: add files, next", w.step_btns["library"].badge.text() == "add files"
      and w.step_btns["assign"].badge.text() == "next")
check("the switcher names the effort", w.rail_effort.name.text().startswith("Kestrel"))
from skqt import frame as FR
acts = [a.text() for a in FR.effort_menu(w).actions() if a.text()]
check("the switcher holds the Dashboard and All Efforts (4.27.2: Quick tools is at the bottom of the menu)", acts[0] == "Dashboard" and acts[-1] == "All Efforts"
      and "Quick tools" not in acts and "tools" in w.step_btns, acts)
# Documents
w.rail_go("library"); app.processEvents()
check("Documents: Customer, Ours, Changes (4.2.0: Text check is Shred's Fix text; 4.6.0: Customer and Ours)", w._tab_keys[:2] == ["library", "compare"] and "verify" not in w._tab_keys
      and w.page_title.text() == "Documents" and w.page_crumb.text() == "Step 1 of 6", (w._tab_keys, w.page_title.text()))
w.go("compare"); app.processEvents()
check("Changes lights Documents", w.step_btns["library"].isChecked() and w.page_title.text() == "Documents")
w.go("verify"); app.processEvents()
check("Text check opens Shred in Fix text (4.2.0)", w.step_btns["assign"].isChecked() and w.stack.currentWidget() is w.assign_page
      and w.assign_page.fix_on)
# Shred
w.rail_go("assign"); app.processEvents()
check("Shred: the stepper, not tabs", w.stepper.isVisibleTo(w) and not w.page_tabs.isVisibleTo(w) and w.page_title.text() == "Shred"
      and w.page_crumb.text() == "Step 2 of 6")
check("... Requirements, Rules & Dates, Evaluation, Acros & Abs with counts (4.1.0): no tab repeats the step's name",
      [w.stepper.chips[k].nm.text() for k, _l in NR.CHIPS] == ["Requirements", "Rules & Dates", "Evaluation", "Acros & Abs"]
      and w.stepper.chips["assign"].ct.text() == "nothing extracted")
check("... See it as: Page, List (4.19.0; 4.3.0: placing, L to M and Coverage are Matrix & Outline's)",
      [b.text() for b in w.stepper.views.values()] == ["Page", "List"] and w.stepper.views["assign"].isChecked())
w.stepper.chips["acronyms"].click(); app.processEvents()
check("a step chip opens its tab: Acros & Abs is the Acronyms page", w.stack.currentWidget() is w.acronym_page and w.step_btns["assign"].isChecked()
      and w.page_title.text() == "Shred")
w.go("crosswalk"); app.processEvents()
check("L to M shows beside the page, in Matrix & Outline (4.3.0)", w.stack.currentWidget() is w.assign_page
      and w.assign_page.views.key == "lm" and w.step_btns["matrix"].isChecked() and w._tab_keys[3] == "crosswalk")
w.stepper.see("shredlist"); app.processEvents()
check("List is a way to see Shred (4.19.0: the shred by the customer's structure): the menu stays on Shred",
      w.stack.currentWidget() is w.shredlist_page and w.step_btns["assign"].isChecked()
      and w.stepper.views["shredlist"].isChecked() and w.page_title.text() == "Shred")
check("Shred's views are Page and List; Sort and Accuracy are Quick tools' (4.19.0)", list(w.stepper.views) == ["assign", "shredlist"]
      and __import__("skqt.mainwin", fromlist=["x"]).RAIL_OF["shredacc"] == "tools")
# Matrix & Outline, Drafts, Submit
w.rail_go("matrix"); app.processEvents()
check("Matrix & Outline: Outline, Place, Matrix, L to M, Coverage (4.3.0)", w._tab_keys == ["outline", "place", "matrix", "crosswalk", "prove"] and w.page_title.text() == "Matrix & Outline"
      and w.page_crumb.text() == "Step 3 of 6", (w._tab_keys, w.page_title.text()))
w.rail_go("drafts"); app.processEvents()
check("Drafts: Status, Acronyms and Edit (4.4.0; Color Reviews and Wall of Truth set aside)", w._tab_keys == ["drafts", "draftacr", "techedit", "markups"]
      and w.page_title.text() == "Drafts" and w.stack.currentWidget() is w.drafts_page, w._tab_keys)
# the bar
w.rail_go("assign"); app.processEvents()
check("4.26.0: Shred has no bar at the bottom (Next: Matrix & Outline is gone)", not w.next_bar.isVisibleTo(w))
w.rail_go("matrix"); app.processEvents()
check("the bar at the bottom: what is left and the next step", w.next_bar.isVisibleTo(w) and w.next_bar.left.text().startswith("On this step:")
      and w.next_bar.btn.text().startswith("Next: Setup"), w.next_bar.btn.text())
w.next_bar.go(); app.processEvents()
check("... its button opens the next step", w.stack.currentWidget() is w.setups_page and w.step_btns["setups"].isChecked())
w.rail_go("finalcheck"); app.processEvents()
check("Submit, the last step: no next button", w.next_bar.isVisibleTo(w) and not w.next_bar.btn.isVisibleTo(w)
      and w._tab_keys == ["finalcheck", "qa", "checks", "postsub", "keywords"])
# the Dashboard
w.rail_go("home"); app.processEvents()
check("4.27.0: the Dashboard entry opens the Overview", w.stack.currentWidget() is w.overview_page and w.step_btns["home"].isChecked())
w.go("home"); app.processEvents()                       # All cards: the Dashboard as it was
hp = w.home_page
check("the Dashboard: six step cards", [c.name.text() for c in hp.map.cards.values()] ==
      ["Documents", "Shred", "Matrix & Outline", "Setup", "Drafts", "Submit"]
      and hp.map.cards["library"].cap.text() == "1  NOW" and hp.map.isVisibleTo(w))
check("... Your next step with one button", hp.map.next_title.text() == "Add the customer's documents" and "Open Documents" in hp.map.next_btn.text())
check("... This week", hp.map.week.isVisibleTo(w))
check("... Overview, All cards, Deliverables, the Effort Record and Meetings are its tabs", w._tab_keys[:5] == ["overview", "home", "deliverables", "record", "meetings"])
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
print(f"QT NAV 400 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
