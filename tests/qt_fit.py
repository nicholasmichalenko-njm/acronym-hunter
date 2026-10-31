"""3.0.4 Effort Home fits a 1440-pixel screen, offscreen: the window can be made 1440 wide (and smaller), and Effort
Home, for every role's layout, shows with no sideways scroll; the page's description wraps rather than widening it."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effortrec as RR, branding as BR
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def settle(n=10):
    for _ in range(n):
        app.processEvents()


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1760, 1000); w.show()
w.go("home"); settle()
f = w.home_page.start
f.name.setText("Kestrel Thermal Control Subsystem Recompete"); f.client.setText("U.S. Space Force, Space Systems Command")
f.sol.setText("FA8810-26-R-0042"); f.create(); settle()
rec = RR.Record(w.ws.root)
rec.add_task("Draft the thermal design approach for Volume I, including the margin analysis and the test plan", owner="J. Garcia",
             due="2026-11-20", who="jsmith")
rec.add_note("Confirm the page limit for Volume II with the contracts lead before the pink team review.", question=True, who="jsmith")
check("the window can be made 1440 wide", w.minimumSizeHint().width() <= 1440, w.minimumSizeHint().width())
w.resize(1440, 900); settle(20)
hp = w.home_page
for role in BR.ROLE_NAMES:
    hp.customize({"role": role, "order": BR.preset(role)["order"], "hidden": BR.preset(role)["hidden"]})
    w.go("home"); hp.refresh(); settle(20)
    sb = hp.scroll.horizontalScrollBar()
    check(f"Effort Home for {role}: no sideways scroll at 1440", w.width() <= 1440 and sb.maximum() == 0,
          (w.width(), sb.maximum(), hp.scroll.widget().minimumSizeHint().width(), hp.scroll.viewport().width()))
check("the page description wraps rather than widening the window", w.page_sub.wordWrap())
w.resize(1280, 800); settle(20)
check("... and at 1280 too", w.width() <= 1280 and hp.scroll.horizontalScrollBar().maximum() == 0, w.width())
t = sum(checks)
print(f"QT FIT {'PASS' if t == len(checks) else 'FAIL'} ({t}/{len(checks)})")
sys.exit(0 if t == len(checks) else 1)
