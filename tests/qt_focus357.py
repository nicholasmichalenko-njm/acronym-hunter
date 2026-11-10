"""3.57.0 Focus and file safety, offscreen. The pages set aside (My Work, Draft Status, Wall of Truth, Storyboards, Data
calls, Color Reviews, Kickoff packets) leave the menu, the tabs and Your Tools' pins, and come back with Show the pages
set aside; Final Checks > Leftovers finds the setup's reference text in a file Make the setup wrote; Your Tools' Check for
leftovers; a file in a OneDrive folder says so when read. Fictional content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


app = QApplication([]); theme.apply(app)
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
from skqt import mainwin as MW
from skqt import modes
import menufocus as MF
from skqt import modes as _modes
_modes.save(show_set_aside=False)   # 3.61.0: a test before may have left the pages set aside showing
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
w.refresh_access(); app.processEvents()
gone = ["truth", "reviews"]                              # 4.0.0: Drafts' tabs; My Work leaves the effort switcher
w.go("drafts"); app.processEvents()
check("the pages set aside leave the menu", not set(gone) & set(w._tab_keys) and "mywork" not in w.step_btns, w._tab_keys)
check("... production's pages stay; Draft Status is back (4.0.0)", all(w.step_btns[k].isVisible() for k in ("library", "assign", "matrix", "setups", "drafts", "finalcheck", "team"))
      and w._tab_keys == ["drafts", "techedit"], w._tab_keys)
from skqt import frame as _FR
check("... My Work is out of the effort switcher", "My Work" not in [a.text() for a in _FR.effort_menu(w).actions()])
w.go("custqa"); app.processEvents()
check("Data calls leaves Documents' tabs", w._tab_keys == ["library", "compare", "verify", "custqa"], w._tab_keys)
w.go("datacalls"); app.processEvents()
check("... but still opens when asked for (its work is kept)", "datacalls" in w._tab_keys and w.stack.currentWidget() is w.pages["datacalls"])
import unfiled as UF
w.work_on(UF.NAME); w.go("structure"); app.processEvents()
check("Setup's Kickoff packets is set aside", not w.structure_page.b_kickoff.isVisible() and not w.setups_page.a_kickoff.isVisible())
import skqt.toolshome as TH
check("Your Tools never pins a set-aside page", not set(TH.load_pins(cfg, "Author")) & MF.hidden({}),
      TH.load_pins(cfg, "Author"))
modes.save(show_set_aside=True)
w.refresh_access(); w.go("structure"); app.processEvents()
w.go("drafts"); app.processEvents()
check("Show the pages set aside brings them back (3.89.0: not Storyboards, turned off)", set(gone) <= set(w._tab_keys)
      and "storyboards" not in w.step_btns and w.setups_page.a_kickoff.isVisible())
w.go("custqa"); app.processEvents()
check("... and the Data calls tab", w._tab_keys == ["library", "compare", "verify", "custqa", "datacalls"])
modes.save(show_set_aside=False); w.refresh_access()
check("the list keeps a date and a reason for each", all(len(v) == 2 and v[1] for v in MF.SET_ASIDE.values()))

# ---------------------------------------------------------------- leftovers in a setup Make the setup wrote
import docxw, leftovers as LO
d = docxw.Doc(); d.styles = {"rfp": "SKRFPRequirement", "pm": "SKPMDirection"}
d.heading("1 Technical Approach", 1)
d.para("The Offeror shall describe its orbit operations.", kind="rfp")
d.para("Lead with the ground station handover.", kind="pm")
d.para("Our approach keeps the network on station.")
vol = os.path.join(tmp, "Volume I Technical.docx"); d.save(vol)
r = LO.check(vol)
check("the setup's reference paragraphs are found by their style", r["counts"][LO.SETUP] == 2, r["counts"])
w.go("checks"); app.processEvents()
cp = w.checks_page
got = cp.check_leftovers([vol])
check("Final Checks > Leftovers: a file added and checked", got and cp.l_table.rowCount() >= 2 and "setup reference text" in cp.l_sum.text(),
      cp.l_sum.text())
check("... exported", os.path.isfile(cp.export_leftovers(os.path.join(tmp, "left.xlsx"))))
w.go("tools"); app.processEvents()
check("Your Tools offers Check for leftovers for a Word file", "leftovers" in [k for k, _t in TH.uses_for([vol])])
cp.l_table.setRowCount(0)
w.tools_page.run("leftovers", [vol]); app.processEvents()
check("... and runs it on Final Checks", w.stack.currentWidget() is cp and cp.l_table.rowCount() >= 2)

# ---------------------------------------------------------------- file warnings when a file is read
od = os.path.join(tmp, "OneDrive - Kestrel Works"); os.makedirs(od)
os.environ["OneDriveCommercial"] = od
import shutil
synced = os.path.join(od, "Volume I Technical.docx"); shutil.copy(vol, synced)
w.go("techedit"); app.processEvents()
w.techedit_page.add_files([synced], run=True); app.processEvents()
check("a draft in a OneDrive folder says so when read", any("OneDrive" in x for x in getattr(w, "last_file_warnings", [])),
      getattr(w, "last_file_warnings", None))
w.close()
n = sum(checks)
print(f"QT FOCUS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
