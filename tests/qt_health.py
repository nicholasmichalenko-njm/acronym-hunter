"""2.80.0 effort health in Qt, offscreen: opening an effort whose matrix was damaged puts back its newest good copy and
says so; Effort record > Effort health lists what is left with a fix for each; Find the folder repoints a moved
customer documents folder; a live effort in a folder OneDrive uploads moves to this PC with one button (through its
package, the old copy backed up); Settings > Your data says where the data lives; new efforts default to its Efforts
folder."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.LOG_DIR = os.path.join(tmp, "logs")
OD = os.path.join(tmp, "OneDrive - Sierra Space"); os.makedirs(OD)
os.environ["OneDriveCommercial"] = OD
import compliance as C, effort as E, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox, QLabel
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(OD, "Efforts", "Heron"); os.makedirs(os.path.join(ED, "Customer documents"))
LIST = os.path.join(ED, "Heron_Effort_List.xlsx")
L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=os.path.join(tmp, "moved away"))
M = C.Matrix(os.path.join(ED, "Heron_Compliance_Matrix.xlsx"), "Heron")
M.items = C.extract([("Section L.docx", [("Page 1", "The Offeror shall describe the thermal design. The Offeror shall provide the schedule.")])])
M.save()
ws0 = W.Workspace(W.data_dir_for(LIST), "Heron"); ws0.set("compliance_path", M.path); ws0.backup(M.path, "matrix", force=True)
open(M.path, "wb").write(b"damaged by a sync conflict")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron")
check("a damaged matrix: its newest good copy is put back on opening, and it says so", w.review is not None and len(w.review.M.items) == 2
      and "newest good copy was put back" in w.statusBar().currentMessage() and any("(damaged" in f for f in os.listdir(ED)))
w.go("record"); app.processEvents()
rp = w.record_page
texts = " ".join(l.text() for l in rp.health.findChildren(QLabel))
check("Effort health lists what is left: the moved folder and the synced live effort", "customer documents folder is not where it was" in texts
      and "folder OneDrive uploads" in texts, texts[:300])
rp.fix("find_customer", os.path.join(ED, "Customer documents"))
check("Find the folder repoints it", w.efforts.get("Heron")["customer_dir"] == os.path.join(ED, "Customer documents")
      and not any(i["kind"] == "customer_moved" for i in w.safety.issues))
LOCAL = os.path.join(tmp, "Stationkeeper Data", "Efforts")
w.presence_answer = "open"
new_list = rp.fix("move_local", LOCAL)
check("Move to this PC: the effort now lives locally and is open there", new_list and new_list.startswith(LOCAL)
      and w.effort_path == new_list and os.path.isfile(new_list) and len(w.review.M.items) == 2, new_list)
check("the old copy was backed up first and left in place", os.path.isfile(LIST) and any("before import" in f for f in os.listdir(os.path.dirname(ED)) + os.listdir(ED)))
check("after the move, no synced-folder warning", not any(i["kind"] == "live_synced" for i in w.safety.health()[0]))
# check before overwrite: another copy saved the matrix meanwhile
mp = w.review.M.path
time.sleep(1.1)
other = C.Matrix(mp).load(); other.items[1]["notes"] = "saved on another PC"; other.save()
w.review.req([w.review.M.items[0]], ""); w.review.M.items[0]["notes"] = "mine"; w.changed()
w.safety.conflict_answer = "theirs"
w.save_now()
here = os.listdir(os.path.dirname(mp))
check("the matrix changed on disk: Open theirs keeps yours as a copy beside it", any("(yours " in f for f in here)
      and w.review.item(other.items[1]["id"]).get("notes") == "saved on another PC", here)
time.sleep(1.1)
other = C.Matrix(mp).load(); other.items[1]["notes"] = "second outside save"; other.save()
w.review.M.items[0]["notes"] = "mine again"; w.changed()
n0 = len(w.ws.backups("matrix"))
w.safety.conflict_answer = "mine"
w.save_now()
check("Keep mine: yours is saved, theirs kept as a dated copy", C.Matrix(mp).load().items[0].get("notes") == "mine again"
      and len(w.ws.backups("matrix")) == n0 + 1)
w.go("settings"); app.processEvents()
check("Settings > Your data says where the data lives", "Your data is in" in w.settings_page.data_text.text())
src = open(os.path.join(A.BASE_DIR, "skqt", "settingspage.py"), encoding="utf-8").read()
check("new efforts default to the data folder's Efforts", "datahome.efforts_dir(app_gui.DATA_DIR)" in src)
w.close()
n = sum(checks)
print(f"QT HEALTH PASS ({n}/{len(checks)})" if n == len(checks) else f"QT HEALTH FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
