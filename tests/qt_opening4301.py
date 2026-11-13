"""4.30.1 offscreen (Nicholas 2026-11-13 14:21): a small window says Stationkeeper is opening while the main window is
built, so nobody double-clicks again. It has no buttons, shows before the main window and goes when that shows."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractButton, QApplication
from skqt import design as D, opening as OP

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


app = QApplication([]); D.apply(app, "light")
w = OP.show(app, "4.30.1", A.asset_path("scanner.ico") or "")
check("the window shows at once, on top, with no frame", w is not None and w.isVisible() and bool(w.windowFlags() & Qt.WindowStaysOnTopHint)
      and bool(w.windowFlags() & Qt.FramelessWindowHint))
check("it says the app is opening and that there is no need to click again", w.title.text() == "Stationkeeper is opening"
      and "no need to click again" in w.says.text() and w.ver.text() == "Version 4.30.1", (w.title.text(), w.says.text()))
check("a bar shows it is working, with no end to count to", w.bar.minimum() == 0 and w.bar.maximum() == 0)
check("it has no buttons: nothing to click", w.findChildren(QAbstractButton) == [])
check("it goes when the main window is up", OP.done(w) is None and not w.isVisible())
src = open(os.path.join(os.path.dirname(HERE), "skqt_main.py"), encoding="utf-8").read()
check("the program shows it before it builds the main window and closes it after the window shows",
      src.index("_OP.show(app") < src.index("w = MainWindow(app, A.CONFIG_DIR") < src.index("_OP.done(opening)\n    from skqt.usage"))
check("the build's own start check does not show it", '"--selftest" not in args:                     # 4.30.1' in src)
check("a window that cannot be shown never stops the app", OP.show(None) is None and OP.done(None) is None)
n = sum(checks)
print(f"QT OPENING 4301 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
