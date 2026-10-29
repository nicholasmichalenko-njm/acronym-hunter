"""2.90.0 an effort's folders in Qt, offscreen: New effort makes Customer Documents, Volumes, Response Setup and Exports
and uses the first two as the effort's customer documents and volumes folders; opening the effort leaves a note in its
app data folder; Open effort folder; saves start in the effort's Exports folder."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effortfolders as EF, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.show()
LIST = os.path.join(tmp, "Efforts", "Heron", "Heron_Effort_List.xlsx")
w.settings_page.new_effort({"name": "Heron", "path": LIST, "first_use": "volume"})
root = os.path.dirname(LIST)
check("a new effort gets its four folders", all(os.path.isdir(os.path.join(root, n)) for n in EF.SUBS.values()), os.listdir(root))
info = w.efforts.get("Heron")
check("its customer documents and volumes folders are its own", info["customer_dir"] == os.path.join(root, "Customer Documents")
      and info["volumes_dir"] == os.path.join(root, "Volumes"))
check("the effort's app data folder has its note", os.path.isfile(os.path.join(W.data_dir_for(LIST), EF.NOTE)))
check("Open effort folder: the effort's folder", w.open_effort_folder() == root and w.open_effort_folder("exports") == os.path.join(root, "Exports"))
x = w.home_page.calfiles.export("xlsx", EF.out(w.effort_path, "Heron_Calendar.xlsx"))
check("saves start in Exports", os.path.isfile(os.path.join(root, "Exports", "Heron_Calendar.xlsx")) and x)
L2 = os.path.join(tmp, "Elsewhere", "Osprey_Effort_List.xlsx"); CD = os.path.join(tmp, "Their docs"); os.makedirs(CD)
w.settings_page.new_effort({"name": "Osprey", "path": L2, "customer_dir": CD})
check("a folder the person picks stays theirs", w.efforts.get("Osprey")["customer_dir"] == CD)
w.close()
n = sum(checks)
print(f"QT FOLDERS PASS ({n}/{len(checks)})" if n == len(checks) else f"QT FOLDERS FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
