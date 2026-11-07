"""3.74.0 offscreen: button use on this PC (decision 4). A button or menu item pressed is counted under its screen, in the
app's words (digits as #, a file name as "(a file)"); kept in button_use.json; nothing in a SCIF-ready install; Settings >
Our data > Button use on this PC... lists it, most pressed first, by screen, exports it, clears it and turns it off."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt import usage as U
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
check("the words counted", U.words("Read 12 document(s)") == "Read # document(s)" and U.words("Kestrel Outline.xlsx") == "(a file)"
      and U.words(r"C:\efforts\x") == "(a file)" and U.words("Choose files...") == "Choose files..." and U.words("") == "")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.usage = U.install(w)
check("installed on the app", w.usage is not None)
w.go("setups"); app.processEvents()
btn = w.setups_page.bar.commands[0]                    # Bring in a file...
w.setups_page.bring_in = lambda *a, **k: None          # the click is what is counted, not the file dialog
btn.clicked.disconnect(); btn.clicked.connect(lambda: None)
QTest.mouseClick(btn, Qt.LeftButton, Qt.NoModifier, QPoint(5, 5)); app.processEvents()
QTest.mouseClick(btn, Qt.LeftButton, Qt.NoModifier, QPoint(5, 5)); app.processEvents()
check("a button pressed is counted under its screen", w.usage.d["counts"].get("setups", {}).get("Bring in a file...") == 2, w.usage.d["counts"])
dis = w.setups_page.b_make
QTest.mouseClick(dis, Qt.LeftButton, Qt.NoModifier, QPoint(5, 5)); app.processEvents()
check("a button that is off is not counted", "Make the setup" not in w.usage.d["counts"].get("setups", {}), w.usage.d["counts"])
w.usage.count(w.usage.screen(w.undo_btn) if hasattr(w, "undo_btn") else "The frame", "Undo")
w.usage.flush()
d = json.load(open(os.path.join(cfg, U.FILE), encoding="utf-8"))
check("kept in button_use.json, format 1, with the day it started", d["format"] == 1 and d["since"] and d["counts"]["setups"]["Bring in a file..."] == 2)
real = U.scif
U.scif = lambda: True
check("nothing is counted in a SCIF-ready install", w.usage.count("setups", "Bring in a file...") is False and U.install(w) is None)
U.scif = real
dlg = w.settings_page.button_use(modal=False); app.processEvents()
check("Settings > Our data > Button use on this PC...: most pressed first", dlg.table.rowCount() >= 2
      and dlg.table.item(0, 1).text() == "Bring in a file..." and dlg.table.item(0, 2).text() == "2" and dlg.table.item(0, 0).text() == "Setup",
      [dlg.table.item(r, 1).text() for r in range(dlg.table.rowCount())])
dlg.pick.setCurrentIndex(dlg.pick.findData("setups")); app.processEvents()
check("... by screen", all(dlg.table.item(r, 0).text() == "Setup" for r in range(dlg.table.rowCount())))
out = dlg.export(os.path.join(tmp, "use.xlsx"))
from openpyxl import load_workbook
ws = load_workbook(out).active
check("... exported to Excel", ws.cell(1, 1).value == "Screen" and ws.cell(2, 2).value == "Bring in a file..." and ws.cell(2, 3).value == 2)
dlg.on.setChecked(False); app.processEvents()
check("... turned off, nothing more is counted", w.usage.count("setups", "Bring in a file...") is False and U.load(cfg)["on"] is False)
dlg.on.setChecked(True); dlg.clear(); app.processEvents()
check("... cleared", dlg.table.rowCount() == 0 and U.load(cfg)["counts"] == {} and U.load(cfg)["on"] is True)
dlg.close()

print(f"QT USAGE 374 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
