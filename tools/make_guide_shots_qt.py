"""The Guide's pictures (3.0.2): one picture of each page, from a fictional effort, for skqt/guide.py.

    venv\\Scripts\\python.exe tools\\make_guide_shots_qt.py            (on the Windows build PC; no screen needed)

Builds the fictional effort Kestrel Thermal from test_samples\\rfp in a neutral folder (C:\\SK Guide, or SK_GUIDE_ROOT),
as user jsmith on TEAM-PC, reads the RFP, decides some sentences, adds a few tasks, questions, customer questions,
evaluation factors and a deliverable, then shows every page offscreen and saves assets\\help\\guide_<topic>.png.
Run it only when the user asks for new Guide pictures, never on every build."""
import os, platform, shutil, sys, tempfile, time
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR); sys.path.insert(0, os.path.join(ROOT_DIR, "tests"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
if os.name == "nt":                                       # offscreen Qt on Windows finds no fonts by itself
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_shots"
for _k in ("LOGNAME", "USER", "LNAME", "USERNAME"):        # the pictures show a neutral user and PC, never this PC's
    os.environ[_k] = "jsmith"
platform.node = lambda: "TEAM-PC"
import getpass
getpass.getuser = lambda: "jsmith"

OUT = os.environ.get("SK_SHOTS_OUT") or os.path.join(ROOT_DIR, "assets", "help")
BASE = os.environ.get("SK_GUIDE_ROOT") or (r"C:\SK Guide" if os.name == "nt" else os.path.join(tempfile.gettempdir(), "SK Guide"))
shutil.rmtree(BASE, ignore_errors=True)
try:
    os.makedirs(BASE)
except OSError:
    BASE = os.path.join(tempfile.mkdtemp(), "SK Guide"); os.makedirs(BASE)
os.environ["SK_DATA_DIR"] = os.path.join(BASE, "Stationkeeper Data")

import app_gui as A
import effort as E, effortrec as RR, custqa as Q, custfocus as F, deliverables as DL, workspace as W
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtTest import QTest
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import theme
from skqt.mainwin import MainWindow
from skqt import guide as GD

cfg = os.path.join(BASE, "Stationkeeper Data", "config"); os.makedirs(cfg, exist_ok=True)
EDIR = os.path.join(BASE, "Kestrel Thermal")
CUST = os.path.join(EDIR, "Customer Documents"); os.makedirs(CUST)
for f in os.listdir(os.path.join(ROOT_DIR, "test_samples", "rfp")):
    shutil.copy2(os.path.join(ROOT_DIR, "test_samples", "rfp", f), CUST)
LIST = os.path.join(EDIR, "Kestrel_Thermal_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel Thermal", client="U.S. Space Force, Space Systems Command", solicitation="FA8810-26-R-0042")
L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel Thermal", path=LIST, customer_dir=CUST)
ws = W.Workspace(W.data_dir_for(LIST), "Kestrel Thermal")
ws.set("outline_text", "Volume I Technical\n1.1 Thermal Design\n1.2 Risk Management\nVolume II Management\n2.1 Schedule\n2.2 Staffing")
A.save_settings(dict(A.load_settings() or {}, work_mode="offline", time_zone="America/Denver"))   # a mode is set: no "Mode not set" chip
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 1000); w.show()


def wait(cond, secs=180):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.03)
    return cond()


def settle(n=12):
    for _ in range(n):
        app.processEvents(); time.sleep(0.02)


made = []


def shot(key, page=None):
    if page:
        w.go(page)
    settle()
    if page == "assign":                                   # the page copy (Word, on the PC) draws a moment later
        wait(lambda: len(getattr(pg.view, "boxes", {}) or {}) > 0, 120)
        settle(40)
    p = os.path.join(OUT, f"guide_{key}.png")
    w.grab().save(p)
    made.append(os.path.basename(p))


w.open_effort("Kestrel Thermal")
rec = RR.Record(w.ws.root)
import branding as BR
BR.set_identity(rec, pm="A. Rivera", sensitivity="Proprietary", who="jsmith")
rec.set_due("2026-12-15T14:00", zone="America/New_York") if hasattr(rec, "set_due") else None
# the documents, read
docs = [os.path.join(CUST, f) for f in sorted(os.listdir(CUST))]
w.read_page.read(docs, os.path.join(EDIR, "Kestrel_Thermal_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None)
M = w.review.M
pg = w.assign_page
w.go("assign"); settle()
import compliance as C
secs = [C.outline_label(o) for o in M.outline]
done = 0
for it in M.items:                               # a believable start: some decided, most still to do
    t = it["text"]
    if done >= 14 or " shall " not in f" {t} ":
        continue
    key = Qt.Key_R if "contractor shall" in t.lower() else (Qt.Key_E if "evaluat" in t.lower() else Qt.Key_L)
    pg.set_target(secs[(done % (len(secs) - 1)) + 1] if len(secs) > 1 else secs[0])
    pg.select(it["id"]); settle(3)
    QTest.keyClick(pg.view, key); settle(3)
    done += 1
# the effort's work
rec = RR.Record(w.ws.root)
rec.add_task("Draft the thermal design approach", owner="J. Garcia", due="2026-11-20", who="jsmith")
rec.add_task("Build the integrated master schedule", owner="M. Chen", due="2026-11-24", who="jsmith")
rec.add_note("Confirm the page limit for Volume II with the contracts lead.", question=True, who="jsmith")
rec.add_note("Kickoff held; volumes assigned.", who="jsmith")
first = next((it for it in M.items if " shall " in f" {it['text']} "), M.items[0])
Q.add(rec, "Will the Government accept thermal analysis results in Excel format?", first["text"][:200],
      doc=os.path.basename(docs[0]), section="L.4", page="3", para="2", category="Technical", owner="J. Garcia", who="jsmith")
Q.add(rec, "Is the integrated master schedule due with the proposal or after award?", "", doc=os.path.basename(docs[-1]),
      section="L.5", category="Schedule", owner="M. Chen", who="jsmith")
F.add_factor(rec, "Technical Approach", importance="Significantly more important", source={"doc": os.path.basename(docs[0])})
F.add_factor(rec, "Past Performance", importance="Pass/fail")
F.add_hot(rec, "Thermal margin under worst-case loads", quote="The Government places emphasis on thermal margin.")
DL.add(rec, "Volume I Technical", kind="Volume", owner="J. Garcia", limit="40 pages", who="jsmith")
DL.add(rec, "CDRL A003 Integrated Master Schedule", owner="M. Chen", who="jsmith")
w.close_effort(); settle()
w.open_effort("Kestrel Thermal"); settle(30)
# every page
pages = {t[0] for t in GD.TOPICS} & set(w.pages)
for key in [t[0] for t in GD.TOPICS]:
    if key in pages:
        shot(key, key)
shot("start", "home")
shot("safe", "record")
w.close_effort(); settle()
w.go("efforts"); shot("efforts")
print("GUIDE SHOTS:", len(made), "pictures in", OUT)
print(", ".join(made))
shutil.rmtree(BASE, ignore_errors=True)
