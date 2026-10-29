"""2.74.0 Stationkeeper.exe is the Qt window: the program's start handles what the classic one did. An effort package
saved in Qt imports in Qt (keep both: a second effort with its own name; use the package: this PC's copy backed up
first); --install-knowledge installs a pack with no window and writes INSTALL OK to the logs; --selftest with sample
files writes the scan report the release smoke test reads; the classic window says it is the classic one."""
import os, sys, tempfile, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.KNOWLEDGE_INFO_FILE = os.path.join(A.CONFIG_DIR, "knowledge_installed.json")
A.KNOWLEDGE_BACKUP_DIR = os.path.join(A.CONFIG_DIR, "knowledge_backups")
A.MODELS_DIR = os.path.join(A.CONFIG_DIR, "models")
A.DB_FILE = os.path.join(tmp, "db.csv"); open(A.DB_FILE, "w", encoding="utf-8").write("Term,Category,Definition,Action\nSOW,Acronym,Statement of Work,Include\n")
A.OCR_FIXES_FILE = os.path.join(A.CONFIG_DIR, "ocr_corrections.csv"); A.OCR_IGNORE_FILE = os.path.join(A.CONFIG_DIR, "ocr_ignore.csv")
A.COMPLIANCE_LEARNED_FILE = os.path.join(A.CONFIG_DIR, "compliance_learned.json")
A.CHOICES_FILE = os.path.join(tmp, "choices.json"); A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
A.LOG_DIR = os.path.join(tmp, "logs")
import effort as E, effortrec as RR
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
import skqt_main

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Heron"); CDIR = os.path.join(EDIR, "Customer documents"); os.makedirs(CDIR)
open(os.path.join(CDIR, "SOW.txt"), "w").write("The contractor shall deliver the bus.")
LIST = os.path.join(EDIR, "Heron_Effort_List.xlsx")
L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CDIR)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron")
pkg = os.path.join(tmp, "Heron.skpkg")
man = w.record_page.save_package(pkg)
check("an effort package saved in Qt", man and os.path.isfile(pkg))
got = w.import_package(pkg, dest=os.path.join(tmp, "PC2"), mode="both")
check("import it in Qt, keep both: a second effort with its own name, opened", got and got["name"].startswith("Heron (from")
      and got["name"] in w.efforts.names() and w.effort_name == got["name"], got and got.get("name"))
check("the second effort's timeline says it came from a package", any("Effort package imported" in e["text"]
                                                                      for e in RR.Record(w.ws.root).events()))
got2 = w.import_package(pkg, dest=os.path.join(tmp, "PC3"), mode="replace")
check("use the package: this PC's copy is backed up first", got2 and got2["name"] == "Heron"
      and glob.glob(os.path.join(EDIR, "*before import*.zip")), glob.glob(os.path.join(EDIR, "*")))
check("Settings has Import effort package", any(b.text() == "Import effort package..." for b in w.settings_page.findChildren(type(w.settings_page.findChildren(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton)[0]))))
w.close()
# --install-knowledge with no window
kp = os.path.join(tmp, "Knowledge.zip")
A.make_knowledge_pack(kp, "test")
rc = skqt_main.main(["Stationkeeper.exe", "--install-knowledge", kp])
log = open(os.path.join(A.LOG_DIR, "knowledge_install.txt"), encoding="utf-8").read()
check("--install-knowledge: installed with no window, INSTALL OK in the logs", rc == 0 and "INSTALL OK" in log, log[-80:])
# the smoke test's scan
doc = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")
import docxw
small = os.path.join(tmp, "s.docx"); d = docxw.Doc(); d.para("The Statement of Work (SOW) is attached."); d.save(small)
A.run_selftest([small])
st = open(os.path.join(A.LOG_DIR, "selftest.txt"), encoding="utf-8").read()
check("--selftest with files writes the scan report the smoke test reads", "SELFTEST OK" in st and "SOW" in st, st[-120:])
src = open(os.path.join(A.BASE_DIR, "skqt_main.py"), encoding="utf-8").read()
check("--selftest passes the sample files to the scan", "A.run_selftest(files)" in src)
spec = open(os.path.join(A.BASE_DIR, "Stationkeeper.spec"), encoding="utf-8").read()
bps = open(os.path.join(A.BASE_DIR, "build.ps1"), encoding="utf-8").read()
check("2.75.0: only the Qt programs are built and allowed in the package", "skqt_main.py" in spec and "skqt_training.py" in spec
      and "Classic' if" not in spec and "classicExe" not in bps)
check("the classic window says it is the classic one", "Stationkeeper (classic)" in open(os.path.join(A.BASE_DIR, "app_gui.py"), encoding="utf-8").read())
n = sum(checks)
print(f"QT MAIN PASS ({n}/{len(checks)})" if n == len(checks) else f"QT MAIN FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
