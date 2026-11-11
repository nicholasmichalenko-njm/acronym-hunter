"""4.9.0 offscreen: the window publishes the effort data for Stationkeeper Macros on its 3-second timer: the first
snapshot when an effort without one opens, then only after something it is made from changed. Fictional (Kestrel)."""
import json, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_EFFORTDATA_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import banned as B, effort as E, effortdata as ED
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show()
w.open_effort("Kestrel"); app.processEvents()
man_p = os.path.join(ED.folder(LIST), "manifest.json")


def wait(cond, secs=40):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.05)
    return cond()


check("opening an effort with no snapshot publishes the first one on the timer", wait(lambda: os.path.isfile(man_p))
      and json.load(open(man_p, encoding="utf-8"))["revision"] == 1)
check("... named for the effort, written by this version", json.load(open(man_p, encoding="utf-8"))["effort"]["name"] == "Kestrel"
      and json.load(open(man_p, encoding="utf-8"))["writer"]["app_version"] == A.APP_VERSION)
time.sleep(3.5); app.processEvents()
check("nothing changed: no new revision", json.load(open(man_p, encoding="utf-8"))["revision"] == 1)
B.save(B.load() + [{"Phrase": "game-changer", "Level": "Avoid", "Use instead": "", "Why": "Jargon"}])
check("a phrase saved: published again within seconds", wait(lambda: json.load(open(man_p, encoding="utf-8"))["revision"] == 2))
w.close()
print(f"QT EFFORTDATA 490 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
