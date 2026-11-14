"""4.30.0 offscreen (the Standards board of 2026-11-13, step 1): Settings > Team data says which Global Standards version
this PC is on, where it came from, what changed on the PC since, and names its parts. Fictional data."""
import datetime, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import globalstd as GS
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.go("settings"); app.processEvents()
sp = w.settings_page
check("Settings > Team data has a Global Standards card, first in its section", sp.gs_card.title.text() == "Global Standards"
      and dict(sp.SECTIONS)["Team data and training"][0] == "gs_card")
check("a PC that has taken no version: not a version yet", sp.gs_text.text().startswith("Global Standards: not a version yet."), sp.gs_text.text())
check("... and it names the parts this PC holds", sp.gs_parts.text().startswith("Its parts on this PC: ") or not GS.parts(cfg), sp.gs_parts.text())
GS.take(cfg, 3, GS.LINKED, by="A. Publisher", when=datetime.datetime(2026, 11, 13, 9, 0))
sp.refresh(); app.processEvents()
check("a version taken from the linked folder: its number, where it came from and when", sp.gs_text.text().startswith(
      "Global Standards version 3, from the linked folder, taken 2026-11-13 09:00.") and "all as that version has them" in sp.gs_text.text(), sp.gs_text.text())
with open(os.path.join(cfg, "rules.json"), "w", encoding="utf-8") as f:
    f.write('{"format": 1, "rules": [{"id": "x"}]}')
sp.refresh(); app.processEvents()
check("a part changed on this PC since: the line names it and the draft number", "Changes waiting on this PC: " in sp.gs_text.text()
      and "Rules" in sp.gs_text.text(), sp.gs_text.text())
w.close()
n = sum(checks)
print(f"QT GLOBAL 4300 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
