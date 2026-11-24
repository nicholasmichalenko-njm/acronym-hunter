"""4.65.0 offscreen (Nicholas 2026-11-23): Drafts opens on Acronyms; Status, Edit and the rest are the tabs after it;
nothing is removed. Fictional (Merlin)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
import skqt.mainwin as MW
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Merlin"); os.makedirs(ED)
LIST = os.path.join(ED, "Merlin_Effort_List.xlsx"); L = E.EffortList(LIST, "Merlin"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Merlin", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Merlin")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Merlin"); app.processEvents()
keys = [k for k, _t in MW.TABS["drafts"]]
check("Acronyms is the first of Drafts' tabs, and every tab it had is still there", keys[0] == "draftacr"
      and sorted(keys) == sorted(["drafts", "draftacr", "techedit", "reviews", "truth", "markups"]), keys)
w.step_btns["drafts"].click(); app.processEvents()
check("the Drafts entry opens Acronyms", w.stack.currentWidget() is w.draftacr_page and w.step_btns["drafts"].isChecked()
      and w.page_title.text() == "Drafts" and w._tab_keys[0] == "draftacr" and w.page_tabs.currentIndex() == 0, w._tab_keys)
check("Status is the tab after it", w._tab_keys[1] == "drafts" and w.page_tabs.tabText(1) == "Status", w._tab_keys)
w.page_tabs.setCurrentIndex(1); app.processEvents()
check("... and still opens", w.stack.currentWidget() is w.drafts_page and w.step_btns["drafts"].isChecked())
w.go("drafts"); app.processEvents()
check("a link to Draft Status from another page still lands on Status", w.stack.currentWidget() is w.drafts_page)
w.close()
print(f"QT DRAFTS 4650 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
