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
check("4.60.0: Quick tools, the effort's pages, Standards and Formatting, Settings", [b.text() for b in w.step_btns.values()] ==
      ["Quick tools", "Overview", "Documents", "Graphics", "Deliverables", "Redlining", "Shred", "Matrix", "Outline", "Setup", "Drafts", "Submission Check", "Global Standards", "Rules", "Team References", "Templates", "Page Layout", "Styles", "Quick Parts", "Check a Draft", "Effort Activity", "Effort Backup", "Settings"],
      [b.text() for b in w.step_btns.values()])
check("4.60.0: no entry is numbered", all(b.n is None and not b.circle.isVisibleTo(w) for b in w.step_btns.values()))
check("the effort switcher is there with nothing open", w.rail_effort.isVisibleTo(w) and w.rail_effort.name.text().startswith("No effort open"))
check("Ctrl+K is named at the foot of the menu", "Ctrl+K" in w.rail_hint.text())
w.open_effort("Kestrel"); app.processEvents()
NR.refresh_steps(w, force=True)
check("each step says what is left (next); 4.29.3: Documents carries no words in the menu", w.step_btns["library"].badge.text() == ""
      and not w.step_btns["library"].badge.isVisibleTo(w) and w.step_btns["assign"].badge.text() == "next")
check("the switcher names the effort", w.rail_effort.name.text().startswith("Kestrel"))
from skqt import frame as FR
acts = [a.text() for a in FR.effort_menu(w).actions() if a.text()]
check("the switcher holds the Overview and All Efforts (4.27.2: Quick tools is at the bottom of the menu)", acts[0] == "Overview" and acts[-1] == "All Efforts"
      and "Quick tools" not in acts and "tools" in w.step_btns, acts)
# Documents
w.rail_go("library"); app.processEvents()
check("Documents: Customer, Ours, Changes (4.2.0: Text check is Shred's Fix text; 4.6.0: Customer and Ours)", w._tab_keys[:2] == ["library", "compare"] and "verify" not in w._tab_keys
      and w.page_title.text() == "Documents" and w.page_crumb.text() == "", (w._tab_keys, w.page_title.text()))
w.go("compare"); app.processEvents()
check("Changes lights Documents", w.step_btns["library"].isChecked() and w.page_title.text() == "Documents")
w.go("verify"); app.processEvents()
check("Text check opens Shred in Fix text (4.2.0)", w.step_btns["assign"].isChecked() and w.stack.currentWidget() is w.assign_page
      and w.assign_page.fix_on)
# Shred
w.rail_go("assign"); app.processEvents()
check("Shred: the stepper, not tabs", w.stepper.isVisibleTo(w) and not w.page_tabs.isVisibleTo(w) and w.page_title.text() == "Shred"
      and w.page_crumb.text() == "")
check("... Requirements, Submission Checklist, Evaluation, Acronyms with counts (4.1.0): no tab repeats the step's name",
      [w.stepper.chips[k].nm.text() for k, _l in NR.CHIPS] == ["Compliance", "Deliverables", "Requirements", "Submission Checklist", "Evaluation Criteria", "Acronyms"]
      and w.stepper.chips["assign"].ct.text() == "nothing extracted")
check("... and no chip carries a number (4.46.0, decision 16: ways to see the shred, not steps)", all(w.stepper.chips[k].no.text() == "" for k, _l in NR.CHIPS))
check("... See it as: On the page, As a table (4.54.0; 4.3.0: placing, Crosswalk and Coverage are Matrix & Outline's)",
      [b.text() for b in w.stepper.views.values()] == ["On the page", "As a table"] and w.stepper.views["assign"].isChecked())
w.stepper.chips["acronyms"].click(); app.processEvents()
check("a step chip opens its tab: Acronyms is the Acronyms page", w.stack.currentWidget() is w.acronym_page and w.step_btns["assign"].isChecked()
      and w.page_title.text() == "Shred")
w.go("crosswalk"); app.processEvents()
check("Crosswalk shows beside the page, in Matrix (4.3.0; 4.60.0)", w.stack.currentWidget() is w.assign_page
      and w.assign_page.views.key == "lm" and w.step_btns["matrix"].isChecked() and "crosswalk" not in w._tab_keys)   # 4.69.0: under Matrix > More   # 4.67.0: after Assign, Check, Matrix
w.stepper.see("shredlist"); app.processEvents()
check("As a table is a way to see Shred (4.54.0): the menu stays on Shred",
      w.stack.currentWidget() is w.shredlist_page and w.step_btns["assign"].isChecked()
      and w.stepper.views["shredlist"].isChecked() and w.page_title.text() == "Shred")
check("Shred's views are On the page and As a table; Sort and Accuracy are Quick tools' (4.19.0)", list(w.stepper.views) == ["assign", "shredlist"]
      and __import__("skqt.mainwin", fromlist=["x"]).RAIL_OF["shredacc"] == "tools")
# Matrix & Outline, Drafts, Submit
w.rail_go("matrix"); app.processEvents()
check("Matrix: Matrix, Place, Crosswalk, Coverage (4.60.0: Outline is its own entry)", w._tab_keys == ["assignto", "linkcheck", "matrix"] and w.page_title.text() == "Matrix"
      and w.page_crumb.text() == "", (w._tab_keys, w.page_title.text()))
w.rail_go("drafts"); app.processEvents()
check("Drafts: Status, Acronyms and Edit (4.4.0; Color Reviews and Wall of Truth set aside)", w._tab_keys == ["draftacr", "drafts", "techedit", "markups"]
      and w.page_title.text() == "Drafts" and w.stack.currentWidget() is w.draftacr_page, w._tab_keys)   # 4.65.0: Drafts opens on Acronyms
# the bar
w.rail_go("assign"); app.processEvents()
check("4.26.0: Shred has no bar at the bottom (Next: Matrix & Outline is gone)", not w.next_bar.isVisibleTo(w))
w.rail_go("matrix"); app.processEvents()
check("4.29.1: no step has a bar at the bottom (answer 10 of 2026-11-13)", not w.next_bar.isVisibleTo(w))
w.rail_go("finalcheck"); app.processEvents()
check("Submit, the last step: its tabs, and no bar", not w.next_bar.isVisibleTo(w)
      and w._tab_keys == ["finalcheck", "qa", "checks", "postsub", "keywords"])
# the Dashboard
w.rail_go("home"); app.processEvents()
check("4.27.0: the Overview entry opens the Overview", w.stack.currentWidget() is w.overview_page and w.step_btns["home"].isChecked())
w.go("home"); app.processEvents()                       # All cards: the Dashboard as it was
hp = w.home_page
check("the Overview: six step cards", [c.name.text() for c in hp.map.cards.values()] ==
      ["Documents", "Shred", "Matrix & Outline", "Setup", "Drafts", "Submit"]
      and hp.map.cards["library"].cap.text() == "1  NOW" and hp.map.isVisibleTo(w))
check("... Your next step with one button", hp.map.next_title.text() == "Add the customer's documents" and "Open Documents" in hp.map.next_btn.text())
check("... This week", hp.map.week.isVisibleTo(w))
check("... Overview, All cards, Calendar, Tasks, the Effort Record and Meetings are its tabs (4.60.0)", w._tab_keys == [])   # 4.61.0: All cards is no tab; the Overview's are Overview, Calendar, Tasks, Meetings
check("... no bar at the bottom of the Overview", not w.next_bar.isVisibleTo(w))
hp.map.cards["assign"].click(); app.processEvents()
check("a card opens its step", w.step_btns["assign"].isChecked())
hp.map.go_next(); app.processEvents()
check("Your next step's button opens it", w.stack.currentWidget() is w.library_page)
# Team
check("4.60.0: no Team entry; what it held is in the menu", "team" not in w.step_btns and {"rules", "refs", "audit"} <= set(w.step_btns))
w.rail_go("rules"); app.processEvents()
check("Rules opens from the menu, under Standards and Formatting", w.stack.currentWidget() is w.pages["rules"] and w.step_btns["rules"].isChecked()
      and w.page_crumb.text() == "Standards and Formatting" and not w.next_bar.isVisibleTo(w), w.page_crumb.text())
check("Ctrl+K finds Rules", any(r[1] == "Rules" for r in __import__("skqt.helpcenter", fromlist=["x"]).open_finder(w, run=False).entries))
print(f"QT NAV 400 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
